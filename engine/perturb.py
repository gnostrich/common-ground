"""A PERTURBATION IS A REGION RELAXATION. One call, one diagram, one mechanism.

This file exists because there were two. The sampler asked the medium to complete a region;
the window ran a different thing — a candidate list ordered by declared degree, cut to a call
budget, interrogated twelve pairs at a time — and the two stood side by side doing one job.
That is the shape `engine/region`'s own docstring calls forbidden, and the window had the worse
half of it: forty-eight claims out of thirty-seven thousand, each asked in isolation, which
reads exactly like a lookup because structurally it is one.

What replaces it is not a better candidate list. It is the region, unchanged, with the typed
input as ONE MORE OBJECT in it:

    typed text -> addressed exactly (gate 1, unchanged)
               -> entered into a region as [0|bias], beside arrow-rich provenance-near claims
               -> ONE call: declared arrows in, implied arrows in, medium completes the diagram
               -> arrows touching [0]        = ATTACHMENT: ephemeral, conditioning-only
               -> arrows among corpus objects = ordinary EXTRACTION, same as the walk's
               -> attachment points seed `engine/relax`; settlement runs; what moved is the answer

Every step after addressing is `engine.region` code the walk calls too: `build_region`,
`render_region`, `REGION_SYSTEM`, `parse_region`, `residuals`, `arrows_from`. This module holds
no wire format, no prompt, no parser and no kind vocabulary of its own. That is what makes it
one mechanism rather than two that agree.

**There is no budget, so there is nothing to disclaim.** The old path reported "48 of 28,398
candidates asked; the rest are UNMEASURED" — true, and a confession that the unit was wrong. A
region is the unit of measurement. It is a SAMPLE of the corpus and the window says so plainly,
but it is not a truncated interrogation of a list, because there is no list.

**The window extracts.** Arrows the medium draws among the corpus objects are real proposals at
extraction tier, identical in kind and warrant to the walk's, and they are returned for the
operator to send through the one inlet. Asking a question therefore does the same work the
sampler does — the corpus grows from being used.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MORPHISM — a proposer into D. The same proposer, the same prompt, pointed at a
region that has a boundary condition in it.
Q2 is why the bias must be IN the diagram: a typed input is an object with no morphisms until
morphisms are proposed for it, so it has no image under any functor and cannot propagate. It
is not enough to ask about it; it has to be an object the medium can draw arrows to.
Q5 is the load-bearing check and it passes ONLY as a REPLACEMENT. `engine/attach` is deleted
by this commit, not supplemented — standing beside it, this would be the second mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .corpus_state import CorpusSnapshot
from .region import (BEARS_ON, BIAS_CHART, REGION_SIZE, REGION_SYSTEM, Region, anchor_for,
                     arrows_from, build_region, parse_region, render_region, residuals)
from .relax import Relaxation, relax
from .types import WarrantTier

#: Attachment enters where every LM proposal enters, and cannot ground or clamp. It does not
#: enter at all, in fact — it evaporates — but the tier is stated because the operator is
#: standing on it while reading the answer.
ATTACH_TIER = WarrantTier.EXTRACTION


@dataclass(frozen=True, slots=True)
class Attachment:
    """One arrow the medium drew to the boundary condition. Ephemeral by construction.

    It is never journalled, never composed, never counted as an arrow and never in the atlas.
    That is not enforced here by remembering to: `region.arrows_from` drops anything touching
    the `bias` chart, so there is no route by which one of these becomes a Correspondence.
    """

    kind: str                                 # bears_on | same_claim | refines | instance_of
    dst_slot: str
    dst_chart: str
    dst_nu: str
    evidence: str
    tier: str = ATTACH_TIER.name

    @property
    def is_bias_only(self) -> bool:
        """True for `bears_on`. Kept as a property because the window prints the two apart:
        a question that is ABOUT a claim and a claim that RESTATES it are different facts."""
        return self.kind == BEARS_ON

    def as_record(self) -> dict[str, object]:
        return {"kind": self.kind, "tier": self.tier, "to": self.dst_slot[:16],
                "chart": self.dst_chart, "nu": self.dst_nu[:220],
                "evidence": self.evidence[:400], "ephemeral": True}


@dataclass(slots=True)
class Perturbation:
    """What one call produced: where the input attached, what else the region yielded, silence."""

    typed_slot: str = ""
    typed_chart: str = ""
    typed_nu: str = ""
    region: Region | None = None
    attachment: list[Attachment] = field(default_factory=list)
    #: Corpus-to-corpus arrows from the SAME call. Ordinary extraction; the window's own yield.
    extracted: list = field(default_factory=list)
    residual: object | None = None             # region.Residual — the full reading discipline
    void: int = 0
    calls: int = 0
    cost: float = 0.0
    error: str = ""
    #: The region could not be aimed — no live arrow anywhere to aim it at. Stated, because
    #: unstated it looks exactly like a region that was aimed.
    unanchored: bool = False
    note: str = ""

    @property
    def consulted(self) -> bool:
        """Was the medium actually asked? The battery's no-silent-zero property turns on this:
        silence after a call is a decline, silence before one is a filter, and the window has
        to be able to tell the operator which it was."""
        return self.calls > 0

    def trace(self) -> dict[str, object]:
        """WHAT WAS ASKED, of whom, over what — so silence is never a bare zero.

        The standing battery requires that every input yields either a conditioned region or
        this: which question was put, how many objects were seated in the diagram, and what
        came back. A silent zero with no trace is the failure this exists to make impossible.
        """
        return {
            "consulted": self.consulted,
            "question": ("complete the diagram: which corpus objects, and which of them bear "
                         "on the boundary condition at index 0"),
            "seated": self.members,
            "corpus_objects": max(0, self.members - 1),
            "declared_in": len(self.region.declared) if self.region else 0,
            "implied_in": len(self.region.implied) if self.region else 0,
            "attached": len(self.attachment),
            "extracted": len(self.extracted),
            "void": self.void,
            "unanchored": self.unanchored,
            "note": self.note,
            "error": self.error,
        }

    @property
    def seeds(self) -> set[str]:
        """Corpus addresses the boundary condition attached to. `engine/relax` starts here."""
        return {a.dst_slot for a in self.attachment}

    @property
    def members(self) -> int:
        return len(self.region.members) if self.region else 0

    @property
    def region_id(self) -> str:
        return self.region.region_id if self.region else ""

    def as_record(self) -> dict[str, object]:
        return {
            "typed_slot": self.typed_slot[:16], "typed_chart": self.typed_chart,
            "region_id": self.region_id, "members": self.members,
            "clamp": self.region.clamp[:16] if self.region else "",
            "declared": len(self.region.declared) if self.region else 0,
            "implied": len(self.region.implied) if self.region else 0,
            "attachment": [a.as_record() for a in self.attachment],
            "attached": len(self.attachment),
            "extracted": len(self.extracted),
            "void": self.void, "calls": self.calls, "cost": round(self.cost, 6),
            "error": self.error,
            "note": ("The typed input entered a REGION as one more object, over the pseudo-"
                     "chart `bias`, and one call completed the diagram. Arrows to the bias "
                     "object are attachment and are EPHEMERAL: conditioning-only, never "
                     "journalled, never composable, never counted. Arrows among the corpus "
                     "objects are ordinary extraction at the same tier the sampler produces. "
                     "The region is a SAMPLE of the corpus chosen by declared structure — it "
                     "is not the part that matches the question, and no text was compared."),
        }


def perturb(text: str, snapshot: CorpusSnapshot, transport, chart: str = "english",
            size: int = REGION_SIZE, quarantined: frozenset = frozenset()) -> Perturbation:
    """Put the typed text in a diagram and let the medium complete it. Exactly one call.

    THE TYPED TEXT GOES TO THE MEDIUM RAW. It used to be segmented by the claim extractor
    first, so a question or a bare topic that yielded no spans bounced before the field was
    ever consulted — and "the field did not respond" then meant a parser had filtered the
    input. That is an ingestion rule governing the bias path, the same class of defect as
    attachment inheriting the identity rule. The extractor's span-typing remains for corpus
    ingestion and for anything the operator proposes into the tape; a bias is neither.
    """
    from .normalize import address

    out = Perturbation()
    if snapshot.empty:
        out.error = "the corpus is empty"
        return out
    if not text.strip():
        out.error = "nothing was typed"
        return out

    slot, nu_value = address(chart, text, "assert")
    out.typed_slot, out.typed_chart, out.typed_nu = slot, chart, nu_value

    anchor = anchor_for(snapshot, slot, quarantined)
    region = build_region(snapshot, clamp=anchor, size=size, quarantined=quarantined,
                          bias=(slot, nu_value))
    out.region = region
    # A snapshot with no live arrow has no arrow-rich neighbourhood, so `anchor_for` returns
    # nothing and `build_region` falls back to the chart-spanning directory — the SAME region
    # for every question, with an empty declared section. That is a real state of the corpus,
    # but silently it reads as "your question landed here", so it is named. The shape was
    # measured: the on-disk snapshot carries 69,446 slots and zero arrows, because the arrows
    # live in the proposer's journal and are laid over the read view by the caller. A caller
    # that forgets makes every perturbation identical and nothing says so.
    out.unanchored = not anchor
    if not anchor:
        out.note = ("no arrow-rich neighbourhood exists: this snapshot carries no declared "
                    "arrow, so the region could not be aimed and is the corpus's most "
                    "chart-spanning directory instead. Every input gets the same one. If the "
                    "corpus does have arrows, they were not laid over this read view.")
    if len(region.members) < 2:
        out.error = ("no corpus claim carries a declared arrow, so there is no region to "
                     "perturb — the field has no structure for a boundary condition to reach")
        return out

    try:
        raw, usage = transport(REGION_SYSTEM, render_region(region))
    except Exception as exc:                      # a dead call is reported, never silent
        out.error = f"{type(exc).__name__}: {exc}"
        return out
    out.calls = 1
    out.cost = float((usage or {}).get("cost") or 0.0)

    proposals = parse_region(raw, region)
    res = residuals(proposals, region)
    out.residual = res
    out.void = len(res.void)

    for p in res.attachment:
        other = p.dst if p.src.chart == BIAS_CHART else p.src
        out.attachment.append(Attachment(kind=p.kind, dst_slot=other.slot,
                                         dst_chart=other.chart, dst_nu=other.nu,
                                         evidence=p.evidence))
    # The corpus-to-corpus half of the same answer. `arrows_from` drops bias-touching
    # proposals itself, so this cannot leak an attachment into the extraction stream.
    out.extracted = arrows_from(res.novel, proposer="lm", prompt_hash="region")
    return out


def relax_from(perturbation: Perturbation, text: str, snapshot: CorpusSnapshot,
               chart: str = "english") -> Relaxation:
    """Settle the corpus with the boundary condition applied at its attachment points.

    The arrows the same call extracted are laid over the READ VIEW so the perturbation can
    travel them. They are extraction tier and are written nowhere; `Moved.weakest_tier` reports
    EXTRACTION on any path that used one, which is how the operator sees that a hop rests on a
    proposal made in this very call rather than on a confirmed arrow.
    """
    return relax(text, snapshot, chart, seeds_from=perturbation.seeds or None,
                 extra_arrows=list(perturbation.extracted) or None)
