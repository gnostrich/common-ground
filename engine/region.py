"""REGION QUERY: the unit of extraction is a region, not a pair.

The LM completes diagrams, and it is not a pairwise oracle. Asking "does A correspond to B?" runs a
full settling over the whole context and keeps one bit of it. Everything else the medium
resolved in that same pass — which of the other claims in front of it state the same thing,
which refine which — is computed and thrown away. That is the waste, and it is not a tuning
problem: it is the wrong unit.

So a call carries a REGION: a clamp point, its declared arrows, and a batch of unattached
corpus claims. The medium is asked to name every correspondence it sees inside that region,
and all of them are read off one call.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — a proposer into D.
Q1 motivated it: the object the query ranges over is a REGION, and a pair is a projection
of one. We were measuring the projection.
Q3 is the prize. A region can name two arrows sharing one English endpoint into DIFFERENT
charts in a single call — the composition precondition, which has occurred zero times in
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

import re
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
    "You are completing a partial DIAGRAM: a finite subcategory of a reconciliation engine's "
    "base. OBJECTS are claims, each living over a chart (english, lean, python, go, tabular, "
    "conversation). ARROWS are typed translations between claims in DIFFERENT charts.\n\n"
    "You are given the objects, the arrows already DECLARED among them, and the arrows those "
    "declared arrows IMPLY by composition. Complete the diagram.\n\n"
    "Emit only lines of the form  i -kind-> j  with i and j among the OBJECTS shown and kind "
    "in {same_claim, refines, instance_of}. Nothing else: no prose, no JSON, no claim text, "
    "no names.\n"
    "  same_claim   — i and j assert the SAME proposition\n"
    "  refines      — i is a strictly more specific form of j (directed)\n"
    "  instance_of  — i is a particular instance of j\'s general form\n\n"
    "Do not introduce new objects: an index not shown does not exist in this diagram.\n"
    "Arrows are CROSS-CHART only; two claims over the same chart are never related here.\n"
    "Pairs you do not name are UNMEASURED, not denied. Naming nothing is a legal completion, "
    "and word overlap between two claims is not a reason to relate them."
)

#: The verbatim task line, kept separate so it can be asserted against.
TASK_LINE = (
    "Complete the diagram. Emit only lines of the form i -kind-> j with i,j in OBJECTS and "
    "kind in {same_claim, refines, instance_of}. Do not introduce new objects. Pairs you do "
    "not name are UNMEASURED, not denied."
)

#: `i -kind-> j`. The whole wire vocabulary on the way back.
#: An index is a WHOLE token. Without the guards, `1.0 -same_claim-> 2` matched the `1` out
#: of `1.0` and silently truncated a float into a valid index — a malformed answer resolving
#: to a real address, which is the exact shape resolve-or-void exists to prevent.
_ARROW_RE = re.compile(r"(?<![\w.])(-?\d+)\s*-\s*([a-z_]+)\s*->\s*(-?\d+)(?![\w.])")


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
    #: Declared, implied and proposed are THREE epistemic states of the same arrow type, and
    #: the residual signal is defined as their difference — so the format keeps them apart.
    declared: dict[tuple[str, str], str] = field(default_factory=dict)
    implied: dict[tuple[str, str], str] = field(default_factory=dict)

    @property
    def region_id(self) -> str:
        """Identity of the CO-PRESENT SET. Two regions with the same members are the same
        observation context; a re-naming inside one is not independent evidence."""
        from .hashing import sha256_text

        return sha256_text("".join(sorted(m.slot for m in self.members)))[:16]

    def overlap(self, other_members: set[str]) -> float:
        """Jaccard overlap of membership. High overlap means the same measurement twice."""
        mine = {m.slot for m in self.members}
        if not mine or not other_members:
            return 0.0
        return len(mine & other_members) / len(mine | other_members)

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


def escape_nu(nu: str) -> str:
    """ITEM 2: the nu-string goes over the wire BYTE-EXACT, with invertible escaping.

    These are the exact bytes the address hash was computed over. Re-wrapping, trimming or
    normalizing whitespace would present the medium with a claim the engine does not hold —
    a different string, hashing to a different address. So nothing is normalized; only the
    characters that would collide with the line format are escaped, and the escaping is
    invertible so `unescape_nu(escape_nu(x)) == x` byte for byte.

    Escaped: backslash (first, or the inversion is ambiguous), newline, carriage return, and
    the \x01 chart tag that rides inside every nu.
    """
    return (nu.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")
              .replace("\x01", "\\x01"))


def unescape_nu(text: str) -> str:
    """The inverse. A control asserts the round trip reproduces the hashed bytes."""
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            if text[i:i + 4] == "\\x01":
                out.append("\x01"); i += 4; continue
            nxt = text[i + 1]
            if nxt == "n":
                out.append("\n"); i += 2; continue
            if nxt == "r":
                out.append("\r"); i += 2; continue
            if nxt == "\\":
                out.append("\\"); i += 2; continue
            # `\x01` escapes to FOUR characters: backslash, x, 0, 1. Slicing five consumed
            # the following character too, so the inverse silently ate a byte and the round
            # trip failed on the first real nu-string tried.
            if text[i:i + 4] == "\\x01":
                out.append("\x01"); i += 4; continue
        out.append(text[i]); i += 1
    return "".join(out)


def render_region(region: Region) -> str:
    """The partial diagram on the wire: OBJECTS, declared ARROWS, implied ARROWS, task.

    All three sections go in. "Complete a partial diagram" is only well-posed if the partial
    diagram is given — withholding the declared arrows would force the medium to re-derive
    structure the registry already holds, and would destroy the residual measurement, which is
    defined as the difference between what is declared, what composition implies, and what the
    medium names.
    """
    lines = ["OBJECTS"]
    for m in region.members:
        lines.append(f"[{m.index}|{m.chart}] {escape_nu(m.nu)}")

    lines += ["", "ARROWS (declared)"]
    idx = {m.slot: m.index for m in region.members}
    declared = [f"{idx[a]} -{k}-> {idx[b]}" for (a, b), k in sorted(region.declared.items())
                if a in idx and b in idx]
    lines += declared or ["(none)"]

    lines += ["", "ARROWS (implied by composition)"]
    implied = [f"{idx[a]} -{k}-> {idx[b]}" for (a, b), k in sorted(region.implied.items())
               if a in idx and b in idx]
    lines += implied or ["(none)"]

    lines += ["", TASK_LINE]
    return "\n".join(lines)


def parse_region(raw: str, region: Region) -> list[Proposal]:
    """Read `i -kind-> j` lines. Resolution is an array lookup; anything else is VOID.

    There are no names anywhere in the wire format — the medium never sees an address and
    never writes one — so a fuzzy match has nothing to attach to even in principle. That is
    the resolve-or-void property, and it is a fact about the format rather than a check bolted
    onto it.
    """
    out: list[Proposal] = []
    for m in _ARROW_RE.finditer(raw or ""):
        i, kind, j = int(m.group(1)), m.group(2), int(m.group(3))
        src, dst = region.by_index(i), region.by_index(j)
        line = m.group(0)
        if src is None or dst is None:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"index outside the region: {line}"))
        elif src.slot == dst.slot:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void="i == j; one claim is not a correspondence"))
        elif kind not in KINDS or kind == "none":
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"unknown correspondence kind {kind!r}"))
        elif src.chart == dst.chart:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void="intra-chart; exact addressing owns intra-chart identity"))
        else:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line))
    return out


@dataclass(slots=True)
class Residual:
    """The reading discipline: what the medium named against what the registry already holds.

    Five outcomes, and only one of them is a new proposal:

      * a DECLARED arrow named        -> confirmation, recorded, not re-proposed
      * an IMPLIED arrow named        -> composition confirmed; the arrow upgrades
      * a NOVEL arrow named           -> proposal, extraction tier, through the inlet
      * an IMPLIED arrow NOT named    -> RESIDUAL: prediction error, the walk's strongest
                                         signal, and the thing the sampler steers toward
      * a pair not named at all       -> UNMEASURED-IN-THIS-REGION. Never a `none`. Coverage
                                         accumulates across overlapping regions; only repeated
                                         non-naming across relaxations trends to a real negative
    """

    confirmed_declared: list = field(default_factory=list)
    confirmed_implied: list = field(default_factory=list)
    novel: list = field(default_factory=list)
    residual: list = field(default_factory=list)      # implied, not named — prediction error
    void: list = field(default_factory=list)
    named_pairs: int = 0
    unmeasured_pairs: int = 0

    @property
    def acceptance(self) -> float:
        """Resolved over named. The guard: pairwise held ~50% on good bounds, and a region
        trending toward ~90% is condensing noise rather than seeing more."""
        total = self.named_pairs + len(self.void)
        return (self.named_pairs / total) if total else 0.0

    def as_record(self) -> dict[str, object]:
        return {
            "confirmed_declared": len(self.confirmed_declared),
            "confirmed_implied": len(self.confirmed_implied),
            "novel": [p.as_record() for p in self.novel],
            "residual": [[a[:16], b[:16]] for a, b in self.residual],
            "void": [p.as_record() for p in self.void],
            "acceptance": round(self.acceptance, 3),
            "named_pairs": self.named_pairs,
            "unmeasured_pairs": self.unmeasured_pairs,
            "note": ("An unmeasured pair is NOT a `none`: it was never put as a question. "
                     "Coverage accumulates across overlapping regions of the walk, and only "
                     "repeated non-naming across relaxations trends toward a real negative."),
        }


def residuals(proposals: list[Proposal], region: Region) -> Residual:
    """Sort what was named into the five outcomes. Both mismatch directions are findings."""
    out = Residual()
    named: set[tuple[str, str]] = set()
    for p in proposals:
        if not p.ok:
            out.void.append(p)
            continue
        key = (p.src.slot, p.dst.slot)
        rev = (p.dst.slot, p.src.slot)
        named.add(key)
        if key in region.declared or rev in region.declared:
            out.confirmed_declared.append(p)
        elif key in region.implied or rev in region.implied:
            out.confirmed_implied.append(p)
        else:
            out.novel.append(p)

    # The reverse arrow is a SEPARATE proposal, so asymmetry stays signal: an implied pair is
    # residual only when the medium named neither direction of it.
    for pair in sorted(region.implied):
        if pair not in named and (pair[1], pair[0]) not in named:
            out.residual.append(pair)

    n = len(region.members)
    out.named_pairs = len({tuple(sorted(k)) for k in named})
    out.unmeasured_pairs = max(0, n * (n - 1) // 2 - out.named_pairs)
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


def provenance_key(doc_id: str) -> str:
    """The directory a claim came from. The only proximity unattached claims DECLARE.

    Measured on the corpus: documents hold a median of 2 slots, which is too thin to relax
    over, while 287 of 460 directories span two or more charts and their median size is 60 —
    exactly one region. Forty-four span three or more, and those are the only places a shared
    English endpoint can reach two different code charts, which is the composition
    precondition that has never once occurred in pairwise proposing.
    """
    repo, _, path = doc_id.partition("||")
    return f"{repo}||{path.rsplit('/', 1)[0] if '/' in path else ''}"


def build_region(snapshot: CorpusSnapshot, clamp: str = "", size: int = REGION_SIZE,
                 extra: list[str] | None = None,
                 quarantined: frozenset = frozenset()) -> Region:
    """Assemble the partial diagram: the clamp, its declared neighbours, then PROVENANCE-NEAR
    claims — same directory, nothing else.

    The first real run filled this by declared degree, corpus-wide. That produced sixty claims
    scattered across unrelated repositories with zero internally-declared pairs, and the medium
    asked to complete an incoherent diagram produced a star: one Lean theorem fanned to
    fifty-one unrelated Python declarations. Degree is not lexical, but it is not proximity
    either — it is a global property that does not make two unattached claims near ANYTHING.
    Provenance is the one relation they declare, and it is what this uses.
    """
    # QUARANTINED arrows do not act. They are not neighbours, they do not raise a claim's
    # degree, and they imply nothing — otherwise the walk aims itself at its own bad output
    # and measures residuals against composites built on leads.
    live = [a for a in snapshot.arrows
            if (a.src_slot, a.dst_slot) not in quarantined
            and (a.dst_slot, a.src_slot) not in quarantined]
    neighbours: dict[str, set[str]] = {}
    for a in live:
        neighbours.setdefault(a.src_slot, set()).add(a.dst_slot)
        neighbours.setdefault(a.dst_slot, set()).add(a.src_slot)

    near: dict[str, list[str]] = {}
    for sid, rec in snapshot.slots.items():
        for doc in rec.docs:
            near.setdefault(provenance_key(doc), []).append(sid)

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
    keys = {provenance_key(d) for sid in list(seen)
            for d in snapshot.slots[sid].docs} if seen else set()
    if not keys:
        # No clamp: start where the diagram can be richest — a directory spanning most charts.
        by_charts = sorted(near, key=lambda k: (-len({snapshot.slots[s].chart
                                                      for s in near[k]}), -len(near[k]), k))
        keys = set(by_charts[:1])
    # CHART-BALANCED within the provenance pool. The pool is still the directory and nothing
    # else — but the ORDER round-robins across charts, because a correspondence is cross-chart
    # by construction and a region of sixty claims from one chart is a diagram in which almost
    # no arrow can exist. Measured before this: 44% of pairs in a region were structurally
    # ineligible, and 32% of directories with ten or more slots are over 90% a single chart.
    # Balancing decides which claims are SHOWN, never which relate; chart is a declared
    # property of a claim (which object of B it lives over), so this compares nothing.
    pool: list[str] = []
    for key in sorted(keys):
        pool.extend(sorted(near.get(key, ())))
    by_chart: dict[str, list[str]] = {}
    for sid in pool:
        by_chart.setdefault(snapshot.slots[sid].chart, []).append(sid)
    while any(by_chart.values()) and len(chosen) < size:
        for chart in sorted(by_chart):
            queue = by_chart[chart]
            if queue:
                take(queue.pop(0))
            if len(chosen) >= size:
                break

    # ITEM 1: index order is engine-assigned and SHUFFLED. Position in a prompt is
    # attention-salient, so ANY systematic order — provenance, arrow density, chart grouping —
    # leaks an undeclared ranking signal into the completion. Order must carry zero
    # information. The permutation is derived from the region's own content, so a region is
    # still reproducible: same members, same shuffle, and a walk anybody can replay.
    chosen = _shuffle(chosen)
    members = [Member(index=i, slot=sid, chart=snapshot.slots[sid].chart,
                      type=snapshot.slots[sid].type, nu=snapshot.slots[sid].nu,
                      attached=bool(neighbours.get(sid)))
               for i, sid in enumerate(chosen)]
    inside = {m.slot for m in members}
    declared = {(a.src_slot, a.dst_slot): a.kind for a in live
                if a.src_slot in inside and a.dst_slot in inside}
    return Region(clamp=clamp, members=members, declared=declared,
                  implied=_compose(declared, inside))


def _shuffle(slots: list[str]) -> list[str]:
    """A content-derived permutation. Deterministic, and carrying no ordering signal.

    Not `random`: an unreproducible region makes a walk unreplayable, and a walk nobody can
    replay is a walk whose findings cannot be checked. Keying the sort on a hash of the
    region's whole membership plus each slot means the order is stable for a given region and
    uncorrelated with degree, provenance or chart — which is exactly "carries no information".
    """
    from .hashing import sha256_text

    seed = sha256_text("".join(sorted(slots)))
    return sorted(slots, key=lambda s: sha256_text(seed + s))


def _compose(declared: dict[tuple[str, str], str], inside: set[str]
             ) -> dict[tuple[str, str], str]:
    """Composition closure, computed by the ENGINE before the call. If 1->2 and 2->3 are
    declared, 1->3 is IMPLIED and is shown as such — a third epistemic state, distinct from
    declared and from proposed, because the residual signal is their difference."""
    from .compose import COMPOSITION

    out: dict[tuple[str, str], str] = {}
    for (a, b), k1 in declared.items():
        for (c, d), k2 in declared.items():
            if b != c or a == d:
                continue
            kind = COMPOSITION.get((k1, k2))
            if kind and (a, d) not in declared and (d, a) not in declared:
                out[(a, d)] = kind
    return out
