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
1.0 down to 0.1, re-annealing from the seed's uniform prior. Warm resumes at the final rung
from a retained state. At the low rungs the entropic term is small and the mirror flow is
near-replicator, whose limit depends on where it started — so the two arms land in
different places exactly when a block is contested, and in the same place when it is not.
If F were minimized at a single fixed rung the arms would coincide and the paired meter
would measure nothing; the anneal is what gives the pairing something to measure.

T2 is the anneal's *schedule* parameter and is the only thing here that behaves like a
temperature. `beta` is not: it is the arm's verification budget (1x and 4x under PREREG),
and it enters as `beta / T2`, the coefficient on the entropic term. Two different numbers,
two different jobs.

## Floor

    floor(loop) = max(0, hol_cold(loop) - shadow(loop))

Shadow is the chart closure defect *declared in the seed*, not measured from the run.
`seed/shadow.json` declares it zero, which is the conservative setting: it cannot deflate
the floor. Warm is reported alongside as path debt, per the paired-loop-side invariant.

## Gate 5

`read_floor` requires a `NullBatteryReport` that passed **on the same seed hash**. There
is no other function in this module that returns a floor.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MEASURE — the invariant read off the settled measure; hol on Pi_1(B).
Q3 motivated it. Holonomy is only measurable where the subgraph has cycles; on a forest it
is necessarily zero, and reporting that zero as agreement would be reporting a fact about
the graph's shape as a fact about the corpus.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from . import EngineError, GateViolation
from .constants import (
    CAST_T2_DECAY,
    CAST_T2_END,
    CAST_T2_START,
    STUDENTIZE_MIN_SCALE,
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

    The anneal's T2 divides the verification budget, so the effective coefficient on the
    entropic term is `beta / T2` and the schedule sharpens the objective monotonically as
    it runs. T2 is the anneal's own schedule parameter; `beta` is the budget the arm was
    given.
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


class OpenWalkError(EngineError):
    """A holonomy was requested over something that is not a cycle in Q."""


def verify_cycle(
    loop: LoopSpec,
    edge_weight: Mapping[tuple[str, str], float],
) -> None:
    """Raise unless `loop` is a genuine cycle in the Q graph.

    Four conditions, all of them load-bearing (the tree-null repair):

    1. **length >= 3.** A two-slot "loop" is the backtracking walk `u -> v -> u`. That is a
       closed walk containing no cycle, and on a tree theory says its holonomy is zero.
       Backtracking is now handled by `measured_shadow` instead, where its residual is a
       property of the translation rather than of the ledger.
    2. **no immediate backtracking** anywhere in the walk, for the same reason.
    3. **every edge present in Q**, closing edge included. A loop spec built from fiber
       membership can name an edge the graph does not have.
    4. **closed** — guaranteed by `LoopSpec.edges()` wrapping, checked here anyway.

    It raises rather than skipping. Skipping a missing edge is what let the meter report
    `TV(start, transported)` for an OPEN walk — the start state compared against a state
    transported somewhere else entirely, which measured more "holonomy" than the genuine
    cycle it should have been dominated by.
    """
    slots = loop.slots
    if len(slots) < 3:
        raise OpenWalkError(
            f"loop {loop.id}: {len(slots)} slots. Holonomy is defined on cycles of length "
            ">= 3; a two-slot walk backtracks and is a measured-shadow channel, not a loop."
        )
    if len(set(slots)) != len(slots):
        raise OpenWalkError(f"loop {loop.id}: repeats a slot, so the walk is not a cycle")

    edges = loop.edges()
    for i, (u, v) in enumerate(edges):
        if u == v:
            raise OpenWalkError(f"loop {loop.id}: self-loop at {u}")
        nxt = edges[(i + 1) % len(edges)]
        if nxt == (v, u):
            raise OpenWalkError(
                f"loop {loop.id}: immediate backtracking {u} -> {v} -> {u}"
            )
        w = edge_weight.get((u, v)) or edge_weight.get((v, u)) or 0.0
        if w <= 0.0:
            raise OpenWalkError(
                f"loop {loop.id}: edge ({u}, {v}) is not in Q, so the walk is open. "
                "Refusing rather than skipping it."
            )


def holonomy(
    loop: LoopSpec,
    p: Mapping[str, Vector],
    edge_weight: Mapping[tuple[str, str], float],
) -> float:
    """Transport the start state once around a verified cycle and measure the residual."""
    verify_cycle(loop, edge_weight)
    start = p.get(loop.slots[0])
    if start is None:
        return 0.0
    carried: Vector = list(start)
    for u, v in loop.edges():
        target = p.get(v)
        if target is None:
            raise OpenWalkError(
                f"loop {loop.id}: no settled state for {v}; the walk cannot be closed"
            )
        w = edge_weight.get((u, v)) or edge_weight.get((v, u)) or 0.0
        carried = mix(carried, target, _alpha(w))
    return total_variation(start, carried)


def path_transport_disagreement(
    walk: LoopSpec,
    p: Mapping[str, Vector],
    edge_weight: Mapping[tuple[str, str], float],
) -> float:
    """`TV(start, transported)` along an OPEN walk. **Diagnostic only — never a floor.**

    This is the quantity `holonomy` used to return when it silently skipped a missing
    closing edge. It is retained under an honest name because it is occasionally useful to
    see how far a chain of transports moves a state, but it is not a holonomy: the start and
    end points are different slots, so the number says nothing about path dependence and
    nothing may be read from it about the ledger.
    """
    start = p.get(walk.slots[0])
    if start is None:
        return 0.0
    carried: Vector = list(start)
    for u, v in walk.edges()[: len(walk.slots) - 1]:
        target = p.get(v)
        if target is None:
            continue
        w = edge_weight.get((u, v)) or edge_weight.get((v, u)) or 0.0
        if w > 0.0:
            carried = mix(carried, target, _alpha(w))
    return total_variation(start, carried)


def measured_shadow(
    u: str,
    v: str,
    p: Mapping[str, Vector],
    edge_weight: Mapping[tuple[str, str], float],
) -> float:
    """Per-edge closure defect `eps_e`: the residual of the backtrack walk `u -> v -> u`.

    This is what the tree-null repair does with backtracking instead of counting it as
    holonomy. Going out along an edge and back is not a cycle, so it cannot carry path
    dependence — but it is not nothing either. Transport is a contraction toward its target,
    so `T_{v->u} . T_{u->v} != id` whenever the two settled states differ, and the residual
    measures how much the round trip through this correspondence loses.

    That is exactly what shadow is supposed to declare. `seed/shadow.json` states a closure
    defect per chart pair *a priori*; this measures the same quantity *a posteriori*. The
    two are compared in `shadow_calibration`, and a cross-chart edge where the measured
    defect exceeds what the seed declared is translator drift.
    """
    pu, pv = p.get(u), p.get(v)
    if pu is None or pv is None:
        return 0.0
    w = edge_weight.get((u, v)) or edge_weight.get((v, u)) or 0.0
    if w <= 0.0:
        return 0.0
    a = _alpha(w)
    out = mix(list(pu), pv, a)
    back = mix(out, pu, a)
    return total_variation(pu, back)


def edge_weight_map(edges: Sequence[QEdge]) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    for e in edges:
        key = (e.u, e.v)
        out[key] = max(out.get(key, 0.0), e.weight)
    return out


# --- shadow -----------------------------------------------------------------------


def _declared_defect(
    cu: Chart | None, cv: Chart | None, shadow_cfg: Mapping[str, object]
) -> float:
    """The seed's a-priori closure defect for one chart pair."""
    if cu is None or cv is None:
        return 0.0
    if cu == cv:
        return float(shadow_cfg.get("intra_chart", {}).get("declared_defect", 0.0))  # type: ignore[union-attr]
    pairs = {
        frozenset(entry["charts"]): float(entry["declared_defect"])  # type: ignore[index]
        for entry in shadow_cfg.get("pairs", [])  # type: ignore[union-attr]
    }
    return pairs.get(frozenset((cu, cv)), 0.0)


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
class ShadowCalibration:
    """Measured closure defect against the seed's declared shadow, per edge.

    The tree-null repair turned backtracking from a bogus holonomy into this. `eps_measured`
    is the residual of the round trip `u -> v -> u`; `declared` is what `seed/shadow.json`
    says the closure defect for that chart pair is, a priori. The seed declares zero, so any
    measured defect is drift — and on a cross-chart edge that is **translator drift**: the
    round trip through the correspondence loses something the seed said it would not.

    This is a calibration channel, not a verdict. Nothing subtracts `eps_measured` from a
    floor; shadow subtraction still uses the declared value, because a measured defect that
    deflated its own floor would be exactly the resample-of-the-observation pattern gate 6
    forbids.
    """

    u: str
    v: str
    crosses_charts: bool
    eps_measured: float
    declared: float

    @property
    def drift(self) -> float:
        return self.eps_measured - self.declared

    def as_record(self) -> dict[str, object]:
        return {
            "u": self.u, "v": self.v, "crosses_charts": self.crosses_charts,
            "eps_measured": self.eps_measured, "declared": self.declared,
            "drift": self.drift,
        }


@dataclass(slots=True)
class MeterResult:
    seed_hash: str
    measurements: list[LoopMeasurement] = field(default_factory=list)
    surrogate: dict[str, float] = field(default_factory=dict)
    #: Per-edge measured-vs-declared closure defect. Standard output, every run.
    shadow_calibration: list[ShadowCalibration] = field(default_factory=list)
    #: Blocks that carry no verified cycle, so no holonomy is defined on them.
    no_cycle_support: list[str] = field(default_factory=list)
    #: loop_id -> that loop's own label-permutation draws (PREREG-AMENDMENT-3). R2 pools
    #: them leave-one-out; kept raw so the pooling is auditable rather than pre-baked.
    loop_nulls: dict[str, list[float]] = field(default_factory=dict)

    def mean_floor(self, beta: float | None = None) -> float:
        rows = [
            m for m in self.measurements if beta is None or m.beta == beta
        ]
        if not rows:
            return 0.0
        return sum(m.floor for m in rows) / len(rows)

    def translator_drift(self) -> list[ShadowCalibration]:
        """Cross-chart edges whose measured closure defect exceeds what the seed declared.

        Sorted worst first. An empty list means every correspondence closed as well as the
        seed said it would; a long one means the translation is losing something the seed
        did not account for, and the shadow declaration is the thing to revisit.
        """
        return sorted(
            (c for c in self.shadow_calibration if c.crosses_charts and c.drift > 0.0),
            key=lambda c: (-c.drift, c.u, c.v),
        )

    def shadow_summary(self) -> dict[str, float]:
        rows = self.shadow_calibration
        cross = [c for c in rows if c.crosses_charts]
        return {
            "edges": float(len(rows)),
            "cross_chart_edges": float(len(cross)),
            "max_drift": max((c.drift for c in rows), default=0.0),
            "max_translator_drift": max((c.drift for c in cross), default=0.0),
            "mean_eps_measured": (
                sum(c.eps_measured for c in rows) / len(rows) if rows else 0.0
            ),
        }

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
) -> tuple[list[LoopMeasurement], SettledBlock, SettledBlock, dict[str, list[float]],
           list[ShadowCalibration]]:
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
    nulls: dict[str, list[float]] = {}

    # The measured-shadow channel. Every Q edge in the block contributes its round-trip
    # closure defect, compared against what the seed declared for that chart pair. This is
    # what backtracking became once it stopped being counted as holonomy.
    calibration: list[ShadowCalibration] = []
    for edge in sorted(block.edges, key=lambda e: (e.u, e.v)):
        cu, cv = chart_of.get(edge.u), chart_of.get(edge.v)
        crosses = cu != cv
        declared = _declared_defect(cu, cv, shadow_cfg)
        calibration.append(ShadowCalibration(
            u=edge.u, v=edge.v, crosses_charts=crosses,
            eps_measured=measured_shadow(edge.u, edge.v, cold.p, weights),
            declared=declared,
        ))

    for loop in loops:
        if not set(loop.slots) <= members:
            continue
        # A spec that is not a verified cycle never reaches the meter: the constructor
        # refuses to emit one, and this is the second line of defence.
        verify_cycle(loop, weights)
        h_cold = holonomy(loop, cold.p, weights)
        h_warm = holonomy(loop, warm.p, weights)
        sh = loop_shadow(loop, chart_of, shadow_cfg)
        nulls[loop.id] = loop_permutation_null(
            loop, warm.p, cold.p, weights, sh, seed_hash
        )
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
    return out, warm, cold, nulls, calibration


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


