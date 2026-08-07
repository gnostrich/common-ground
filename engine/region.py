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

**A PERTURBATION IS A REGION, and that is why there is only one of these.** Typed input used
to reach the field by a second route: a candidate list ordered by degree, cut to a call budget,
interrogated pairwise. Two mechanisms for one job — the forbidden shape — and the window got
the worse one, which is why it felt like lookup. The typed input is now ONE MORE OBJECT in the
diagram, over the pseudo-chart `bias`, and the same region goes out on the same wire in one
call. Arrows the medium draws to the bias object are ATTACHMENT: ephemeral, conditioning-only,
never journalled, never composable, never an arrow. Arrows it draws among the corpus objects
are ordinary extraction, indistinguishable from the walk's, because they came from the same
call. There is no candidate list left to be truncated, so there is no truncation to disclaim.
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

#: How many arrow-rich hubs a perturbation may be aimed at. Wide enough that successive
#: questions land in different neighbourhoods, narrow enough that every one of them is a place
#: where declared structure exists and a perturbation can actually travel.
HUBS = 64

#: Each claim is cut to this for rendering. Cutting is MARKED, because a medium shown half a
#: claim and not told so is being asked about something other than the claim.
NU_CAP = 300

#: Region proposals enter where every LM proposal enters. Nothing here can ground or clamp.
REGION_TIER = WarrantTier.EXTRACTION

#: The pseudo-chart the typed input lives over inside a diagram. Not one of B's objects: no
#: corpus claim can ever carry it, so an arrow touching it is cross-chart by construction and
#: the intra-chart refusal can never fire on an attachment. It is also the marker that keeps
#: attachment ephemeral — `arrows_from` drops anything touching it, structurally rather than
#: by anyone remembering to.
BIAS_CHART = "bias"

#: The BIAS relation. Not a corpus morphism — the base's kinds stay exactly three.
#:
#: A topic or a question cannot correspond to anything: "does `holonomy` state the same
#: proposition as this Lean theorem?" has one correct answer forever, so asking the identity
#: question of a bias guarantees `none` and the field is never reached. The aboutness question
#: is a different question and it gets a different relation — legal ONLY on an arrow touching
#: the bias object, and discarded between two corpus objects.
BEARS_ON = "bears_on"

#: THE LEGEND — what an object, a chart and an arrow ARE. Shared, because both prompts need it
#: and neither may drift from the other: the daemon's coordinates prompt and the dialogue's
#: turn-one prompt describe the SAME diagram, and a second copy of this paragraph would be two
#: descriptions of one wire waiting to disagree.
REGION_LEGEND = (
    "You are completing a partial DIAGRAM: a finite subcategory of a reconciliation engine's "
    "base. OBJECTS are claims, each living over a chart (english, lean, python, go, tabular, "
    "conversation). ARROWS are typed translations between claims in DIFFERENT charts.\n\n"
    "You are given the objects, the arrows already DECLARED among them, and the arrows those "
    "declared arrows IMPLY by composition. Complete the diagram.")

REGION_SYSTEM = (
    REGION_LEGEND + "\n\n"
    "Emit only lines of the form  i -kind-> j  where i and j are OBJECT LABELS exactly as "
    "shown — a chart letter followed by a number, like `e12` or `p7` — and kind is in "
    "{same_claim, refines, instance_of}. Nothing else: no prose, no JSON, no claim text, "
    "no names.\n"
    "  same_claim   — i and j assert the SAME proposition\n"
    "  refines      — i is a strictly more specific form of j (directed)\n"
    "  instance_of  — i is a particular instance of j\'s general form\n\n"
    "Do not introduce new objects: a label not shown does not exist in this diagram.\n"
    "THE LEGAL ARROW FORMS ARE ENUMERATED IN THE DIAGRAM. Only those forms exist. Two labels "
    "carrying the SAME chart letter have no legal form between them, so such an arrow cannot "
    "be written — this is a property of the notation, not a rule to remember.\n"
    "Pairs you do not name are UNMEASURED, not denied. Naming nothing is a legal completion, "
    "and word overlap between two claims is not a reason to relate them.\n\n"
    "A diagram MAY contain exactly one object over the chart `bias`. That is a BOUNDARY "
    "CONDITION an operator typed, not a corpus claim, and it may be a question or a bare topic "
    "rather than an assertion. One extra kind is available for it:\n"
    "  bears_on     — the corpus claim is ABOUT what the bias is about: a question it would "
    "help answer, or a topic it falls under. A question asserts nothing, so it cannot "
    "correspond to anything; it can still be about something.\n"
    "Emit those as  b -bears_on-> j  with b the bias object's index. `bears_on` is legal ONLY "
    "on an arrow touching the bias object; between two corpus objects it is not a relation and "
    "is discarded. It is also the ONLY kind legal there: a boundary condition asserts nothing, "
    "so same_claim, refines and instance_of cannot touch it and are discarded if written. "
    "Relate the corpus objects to EACH OTHER in the same answer — that is the diagram, and the "
    "bias is one object in it, not the question being asked about it."
    # THE ACT LINE. Codomain syntax, one sentence — the razor. What the operator's
    # utterance DOES is read here, at attachment, like every other proposal: a declared
    # token in a closed vocabulary, resolve-or-void, never inferred from prose.
)

