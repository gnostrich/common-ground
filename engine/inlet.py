"""The single inlet — the one and only write-path to the fast tape.

Every proposer enters here and only here: me (typing), the LM (Opus), and — same signature,
a translator in front — another instance. `FastTape.propose(delta, source_tag)` is the whole
door. No source can write past it; all are equal at the bottom of the gradient, all at
proposal (extraction) tier. The inlet confers no warrant. Warrant rises in exactly one other
place — the gate (K, `engine/mint_tape.MintController`), where a proposal that cleared
Hankel ∧ conservative is promoted to the slow corpus. Inlet in, gate up: two doors, no others.

The "one write-path" is the naturality guarantee. `tests/test_inlet.py` asserts by AST that
the tape's entry list is appended to in exactly one place — `propose` — so if any source
could reach the tape another way, the build has failed. Behaviourally: a clamp-eligible
warrant is refused at the inlet (a clamp is not a proposal), and me/LM/instance proposals are
indistinguishable in tier once inside.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from . import EngineError
from .types import Delta, Warrant, WarrantTier


@dataclass(frozen=True, slots=True)
class Proposal:
    """A delta on the fast tape, tagged by the source that proposed it."""
    delta: Delta
    source_tag: str          # "me" | "lm" | "instance:<id>"

    @property
    def tier(self) -> WarrantTier:
        return self.delta.warrant.tier


@dataclass(slots=True)
class FastTape:
    """p_fast. The one place proposals live before the gate. Appended to only by `propose`."""
    _entries: list[Proposal] = field(default_factory=list)

    def propose(self, delta: Delta, source_tag: str) -> Proposal:
        """The single write-path. Enter at proposal tier; a clamp cannot enter here.

        Warrant does not rise at the inlet, so a clamp-eligible (kernel / test-receipt)
        warrant is refused — clamps are applied at settlement, they are not proposed. Every
        source calls exactly this method with exactly this signature.
        """
        if delta.warrant.clamp_eligible:
            raise EngineError(
                "the inlet accepts proposals only: a clamp-eligible (kernel/receipt) warrant "
                "cannot enter the fast tape. Warrant rises at the gate, never at the inlet."
            )
        if not str(source_tag).strip():
            raise EngineError("every proposal must carry a source tag")
        proposal = Proposal(delta=delta, source_tag=str(source_tag))
        self._entries.append(proposal)          # the ONLY append to the tape
        return proposal

    @property
    def entries(self) -> tuple[Proposal, ...]:
        return tuple(self._entries)

    def deltas(self) -> list[Delta]:
        return [p.delta for p in self._entries]

    def by_source(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self._entries:
            counts[p.source_tag] = counts.get(p.source_tag, 0) + 1
        return counts


def as_proposal_tier(delta: Delta, detail: str) -> Delta:
    """Re-stamp a delta to proposal (extraction) tier — used by translators before the inlet.

    A source that holds a clamp in its own instance does not carry that clamp across: the
    translated delta enters the target as a proposal like any other, so no source surrenders
    or imports warrant.
    """
    return dataclasses.replace(
        delta, warrant=Warrant(tier=WarrantTier.EXTRACTION, detail=detail))


def stub_translator(delta: Delta, instance_id: str) -> Delta:
    """A stand-in for T_ij at the per-delta level: re-stamp as an external proposal.

    The real translator (engine/coupling.translate) does this ledger-wide with provenance
    attribution; this stub is enough to prove the inlet accepts a third source identically.
    """
    return as_proposal_tier(delta, f"external proposal from instance {instance_id}")
