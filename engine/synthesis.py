"""THE FOURTH DOOR: the medium NOMINATES, and never mints.

THE TWO-MOUTH LAW, unchanged. New objects arise from exactly two mouths — the operator's, and
the measure's own quotients. Everything here produces NOMINATIONS: records that enter no slot,
carry no warrant, compose with nothing, and reach the field only through the operator's
signature or decay with the testimony that carried them. There is no code path in this module
that creates a slot, an arrow or an apex, and `tests/test_synthesis.py` asserts that by
execution rather than by reading.

NO NEW MECHANISM (Q5). Three existing ones gain a case:

  * a TESTIMONY subclass — `synthesis-candidate` / `term-candidate`. Testimony is off the
    warrant poset entirely, unpromotable BY TYPE, exactly as it landed;
  * a RESIDUAL class for the interrogator — LEXICAL FRUSTRATION — beside implied-unaddressed
    and contested, on the same structural machinery;
  * the operator's signature remains the only content mouth.

WHERE A SYNTHESIS CANDIDATE COMES FROM, and why it is not a second detector. A candidate
synthesis is "a proposition resting on cited claims that none of them states". The checker
ALREADY computes exactly that, and has since before this file existed: the WELD rule fires on a
sentence citing objects from different declared groups with no arrow joining them. A weld and a
synthesis candidate are ONE measurement seen by two consumers — the faithfulness gate reads it
as an unlicensed relation, the fourth door reads it as a nomination. Building a second detector
would have been the Q5 violation this project deletes on sight, so this module reads the
verdict rather than the prose.

NOTHING HERE READS WORDS. Footprints are citation labels, groups are declared fibers, and the
one string this module handles — a proposed term — is captured by an exact FORM (`NAME [i][j]
AS "..."`), resolve-or-void, never inferred from a sentence. The standing AST sweep covers this
module like any other: no tokenizer, no similarity, no distance, no case folding.

Spec: seed/DIALOGIC.md, "THE FOURTH DOOR", written before this file existed. Controls c1-c6 are
in tests/test_synthesis.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: TESTIMONY SUBCLASSES. Testimony carries no warrant at all — not a low tier, the absence of
#: one — and these narrow it without moving it. `WarrantTier` has no member for either and must
#: never gain one: a nomination that could be compared to EXTRACTION on a poset is a nomination
#: that could be promoted, and unpromotable-by-type is the whole design.
SYNTHESIS_CANDIDATE = "synthesis-candidate"
TERM_CANDIDATE = "term-candidate"

#: THE FOUR DECIDABLE CHECKS a proposed term is stressed by. Closed vocabulary: a check
#: resolved against a closed set is a measurement, and a check phrased in prose is an opinion.
COVERAGE, COLLISION, SPLIT, RESIDUE = "coverage", "apex-collision", "split", "residue"

#: A TERM NOMINATION, as an exact form. The labels it covers, then the candidate surface in
#: quotes. Resolve-or-void: every label must be one the field showed, and a line that does not
#: match this shape is prose and yields nothing. The quoted string is a CANDIDATE SURFACE for a
#: footprint — never a name the engine adopts, because adopting is the operator's act.
NAME_FORM = re.compile(r'NAME\s+((?:\[[a-z]?\d+\]\s*)+)AS\s+"([^"]{1,60})"')

_LABEL = re.compile(r"\[([a-z]?\d+)\]")


@dataclass(frozen=True, slots=True)
class Candidate:
    """One nomination. THE FOOTPRINT IS THE IDENTITY, never the words.

    Two nominations resting on the same objects are one nomination with two candidate surfaces
    — which is the records-versus-pairs law applied to vocabulary, and is why `surfaces` is a
    tuple rather than a string.
    """

    kind: str
    footprint: tuple           # the labels it rests on, sorted. THE IDENTITY.
    turn: int
    text: str = ""             # the testimony sentence, verbatim, for the operator to read
    groups: tuple = ()         # the declared groups the footprint spans
    surfaces: tuple = ()       # candidate words, for a term nomination
    offer: str = ""            # what the informed offer says about this footprint

    def as_record(self) -> dict:
        return {"kind": self.kind, "footprint": list(self.footprint), "turn": self.turn,
                "text": self.text, "groups": list(self.groups),
                "surfaces": list(self.surfaces), "offer": self.offer,
                # STATED ON EVERY RECORD, because a reader who has to remember it will not.
                "warrant": None, "record_kind": "testimony",
                "entered": "nothing — a nomination reaches the field only by the operator's "
                           "signature, or it decays with the testimony that carried it"}


def _group_of(compiled: dict) -> dict:
    """label -> the declared group it belongs to. Ungrouped objects get their own group.

    The same rule `engine.grounded.group_of` applies, read off the same citations, because two
    functions disagreeing about what a group is would put the weld rule and the fourth door on
    different maps of one field.
    """
    out = {}
    for c in (compiled.get("citations") or ()):
        if c.get("kind") == "arrow":
            continue
        n = str(c.get("n") or "")
        if n:
            out[n] = str(c.get("group") or "") or f"~{n}"
    return out


def _members(compiled: dict) -> dict:
    """group -> the labels in it, sorted. The cluster, as the field declares it."""
    out: dict = {}
    for n, g in _group_of(compiled).items():
        out.setdefault(g, set()).add(n)
    return {g: tuple(sorted(v)) for g, v in out.items()}


def _label_of_slot(compiled: dict) -> dict:
    """corpus slot -> the label it was shown under, for the informed offer's identity check."""
    return {str(c.get("slot")): str(c.get("n")) for c in (compiled.get("citations") or ())
            if c.get("slot") and c.get("n")}