#: The verbatim task line, kept separate so it can be asserted against.
TASK_LINE = (
    "Complete the diagram. Emit only lines matching a LEGAL ARROW FORM above, with i,j the "
    "object labels shown and kind in {same_claim, refines, instance_of}. Do not introduce new "
    "objects. Pairs you do not name are UNMEASURED, not denied."
)

#: THE CHART TAG that prefixes every index. One letter per chart, collision-free across the
#: seven charts in play (english, lean, python, go, tabular, conversation, bias).
#:
#: This is what makes cross-chart-only a GRAMMAR rule instead of a prose one. An index reads
#: `e12` or `p07`, and the legal arrow forms are enumerated per region as chart-pairs — so an
#: intra-chart arrow has no form to be written in, rather than being written and then refused.
#: Measured before the change: 827 of 827 voids on one region were intra-chart, and about half
#: of every response was spent on arrows the engine would discard. Prose said "CROSS-CHART
#: only" and every medium ignored it at scale; grammar has won every previous round.
CHART_TAG = {"english": "e", "lean": "l", "python": "p", "go": "g",
             "tabular": "t", "conversation": "c", BIAS_CHART: "b"}


def tag_of(chart: str) -> str:
    """One letter for a chart. Unknown charts fall back to their own first letter, which is
    still deterministic and still distinguishes them from any other chart present."""
    return CHART_TAG.get(chart) or (chart[:1] or "x")


def labels(region) -> dict:
    """slot -> the region's own label for it. The seed of the ONE label space.

    THE COLLAPSE RESTS ON THIS. The dialogue, the extraction and the answer's citations all
    resolve against region labels, so there is no renumbering step between what the medium
    said and what the checker verifies — and a renumbering step is one more place a bug can
    hide, which is not hypothetical: a half-collapsed pipeline shipped green this morning.
    """
    return {m.slot: label(m.chart, m.index) for m in getattr(region, "members", ()) or ()}


class Labeller:
    """One tagged label space, seeded by the region and extended for anything outside it.

    A moved claim can be OUTSIDE the region — reached over a declared arrow — so it has no
    region label and needs one. It gets the next free index IN ITS OWN CHART, so the label
    keeps meaning what it means everywhere else: the letter is the chart, and two objects with
    the same letter are over the same chart. A separate scheme for the strays would be a second
    numbering, which is the thing being deleted.
    """

    __slots__ = ("_by_slot", "_next")

    def __init__(self, region=None):
        self._by_slot = labels(region) if region is not None else {}
        self._next = {}
        for lab in self._by_slot.values():
            tag, digits = lab[:1], lab[1:]
            if digits.isdigit():
                self._next[tag] = max(self._next.get(tag, -1), int(digits))

    def label_for(self, slot: str, chart: str) -> str:
        """The region's label if this slot was seated, otherwise a fresh one in its chart."""
        got = self._by_slot.get(slot)
        if got:
            return got
        tag = tag_of(chart)
        self._next[tag] = self._next.get(tag, -1) + 1
        got = f"{tag}{self._next[tag]}"
        self._by_slot[slot] = got
        return got

    def known(self) -> dict:
        return dict(self._by_slot)


def label(chart: str, index: int) -> str:
    return f"{tag_of(chart)}{index}"


