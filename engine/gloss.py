"""THE LEXICON LANE: one declared handle beside a Lean object, so a chart boundary is crossable.

THE GAP, from the measurements rather than from intuition. Lean attachment is 0 of 19 in every
honest column of seed/FIXTURE-CERTIFIED-POSITIVITY.md, and column D settled that it is not model
capability — a larger tier moved it in 2 of 6 draws at ~20x cost with worse faithfulness. The
one time it read 19 of 19 the discrimination fraction was 1.00 and the number was void.

WHAT THE CODE SAYS. `engine.inbound` already prints a cross-chart handle when a `same_claim`
fiber exists — the "the medium reads this as" slot `medium.fiber_label` fills — and that handle
took ENGLISH attachment from 2 to 22 in column C. No fiber has ever formed across english/lean,
because forming one requires the very correspondence arrow lean-attachment measures. That is a
COLD START, not a capability limit, and `engine.lexicon` was built to be exactly this handle and
was never wired into the dialogue's sheet.

WHAT THIS IS NOT. It is not a chart, not an address space, not a ν. A gloss is an ANNOTATION ON
AN EXISTING OBJECT'S LINE: it gets no label, is never citable, never enters `Citable`, never
touches `group`, and cannot be the endpoint of an arrow. A gloss that could be cited would be a
claim the corpus never ingested.

RESOLUTION IS EXACT WHOLE-STRING MEMBERSHIP OR NOTHING. No tokenizer, no distance, no case
folding, no fragment matching, no ranking. `engine/faces.py`'s word-fragment anchoring was
killed for "growing a rule pile — the same failure as similarity, one layer up", and the
difference is exactly this: a whole declared name matches an authored face or it does not.

TWO TIERS, AND THE SECOND ONE IS TOTAL — stated rather than hidden, because it is this design's
one soft spot. Tier A is an AUTHORED face: the operator's own lexicon, exact match on the Lean
declaration name. Tier B is `engine.rmap.render`, a declared deterministic name→English
rendering, which always produces something and therefore always could. It travels wearing
`[REPO_DOC — unauthored]` so no reader can mistake a mechanical rendering for an authored one.

Spec: sent before this file existed. Controls c1-c11 in tests/test_gloss.py.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The tiers, as a closed vocabulary. A gloss whose provenance is not one of these does not
#: exist — the same shape every other declared thing in this codebase has.
AUTHORED, RENDERED = "authored", "rendered"

#: WHAT AN UNAUTHORED GLOSS WEARS ON THE WIRE. Tier B is total: it renders any well-formed name,
#: so its output can never be read as evidence that somebody decided anything. The tag is not
#: decoration — it is the difference between a fact and a convenience.
UNAUTHORED_TAG = "[REPO_DOC — unauthored]"

#: The chart this lane serves. One chart at v0: the boundary under measurement is english/lean,
#: and a lane that glossed every chart would be answering a question nobody asked.
GLOSSED_CHART = "lean"


@dataclass(frozen=True, slots=True)
class Gloss:
    """One handle. The name it was derived from, the reading, and which tier produced it."""

    name: str
    reading: str
    tier: str

    @property
    def line(self) -> str:
        """What goes on the wire, under the object's own line."""
        tag = "" if self.tier == AUTHORED else f"  {UNAUTHORED_TAG}"
        return f"reads as: {self.reading}{tag}"

    def as_record(self) -> dict:
        return {"name": self.name, "reading": self.reading, "tier": self.tier,
                "citable": False, "entered": "nothing — a gloss is an annotation on an "
                                             "object's line, not an object"}


def authored_faces(registry) -> dict:
    """formal surface -> the English face the operator authored for it. Exact keys only.

    VERBATIM SURFACES. `lexicon.Face` stores a surface unnormalized on purpose — Mathlib names
    keep their case and their namespace path — and this preserves that: the key is the declared
    name as written, and a lookup either hits it or does not. Case-folding here would be the
    matching this lane exists to avoid.
    """
    out: dict = {}
    for sense in (getattr(registry, "senses", None) or ()):
        core = getattr(sense, "core", None)
        if core is None:
            continue
        english = ""
        for face in (getattr(core, "formal_faces", None) or ()):
            if getattr(face, "kind", "") == "english" and not english:
                english = str(getattr(face, "surface", ""))
        if not english:
            english = str(getattr(core, "lemma", "") or "")
        if not english:
            continue
        for face in (getattr(core, "formal_faces", None) or ()):
            if getattr(face, "kind", "") == "formal":
                out.setdefault(str(getattr(face, "surface", "")), english)
    return out


def gloss_for(nu: str, faces: dict | None = None) -> Gloss | None:
    """The handle for one Lean object, or None when the line declares no name.

    THE ORDER IS THE WHOLE POLICY: an authored face wins, a rendering fills in, and a line that
    declares nothing gets nothing. There is no third source and no fallback that guesses.
    """
    from .rmap import render
    from .scaffold_lean import declared_name

    name = declared_name(nu or "")
    if not name:
        return None
    authored = (faces or {}).get(name)
    if authored:
        return Gloss(name=name, reading=str(authored), tier=AUTHORED)
    reading = render(name)
    return Gloss(name=name, reading=reading, tier=RENDERED) if reading else None


def glosses_for(region, faces: dict | None = None) -> dict:
    """slot -> Gloss for every Lean member of a region. Nothing else is touched.

    Keyed by SLOT rather than by label, because a label is assigned downstream and a handle
    keyed on it would be a second thing to keep in step with the labeller.
    """
    out: dict = {}
    for m in (getattr(region, "members", None) or ()):
        if getattr(m, "chart", "") != GLOSSED_CHART:
            continue
        g = gloss_for(getattr(m, "nu", "") or "", faces)
        if g is not None:
            out[m.slot] = g
    return out


def coverage(region, glosses: dict) -> dict:
    """How much of what was shown carried a handle, split by tier.

    MANDATORY ON EVERY MEASUREMENT THIS LANE PRODUCES. Without it a data gap reads as a
    mechanism failure: lean attachment staying flat means one thing when every Lean object
    carried an authored handle and something entirely different when none did.
    """
    lean = [m for m in (getattr(region, "members", None) or ())
            if getattr(m, "chart", "") == GLOSSED_CHART]
    got = [glosses[m.slot] for m in lean if m.slot in glosses]
    authored = sum(1 for g in got if g.tier == AUTHORED)
    return {"chart": GLOSSED_CHART, "shown": len(lean), "glossed": len(got),
            "authored": authored, "rendered": len(got) - authored,
            "fraction": round(len(got) / len(lean), 4) if lean else 0.0,
            "authored_fraction": round(authored / len(lean), 4) if lean else 0.0,
            "note": ("Coverage travels with every figure this lane produces. Flat attachment "
                     "over zero authored coverage is a fact about the DATA; flat attachment "
                     "over full coverage is a fact about the MECHANISM, and only this number "
                     "tells them apart.")}
