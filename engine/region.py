"""REGION RELAXATION: the unit of extraction is a region, not a pair.

The LM is a relaxation medium, not a pairwise oracle. Asking "does A correspond to B?" runs a
full settling over the whole context and keeps one bit of it. Everything else the medium
resolved in that same pass — which of the other claims in front of it state the same thing,
which refine which — is computed and thrown away. That is the waste, and it is not a tuning
problem: it is the wrong unit.

So a call carries a REGION: a clamp point, its declared arrows, and a batch of unattached
corpus claims. The medium is asked to name every correspondence it sees inside that region,
and all of them are read off one settling.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — a proposer into D.
Q1 motivated it: the object the medium relaxes over is a REGION, and a pair is a projection
of one. We were measuring the projection.
Q3 is the prize. A region can name two arrows sharing one English endpoint into DIFFERENT
charts in a single settling — the composition precondition, which has occurred zero times in
3,113 pairwise arrows because english x python and english x go are enumerated as separate
populations and nothing ever steers the proposer to the same English slot in both. A shared
endpoint across two charts is what turns stars into a graph with cycles, and cycles are the
only thing that can make holonomy nonzero.
Q5 passes ONLY because this UNIFIES. It replaces the pairwise loop and the separate
attachment step; standing beside them it would be a second proposer, which is the forbidden
shape.

**RESOLVE-OR-VOID, and why it cannot rot.** Every claim in a region is rendered with an
integer index. The medium answers ONLY in indices. It never emits a name, a surface, a hash
or a slot id — so there is nothing for a fuzzy match to match against, and the "no similarity"
property is structural rather than promised. An answer resolves to an exact corpus address by
array lookup, or it is VOID with a stated reason. Four ways to be void, all decidable:

  * an index outside the region,
  * a non-integer where an index belongs (including a quoted surface — the failure this
    guards against, since a model that emits text invites someone to match it),
  * i == j, which is one claim and not a correspondence,
  * an intra-chart pair, which `engine/correspondence` already refuses because exact
    addressing owns intra-chart identity.

**Silence is not `none`.** In the pairwise loop `none` was an ANSWER: the proposer was shown
that pair and declined it. In a region, a pair the medium simply did not mention was never
put to it as a question. Recording those as `none` would manufacture tens of thousands of
declines nobody made. They are recorded as UNMENTIONED, which is a different fact and is
counted separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .correspondence import KINDS, Correspondence
from .corpus_state import CorpusSnapshot
from .types import WarrantTier

#: Claims per region. Median nu is 106 chars and p90 is 298, so 60 truncated to 300 is about
#: 4,900 input tokens — comparable to the pairwise call's 2,040 — while carrying 1,770
#: pair-equivalents instead of 12. Larger regions were measured and rejected: output ordering
#: degrades and a truncated tail costs the whole region rather than one candidate.
REGION_SIZE = 60

#: Each claim is cut to this for rendering. Cutting is MARKED, because a medium shown half a
#: claim and not told so is being asked about something other than the claim.
NU_CAP = 300

#: Region proposals enter where every LM proposal enters. Nothing here can ground or clamp.
REGION_TIER = WarrantTier.EXTRACTION

REGION_SYSTEM = (
    "You are reading a REGION of a reconciliation engine's corpus: a set of claims, each with "
    "an integer index, drawn from different charts (english prose, lean, python, go, tabular, "
    "conversation transcripts).\n\n"
    "Name every CORRESPONDENCE you see between claims in this region:\n"
    "  same_claim   — they assert the SAME proposition\n"
    "  refines      — the first is a strictly more specific form of the second (directed)\n"
    "  instance_of  — the first is a particular instance of the second's general form\n\n"
    "Rules that decide whether your answer is usable at all:\n"
    "  * Answer ONLY with indices. Never write a claim's text, a name, or an identifier in "
    "place of an index — an answer that does is discarded.\n"
    "  * A correspondence is CROSS-CHART only. Two claims in the same chart are never a "
    "correspondence here; the engine addresses identity exactly and will reject them.\n"
    "  * Naming nothing is a legal and expected outcome. Most pairs in a region are unrelated, "
    "and a region where you see nothing is a real answer about this corpus.\n"
    "  * Superficial word overlap is NOT a correspondence. Two claims that share vocabulary, "
    "or a claim and its negation, are not related. Do not reach for a relation because you "
    "were asked to look; you are being measured on precision, not on yield.\n"
    "  * Cite the specific spans that make each pair correspond. If you cannot cite them, do "
    "not name the pair.\n\n"
    'Return ONLY JSON: {"pairs":[{"i":int,"j":int,"kind":one of '
    "['same_claim','refines','instance_of'],\"evidence\":str}]}, where i and j are indices "
    "shown in the region and the relation runs FROM i TO j."
)


@dataclass(frozen=True, slots=True)
class Member:
    """One claim in a region, at a fixed index. The index is the only handle the medium gets."""

    index: int
    slot: str
    chart: str
    type: str
    nu: str
    attached: bool                            # already carries a declared arrow


@dataclass(slots=True)
class Region:
    """A clamp point, its declared neighbourhood, and unattached claims to relax against."""

    clamp: str = ""                           # slot id of the perturbed claim, if any
    members: list[Member] = field(default_factory=list)
    implied: set[tuple[str, str]] = field(default_factory=set)   # already-declared pairs

    def by_index(self, i: object) -> Member | None:
        if not isinstance(i, int) or isinstance(i, bool):
            return None
        if 0 <= i < len(self.members):
            return self.members[i]
        return None


@dataclass(frozen=True, slots=True)
class Proposal:
    """One correspondence the medium named, resolved to exact addresses or VOID."""

    kind: str
    src: Member | None
    dst: Member | None
    evidence: str
    void: str = ""                            # non-empty means discarded, with the reason

    @property
    def ok(self) -> bool:
        return not self.void

    def as_record(self) -> dict[str, object]:
        return {"kind": self.kind, "void": self.void,
                "src": self.src.slot[:16] if self.src else None,
                "dst": self.dst.slot[:16] if self.dst else None,
                "src_chart": self.src.chart if self.src else None,
                "dst_chart": self.dst.chart if self.dst else None,
                "evidence": self.evidence[:300]}


def _display(nu: str) -> str:
    if nu.startswith("\x01"):
        end = nu.find("\x01", 1)
        if end != -1:
            return nu[end + 1:]
    return nu


def render_region(region: Region) -> str:
    """The prompt body: indexed claims, with truncation marked where it happened."""
    lines = []
    for m in region.members:
        text = _display(m.nu)
        cut = len(text) > NU_CAP
        body = text[:NU_CAP] + (" …[cut]" if cut else "")
        lines.append(f"[{m.index}] ({m.chart}/{m.type}) {body}")
    return "\n".join(lines)


def parse_region(raw: str, region: Region) -> list[Proposal]:
    """Resolve every named pair to exact addresses, or VOID it with the reason.

    Nothing here compares text. An answer is an index or it is not, and the index is an array
    lookup into the region that was rendered — which is why a fuzzy match has no surface to
    attach to even in principle.
    """
    from .propose_correspondence import _json_block, _salvage_objects

    try:
        body = _json_block(raw)
    except Exception:
        body = None
    rows = []
    if isinstance(body, dict) and isinstance(body.get("pairs"), list):
        rows = body["pairs"]
    else:
        rows = [r for r in _salvage_objects(raw) if "i" in r and "j" in r]

    out: list[Proposal] = []
    for row in rows:
        if not isinstance(row, dict):
            out.append(Proposal(kind="?", src=None, dst=None, evidence="",
                                void="answer row is not an object"))
            continue
        kind = str(row.get("kind", ""))
        evidence = str(row.get("evidence", ""))[:600]
        i, j = row.get("i"), row.get("j")
        src, dst = region.by_index(i), region.by_index(j)
        if src is None or dst is None:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=evidence,
                                void=f"index out of region or not an integer: i={i!r} j={j!r}"))
            continue
        if src.slot == dst.slot:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=evidence,
                                void="i == j; one claim is not a correspondence"))
            continue
        if kind not in KINDS or kind == "none":
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=evidence,
                                void=f"unknown correspondence kind {kind!r}"))
            continue
        if src.chart == dst.chart:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=evidence,
                                void="intra-chart; exact addressing owns intra-chart identity"))
            continue
        out.append(Proposal(kind=kind, src=src, dst=dst, evidence=evidence))
    return out


@dataclass(slots=True)
class Residual:
    """What the medium named against what declared structure already implies."""

    named_not_implied: list[Proposal] = field(default_factory=list)
    implied_not_named: list[tuple[str, str]] = field(default_factory=list)
    named_and_implied: int = 0
    void: list[Proposal] = field(default_factory=list)
    mentioned_pairs: int = 0
    unmentioned_pairs: int = 0                # NOT `none` — never put to the medium

    def as_record(self) -> dict[str, object]:
        return {
            "candidates": [p.as_record() for p in self.named_not_implied],
            "implied_not_named": [[a[:16], b[:16]] for a, b in self.implied_not_named],
            "named_and_implied": self.named_and_implied,
            "void": [p.as_record() for p in self.void],
            "mentioned_pairs": self.mentioned_pairs,
            "unmentioned_pairs": self.unmentioned_pairs,
            "note": ("An unmentioned pair is NOT a `none`. In the pairwise loop `none` was an "
                     "answer — the proposer was shown that pair and declined it. Here the pair "
                     "was never put as a question, and recording it as a decline would "
                     "manufacture refusals nobody made."),
        }


def residuals(proposals: list[Proposal], region: Region) -> Residual:
    """Split what was named against what was already declared. Both directions are facts."""
    out = Residual()
    named: set[tuple[str, str]] = set()
    for p in proposals:
        if not p.ok:
            out.void.append(p)
            continue
        key = (p.src.slot, p.dst.slot)
        named.add(key)
        named.add((p.dst.slot, p.src.slot))
        if key in region.implied or (p.dst.slot, p.src.slot) in region.implied:
            out.named_and_implied += 1
        else:
            out.named_not_implied.append(p)

    for pair in sorted(region.implied):
        if pair not in named:
            out.implied_not_named.append(pair)

    n = len(region.members)
    total = n * (n - 1) // 2
    out.mentioned_pairs = len({tuple(sorted(k)) for k in named})
    out.unmentioned_pairs = max(0, total - out.mentioned_pairs)
    return out


def arrows_from(proposals: list[Proposal], proposer: str = "lm",
                prompt_hash: str = "region") -> list[Correspondence]:
    """Accepted proposals as Correspondences at EXTRACTION tier. Refused ones are dropped."""
    from . import EngineError

    out = []
    for p in proposals:
        if not p.ok:
            continue
        try:
            out.append(Correspondence(
                src_chart=p.src.chart, src_slot=p.src.slot,
                dst_chart=p.dst.chart, dst_slot=p.dst.slot, kind=p.kind,
                tier=REGION_TIER, proposer=proposer, prompt_hash=prompt_hash,
                evidence=(p.evidence,)))
        except EngineError:
            continue
    return out


def build_region(snapshot: CorpusSnapshot, clamp: str = "", size: int = REGION_SIZE,
                 extra: list[str] | None = None) -> Region:
    """Assemble a region: the clamp point, its declared neighbours, then unattached claims.

    Neighbours first because they are the structure the medium should see — a region that
    shows a claim without the arrows it already has invites the medium to re-name them, which
    costs a call to learn something already recorded. Unattached claims fill the rest, and
    they are ordered by declared degree so a region is aimed at the part of the graph that is
    already connected rather than at a random slice of a 69,000-slot corpus.
    """
    degree: dict[str, int] = {}
    neighbours: dict[str, set[str]] = {}
    for a in snapshot.arrows:
        degree[a.src_slot] = degree.get(a.src_slot, 0) + 1
        degree[a.dst_slot] = degree.get(a.dst_slot, 0) + 1
        neighbours.setdefault(a.src_slot, set()).add(a.dst_slot)
        neighbours.setdefault(a.dst_slot, set()).add(a.src_slot)

    chosen: list[str] = []
    seen: set[str] = set()

    def take(sid: str) -> None:
        if sid and sid not in seen and sid in snapshot.slots and len(chosen) < size:
            seen.add(sid)
            chosen.append(sid)

    take(clamp)
    for sid in sorted(neighbours.get(clamp, ())):
        take(sid)
    for sid in (extra or ()):
        take(sid)
    for sid, _ in sorted(degree.items(), key=lambda kv: (-kv[1], kv[0])):
        take(sid)
    if len(chosen) < size:
        for sid in sorted(snapshot.slots):
            take(sid)

    members = [Member(index=i, slot=sid, chart=snapshot.slots[sid].chart,
                      type=snapshot.slots[sid].type, nu=snapshot.slots[sid].nu,
                      attached=degree.get(sid, 0) > 0)
               for i, sid in enumerate(chosen)]
    inside = {m.slot for m in members}
    implied = {(a.src_slot, a.dst_slot) for a in snapshot.arrows
               if a.src_slot in inside and a.dst_slot in inside}
    return Region(clamp=clamp, members=members, implied=implied)