#: `i -kind-> j`. The whole wire vocabulary on the way back.
#: An index is a WHOLE token. Without the guards, `1.0 -same_claim-> 2` matched the `1` out
#: of `1.0` and silently truncated a float into a valid index — a malformed answer resolving
#: to a real address, which is the exact shape resolve-or-void exists to prevent.
#: A tagged index is `<letter><digits>`; the bare-integer form is still read so that a
#: response in the old vocabulary parses rather than silently scoring zero.
#: BRACKETS OPTIONAL, and that is what makes ONE parser serve both channels. The coordinates
#: wire writes `e1 -refines-> l45`; prose writes `[e1] -refines-> [l45]`, because in prose the
#: brackets are what a citation looks like everywhere else. Two parsers for one grammar is the
#: forbidden shape, so the grammar admits both spellings and the parser stays single.
_ARROW_RE = re.compile(
    r"(?<![\w.])\[?([a-z]?)(-?\d+)\]?\s*-\s*([a-z_]+)\s*->\s*\[?([a-z]?)(-?\d+)\]?(?![\w.])")


@dataclass(frozen=True, slots=True)
class Member:
    """One claim in a region, at a fixed index. The index is the only handle the medium gets."""

    index: int
    slot: str
    chart: str
    type: str
    nu: str
    attached: bool                            # already carries a declared arrow
    #: WHAT GOES ON THE WIRE when it is not the nu. Empty for every corpus object, because a
    #: corpus object has no other bytes — nu IS what the engine holds for it. Non-empty for the
    #: bias alone: the operator typed something, and nu is the engine's paraphrase of it.
    #: OI-19 is the whole reason this field exists; see `tests/test_bias_bytes.py`.
    surface: str = ""

    @property
    def wire(self) -> str:
        """The bytes the medium reads. One accessor, so no renderer can pick the other one."""
        return self.surface or self.nu