def named(group: str) -> str:
    """The apex-name of a group, or "" when it has none.

    "" IS THE SAFE DEFAULT AND THE HONEST ONE: an unnamed cluster becomes a QUESTION, never a
    silent assumption that it is covered. `engine.medium.fiber_label` keys its glosses by the
    fiber id the gloss validator wrote; a group whose key does not match simply reads as
    unnamed and is asked about, which is the direction an uncertainty in this lookup should
    fail in.
    """
    if not group or group.startswith("~"):
        return ""
    try:
        from .medium import fiber_label

        return fiber_label(group) or ""
    except Exception:
        return ""


def synthesis_candidates(verdict: dict, compiled: dict, turn: int = 0) -> list:
    """Every WELD in one turn, read as a nomination instead of as a conviction.

    Same measurement, second consumer. The weld rule fires when a sentence cites objects from
    different declared groups and no arrow joins them — which is precisely "a proposition
    resting on cited claims that none of them states". It enters nothing here either.
    """
    groups = _group_of(compiled)
    out = []
    for v in (verdict.get("violations") or ()):
        if v.get("kind") != "welded":
            continue
        foot = tuple(sorted(str(n) for n in (v.get("numbers") or ())))
        if len(foot) < 2:
            continue
        out.append(Candidate(kind=SYNTHESIS_CANDIDATE, footprint=foot, turn=turn,
                             text=str(v.get("sentence") or "").strip(),
                             groups=tuple(sorted({groups.get(n, f"~{n}") for n in foot}))))
    return collapse(out)


def collapse(candidates: list) -> list:
    """ONE NOMINATION PER FOOTPRINT (c3). Duplicates fold; their surfaces accumulate.

    The footprint is the identity, so two candidates over the same objects are one candidate
    that has been said twice — five restatements are five records and one claim, at the level
    of vocabulary. The earliest turn is kept, because the nomination happened then.
    """
    out: dict = {}
    for c in candidates:
        # SORTED, because the footprint is the identity and an identity that depends on the
        # order the medium happened to write its labels in is not one.
        key = (c.kind, tuple(sorted(c.footprint)))
        prior = out.get(key)
        if prior is None:
            out[key] = c
            continue
        surfaces = tuple(dict.fromkeys(prior.surfaces + c.surfaces))
        out[key] = Candidate(kind=prior.kind, footprint=key[1],
                             turn=min(prior.turn, c.turn), text=prior.text or c.text,
                             groups=prior.groups or c.groups, surfaces=surfaces,
                             offer=prior.offer or c.offer)
    return [out[k] for k in sorted(out, key=lambda k: (k[0], k[1]))]


def inform(candidate: Candidate, compiled: dict, snapshot=None) -> str:
    """THE INFORMED OFFER. What the field already holds that this nomination would duplicate.

    Two identity checks, both EXACT, neither a comparison of meaning:

      1. the candidate's own text addressed by the ordinary normalizer — if that address is
         already in the corpus, claiming it adds an EVENT, not a slot;
      2. the footprint sitting inside ONE declared group — the quotient IS the declared
         relation between its faces, so a nomination over one fiber names something the field
         has already named as one proposition.

    An offer that cannot name anything returns "", which is a genuine gap and the case the
    whole door exists for.
    """
    if snapshot is not None and candidate.text:
        try:
            from .normalize import address

            slot, _nu = address("english", candidate.text, "assert")
            if slot in getattr(snapshot, "slots", {}):
                shown = _label_of_slot(compiled).get(slot)
                where = f" as [{shown}]" if shown else f" at slot {slot[:16]}"
                return (f"this already exists{where}; claiming it adds an event, not a slot")
        except Exception:
            pass
    if len(candidate.groups) == 1 and not candidate.groups[0].startswith("~"):
        return (f"these are one declared proposition already — fiber "
                f"{candidate.groups[0][:12]}; the quotient IS the relation between them")
    return ""


