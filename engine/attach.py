"""How a BIAS reaches the field. It is proposed and gated, exactly like every other arrow.

The defect this fixes was inherited, not designed. Gate 1 says two CLAIMS are the same claim
iff `hash(nu(surface), type)` agrees, and that is right. A bias is not a claim, and how a bias
attaches to the field was never specified — so the implementation reused the addressing rule
because it was the rule that was there. The consequence: typed text that did not already exist
verbatim in the corpus attached to nothing, propagated nowhere, and the window reported that a
69,000-slot corpus had not responded. Correct under the rule it inherited, and the wrong rule.

Attachment is a CORRESPONDENCE. The typed claim and a corpus claim either correspond or they
do not, and that question already has a mechanism: the same proposer, the same prompt, the
same three kinds, with `none` legal and expected. So:

    typed text -> addressed like any claim (gate 1, unchanged)
               -> the proposer is asked which corpus claims it corresponds to
               -> accepted proposals are Correspondences at EXTRACTION tier
               -> those attachment points are handed to `engine/relax` as seeds
               -> everything downstream travels declared arrows only

No string is ever compared. The proposer reads two claims and judges; superficial word overlap
is explicitly `none` in its instructions, and a bias that attaches to nothing is a field that
genuinely did not respond rather than a search that missed.

**Which candidates it is shown, and why that is not selection by another name.** The corpus is
too large to ask about exhaustively, so candidates are ordered — and the ordering is by
DECLARED DEGREE, the number of correspondences already touching a slot. That is a property of
the arrow graph, not of any text: it compares nothing, it reads no surface, and it prefers the
claims a perturbation could actually travel from, since a slot no arrow touches can only ever
report that nothing moved. What the budget does not reach is COUNTED and reported as
unmeasured, never as absent.

**Attachment is cross-chart, and that is constitutional rather than incidental.** A
correspondence between two claims in one chart is refused by `engine/correspondence`, because
exact addressing already owns intra-chart identity and an intra-chart arrow would reintroduce
similarity by the back door. So a claim typed in the english chart attaches to lean, python,
go, tabular or conversation claims, and reaches english claims through them. That is the
engine working as specified, not a limitation of this file.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — a proposer into D, for attaching a typed object.
Q2 motivated it. A typed input is an OBJECT WITH NO MORPHISMS until morphisms are proposed
for it; it has no image under any functor, lies outside the fundamental groupoid, and
cannot propagate. Nothing will move no matter how the code is tuned. The fix is to propose
morphisms, which is what this module does.
Q5 checked: this creates NO second mechanism. It is the SAME proposer, prompt and three
kinds the corpus's own arrows use — a different job, not a different rule.

"""

from __future__ import annotations

from dataclasses import dataclass, field

from .correspondence import Correspondence
from .corpus_state import CorpusSnapshot
from .holes import Hole
from .propose_correspondence import render_candidates
from .types import WarrantTier

#: Candidate pairs per call. The daemon's batch; kept the same so the prompt the attachment
#: proposer sees is the prompt the corpus proposer sees, down to the shape of the body.
BATCH = 12

#: Calls one attachment may spend. A question is interactive, so this is a latency and cost
#: budget, and what it does not reach is reported as unmeasured rather than treated as none.
CALL_BUDGET = 4

#: Attachment enters at EXTRACTION, like every LM proposal. It cannot ground and cannot clamp.
ATTACH_TIER = WarrantTier.EXTRACTION

#: The BIAS relation. Not a corpus morphism — the base's kinds stay exactly three.
#:
#: A topic or a question cannot correspond to anything: "does `holonomy` state the same
#: proposition as this Lean theorem?" has one correct answer forever, so asking the identity
#: question of a bias guarantees `none` and the field is never reached. The aboutness question
#: is a different question, and it gets a different relation.
#:
#: `bears_on` is EPHEMERAL. It conditions one perturbation and then it is gone: never
#: journalled, never composable, never counted as an arrow, never in the atlas. It is a
#: boundary condition, not structure. Q5-clean because it is the SAME proposer through the
#: SAME path — asked the identity question for claims and the aboutness question for a bias.
BEARS_ON = "bears_on"

#: The kinds an ATTACHMENT may return. The first three are real correspondences and become
#: arrows; `bears_on` seeds the relaxation and evaporates.
ATTACH_KINDS = ("same_claim", "refines", "instance_of", BEARS_ON)

ATTACH_SYSTEM = (
    "A reconciliation engine holds a corpus of CLAIMS across charts (english prose, lean, "
    "python, go, tabular, conversation). You are shown one INPUT and a numbered list of "
    "corpus claims. The input may be a claim, a question, or a bare topic — it is a boundary "
    "condition, not necessarily an assertion.\n\n"
    "For each candidate, say how the input relates to it:\n"
    "  same_claim   — the input asserts the SAME proposition as the candidate\n"
    "  refines      — the input is a strictly more specific form of the candidate\n"
    "  instance_of  — the input is a particular instance of the candidate's general form\n"
    "  bears_on     — the input is ABOUT what the candidate is about: a question this claim "
    "would help answer, or a topic this claim falls under. Use this for questions and topics; "
    "they assert nothing, so they cannot correspond, but they can still be about something.\n"
    "  none         — unrelated. Legal and expected for most candidates.\n\n"
    "Do not force a relation. Shared vocabulary is not aboutness: a claim that merely uses "
    "the same words as the input, without bearing on it, is `none`.\n\n"
    'Return ONLY JSON: {"answers":[{"i":int,"kind":one of '
    "['same_claim','refines','instance_of','bears_on','none'],\"evidence\":str}]}."
)