@dataclass(slots=True)
class Region:
    """A clamp point, its declared neighbourhood, and unattached claims to relax against."""

    clamp: str = ""                           # slot id of the perturbed claim, if any
    members: list[Member] = field(default_factory=list)
    #: Declared, implied and proposed are THREE epistemic states of the same arrow type, and
    #: the residual signal is defined as their difference — so the format keeps them apart.
    declared: dict[tuple[str, str], str] = field(default_factory=dict)
    implied: dict[tuple[str, str], str] = field(default_factory=dict)
    #: Address of the typed input when this region carries one. Empty for a walk region, and
    #: the walk's regions are byte-identical to what they were before the bias object existed.
    bias: str = ""

    @property
    def bias_member(self) -> Member | None:
        for m in self.members:
            if m.chart == BIAS_CHART:
                return m
        return None

    def touches_bias(self, p: "Proposal") -> bool:
        return bool(p.src and p.dst) and BIAS_CHART in (p.src.chart, p.dst.chart)

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
        # `m.wire`, never `m.nu`. For every corpus object these are the same string; for the
        # bias they are not, and the difference is OI-19.
        lines.append(f"[{label(m.chart, m.index)}] {escape_nu(m.wire)}")

    # THE LEGAL ARROW FORMS, enumerated. Cross-chart-only stops being an instruction the
    # medium may ignore and becomes the shape of the token itself: with the charts present
    # tagged, an intra-chart arrow has no form here to be written in. Enumerating FORMS costs
    # one line per chart-pair — at most fifteen for six charts — where enumerating the legal
    # index pairs would cost nine hundred.
    present = sorted({m.chart for m in region.members})
    forms = [f"  {tag_of(a)}<i> -kind-> {tag_of(b)}<j>"
             for i, a in enumerate(present) for b in present[i + 1:]]
    lines += ["", "LEGAL ARROW FORMS (these and no others)"]
    lines += forms or ["  (none: every object here is over one chart, so no arrow is legal)"]
    lines += [f"  charts present: {', '.join(f'{tag_of(c)}={c}' for c in present)}"]

    idx = {m.slot: label(m.chart, m.index) for m in region.members}
    lines += ["", "ARROWS (declared)"]
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
        ti, i, kind, tj, j = (m.group(1), int(m.group(2)), m.group(3),
                              m.group(4), int(m.group(5)))
        src, dst = region.by_index(i), region.by_index(j)
        line = m.group(0)
        # A TAG THAT DISAGREES with the object it points at is void. Without this the tag
        # would be decoration: a medium could write `e5` at a python object and the index
        # would silently win, which is the resolve-or-void property leaking.
        if src is not None and ti and ti != tag_of(src.chart):
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"tag {ti!r} does not match the object's chart "
                                     f"{src.chart!r}"))
            continue
        if dst is not None and tj and tj != tag_of(dst.chart):
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"tag {tj!r} does not match the object's chart "
                                     f"{dst.chart!r}"))
            continue
        bias_arrow = (src is not None and dst is not None
                      and BIAS_CHART in (src.chart, dst.chart))
        if src is None or dst is None:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"index outside the region: {line}"))
        elif src.slot == dst.slot:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void="i == j; one claim is not a correspondence"))
        elif kind == BEARS_ON and not bias_arrow:
            # The one extra kind exists for the boundary condition and nowhere else. Between
            # two corpus claims it is not a morphism of B, and letting it through would put a
            # fourth kind into the corpus vocabulary by the back door.
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void="bears_on is legal only on an arrow touching the bias "
                                     "object; it is not a corpus morphism"))
        elif bias_arrow and kind != BEARS_ON:
            # AND THE CONVERSE, which was missing — the rule ran in one direction only, so
            # `bears_on` between two claims was refused while `same_claim` TO THE BIAS was
            # waved through. Measured on a served transcript: turn 1 wrote
            # `e3 -same_claim-> b0` and `e7 -refines-> b0`, and the window reported them as
            # two CORRESPONDENCE attachments.
            #
            # That is the prompt's own law broken by the parser meant to enforce it. A boundary
            # condition may be a question or a bare topic, and A QUESTION ASSERTS NOTHING: it
            # cannot assert the same proposition as a claim, cannot be a strictly more specific
            # form of one, and cannot be an instance of one. What it can be is ABOUT something,
            # which is the entire reason `bears_on` exists. Letting identity and refinement
            # touch the bias gives an utterance assertion-grade coupling to the corpus on the
            # strength of having been typed.
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"{kind!r} is not legal on an arrow touching the bias "
                                     f"object: a boundary condition asserts nothing, so only "
                                     f"bears_on can relate it to a claim"))
        elif kind not in KINDS and kind != BEARS_ON:
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void=f"unknown correspondence kind {kind!r}"))
        elif kind == "none":
            out.append(Proposal(kind=kind, src=src, dst=dst, evidence=line,
                                void="unknown correspondence kind 'none'"))
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
    #: Arrows the medium drew to the BIAS object. A sixth outcome, kept out of the five above
    #: because it is not a corpus finding: it is ephemeral, conditions one perturbation and is
    #: gone. Empty for every walk region, so the walk's accounting is unchanged.
    attachment: list = field(default_factory=list)
    named_pairs: int = 0
    unmeasured_pairs: int = 0

    @property
    def void_pairs(self) -> int:
        """DISTINCT void pairs. `void` is a list of proposals and a medium that repeats
        itself puts the same refusal in it many times over."""
        out = set()
        for p in self.void:
            if p.src and p.dst:
                out.add(tuple(sorted((p.src.slot, p.dst.slot))))
            else:
                out.add(("?", p.evidence))     # unresolvable: keep each distinct line once
        return len(out)

    @property
    def acceptance(self) -> float:
        """Resolved over named, BOTH SIDES DEDUPED. The guard: pairwise held ~50% on good
        bounds, and a region trending toward ~90% is condensing noise rather than seeing more.

        Both sides deduped, because they were not. `named_pairs` collapsed repeats and
        `len(self.void)` did not, so acceptance compared a deduped numerator against a
        repetition-inflated denominator. On a live step the medium emitted 1,789 arrow lines
        that collapsed to 51 distinct pairs — about 35 repeats each — and the reported
        acceptance swung between 97% and 2% across steps as a function of how much the model
        had repeated itself rather than of what it had resolved. The number the guard watches
        was measuring generation verbosity.
        """
        total = self.named_pairs + self.void_pairs
        return (self.named_pairs / total) if total else 0.0

    def as_record(self) -> dict[str, object]:
        return {
            "confirmed_declared": len(self.confirmed_declared),
            "confirmed_implied": len(self.confirmed_implied),
            "novel": [p.as_record() for p in self.novel],
            "residual": [[a[:16], b[:16]] for a, b in self.residual],
            "void": [p.as_record() for p in self.void],
            "void_pairs": self.void_pairs,
            "void_lines": len(self.void),
            "attachment": [p.as_record() for p in self.attachment],
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
        if region.touches_bias(p):
            # ATTACHMENT. Routed out before the five outcomes, because it is not a corpus
            # arrow: it can neither confirm a declared one nor be residual against an implied
            # one, and counting it as novel would put it in the extraction stream.
            out.attachment.append(p)
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
    """Accepted proposals as Correspondences at EXTRACTION tier. Refused ones are dropped.

    THE EPHEMERALITY GUARD lives here, at the one place a region proposal becomes a
    Correspondence, so an arrow to the bias object cannot become structure by any route: not
    by a caller forgetting to filter, not by a new caller that never knew to. `bias` is not an
    object of B, so a Correspondence over it would be ill-typed even if one were minted.
    """
    from . import EngineError

    out = []
    for p in proposals:
        if not p.ok:
            continue
        if BIAS_CHART in (p.src.chart, p.dst.chart):
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


def anchor_for(snapshot: CorpusSnapshot, seed: str,
               quarantined: frozenset = frozenset(), text: str = "",
               chart: str = "english") -> str:
    """Which arrow-rich neighbourhood a PERTURBATION samples. Structure picks it; a hash orders it.

    A typed input has no position in the corpus — that is what Q2 says about an object with no
    morphisms — so a region has to be chosen for it, and the choice must not be a search. It is
    made in two parts, and neither part reads the corpus's text:

      * the ELIGIBLE set is the arrow-richest slots, by declared degree. That is the walk's own
        seeding rule (`_seed_frontier`): a claim no arrow touches can only ever report that
        nothing moved, so a perturbation aimed there is a wasted call.
      * WHICH of them is a rotation keyed on the typed input's ADDRESS. A hash is not a
        similarity: it carries no relation to what the text means, two nearly identical inputs
        land in unrelated neighbourhoods, and a control asserts exactly that. What it buys is
        that successive questions probe different parts of the corpus instead of every question
        re-measuring one hub forever.

    EXACT LANDING COMES FIRST, and it is not a search either. `seed` is the typed text's own
    address under this chart's nu — gate 1 addressing, byte-exact. If the corpus already
    carries that address, the input IS that claim and the neighbourhood to sample is its own.
    Falling through to the hash-rotated hub in that case inverts the spec: a claim the corpus
    holds verbatim gets sampled somewhere unrelated and declines, which is what the battery's
    sharp input did — 59 claims shown, zero arrows drawn, on a slot with 254 declared arrows
    sitting elsewhere in the corpus. Exact identity is the one relation available without a
    proposal, so it is used before anything else is.

    Otherwise the region is a SAMPLE, stated as one. It is not the part of the corpus that
    matches the question — nothing here could compute that — and the window says so rather
    than letting the operator infer relevance from the fact that these sixty claims and not
    others came back.
    """
    from .hashing import sha256_text

    # GATE 1, USED AS ITSELF. An exact address hit is identity, not resemblance: same nu,
    # same type, same chart, same sha256. No text is compared to reach this branch.
    if seed and seed in getattr(snapshot, "slots", {}):
        return seed

    # NOMINATION, BEFORE THE ARROW-RICH CORE. Degree eligibility is self-reinforcing: walked
    # material gets arrows, arrows make it eligible, eligibility routes questions there, and
    # those questions produce more arrows. Measured on the live corpus, the eligible set was
    # 71% one repository holding 15% of the material, and a question about certified
    # positivity could draw 2 of 512 eligible slots from that provenance — so no question
    # about arrow-poor material could ever assemble a region about it. A phrase the corpus
    # literally contains is a declared fact about that claim's TEXT; it nominates where to
    # sample and creates nothing. See engine/nominate.
    if text:
        from .nominate import nominate

        nom = nominate(snapshot, text, chart)
        if nom["slots"]:
            return min(nom["slots"], key=lambda s: sha256_text(seed + s))

    live = [a for a in snapshot.arrows
            if (a.src_slot, a.dst_slot) not in quarantined
            and (a.dst_slot, a.src_slot) not in quarantined]
    degree: dict[str, int] = {}
    for a in live:
        degree[a.src_slot] = degree.get(a.src_slot, 0) + 1
        degree[a.dst_slot] = degree.get(a.dst_slot, 0) + 1
    hubs = [s for s, _ in sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))[:HUBS]
            if s in snapshot.slots]
    if not hubs:
        return ""
    return min(hubs, key=lambda s: sha256_text(seed + s))