def loop_permutation_null(
    loop: LoopSpec,
    warm_p: Mapping[str, Vector],
    cold_p: Mapping[str, Vector],
    weights: Mapping[tuple[str, str], float],
    shadow: float,
    seed_hash: str,
    trials: int = SURROGATE_TRIALS,
) -> list[float]:
    """One loop's own second-FDT label-permutation null (PREREG-AMENDMENT-3).

    Per trial, each slot on the loop independently supplies its state from the warm arm or
    the cold arm, and the holonomy is recomputed from that mixture. Under the no-effect
    hypothesis — the two arms settled to the same place on this loop, so there is no path
    dependence — which arm supplies which slot cannot matter and the recomputed floors
    match the observed one. Under real path dependence the all-cold assignment stands above
    the mixtures.

    Note the support. A loop with `k` slots has `2**k` distinct assignments, so the null's
    upper tail is coarse for small loops: a 2-slot loop has four, and no q95 can then sit
    below the maximum, which the all-cold assignment attains. This is a property of
    permutation tests at small n — the smallest achievable p-value is one over the number
    of permutations — and it is why `pooled_loop_null` exists.
    """
    rng = DRNG("loop-perm", seed_hash, loop.id)
    slots = list(loop.slots)
    draws: list[float] = []
    for _ in range(trials):
        mixed: dict[str, Vector] = {}
        for s in slots:
            source = cold_p if rng.random() < 0.5 else warm_p
            state = source.get(s)
            if state is not None:
                mixed[s] = state
        draws.append(max(0.0, holonomy(loop, mixed, weights) - shadow))
    return draws


