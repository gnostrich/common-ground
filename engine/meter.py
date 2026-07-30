"""The paired warm/cold loop meter, shadow subtraction, and the floor.

## Holonomy

A loop is a closed path through slots. Transport along a Q edge `u -> v` with weight `w`
is the relaxation

    T_{u->v}(q) = (1 - a) * q + a * p_v ,      a = w / (1 + w)

that is, the edge pulls a carried distribution toward the settled state at its far end,
with strength set by the equivalence prior. Holonomy is the residual after going all the
way round:

    hol(loop) = TV( p_start , T_loop(p_start) )

Two properties make this the right quantity. It vanishes identically when every settled
state on the loop agrees — perfect agreement has no holonomy, which is the null behaviour
cells (iii)-(v) test for. And it is path-ordered: the operators do not commute unless the
states already agree, so a loop that fails to close is reporting genuine path dependence
rather than a summed disagreement.

## Warm and cold

The arms differ in their anneal, not their objective. Cold runs the full T2 schedule from
1.0 down to 0.1, re-annealing from the seed's uniform prior. Warm resumes at the final
temperature from a retained state. At low temperature the entropic term is small and the
mirror flow is near-replicator, whose limit depends on where it started — so the two arms
land in different places exactly when a block is contested, and in the same place when it
is not. If F were minimized at a fixed temperature the arms would coincide and the paired
meter would measure nothing; the anneal is what gives the pairing something to measure.

## Floor

    floor(loop) = max(0, hol_cold(loop) - shadow(loop))

Shadow is the chart closure defect *declared in the seed*, not measured from the run.
`seed/shadow.json` declares it zero, which is the conservative setting: it cannot deflate
the floor. Warm is reported alongside as path debt, per the paired-loop-side invariant.

## Gate 5

`read_floor` requires a `NullBatteryReport` that passed **on the same seed hash**. There
is no other function in this module that returns a floor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from . import GateViolation
from .constants import (
    CAST_T2_DECAY,
    CAST_T2_END,
    CAST_T2_START,
    SURROGATE_QUANTILE,
    SURROGATE_TRIALS,
)
from .hashing import DRNG, quantile
from .linalg import Vector, mix, total_variation
from .settle import settle
from .types import (
    Block,
    Chart,
    Clamp,
    LoopSpec,
    NullBatteryReport,
    NullStatus,
    QEdge,
    SettledBlock,
)


# --- annealing --------------------------------------------------------------------


def _temperatures() -> list[float]:
    out: list[float] = []
    t = CAST_T2_START
    while t > CAST_T2_END:
        out.append(t)
        t *= CAST_T2_DECAY
    out.append(CAST_T2_END)
    return out


def anneal(
    block: Block,
    evidence: Mapping[str, Vector],
    priors: Mapping[str, Vector],
    beta: float,
    clamps: Sequence[Clamp] = (),
    retained: Mapping[str, Vector] | None = None,
) -> SettledBlock:
    """Settle under the T2 anneal.

    `retained is None` is the cold arm: run the whole schedule from T2 = 1.0, each step
    warm-starting from the last. `retained` given is the warm arm: resume directly at the
    final temperature from the carried state, skipping the schedule.

    Temperature enters as an effective inverse temperature `beta / T2`, so the schedule
    sharpens the objective monotonically as it runs.
    """
    if retained is not None:
        return settle(
            block, evidence, priors, beta / CAST_T2_END, clamps=clamps, warm_from=retained
        )

    state: Mapping[str, Vector] | None = None
    result: SettledBlock | None = None
    trace: list[float] = []
    backtracks = 0
    for t2 in _temperatures():
        result = settle(
            block, evidence, priors, beta / t2, clamps=clamps, warm_from=state
        )
        state = result.p
        trace.extend(result.f_trace)
        backtracks += result.backtracks
        if result.certificate == "violated":
            break

    assert result is not None  # _temperatures() is never empty
    result.f_trace = trace
    result.backtracks = backtracks
    return result


# --- holonomy ---------------------------------------------------------------------


def _alpha(weight: float) -> float:
    return weight / (1.0 + weight)


def holonomy(
    loop: LoopSpec,
    p: Mapping[str, Vector],
    edge_weight: Mapping[tuple[str, str], float],
) -> float:
    """Transport the start state once around the loop and measure the residual."""
    start = p.get(loop.slots[0])
    if start is None:
        return 0.0
    carried: Vector = list(start)
    for u, v in loop.edges():
        target = p.get(v)
        if target is None:
            continue
        w = edge_weight.get((u, v)) or edge_weight.get((v, u)) or 0.0
        if w <= 0.0:
            continue
        carried = mix(carried, target, _alpha(w))
    return total_variation(start, carried)


def edge_weight_map(edges: Sequence[QEdge]) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for e in edges:
        key = (e.u, e.v)
        out[key] = max(out.get(key, 0.0), e.weight)
    return out


# --- shadow -----------------------------------------------------------------------


def loop_shadow(
    loop: LoopSpec, chart_of: Mapping[str, Chart], shadow_cfg: Mapping[str, object]
) -> float:
    """The declared closure defect for this loop's chart crossings.

    Summed over the loop's chart-crossing edges. With `seed/shadow.json` declaring zero,
    this is zero and shadow subtraction is a no-op — deliberately, so that no measured
    holonomy is absorbed into an undeclared defect.
    """
    pairs = {
        frozenset(entry["charts"]): float(entry["declared_defect"])  # type: ignore[index]
        for entry in shadow_cfg.get("pairs", [])  # type: ignore[union-attr]
    }
    intra = float(shadow_cfg.get("intra_chart", {}).get("declared_defect", 0.0))  # type: ignore[union-attr]

    total = 0.0
    for u, v in loop.edges():
        cu, cv = chart_of.get(u), chart_of.get(v)
        if cu is None or cv is None:
            continue
        total += intra if cu == cv else pairs.get(frozenset((cu, cv)), 0.0)
    return total


# --- results ----------------------------------------------------------------------


@dataclass(slots=True)
class LoopMeasurement:
    loop_id: str
    kind: str
    beta: float
    warm: float
    cold: float
    shadow: float
    floor: float
    path_debt: float
    slots: tuple[str, ...]
    warm_source: str = "in-process-partial-anneal"


@dataclass(slots=True)
class MeterResult:
    seed_hash: str
    measurements: list[LoopMeasurement] = field(default_factory=list)
    surrogate: dict[str, float] = field(default_factory=dict)

    def mean_floor(self, beta: float | None = None) -> float:
        rows = [
            m for m in self.measurements if beta is None or m.beta == beta
        ]
        if not rows:
            return 0.0
        return sum(m.floor for m in rows) / len(rows)

    def modes(self, beta: float | None = None) -> list[LoopMeasurement]:
        """Loops sorted by floor, descending. PREREG R3 reports these verbatim."""
        rows = [m for m in self.measurements if beta is None or m.beta == beta]
        return sorted(rows, key=lambda m: (-m.floor, m.loop_id))


def measure(
    block: Block,
    loops: Sequence[LoopSpec],
    evidence: Mapping[str, Vector],
    priors: Mapping[str, Vector],
    chart_of: Mapping[str, Chart],
    shadow_cfg: Mapping[str, object],
    beta: float,
    seed_hash: str,
    clamps: Sequence[Clamp] = (),
    retained: Mapping[str, Vector] | None = None,
) -> tuple[list[LoopMeasurement], SettledBlock, SettledBlock]:
    """Run both arms on one block and measure every loop inside it.

    The warm arm's starting state matters, and it is reported rather than assumed. With
    an externally `retained` state — P3's settlement carried into P4 — the warm arm is
    the real cross-phase arm KICKOFF section 7.3 describes. Without one, it falls back to
    resuming from the *first rung* of the anneal (the high-temperature state), which is a
    genuinely different trajectory to the cold arm's full descent.

    What it must not do is resume from the cold arm's own answer: that would start the
    warm arm at the fixed point and report `path_debt = 0` as a tautology rather than a
    measurement. Every measurement carries `warm_source` so a reader can tell which arm
    was actually run.
    """
    cold = anneal(block, evidence, priors, beta, clamps=clamps, retained=None)

    if retained is not None:
        warm_seed: Mapping[str, Vector] = retained
        warm_source = "retained-cross-phase"
    else:
        warm_seed = settle(
            block, evidence, priors, beta / CAST_T2_START, clamps=clamps, warm_from=None
        ).p
        warm_source = "in-process-partial-anneal"

    warm = anneal(block, evidence, priors, beta, clamps=clamps, retained=warm_seed)

    weights = edge_weight_map(block.edges)
    members = set(block.slots)
    out: list[LoopMeasurement] = []
    for loop in loops:
        if not set(loop.slots) <= members:
            continue
        h_cold = holonomy(loop, cold.p, weights)
        h_warm = holonomy(loop, warm.p, weights)
        sh = loop_shadow(loop, chart_of, shadow_cfg)
        out.append(
            LoopMeasurement(
                loop_id=loop.id,
                kind=loop.kind,
                beta=beta,
                warm=h_warm,
                cold=h_cold,
                shadow=sh,
                floor=max(0.0, h_cold - sh),
                path_debt=max(0.0, h_warm - h_cold),
                slots=loop.slots,
                warm_source=warm_source,
            )
        )
    return out, warm, cold


# --- surrogates -------------------------------------------------------------------


def surrogate_floor_distribution(
    measurements: Sequence[LoopMeasurement],
    seed_hash: str,
    trials: int = SURROGATE_TRIALS,
) -> list[float]:
    """Bootstrap band for the mean floor.

    Resamples loops with replacement. This is the noise band that "~0 within surrogate
    noise" is read against in null cell (iv) and PREREG R3/R4; without it, "approximately
    zero" would be an eyeball judgement rather than a pre-registered test.
    """
    if not measurements:
        return []
    rng = DRNG("surrogate", seed_hash)
    n = len(measurements)
    out: list[float] = []
    for _ in range(trials):
        total = 0.0
        for _ in range(n):
            total += measurements[rng.randrange(n)].floor
        out.append(total / n)
    return out


def second_fdt_surrogate_floor(
    measurements: Sequence[LoopMeasurement],
    seed_hash: str,
    trials: int = SURROGATE_TRIALS,
) -> float:
    """The second-kind (fluctuation-dissipation) surrogate floor.

    Permutes the warm/cold labels loop by loop and recomputes the mean floor. Under the
    null that the two arms are exchangeable — no path dependence — this distribution
    matches the observed floor. Its upper quantile is the reference the mint threshold is
    quoted against (3x, LOGGED ONLY, mint OFF).
    """
    if not measurements:
        return 0.0
    rng = DRNG("fdt2", seed_hash)
    draws: list[float] = []
    for _ in range(trials):
        total = 0.0
        for m in measurements:
            swap = rng.random() < 0.5
            value = m.warm if swap else m.cold
            total += max(0.0, value - m.shadow)
        draws.append(total / len(measurements))
    return quantile(draws, SURROGATE_QUANTILE)


def within_noise(observed: float, surrogate: Sequence[float]) -> bool:
    """True if `observed` sits at or below the surrogate's upper quantile."""
    if not surrogate:
        return observed == 0.0
    return observed <= quantile(surrogate, SURROGATE_QUANTILE)


# --- gate 5 -----------------------------------------------------------------------


def read_floor(
    result: MeterResult,
    nulls: NullBatteryReport,
    seed_hash: str,
    beta: float | None = None,
) -> float:
    """Gate 5. The only path in this codebase that yields a floor value.

    Refuses unless the null battery passed on this exact seed hash. A battery from a
    different seed is not evidence about this one — that is the whole point of hashing
    the seed in the first place.
    """
    if nulls.seed_hash != seed_hash:
        raise GateViolation(
            5,
            f"null battery was run on seed {nulls.seed_hash[:12]} but the floor is being "
            f"read on seed {seed_hash[:12]}",
        )
    if nulls.status is not NullStatus.PASS:
        raise GateViolation(
            5,
            f"null battery status is {nulls.status.value}; no floor may be read until it "
            "passes on this seed hash",
        )
    if result.seed_hash != seed_hash:
        raise GateViolation(
            5,
            f"meter result carries seed {result.seed_hash[:12]}, expected {seed_hash[:12]}",
        )
    return result.mean_floor(beta)