def build_region(snapshot: CorpusSnapshot, clamp: str = "", size: int = REGION_SIZE,
                 extra: list[str] | None = None,
                 quarantined: frozenset = frozenset(),
                 bias: tuple[str, str, str] | None = None) -> Region:
    """Assemble the partial diagram: the clamp, its declared neighbours, then PROVENANCE-NEAR
    claims — same directory, nothing else.

    The first real run filled this by declared degree, corpus-wide. That produced sixty claims
    scattered across unrelated repositories with zero internally-declared pairs, and the medium
    asked to complete an incoherent diagram produced a star: one Lean theorem fanned to
    fifty-one unrelated Python declarations. Degree is not lexical, but it is not proximity
    either — it is a global property that does not make two unattached claims near ANYTHING.
    Provenance is the one relation they declare, and it is what this uses.

    `bias` is `(address, nu)` for a typed input, and it makes this the WINDOW's region rather
    than the walk's. It is one more object, over the pseudo-chart `bias`, and everything
    downstream — the renderer, the wire grammar, the parser, the reading discipline — is the
    same code the walk runs. With `bias=None` this function returns exactly what it returned
    before the boundary condition existed, which is the property that makes it one path and
    not two.
    """
    # The bias occupies an index, so it costs one corpus object rather than widening the
    # region: a diagram the medium was measured on at sixty stays sixty.
    if bias:
        size = max(1, size - 1)

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
    chart_of = {m.slot: m.chart for m in members}
    implied = _compose(declared, inside, chart_of)

    if bias:
        # INDEX 0, and the shuffle argument does not reach it. Order is shuffled because
        # position is attention-salient and a systematic order leaks an UNDECLARED ranking.
        # The bias's role is not undeclared: it is written on the object, `[0|bias]`, so its
        # position tells the medium nothing its own chart tag has not already said. It is the
        # distinguished object of the diagram and it is rendered as one.
        # THREE PARTS, TWO ROLES. `b_nu` is the address's bytes and never reaches the wire;
        # `b_surface` is the operator's bytes and is all that does. OI-19: input is an external
        # field term, so the addresser's fold — case, whitespace, terminal punctuation, the
        # chart tag itself — is a fact about identity and not about what was asked.
        b_slot, b_nu, b_surface = bias
        members = ([Member(index=0, slot=b_slot, chart=BIAS_CHART, type="bias", nu=b_nu,
                           attached=False, surface=b_surface)]
                   + [Member(index=m.index + 1, slot=m.slot, chart=m.chart, type=m.type,
                             nu=m.nu, attached=m.attached, surface=m.surface)
                      for m in members])
        # The bias carries no declared arrow — it is new, and Q2 is the whole point — so it
        # cannot appear in `declared` and therefore cannot compose. Nothing to exclude.
        return Region(clamp=clamp, members=members, declared=declared, implied=implied,
                      bias=b_slot)
    return Region(clamp=clamp, members=members, declared=declared, implied=implied)


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


