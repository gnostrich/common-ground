"""Mirror descent on F over contested blocks, with a monotone F-trace certificate.

The map is entropic (exponentiated gradient / multiplicative weights), which is the
natural geometry for the probability simplex: iterates stay strictly positive, no
projection step is needed, and the update is a single elementwise multiply.

    p_i <- normalize( p_i * exp(-eta * grad_i) )

`eta = 0.1` is the nominal step from SEED.lock. The certificate asserts that F never
rises, so the step is halved whenever it would — up to SETTLE_MAX_BACKTRACKS times — and
each halving is counted into the run log rather than hidden. If no descending step can be
found, settling stops and the certificate is stamped `violated`; it never silently ascends.
"""

from __future__ import annotations

import math
from typing import Mapping, Sequence

from . import GateViolation
from .constants import (
    EPS,
    ETA,
    NBV,
    SETTLE_GRAD_TOL,
    SETTLE_MAX_BACKTRACKS,
    SETTLE_MAX_ITERS,
)
from .energy import FreeEnergy
from .linalg import Vector, normalize_simplex, uniform_simplex
from .types import Block, Clamp, SettledBlock


def _clamp_vector(index: int) -> Vector:
    """One-hot with an EPS floor, so log(p) stays finite in F's entropy term."""
    v = [EPS] * NBV
    v[index] = 1.0
    return normalize_simplex(v)


def initial_state(
    block: Block,
    clamps: Mapping[str, Clamp] | None = None,
    warm_from: Mapping[str, Vector] | None = None,
) -> dict[str, Vector]:
    """Build the starting state.

    `warm_from` is the warm arm: settlement resumes from a previously settled state
    rather than from the seed's uniform prior. The cold arm passes `None`, which is what
    makes a cold run reproducible from the seed hash alone.
    """
    from .constants import BVALUE_INDEX

    clamps = clamps or {}
    state: dict[str, Vector] = {}
    for s in block.slots:
        c = clamps.get(s)
        if c is not None:
            state[s] = _clamp_vector(BVALUE_INDEX[c.value])
        elif warm_from is not None and s in warm_from:
            state[s] = normalize_simplex(warm_from[s])
        else:
            state[s] = uniform_simplex(NBV)
    return state


def settle(
    block: Block,
    evidence: Mapping[str, Vector],
    priors: Mapping[str, Vector],
    beta: float,
    clamps: Sequence[Clamp] = (),
    warm_from: Mapping[str, Vector] | None = None,
) -> SettledBlock:
    """Run mirror descent to stationarity. Returns the settled block plus its certificate."""

    clamp_map: dict[str, Clamp] = {}
    for c in clamps:
        # Redundant with Clamp.__post_init__, and deliberately so: gate 3 is cheap to
        # re-check and expensive to get wrong.
        if not c.warrant.clamp_eligible:
            raise GateViolation(
                3,
                f"clamp on slot {c.slot} carries tier {c.warrant.tier.name}, "
                "which does not ground",
            )
        if c.slot in block.slots:
            clamp_map[c.slot] = c

    f = FreeEnergy(
        slots=tuple(block.slots),
        evidence=dict(evidence),
        priors=dict(priors),
        edges=tuple(block.edges),
        beta=beta,
        clamped=frozenset(clamp_map),
    )

    p = initial_state(block, clamp_map, warm_from)
    f_before = f.value(p)
    f_current = f_before
    trace = [f_current]
    backtracks = 0
    certificate = "monotone"
    iterations = 0
    grad_norm = 0.0

    for iterations in range(1, SETTLE_MAX_ITERS + 1):
        grad = f.gradient(p)
        grad_norm = f.stationarity(p, grad)
        if grad_norm < SETTLE_GRAD_TOL:
            break

        step = ETA
        accepted = False
        for _ in range(SETTLE_MAX_BACKTRACKS + 1):
            candidate = dict(p)
            for s, g in grad.items():
                ps = p[s]
                # Shift by the max to keep exp() away from overflow; the shift cancels
                # in the renormalization.
                shift = max(-step * gk for gk in g)
                candidate[s] = normalize_simplex(
                    [ps[k] * math.exp(-step * g[k] - shift) for k in range(NBV)]
                )
            f_next = f.value(candidate)
            if f_next <= f_current + 1e-12:
                p = candidate
                f_current = f_next
                trace.append(f_current)
                accepted = True
                break
            step *= 0.5
            backtracks += 1

        if not accepted:
            # No descending step exists at any admissible size. Report, do not ascend.
            certificate = "violated"
            break

    return SettledBlock(
        block_id=block.id,
        p=p,
        f_before=f_before,
        f_after=f_current,
        certificate=certificate,
        iterations=iterations,
        backtracks=backtracks,
        grad_norm=grad_norm,
        f_trace=trace,
        clamped=tuple(sorted(clamp_map)),
    )


def verify_monotone(trace: Sequence[float], tol: float = 1e-9) -> bool:
    """Independent re-check of a logged F-trace.

    Used by the null battery and the audit so that the certificate is verified from the
    log rather than trusted from the writer.
    """
    return all(b <= a + tol for a, b in zip(trace, trace[1:]))