@dataclass(frozen=True, slots=True)
class Attachment:
    """One proposed bridge from the typed input into the corpus, accepted or not."""

    kind: str                                 # same_claim | refines | instance_of | none
    dst_slot: str
    dst_chart: str
    dst_nu: str
    evidence: str
    tier: str = ATTACH_TIER.name

    @property
    def accepted(self) -> bool:
        return self.kind != "none"

    @property
    def is_bias_only(self) -> bool:
        """`bears_on` conditions the perturbation and never becomes structure."""
        return self.kind == BEARS_ON

    def as_record(self) -> dict[str, object]:
        return {"kind": self.kind, "accepted": self.accepted, "tier": self.tier,
                "to": self.dst_slot[:16], "chart": self.dst_chart,
                "nu": self.dst_nu[:220], "evidence": self.evidence[:400]}


@dataclass(slots=True)
class AttachResult:
    """What the proposer said about the typed input, in full. The bridge, not just the result."""

    typed_slot: str = ""
    typed_chart: str = ""
    typed_nu: str = ""
    proposed: list[Attachment] = field(default_factory=list)
    considered: int = 0                       # candidate pairs actually asked about
    available: int = 0                        # candidates the corpus offered
    calls: int = 0
    budget_exhausted: bool = False
    error: str = ""

    @property
    def accepted(self) -> list[Attachment]:
        return [a for a in self.proposed if a.accepted]

    @property
    def seeds(self) -> set[str]:
        """Where the bias actually attached. `engine/relax` takes these as its starting set.

        This module proposes attachment and does nothing else. Gate 10 caught an earlier
        wording here that described this file as performing the settling, which it does not;
        the check was right, and the phrasing changed rather than the check.

        Note for anyone tempted to quote the offending sentence back into a docstring: the
        check cannot distinguish a phrase asserted from a phrase quoted, and it should not
        try. Naming the defect without reproducing its words is the cheaper discipline.
        """
        return {a.dst_slot for a in self.accepted}

    def arrows(self, typed_slot: str) -> list[Correspondence]:
        """Accepted attachments as real Correspondence objects, at extraction tier."""
        from . import EngineError

        out = []
        for a in self.accepted:
            if a.is_bias_only:
                # EPHEMERAL. It seeded the relaxation; it is not an arrow, is never
                # journalled, and cannot enter composition. The base's kinds stay three.
                continue
            try:
                out.append(Correspondence(
                    src_chart=self.typed_chart, src_slot=typed_slot,
                    dst_chart=a.dst_chart, dst_slot=a.dst_slot, kind=a.kind,
                    tier=ATTACH_TIER, proposer="lm", prompt_hash="attach",
                    evidence=(a.evidence,)))
            except EngineError:
                continue          # refused (intra-chart, self-pair) — skipped, never coerced
        return out

    def as_record(self) -> dict[str, object]:
        return {"typed_slot": self.typed_slot[:16], "typed_chart": self.typed_chart,
                "proposed": [a.as_record() for a in self.proposed],
                "accepted": len(self.accepted), "considered": self.considered,
                "available": self.available, "calls": self.calls,
                "budget_exhausted": self.budget_exhausted, "error": self.error,
                "note": ("Attachment is a PROPOSED correspondence at extraction tier, judged "
                         "by the same proposer and the same prompt the corpus arrows use. "
                         "`none` is legal and expected; nothing here is promoted.")}


def _parse_attach(raw: str, holes) -> list[tuple[int, str, str]]:
    """(index, kind, evidence) for an ATTACHMENT reply. Its own parser, deliberately.

    `propose_correspondence.parse_answers` filters on `KINDS`, and `KINDS` is the base
    category's morphism set — exactly three. Widening it so `bears_on` could pass would put a
    non-morphism into the corpus vocabulary, which is the thing that must not happen. So the
    bias path parses its own replies against its own kind set, and the base is untouched.
    """
    from .propose_correspondence import _json_block, _salvage_objects

    try:
        body = _json_block(raw)
    except Exception:
        body = None
    rows = (body.get("answers") if isinstance(body, dict) else None)
    if not isinstance(rows, list):
        rows = [r for r in _salvage_objects(raw) if isinstance(r, dict) and "i" in r]
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        i, kind = row.get("i"), str(row.get("kind", ""))
        if not isinstance(i, int) or isinstance(i, bool):
            continue
        if not (0 <= i < len(holes)) or kind not in (set(ATTACH_KINDS) | {"none"}):
            continue
        out.append((i, kind, str(row.get("evidence", ""))[:600]))
    return out