def pooled_loop_nulls(
    draws_by_loop: Mapping[str, Sequence[float]],
    quantile_q: float = SURROGATE_QUANTILE,
) -> dict[str, float]:
    """Leave-one-out pooled thresholds from per-loop label-permutation draws.

    `loop_permutation_null` gives each loop its own null, but that null has only `2**k`
    distinct values and the all-cold assignment — the observed floor — sits at or below the
    maximum. q95 of four points *is* the maximum, so a loop can never exceed its own null
    and the criterion flags nothing at any floor. That is measured, not argued: on a
    synthetic contested corpus, 0 of 4 loops could flag.

    Pooling fixes the support. Each loop's threshold is the q95 of every *other* loop's
    permuted floors, so the null still consists of nothing but relabelled observations — it
    is a permutation null, not a resample of the answer — while a loop's own value can no
    longer inflate the bar it has to clear.

    A single loop has no leave-one-out pool. Rather than fall back to the degenerate
    self-comparison, the loop is given `inf` and the caller reports the rule as
    inconclusive: a permutation null needs more than one exchangeable unit.
    """
    out: dict[str, float] = {}
    for loop_id in draws_by_loop:
        others = [d for lid, ds in draws_by_loop.items() if lid != loop_id for d in ds]
        out[loop_id] = quantile(others, quantile_q) if others else float("inf")
    return out


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return 0.5 * (ordered[mid - 1] + ordered[mid])


