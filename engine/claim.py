"""THE AUTHORSHIP PULLBACK: the operator claims a sentence the medium said.

THE DERIVATION, because this is read off the object rather than designed. The operator's
utterance is a candidate object approaching the category, and the type system exposes exactly
two independent binary coordinates plus one constructible arrow:

  OBJECTHOOD   AUTHORSHIP or nothing — the utterance is a claim of the operator's, or it is a
               pure boundary condition and not an object at all. Binary because objecthood is
               binary. (assert / brainstorm)
  PERSISTENCE  discard or keep — the input adjoins a transient object to the diagram, and the
               question is whether that extension survives settling. Binary because a colimit
               is either taken or not. (retain)

The 2x2 is FORCED AND COMPLETE: the product of two two-element sets. No fifth state is
constructible.

THIS MODULE IS THE ONE ARROW. Firing `claim` on something the medium said constructs a NEW
object: the same surface text, the operator's authorship, entering through the ordinary inlet.
It is a VERB, not a state — an arrow the operator fires, not a place the system sits — and it
is available in any mode at any time, because the MODE governs the PROMPT'S standing and never
the gesture's. The gesture IS assert.

THIS IS NOT A NEW WRITE-POINT. The gesture invokes the EXISTING `perturb.retain` write-point
with authorship warrant and `claimed_from` provenance. The closed set — `perturb.retain`,
`walk.arrow`, `aging.decay`, `mz.promote` — is unchanged (OI-33), and a claim implemented as
any other path must trip the existing write-point control. A gesture that quietly opened a
fifth door would be the tape growing a second entrance, which is the one thing the inlet rule
exists to prevent.

ALWAYS RETAIN, and it is not a convenience: claiming-to-discard is incoherent. The gesture's
whole content is "this becomes mine", and an object that vanishes after settling was never
taken.

"ACCEPT" DOES NOT EXIST AND CANNOT BE ADDED (OI-41). It would be warrant increasing by
approval WITHOUT authorship — a third arrow up the tier poset, which has exactly two lifts: K
promotes by measurement, authorship enters by assertion. An accept button is an arrow that is
not in the diagram, and its absence is constitutional rather than an omission.

THE PULLBACK IS AUDITABLE. `claimed_from` names the record the surface came from, so a later
reader can see that this AUTHORSHIP claim began as something a model said and which act
produced it. Laundering is prevented by the gesture being explicit, not by hoping nobody
routes around it: in-session agreement, however enthusiastic, confers nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .mode import ASSERT
from .types import WarrantTier

#: What a claimed object enters at. The operator asserted it; that is what AUTHORSHIP means.
CLAIM_TIER = WarrantTier.AUTHORSHIP

#: Claiming always retains. Claiming-to-discard is incoherent — the gesture's content is that
#: this becomes the operator's, and an object discarded after settling was never taken.
CLAIM_RETAINS = True


@dataclass(frozen=True, slots=True)
class Claim:
    """One firing of the pullback."""

    surface: str               # BYTE-IDENTICAL to what was displayed. No paraphrase.
    chart: str
    claimed_from: str          # the record id the surface came from
    source_mode: str           # the mode the ORIGINAL act ran in, kept for audit
    tier: WarrantTier = CLAIM_TIER
    retains: bool = CLAIM_RETAINS
    #: The gesture is always an assertion. The mode of the act that produced the SOURCE is
    #: recorded above; it does not travel into the claim, because the mode governs the
    #: prompt's standing and never the gesture's.
    mode: str = ASSERT

    def __post_init__(self) -> None:
        if not (self.surface or "").strip():
            raise ValueError("a claim needs a surface; there is nothing to assert")
        if not (self.claimed_from or "").strip():
            raise ValueError(
                "a claim needs `claimed_from`: the pullback is auditable or it is laundering. "
                "Without the source record nobody can see that this AUTHORSHIP claim began as "
                "something a model said.")

    def as_record(self) -> dict[str, object]:
        return {"surface": self.surface, "chart": self.chart, "tier": self.tier.name,
                "mode": self.mode, "retains": self.retains,
                "claimed_from": self.claimed_from, "source_mode": self.source_mode,
                "note": ("the authorship pullback: the operator asserted a sentence the medium "
                         "produced. Same surface, operator warrant, source recorded. This is "
                         "one of exactly two lifts up the tier poset — the other is K, which "
                         "promotes by measurement (OI-41).")}


def claim(surface: str, chart: str, claimed_from: str, source_mode: str = "") -> Claim:
    """Fire the pullback. The surface travels VERBATIM: a paraphrase would be a new claim
    wearing the old one's provenance."""
    return Claim(surface=surface, chart=chart, claimed_from=claimed_from,
                 source_mode=source_mode or ASSERT)


def lifts() -> tuple[str, ...]:
    """The COMPLETE set of ways warrant rises. Stated as a function so it is assertable."""
    return ("K promotes by measurement", "authorship enters by assertion")