def _degree(snapshot: CorpusSnapshot) -> dict[str, int]:
    """Declared arrows touching each slot. Structure, not text — nothing is compared."""
    out: dict[str, int] = {}
    for a in snapshot.arrows:
        out[a.src_slot] = out.get(a.src_slot, 0) + 1
        out[a.dst_slot] = out.get(a.dst_slot, 0) + 1
    return out


def candidates(snapshot: CorpusSnapshot, typed_chart: str, typed_type: str,
               limit: int, near: frozenset[str] = frozenset()) -> list[tuple[str, object]]:
    """Corpus claims to ask about: ARROW-RICH FIRST, then provenance-relevant.

    The field's own measured structure does the ordering. A claim that already carries
    correspondences is a better bridge than an isolated one — it is where the graph is
    connected, so an attachment there can actually propagate — and degree is read off the
    declared arrows, not computed from any text. Provenance breaks ties beneath it. Nothing
    lexical is consulted and nothing about this ordering reaches the compiled input: it
    decides only what is ASKED ABOUT, and the proposer's `none` still gates every answer.

    NO TYPE FILTER. It used to require the candidate's claim-form to match the typed input's,
    which was inherited from hole enumeration where both sides are corpus claims of a known
    form. A bias has no form until something assigns one, and the extractor that used to
    assign it is no longer in this path — so filtering on it would be asserting a property
    the bias does not have. This is stated rather than assumed; the operator has not ruled on
    whether a bias may attach across claim-forms, and this path now does.
    """
    degree = _degree(snapshot)
    rows = [(sid, rec) for sid, rec in snapshot.slots.items() if rec.chart != typed_chart]
    rows.sort(key=lambda kv: (-degree.get(kv[0], 0),
                              0 if kv[0] in near else 1,
                              kv[0]))
    return rows[:limit]


def attach(text: str, snapshot: CorpusSnapshot, transport, chart: str = "english",
           call_budget: int = CALL_BUDGET) -> AttachResult:
    """Ask the proposer where this input attaches. Its answer, in full, is the return value.

    THE TYPED TEXT GOES TO THE PROPOSER RAW. It used to be segmented by the claim extractor
    first, so a question or a topic phrase that yielded no spans bounced before the field was
    ever consulted — and "the field did not respond" then meant a parser had filtered the
    input, not that anything had been asked. That is an INGESTION rule governing the bias
    path, the same class as attachment inheriting the identity rule. The extractor's
    span-typing remains for corpus ingestion and for anything the operator proposes into the
    tape; a bias is neither of those.

    So the whole text is addressed as one surface — gate 1, exact, unchanged — and handed to
    the proposer as the source side of every candidate pair. "The field did not respond" now
    means one thing only: the proposer was consulted and declined.
    """
    from .normalize import address

    out = AttachResult()
    if snapshot.empty:
        out.error = "the corpus is empty"
        return out
    if not text.strip():
        out.error = "nothing was typed"
        return out

    # One surface, addressed exactly. No segmentation, no claim-shape gate.
    slot, nu_value = address(chart, text, "assert")
    out.typed_slot, out.typed_chart, out.typed_nu = slot, chart, nu_value

    near = frozenset()
    pool = candidates(snapshot, chart, "assert", limit=BATCH * call_budget, near=near)
    out.available = sum(1 for rec in snapshot.slots.values() if rec.chart != chart)
    if not pool:
        out.error = (f"no corpus claim lives over a chart other than {chart}, so there is no "
                     f"legal correspondence to propose")
        return out

    for start in range(0, len(pool), BATCH):
        if out.calls >= call_budget:
            out.budget_exhausted = True
            break
        chunk = pool[start:start + BATCH]
        holes = [Hole(src_chart=chart, src_slot=slot, src_nu=nu_value,
                      dst_chart=rec.chart, dst_slot=sid, dst_nu=rec.nu,
                      type="assert", restatement=0)
                 for sid, rec in chunk]
        try:
            raw, _usage = transport(ATTACH_SYSTEM, render_candidates(holes))
        except Exception as exc:                     # a dead call is reported, never silent
            out.error = f"{type(exc).__name__}: {exc}"
            break
        out.calls += 1
        out.considered += len(holes)
        for i, kind, evidence in _parse_attach(raw, holes):
            h = holes[i]
            out.proposed.append(Attachment(
                kind=kind, dst_slot=h.dst_slot, dst_chart=h.dst_chart, dst_nu=h.dst_nu,
                evidence=evidence))

    # Compared against `available`, NOT against `len(pool)`. The pool is ALREADY truncated to
    # the budget, so comparing with it asks "did we ask about everything we decided to ask
    # about" — which is always yes, and would have reported a budget-limited search as a
    # complete one. The question is whether every type-compatible candidate was reached.
    if out.considered < out.available and not out.error:
        out.budget_exhausted = True
    return out