def apexless(compiled: dict, asked: set) -> tuple:
    """The first declared cluster in this field that NO apex names. Structure, never prose.

    A cluster of one is not a lexical gap: a claim in no fiber is its own group by construction,
    and asking for a name for every ungrouped claim would ask about every claim in the corpus.
    The gap is a MEASURED one — several claims the field says are one proposition, with no word
    for the proposition.
    """
    # SCOPED TO THE PERTURBATION, by the same law the contested residual now obeys: a cluster
    # nothing in this perturbation reached is a fact about the corpus, not a residual this
    # question raised, and spending a turn on it spends the operator's budget on the sample.
    from .dialogue import REACHED

    reached = {str(c.get("n")) for c in (compiled.get("citations") or ())
               if c.get("kind") in REACHED and c.get("n")}
    for group, members in sorted(_members(compiled).items()):
        if len(members) < 2 or group.startswith("~"):
            continue
        if named(group) or not (set(members) & reached):
            continue
        ident = ("lex", group)
        if ident in asked:
            continue
        return ident, members
    return (), ()


def lexical_question(members: tuple) -> str:
    """The interrogator's lexical question. Generated from the cluster, never from a reply."""
    cited = "".join(f"[{n}]" for n in members)
    return (f"The structure at {cited} has no name. Name it with "
            f'NAME {cited} AS "your-term", or decompose it through an existing name by '
            f"relating its members to objects that have one. If the field gives you no basis "
            f"for either, say so with [∅].")


def terms_from(prose: str, citable: set, turn: int = 0) -> list:
    """Every `NAME [i][j] AS "..."` in one reply. Resolve-or-void, exactly like an arrow.

    A label the field never showed voids the whole nomination rather than being repaired to a
    nearby one: there is no nearest neighbour here and inventing one would be the mint this
    module exists to make impossible.
    """
    out = []
    for m in NAME_FORM.finditer(prose or ""):
        foot = tuple(sorted(_LABEL.findall(m.group(1))))
        if not foot or any(n not in citable for n in foot):
            continue
        out.append(Candidate(kind=TERM_CANDIDATE, footprint=foot, turn=turn,
                             text=m.group(0), surfaces=(m.group(2).strip(),)))
    return collapse(out)


def stress(candidate: Candidate, compiled: dict, cluster: tuple = ()) -> list:
    """THE FOUR DECIDABLE CHECKS. Each returns a failure or nothing; none reads a word.

    | check         | question                                          | a failure means      |
    |---------------|---------------------------------------------------|----------------------|
    | coverage      | does its claimed footprint hold when settled?     | the name outran it   |
    | apex-collision| does it land on a fiber something already names?  | synonym, decompose   |
    | split         | do its citations span several clusters?           | two structures       |
    | residue       | does it leave measured structure uncovered?       | the residue is next  |
    """
    groups = _group_of(compiled)
    members = _members(compiled)
    foot = set(candidate.footprint)
    out = []

    unknown = sorted(n for n in foot if n not in groups)
    if unknown:
        out.append({"check": COVERAGE, "failed": True, "detail": unknown,
                    "note": "the name claims objects the settled field does not carry"})

    spans = sorted({groups.get(n, f"~{n}") for n in foot})
    for g in spans:
        label = named(g)
        if label:
            out.append({"check": COLLISION, "failed": True, "detail": [g, label],
                        "note": "this fiber already has a name; decompose, do not mint"})
    if len(spans) > 1:
        out.append({"check": SPLIT, "failed": True, "detail": spans,
                    "note": "the citations span several declared clusters: two structures"})

    whole = set(cluster) or {n for g in spans for n in members.get(g, ())}
    left = sorted(whole - foot)
    if left:
        out.append({"check": RESIDUE, "failed": True, "detail": left,
                    "note": "measured structure the name leaves uncovered — the residue IS "
                            "the next question"})
    return out


@dataclass
class Lexicon:
    """What one dialogue did to the vocabulary. Counted, and every count says which it counts."""

    nominated: list = field(default_factory=list)   # term candidates that survived the checks
    rejected: list = field(default_factory=list)    # {candidate, failures}
    open: list = field(default_factory=list)        # clusters asked about and still unnamed

    def as_record(self) -> dict:
        return {
            "named": len(self.nominated), "rejected": len(self.rejected),
            "open": len(self.open),
            "nominations": [c.as_record() for c in self.nominated],
            "rejections": [{"candidate": c.as_record(), "failures": f}
                           for c, f in self.rejected],
            "open_clusters": [list(x) for x in self.open],
            # THE LEGAL ENDING, SPELLED. Budget exhaustion with open lexical residue is a
            # recorded ending, never a silent one.
            "note": (f"named: {len(self.nominated)}, open: {len(self.open)}. A nomination "
                     f"entered nothing; the operator's signature is the only way in."),
        }