def _mad(values: Sequence[float]) -> float:
    """Median absolute deviation. A scale estimate that a single outlier cannot inflate."""
    if not values:
        return 0.0
    centre = _median(values)
    return _median([abs(v - centre) for v in values])


@dataclass(slots=True)
class LoopThreshold:
    """One loop's flagging decision, with the units it was decided in."""

    loop_id: str
    threshold: float
    observed: float
    mode: str            # "studentized" | "raw-loo"
    centre: float = 0.0
    scale: float = 1.0

    @property
    def flags(self) -> bool:
        return self.observed > self.threshold

    def as_record(self) -> dict[str, object]:
        return {
            "loop_id": self.loop_id, "threshold": self.threshold,
            "observed": self.observed, "mode": self.mode,
            "centre": self.centre, "scale": self.scale, "flags": self.flags,
        }


def studentized_loop_thresholds(
    draws_by_loop: Mapping[str, Sequence[float]],
    floors_by_loop: Mapping[str, float],
    quantile_q: float = SURROGATE_QUANTILE,
) -> dict[str, LoopThreshold]:
    """**REJECTED REPAIR — retained as evidence, decides nothing.**

    Attempted once under PREREG-AMENDMENT-3's repair window and rejected on its controls.
    `ground_truth_rediscovery` uses `pooled_loop_nulls`; nothing calls this. It is kept so
    the failure is pinned by a test rather than remembered, on the same terms as every other
    superseded computation in this repo.

    **Why it failed.** Not merely inconclusive — it *inverted* the result. On the mandated
    direction-one control (clean synthetic run plus one planted gap), the planted gap's
    loop, floor 0.218, studentized to **-0.089** and did not flag, while a numerically
    negligible loop at floor 5.5e-08 studentized to **+4.573** and did. Miss rate 1.0 where
    raw leave-one-out gives 0.0.

    The reason is structural, not a tuning problem. A loop's floor and its permutation
    null's scale are *the same quantity*: both are produced by warm/cold disagreement on
    that loop. A loop with a real gap has a large floor **and** a large null MAD. Dividing
    the first by the second divides out precisely the signal the rule exists to detect, and
    what remains is dominated by loops whose null is nearly degenerate — where a tiny
    absolute difference over a tinier scale yields a large ratio.

    Studentizing is the right instinct when scale is a nuisance parameter. Here it is the
    estimand.

    Leave-one-out pooling in absolute units keeps the exchangeability limitation it was
    meant to mitigate: loops differ in slot count and edge weight, so one loud loop raises
    every other loop's threshold. That limitation **stays open**, recorded as such.

    The mechanics below are as specified, so the record is checkable: each loop's permuted
    floors centred on their own median and divided by their own null MAD, observed floors
    put in the same units, leave-one-out pooling across loops, and a per-loop fallback to
    raw pooling where the null scale is degenerate below `STUDENTIZE_MIN_SCALE`.

    Raw LOO pooling works — it gives the null usable support where a single loop's `2**k`
    draws cannot — but it assumes loops are exchangeable with one another, and they are
    not: they differ in slot count and edge weight, so their permutation nulls differ in
    *scale*. One loud loop therefore raised every other loop's threshold in absolute units.

    Studentizing removes the scale difference. Each loop's permuted floors are centred on
    their own median and divided by their own null MAD, and its observed floor is put in
    the same units. What pools is then a set of dimensionless deviations, so a loud loop
    contributes its *shape*, not its magnitude.

    Gate 6 is unaffected. Centre and scale are computed from the loop's own permutation
    draws, which are relabelled observations — nothing is resampled and no distribution is
    borrowed from outside the exchange. Studentizing a permutation statistic is still a
    permutation test.

    Where a loop's null MAD is degenerate (below `STUDENTIZE_MIN_SCALE` — every permutation
    landing on the same value, so there is no scale to divide by) that loop falls back to
    raw leave-one-out pooling and says so in `mode`. The fallback is per loop and reported
    per loop, never a silent global switch.
    """
    stats: dict[str, tuple[float, float]] = {}
    for loop_id, draws in draws_by_loop.items():
        stats[loop_id] = (_median(draws), _mad(draws))

    scaled = {
        loop_id: (
            [(d - stats[loop_id][0]) / stats[loop_id][1] for d in draws]
            if stats[loop_id][1] > STUDENTIZE_MIN_SCALE
            else None
        )
        for loop_id, draws in draws_by_loop.items()
    }

    out: dict[str, LoopThreshold] = {}
    for loop_id, draws in draws_by_loop.items():
        centre, scale = stats[loop_id]
        floor = floors_by_loop.get(loop_id, 0.0)
        pool = [
            v for other, vs in scaled.items()
            if other != loop_id and vs is not None for v in vs
        ]
        if scaled[loop_id] is not None and pool:
            out[loop_id] = LoopThreshold(
                loop_id=loop_id,
                threshold=quantile(pool, quantile_q),
                observed=(floor - centre) / scale,
                mode="studentized",
                centre=centre,
                scale=scale,
            )
            continue

        raw_pool = [d for other, ds in draws_by_loop.items() if other != loop_id for d in ds]
        out[loop_id] = LoopThreshold(
            loop_id=loop_id,
            threshold=quantile(raw_pool, quantile_q) if raw_pool else float("inf"),
            observed=floor,
            mode="raw-loo",
        )
    return out


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
