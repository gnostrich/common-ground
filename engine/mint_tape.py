"""Mint tape + the memory kernel K — now LIVE, gate-guarded.

The tape watches the settlement's residual stream for structure. A residual that decays like
a single mode has a rank-1 Hankel block; extra singular values above the noise mean the
settlement is carrying dynamics the single-mode picture does not explain.

**K is live (operator-authorized).** `act_on_mint` no longer refuses; it reports whether a
residual clears the Hankel gate, and `MintController.consider` promotes a fast-tape entry
(a proposal + its verdict) into the slow corpus IFF:

    Hankel(residual) > second-FDT floor   (the tape's own gate)
    AND conservative-extension            (the promotion does not overwrite an existing
                                           corpus entry with a different value)

This is the NELL hazard the build quarantined for v0; the gate is the whole safety. Promotion
is gate-only — nothing reaches the corpus around it — every promotion is logged in
`MintController.log` and reversible via `revert()`, and a planted-noise control asserts that a
residual below the floor never promotes. `MINT_ENABLED` is the master switch (now true in the
seed); with it false `act_on_mint` still refuses, so the quarantine is one seed-flip away in
either direction. Null cell (v) uses the tape's effective rank: ingesting the same corpus
twice under distinct provenance must produce zero rank growth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from . import EngineError
from .constants import HANKEL_WINDOW, MINT_ENABLED, MINT_THRESHOLD_MULTIPLE
from .linalg import effective_rank, hankel, singular_values
from .types import SettledBlock


@dataclass(slots=True)
class TapeReading:
    singular_values: list[float]
    effective_rank: int
    window: int
    stream_length: int
    threshold: float
    mint_flag: bool
    mint_enabled: bool = MINT_ENABLED

    def as_record(self) -> dict[str, object]:
        return {
            "hankel_sv": self.singular_values,
            "effective_rank": self.effective_rank,
            "window": self.window,
            "stream_length": self.stream_length,
            "mint_threshold": self.threshold,
            "mint_flag": self.mint_flag,
            "mint_enabled": self.mint_enabled,
        }


def residual_stream(settled: SettledBlock) -> list[float]:
    """F_t - F_final over the settling trace. Non-negative and decaying under a monotone cert."""
    if not settled.f_trace:
        return []
    final = settled.f_trace[-1]
    return [max(0.0, f - final) for f in settled.f_trace]


def read_tape(
    stream: Sequence[float],
    second_fdt_floor: float,
    window: int = HANKEL_WINDOW,
) -> TapeReading:
    """Hankel spectrum of the residual stream, with the promotion threshold."""
    matrix = hankel(stream, window)
    svs = singular_values(matrix) if matrix else []
    threshold = MINT_THRESHOLD_MULTIPLE * second_fdt_floor
    top = svs[0] if svs else 0.0
    return TapeReading(
        singular_values=svs,
        effective_rank=effective_rank(svs),
        window=window,
        stream_length=len(stream),
        threshold=threshold,
        mint_flag=bool(svs) and top > threshold > 0.0,
        mint_enabled=MINT_ENABLED,
    )


def rank_growth(before: TapeReading, after: TapeReading) -> int:
    """Change in effective rank. Null cell (v) requires this to be zero on a duplicate."""
    return after.effective_rank - before.effective_rank


def act_on_mint(reading: TapeReading, *, enabled: bool | None = None) -> bool:
    """Does this residual clear the Hankel gate for promotion?

    Raises when mint is DISABLED — the quarantine — so a caller cannot read `mint_flag`
    directly and quietly act while the switch is off. When enabled, returns the gate result
    (Hankel top singular value above the second-FDT-derived threshold). This is only the
    numeric half of the gate; `MintController.consider` also requires conservative-extension.
    """
    enabled = MINT_ENABLED if enabled is None else enabled
    if not enabled:
        raise EngineError(
            "mint is OFF (mint_enabled=false); the tape is logged only and carries no "
            "authority. Enabling it is plastic under gate 4 and requires a cold re-anneal."
        )
    return bool(reading.mint_flag and reading.threshold > 0.0)


@dataclass(slots=True)
class Promotion:
    """One K decision: whether a fast-tape entry entered the slow corpus, and why."""
    slot: str
    value: str
    source: str          # e.g. "conversation:accepted"
    hankel_top: float
    threshold: float
    gate_pass: bool      # Hankel gate cleared
    conservative: bool   # does not overwrite an existing entry with a different value
    promoted: bool
    reason: str

    def as_record(self) -> dict[str, object]:
        return {
            "slot": self.slot, "value": self.value, "source": self.source,
            "hankel_top": self.hankel_top, "threshold": self.threshold,
            "gate_pass": self.gate_pass, "conservative": self.conservative,
            "promoted": self.promoted, "reason": self.reason,
        }


@dataclass(slots=True)
class MintController:
    """The live memory kernel: promotes fast-tape entries into the slow corpus, gate-only.

    The corpus is the durable settled section (slot -> value). `consider` is the ONLY way an
    entry reaches it, and it reaches it iff both halves of the gate hold. Every decision is
    appended to `log`, and `revert` undoes a promotion — so the tape entering the corpus is
    always auditable and reversible.
    """
    enabled: bool = MINT_ENABLED
    corpus: dict[str, str] = field(default_factory=dict)
    log: list[Promotion] = field(default_factory=list)

    def consider(self, slot: str, value: str, reading: TapeReading,
                 source: str = "tape") -> Promotion:
        gate_pass = act_on_mint(reading, enabled=self.enabled)   # raises if disabled
        existing = self.corpus.get(slot)
        conservative = existing is None or existing == value
        promoted = bool(gate_pass and conservative)
        reason = ("promoted through the gate" if promoted
                  else "blocked: not conservative (would overwrite a settled value)"
                  if not conservative else "blocked: residual below the Hankel floor (noise)")
        top = reading.singular_values[0] if reading.singular_values else 0.0
        p = Promotion(slot, value, source, top, reading.threshold, gate_pass, conservative,
                      promoted, reason)
        if promoted:
            self.corpus[slot] = value
        self.log.append(p)
        return p

    def revert(self, promotion: Promotion) -> bool:
        """Undo a promotion. Returns True if the corpus entry was removed."""
        if promotion.promoted and self.corpus.get(promotion.slot) == promotion.value:
            del self.corpus[promotion.slot]
            return True
        return False

    def promoted(self) -> list[Promotion]:
        return [p for p in self.log if p.promoted]
