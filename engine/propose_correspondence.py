"""The LM proposal loop: holes -> proposals -> the one inlet -> the engine disposes.

Demand-driven, not exhaustive. `engine/holes.py` enumerates where the base category is
missing a morphism; this module shows those candidate pairs to a proposer, turns each answer
into a **correspondence claim**, and enters it through `FastTape.propose` at EXTRACTION tier.
Nothing here writes structure: the arrows become structure only by being derived back off the
accepted claims (`engine/correspondence.correspondences_from_deltas`), so the single
write-path is intact and `tests/test_inlet.py` still covers this path.

`"none"` is a legal and expected answer. The prompt says so explicitly, and a proposer that
returns `none` for every candidate is behaving correctly on a corpus with no real bridges —
forcing matches is exactly how a similarity engine gets rebuilt by accident.

The engine then disposes: settlement over the provisional structure, clamp conflict and loop
closure deciding survival. K promotes nothing below AUTHORSHIP.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Sequence

from .correspondence import CORRESPONDENCE_CHART, KINDS, Correspondence
from .holes import Hole
from .normalize import address
from .types import Delta, Provenance, Slot, Warrant, WarrantTier

PROPOSE_SYSTEM = (
    "You propose CORRESPONDENCES between claims that live in different charts of a "
    "reconciliation engine. You are shown pairs of normalized claim surfaces. For each pair "
    "decide the relation from the SOURCE claim to the TARGET claim:\n"
    "  same_claim   — they assert the SAME proposition (an isomorphism class)\n"
    "  refines      — the source is a strictly more specific form of the target (directed)\n"
    "  instance_of  — the source is a particular instance of the target's general form\n"
    "  none         — no correspondence. THIS IS A LEGAL AND EXPECTED ANSWER.\n\n"
    "Do NOT force matches. Superficial word overlap is NOT a correspondence; two claims that "
    "merely share vocabulary, or a claim and its NEGATION, are `none`. If you are unsure "
    "whether it is the same claim, answer same_claim only if you can cite the evidence that "
    "makes them the same; otherwise answer none — your uncertainty is recorded as warrant, "
    "not as a weaker relation.\n\n"
    "Return ONLY JSON: {\"answers\":[{\"i\":int,\"kind\":one of "
    "['same_claim','refines','instance_of','none'],\"evidence\":str}]} where `i` is the "
    "candidate index and `evidence` quotes the spans that justify the answer."
)


@dataclass(frozen=True, slots=True)
class ProposalOutcome:
    hole: Hole
    kind: str
    evidence: str

    @property
    def is_arrow(self) -> bool:
        return self.kind in KINDS


def render_candidates(holes: Sequence[Hole]) -> str:
    """The prompt body: candidate pairs with their nu-strings, indexed."""
    lines = []
    for i, h in enumerate(holes):
        lines.append(
            f"[{i}] type={h.type}\n"
            f"  SOURCE ({h.src_chart}): {h.src_nu[:400]}\n"
            f"  TARGET ({h.dst_chart}): {h.dst_nu[:400]}"
        )
    return "\n\n".join(lines)


def _json_block(raw: str) -> object:
    """Tolerant JSON extraction — bare object or ```json fence. Stdlib only.

    Kept here rather than imported from `ui/` so the engine has no dependency on the window.
    """
    import re

    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = min((i for i in (text.find("{"), text.find("[")) if i != -1), default=-1)
    if start == -1:
        return {}
    # strict=False: the proposer quotes the corpus back, and a nu-string carries the \x01
    # chart tag as a literal control character. Strict JSON forbids an unescaped control
    # character inside a string, so a faithful quotation of our own normalized surface would
    # otherwise be unparsable — which is a defect in the reader, not in the answer.
    try:
        return json.loads(text[start:], strict=False)
    except json.JSONDecodeError:
        pass
    end = max(text.rfind("}"), text.rfind("]"))
    try:
        return json.loads(text[start:end + 1], strict=False) if end > start else {}
    except json.JSONDecodeError:
        return {"answers": _salvage_objects(text)}


def _salvage_objects(text: str) -> list[dict]:
    """Recover the COMPLETE answer objects from a reply whose array was cut off mid-write.

    A proposer answering 25 candidates with cited evidence can exhaust the token budget
    partway through, leaving `{"answers": [ {...}, {...}, {"i": 7, "kind": "no` — strictly
    invalid, but the objects before the cut are fully specified and were genuinely answered.
    Dropping all of them would silently discard real answers and leave those candidates
    looking unasked.

    Every complete brace-balanced object is parsed on its own; the truncated tail is DROPPED
    and never completed. Nothing is inferred about the answer that was being written.
    """
    out: list[dict] = []
    starts: list[int] = []          # a STACK, because the answer objects are nested inside
    in_string = False               # the outer `{"answers": [...]}` which never closes
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            starts.append(i)
        elif ch == "}" and starts:
            begin = starts.pop()
            try:
                obj = json.loads(text[begin:i + 1], strict=False)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "i" in obj and "kind" in obj:
                out.append(obj)
    return out


def parse_answers(raw: str, holes: Sequence[Hole]) -> list[ProposalOutcome]:
    """Tolerant parse; anything unparseable or out-of-range is dropped, never guessed."""
    payload = _json_block(raw)
    if isinstance(payload, dict):
        answers = payload.get("answers", [])
    elif isinstance(payload, list):
        answers = payload      # a proposer that returned the bare array without the wrapper
    else:
        answers = []
    out: list[ProposalOutcome] = []
    for a in answers:
        # A tolerant parser has to tolerate ANY shape, not just the wrong-but-dict shapes.
        # A proposer returned `{"answers": [0, 1, 2]}` on the real corpus and this function
        # raised `AttributeError` on the bare int, which killed an unattended process that
        # had been running for ninety minutes. Anything that is not a mapping is not an
        # answer, and is dropped like every other unparseable thing here.
        if not isinstance(a, dict):
            continue
        try:
            i = int(a.get("i", -1))
        except (TypeError, ValueError):
            continue
        kind = str(a.get("kind", "none"))
        if not (0 <= i < len(holes)) or kind not in (KINDS | {"none"}):
            continue
        out.append(ProposalOutcome(hole=holes[i], kind=kind,
                                   evidence=str(a.get("evidence", ""))[:300]))
    return out


def as_correspondence_delta(
    outcome: ProposalOutcome,
    proposer: str,
    prompt_hash: str,
    tier: WarrantTier = WarrantTier.EXTRACTION,
) -> Delta:
    """Turn an accepted answer into a correspondence CLAIM, ready for the inlet.

    The claim is an ordinary delta in the `correspondence` chart, so it is addressed exactly
    (gate 1) and valued over its own content (gate 8). The tier defaults to EXTRACTION: an LM
    proposal is a proposal. The operator's confirmation re-enters as a separate claim at
    AUTHORSHIP; it does not mutate this one.
    """
    h = outcome.hole
    arrow = Correspondence(
        src_chart=h.src_chart, src_slot=h.src_slot,
        dst_chart=h.dst_chart, dst_slot=h.dst_slot,
        kind=outcome.kind, tier=tier, proposer=proposer,
        prompt_hash=prompt_hash, evidence=(outcome.evidence,),
    )
    surface = arrow.surface()
    slot, nu_value = address(CORRESPONDENCE_CHART, surface, "assert")
    return Delta(
        slot=slot, chart=CORRESPONDENCE_CHART, type="assert", value="T",
        confidence=0.6,
        warrant=Warrant(tier=tier, detail=f"correspondence proposal by {proposer}"),
        provenance=Provenance(
            source="correspondence-proposer", doc_id=f"corr:{arrow.id()}",
            locator=outcome.evidence[:120] or "(no evidence cited)",
            extractor_id=proposer, content_hash=prompt_hash,
        ),
        surface=surface, nu=nu_value,
    )


Transport = Callable[[str, str], str]      # (system, user) -> raw completion


def propose_over_holes(
    holes: Sequence[Hole],
    tape,
    transport: Transport,
    proposer: str = "lm",
    prompt_hash: str = "",
    batch: int = 25,
    source_tag: str = "lm",
) -> tuple[list[ProposalOutcome], list[Delta]]:
    """Run the loop: batched candidates -> proposer -> the ONE inlet.

    Returns `(all_outcomes, entered_deltas)`. `none` answers are kept in the outcomes (they
    are information about the corpus) but produce no claim and enter nothing.
    """
    outcomes: list[ProposalOutcome] = []
    entered: list[Delta] = []
    for start in range(0, len(holes), batch):
        chunk = list(holes[start:start + batch])
        raw = transport(PROPOSE_SYSTEM, render_candidates(chunk))
        for outcome in parse_answers(raw, chunk):
            outcomes.append(outcome)
            if not outcome.is_arrow:
                continue
            delta = as_correspondence_delta(outcome, proposer, prompt_hash)
            tape.propose(delta, source_tag)      # the single write-path, EXTRACTION tier
            entered.append(delta)
    return outcomes, entered


# ---- the review surface: where the operator's confirmations buy the most --------------

@dataclass(frozen=True, slots=True)
class ReviewItem:
    arrow: Correspondence
    loops_closed: int
    src_nu: str
    dst_nu: str

    def as_record(self) -> dict[str, object]:
        return {**self.arrow.as_record(), "loops_closed": self.loops_closed,
                "src_nu": self.src_nu[:160], "dst_nu": self.dst_nu[:160]}


def review_list(
    arrows: Sequence[Correspondence],
    slots: Sequence[Slot],
) -> list[ReviewItem]:
    """Provisional arrows ranked by STRUCTURAL IMPACT — how many loops each would close.

    Confirmations are scarce and expensive (they are the operator's own attention), so the
    list is sorted by what each one buys: the number of holonomy cycles that come into
    existence if this arrow is confirmed. An arrow that closes no cycle is still listed, last,
    because it is still structure — it just does not yet buy a floor.
    """
    from .blocks import build_loop_fibers, edges_from_fibers, loops_from_fibers

    nu_of = {s.id: s.nu for s in slots}
    chart_of = {s.id: s.chart for s in slots}
    active = {s.id for s in slots}

    def loop_count(subset: Sequence[Correspondence]) -> int:
        fibers = build_loop_fibers(list(slots), subset)
        edges = edges_from_fibers(fibers, list(slots))
        return len(loops_from_fibers(fibers, chart_of, restrict_to=active, edges=edges))

    provisional = [a for a in arrows if a.provisional]
    base = loop_count(arrows)
    out: list[ReviewItem] = []
    for a in provisional:
        without = [b for b in arrows if b is not a]
        out.append(ReviewItem(
            arrow=a, loops_closed=max(0, base - loop_count(without)),
            src_nu=nu_of.get(a.src_slot, ""), dst_nu=nu_of.get(a.dst_slot, ""),
        ))
    out.sort(key=lambda r: (-r.loops_closed, r.arrow.id()))
    return out


def confirm(arrow: Correspondence, tape, source_tag: str = "me") -> Delta:
    """The operator's confirmation — a SEPARATE claim at AUTHORSHIP tier, through the inlet.

    It does not mutate the LM's proposal; it is its own assertion of the same arrow, and the
    two collide on one address, so the confirmation raises the tier of what that address
    asserts rather than editing anyone's earlier claim.
    """
    surface = arrow.surface()
    slot, nu_value = address(CORRESPONDENCE_CHART, surface, "assert")
    delta = Delta(
        slot=slot, chart=CORRESPONDENCE_CHART, type="assert", value="T", confidence=1.0,
        warrant=Warrant(tier=WarrantTier.AUTHORSHIP, detail="operator confirmation"),
        provenance=Provenance(source="operator", doc_id=f"corr:{arrow.id()}",
                              locator="confirmed", extractor_id=source_tag,
                              content_hash=arrow.id()),
        surface=surface, nu=nu_value,
    )
    return tape.propose(delta, source_tag)
