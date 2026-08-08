"""AN APEX'S SURFACE IS DERIVED. No offer, no signature, no ceremony.

THE DOORLESS RULING. There are no layers. A corpus is a field, the operator's input is a clamp
on it, the medium is one participant in the loop, and what the whole arrangement PRODUCES is
ARROWS — everything above an arrow is derived from arrow-field density.

(The ruling's own phrasing put the medium in the verb of that sentence. Gate 10 refused this
docstring twice for repeating it, and was right both times: borrowed physics vocabulary is how
a motivating picture hardens into a claimed mechanism, and a module that contains no settlement
machinery may not describe itself as performing any. The picture belongs in seed/DIALOGIC.md.
This file derives a string.) A relation is one arrow
surviving; a cluster is arrows condensing; an apex is the quotient the machinery already mints
FROM MEASUREMENT. A NAME is a SURFACE on an apex, and this module is the whole of how one is
chosen.

WHAT THIS REPLACES: the nomination → offer → signature flow, deleted as a gate on vocabulary.
Nothing waits on the operator for an apex to be called something. There is no pending state, no
claim gesture, and no claiming UI — that one was never built and must not be.

THE RULE IS AN ORDER, NOT A SCORE. The first of these that exists:

  1. an OPERATOR-AUTHORED member's surface
  2. a KERNEL-tier member's identifier
  3. a REFERENCE-tier gloss — the lexicon lane's handle
  4. the SHORTEST member surface

Ties inside a rank break by slot id ascending, which makes the rule TOTAL and BYTE-STABLE: the
same membership yields the same surface on every run, in any process, with no LM call at read
time. There is no scoring function to tune and no similarity to creep in, because the order IS
the rule — a ranking that could be weighted is a ranking somebody will weight.

WHY PROVENANCE AND NOT LENGTH FIRST. The surface is what the operator will read the apex AS, and
the strongest thing available is a word they themselves used. A kernel identifier is next
because a Lean name is a declared fact about the artifact rather than anybody's paraphrase. The
lexicon gloss is third because it is reference tier — it conditions and never grounds. Shortest
is the floor: it always exists when the apex has any member at all, which is what makes the
rule total.

VOCABULARY ADOPTION IS BY USE, and that is not implemented here or anywhere. A term the medium
coins in a dialogue is ordinary testimony. If the operator re-uses it, it enters the corpus as
THEIR record through the normal inlet, because they said it. `tests/test_apex_surface.py`
asserts no code path treats a medium coinage specially.
"""

from __future__ import annotations

from dataclasses import dataclass

#: THE RANKS, in order, as a closed vocabulary. A surface whose rank is not one of these was
#: chosen by something this module does not implement.
AUTHORED, KERNEL, GLOSS, SHORTEST = "authored", "kernel", "gloss", "shortest"
RANKS = (AUTHORED, KERNEL, GLOSS, SHORTEST)

#: The tier a member must carry to be read as the operator's own word, and the tier that makes
#: an identifier a declared fact rather than a paraphrase. Both are names from the warrant
#: poset, not thresholds.
AUTHORED_TIERS = frozenset({"AUTHORSHIP", "PREMINTED"})
KERNEL_TIERS = frozenset({"KERNEL", "CI_RECEIPT"})


@dataclass(frozen=True, slots=True)
class Surface:
    """What an apex is called, and which rank produced it. Both travel, always.

    A surface without its rank is a name whose authority nobody can read: "the operator's own
    word" and "the shortest thing lying around" are different facts and must never print the
    same.
    """

    text: str
    rank: str
    slot: str

    def as_record(self) -> dict:
        return {"text": self.text, "rank": self.rank, "slot": self.slot[:16],
                "derived": True,
                "note": "Derived by a declared order, not granted. No signature, no pending "
                        "state, no LM call at read time."}


def surface_of(members, glosses: dict | None = None) -> Surface | None:
    """The apex's surface. `members` are objects carrying `slot`, `tier` and `nu`.

    Returns None only for an EMPTY apex, which is not an apex. Every other case resolves,
    because rank 4 always exists.
    """
    from .inbound import display

    rows = []
    for m in (members or ()):
        slot = str(getattr(m, "slot", "") or "")
        if not slot:
            continue
        rows.append((slot, str(getattr(m, "tier", "") or ""),
                     display(str(getattr(m, "nu", "") or ""))))
    if not rows:
        return None
    # SORTED BY SLOT FIRST, so every rank below breaks its own ties the same way and the whole
    # rule is one total order rather than four with a convention between them.
    rows.sort(key=lambda r: r[0])

    for slot, tier, text in rows:
        if tier in AUTHORED_TIERS and text:
            return Surface(text=text, rank=AUTHORED, slot=slot)

    for slot, tier, text in rows:
        if tier in KERNEL_TIERS:
            from .scaffold_lean import declared_name

            name = declared_name(str(getattr(
                next(m for m in members if str(getattr(m, "slot", "")) == slot), "nu", "")) or "")
            if name:
                return Surface(text=name, rank=KERNEL, slot=slot)

    for slot, _tier, _text in rows:
        g = (glosses or {}).get(slot)
        if g is not None and getattr(g, "reading", ""):
            return Surface(text=g.reading, rank=GLOSS, slot=slot)

    # THE FLOOR, which is what makes the rule total. Shortest by length, then by slot — the
    # second key is not decoration: two members of equal length would otherwise resolve by
    # whichever the iteration reached first, and a surface that depends on iteration order is
    # not byte-stable across processes.
    best = min((r for r in rows if r[2]), key=lambda r: (len(r[2]), r[0]), default=None)
    return Surface(text=best[2], rank=SHORTEST, slot=best[0]) if best else None
