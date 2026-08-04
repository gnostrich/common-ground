"""Correspondence — the base category's morphisms, as CLAIMS.

The gap is filled. A correspondence is a **directed, typed morphism between two slots**, and
it enters the engine the way every other assertion does: as a claim, through the one inlet,
at the tier its proposer earns. There is **no side registry as a write path** — the
correspondence set is DERIVED state, read off accepted correspondence claims and never
written directly. That is what keeps `propose()` the single door.

    src: (chart, slot_address)   dst: (chart, slot_address)   kind: same_claim|refines|instance_of

**The three kinds, and the one that isn't.**

- `same_claim` — an isomorphism class. Composable and invertible *in principle*, but the
  reverse arrow is a **separate proposal**: it may never arrive, or may disagree, and that
  mismatch is signal rather than noise. **Holonomy loops run only on `same_claim` arrows.**
- `refines` — directed, non-invertible. Recorded, contributes coupling structure, and is
  **excluded from holonomy loops**.
- `instance_of` — directed, non-invertible. Same treatment as `refines`.

There is deliberately **no `approximates` kind**. Uncertainty about a correspondence is
expressed as **low warrant on a `same_claim` proposal**, never as a fuzzy morphism type:
fuzziness lives in the warrant ladder, not in the structure (GATES sentence 9). A fuzzy arrow
type would put a similarity score back into the algebra, which is the defect this build spent
its whole life deleting.

**Granularity is SLOT-LEVEL** at v0 — a faithful, *non-compositional* approximation of the
functorial thing. The designed v-next is TERM-LEVEL: a lexicon-entry ~ Lean-name correspondence
that *induces* slot correspondences compositionally. Recorded in `seed/DECISIONS.json` as
`correspondence_granularity`, not left implicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from . import EngineError
from .hashing import join_hash
from .types import Delta, WarrantTier

#: The correspondence chart's name. A correspondence claim is an ordinary claim in its own
#: chart (a seed manifest row — move 1, additive), so it is addressed, valued, settled and
#: contested by exactly the same machinery as any other claim, and gate 8 applies to it
#: unchanged: its value derives from its own content, never from surrounding text.
CORRESPONDENCE_CHART = "correspondence"

SAME_CLAIM = "same_claim"
REFINES = "refines"
INSTANCE_OF = "instance_of"

#: The three legal kinds. `approximates` is deliberately absent — see the module docstring.
KINDS: frozenset[str] = frozenset({SAME_CLAIM, REFINES, INSTANCE_OF})

#: Only these arrows may carry holonomy. `refines` / `instance_of` are directed and
#: non-invertible, so a round trip through one is not a round trip at all.
LOOP_ELIGIBLE_KINDS: frozenset[str] = frozenset({SAME_CLAIM})


@dataclass(frozen=True, slots=True)
class Correspondence:
    """One directed, typed arrow between two slot addresses."""

    src_chart: str
    src_slot: str
    dst_chart: str
    dst_slot: str
    kind: str
    tier: WarrantTier = WarrantTier.EXTRACTION
    proposer: str = ""
    prompt_hash: str = ""
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise EngineError(
                f"unknown correspondence kind {self.kind!r}; legal kinds are "
                f"{sorted(KINDS)}. There is no 'approximates' kind: uncertainty is low "
                "warrant on a same_claim proposal, never a fuzzy morphism type (GATES 9)."
            )
        if self.src_slot == self.dst_slot:
            raise EngineError("a correspondence needs two distinct slots; this is one claim")
        if self.src_chart == self.dst_chart:
            raise EngineError(
                "correspondence is cross-chart only: exact addressing already owns "
                "intra-chart identity (gate 1), so an intra-chart arrow would re-introduce "
                "similarity by the back door"
            )

    @property
    def loop_eligible(self) -> bool:
        return self.kind in LOOP_ELIGIBLE_KINDS

    @property
    def provisional(self) -> bool:
        """True while the arrow is below the promotion floor — reportable, never promoted."""
        from .types import promotable

        return not promotable(self.tier)

    @property
    def pair(self) -> tuple[str, str]:
        """The unordered endpoint pair, for fiber construction."""
        return ((self.src_slot, self.dst_slot) if self.src_slot < self.dst_slot
                else (self.dst_slot, self.src_slot))

    def surface(self) -> str:
        """The claim's surface: a canonical, content-derived statement of the arrow.

        This is what gets addressed, so a correspondence claim has an exact address like any
        other claim — two proposers asserting the same arrow collide on one slot, and the
        reverse arrow is a *different* claim with a *different* address, which is precisely
        why asymmetry can be detected instead of assumed away.
        """
        return (f"{self.src_chart}:{self.src_slot} -{self.kind}-> "
                f"{self.dst_chart}:{self.dst_slot}")

    def id(self) -> str:
        return join_hash("corr", self.src_slot, self.dst_slot, self.kind)[:16]

    def reverse(self) -> "Correspondence":
        """The opposite arrow — a DIFFERENT claim, which must be proposed separately."""
        return Correspondence(
            src_chart=self.dst_chart, src_slot=self.dst_slot,
            dst_chart=self.src_chart, dst_slot=self.src_slot,
            kind=self.kind, tier=self.tier, proposer=self.proposer,
            prompt_hash=self.prompt_hash, evidence=self.evidence,
        )

    def as_record(self) -> dict[str, object]:
        return {
            "id": self.id(), "src_chart": self.src_chart, "src_slot": self.src_slot,
            "dst_chart": self.dst_chart, "dst_slot": self.dst_slot, "kind": self.kind,
            "tier": self.tier.name, "provisional": self.provisional,
            "loop_eligible": self.loop_eligible, "proposer": self.proposer,
            "prompt_hash": self.prompt_hash, "evidence": list(self.evidence),
        }


_ARROW = " -"
_ARROW_END = "-> "


def parse_surface(surface: str) -> tuple[str, str, str, str, str] | None:
    """Inverse of `Correspondence.surface`: (src_chart, src_slot, kind, dst_chart, dst_slot)."""
    if _ARROW not in surface or _ARROW_END not in surface:
        return None
    left, rest = surface.split(_ARROW, 1)
    kind, right = rest.split(_ARROW_END, 1)
    if kind not in KINDS or ":" not in left or ":" not in right:
        return None
    src_chart, src_slot = left.split(":", 1)
    dst_chart, dst_slot = right.split(":", 1)
    return src_chart.strip(), src_slot.strip(), kind, dst_chart.strip(), dst_slot.strip()


def correspondences_from_deltas(deltas: Sequence[Delta]) -> list[Correspondence]:
    """DERIVE the correspondence set from accepted correspondence-chart claims.

    This is the only way arrows enter the structure. They are claims that came through the
    inlet, so the write-path is unchanged and `tests/test_inlet.py`'s one-write-path assertion
    still covers them. A claim read as `F` is a *denial* of the arrow and contributes nothing;
    an `N`/`B` reading is unsettled and likewise contributes nothing.
    """
    out: list[Correspondence] = []
    for d in deltas:
        if d.chart != CORRESPONDENCE_CHART or d.value != "T":
            continue
        parsed = parse_surface(d.surface)
        if parsed is None:
            continue
        src_chart, src_slot, kind, dst_chart, dst_slot = parsed
        try:
            out.append(Correspondence(
                src_chart=src_chart, src_slot=src_slot,
                dst_chart=dst_chart, dst_slot=dst_slot, kind=kind,
                tier=d.warrant.tier, proposer=d.provenance.extractor_id,
                prompt_hash=d.provenance.content_hash[:16],
                evidence=(d.provenance.locator,),
            ))
        except EngineError:
            continue          # a malformed or intra-chart arrow is refused, never coerced
    return out


def loop_pairs(arrows: Iterable[Correspondence]) -> frozenset[tuple[str, str]]:
    """Endpoint pairs eligible to carry holonomy — `same_claim` only."""
    return frozenset(a.pair for a in arrows if a.loop_eligible)


def structural_pairs(arrows: Iterable[Correspondence]) -> frozenset[tuple[str, str]]:
    """Every endpoint pair, including `refines` / `instance_of`.

    These contribute coupling structure (an equivalence-prior edge, gate 2 energy) but are
    excluded from loops, so they can tie the graph together without manufacturing holonomy.
    """
    return frozenset(a.pair for a in arrows)


def asymmetries(arrows: Sequence[Correspondence]) -> list[Correspondence]:
    """`same_claim` arrows whose reverse has NOT been proposed.

    Reported as OPEN rather than assumed symmetric: the reverse is a separate claim, and its
    absence (or disagreement) is signal about the translation, not a bookkeeping gap to close
    silently.
    """
    present = {(a.src_slot, a.dst_slot) for a in arrows if a.loop_eligible}
    return [a for a in arrows
            if a.loop_eligible and (a.dst_slot, a.src_slot) not in present]
