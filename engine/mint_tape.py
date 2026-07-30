"""Mint tape: residual stream -> Hankel singular values. LOGGED ONLY. Mint is OFF.

The tape watches the settlement's residual stream for structure. A residual that decays
like a single mode has a rank-1 Hankel block; extra singular values above the noise mean
the settlement is carrying dynamics the single-mode picture does not explain.

Nothing acts on it at v0. `MINT_ENABLED` is False in SEED.lock, `act_on_mint()` raises
unconditionally, and the threshold — 3x the second-FDT surrogate floor — is computed and
written to the log so it can be read later, never to gate anything now. Null cell (v)
uses the tape's effective rank: ingesting the same corpus twice under distinct provenance
must produce zero rank growth, because a duplicate is not new information.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    mint_enabled: bool = False

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
    """F_t - F_final over the settling trace.

    Non-negative and decaying whenever the certificate is monotone, which is what makes
    its Hankel spectrum interpretable as relaxation modes rather than noise.
    """
    if not settled.f_trace:
        return []
    final = settled.f_trace[-1]
    return [max(0.0, f - final) for f in settled.f_trace]


def read_tape(
    stream: Sequence[float],
    second_fdt_floor: float,
    window: int = HANKEL_WINDOW,
) -> TapeReading:
    """Hankel spectrum of the residual stream. Computes the threshold; does not act."""
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
        # Logged, never acted on. A True here is a note in the run log and nothing else.
        mint_flag=bool(svs) and top > threshold > 0.0,
        mint_enabled=MINT_ENABLED,
    )


def rank_growth(before: TapeReading, after: TapeReading) -> int:
    """Change in effective rank. Null cell (v) requires this to be zero on a duplicate."""
    return after.effective_rank - before.effective_rank


def act_on_mint(reading: TapeReading) -> None:
    """Never callable at v0.

    Present so that any future code that tries to *use* the tape has to come through a
    function that refuses, rather than reading `mint_flag` directly and quietly acting.
    """
    raise EngineError(
        "mint is OFF at v0 (SEED.lock: mint_enabled=false). The tape is logged only; "
        f"mint_flag={reading.mint_flag} carries no authority and must not gate anything. "
        "Enabling mint is plastic under gate 4 and requires a cold re-anneal."
    )