def _compose(declared: dict[tuple[str, str], str], inside: set[str],
             chart_of: dict[str, str]) -> dict[tuple[str, str], str]:
    """Composition closure — delegated to `engine.compose`, not reimplemented here.

    This function used to compose A->B->C without checking that A and C live over DIFFERENT
    charts. `Correspondence` refuses an intra-chart arrow outright, so every such composite
    was an arrow that cannot exist — and the walk then counted the medium's correct refusal to
    name it as prediction error. 100% of 640 measured drifts were this: english x english and
    python x python composites manufactured between the leaves of 29 hubs, one of them 64
    times over.

    Two defects in one. The missing cross-chart guard, and the fact that a SECOND composition
    existed at all: `engine.compose` already had the rule and a control asserting it
    (`test_intra_chart_implication_is_residue_not_an_arrow`). Writing another was the Q5
    violation this module's own docstring warns about.
    """
    from .compose import COMPOSITION

    out: dict[tuple[str, str], str] = {}
    for (a, b), k1 in declared.items():
        for (c, d), k2 in declared.items():
            if b != c or a == d:
                continue
            # THE GUARD. Gate 1 owns intra-chart identity, so composition may not manufacture
            # one; `engine.compose` calls the same case a residue rather than an arrow.
            if chart_of.get(a) == chart_of.get(d):
                continue
            kind = COMPOSITION.get((k1, k2))
            if kind and (a, d) not in declared and (d, a) not in declared:
                out[(a, d)] = kind
    return out
