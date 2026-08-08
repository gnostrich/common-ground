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

from dataclasses import dataclass, field

#: TESTIMONY SUBCLASSES. Testimony carries no warrant at all — not a low tier, the absence of
#: one — and these narrow it without moving it. `WarrantTier` has no member for either and must
#: never gain one: a nomination that could be compared to EXTRACTION on a poset is a nomination
#: that could be promoted, and unpromotable-by-type is the whole design.
SYNTHESIS_CANDIDATE = "synthesis-candidate"

#: DELETED BY THE DOORLESS RULING: the NAME form, the term-candidate subclass, and the four
#: decidable checks that stressed a proposed term. All three were the SIGNATURE CEREMONY —
#: apparatus for turning a coinage into an offer the operator could sign — and vocabulary no
#: longer works that way. An apex's surface is DERIVED (see engine/apex_surface.py); a term the
#: medium coins is ordinary testimony; adoption happens when the operator RE-USES the word,
#: which puts it in the corpus as their own record through the normal inlet. See
#: seed/DIALOGIC.md, THE DOORLESS SIMPLIFICATION.


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

    def as_record(self) -> dict:
        return {"kind": self.kind, "footprint": list(self.footprint), "turn": self.turn,
                "text": self.text, "groups": list(self.groups),

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
        out[key] = Candidate(kind=prior.kind, footprint=key[1],
                             turn=min(prior.turn, c.turn), text=prior.text or c.text,
                             groups=prior.groups or c.groups)
    return [out[k] for k in sorted(out, key=lambda k: (k[0], k[1]))]


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
    """The interrogator's lexical question. Generated from the cluster, never from a reply.

    THE RESIDUAL STAYS AND THE CEREMONY IS GONE. This used to ask for a NAME in a declared form,
    which existed so the name could become an offer the operator signed. There is no signature
    now: an apex's surface is derived, and a coinage is testimony. So the question asks for what
    the dialogue can actually consume — an ARROW relating the cluster to something already
    named, or a stated absence. Its output is arrows and testimony like any other turn, which is
    what "measurement pressure, part of settlement" means.
    """
    cited = "".join(f"[{n}]" for n in members)
    return (f"The field says {cited} are one proposition and nothing here names it. Relate one "
            f"of them to an object that IS named, writing the arrow, or say the field gives no "
            f"basis for that with [∅].")


