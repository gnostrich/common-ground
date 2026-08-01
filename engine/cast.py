"""Gumbel-max sequential commit, with the T2 geometric anneal 1.0 -> 0.1 (x0.9/sweep).

Casting is the discrete half of the cast/settle split: settling produces a distribution,
casting commits to a value. At v0 casting is **withheld** — KICKOFF section 3, P3 reports
soft state only, except where a block's fiber contains a kernel clamp, and those may cast.
`cast()` refuses unless that condition is passed in explicitly, so the withholding is a
property of the code rather than of the operator remembering.

Sequential means each commitment conditions the ones after it: a slot's score picks up a
coupling bonus from neighbours already committed this sweep. That is what makes casting a
joint commitment over a block rather than independent per-slot rounding, and it is why the
draw order is fixed by slot id instead of left to iteration order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from . import GateViolation
from .constants import (
    BVALUES,
    CAST_T2_DECAY,
    CAST_T2_END,
    CAST_T2_START,
    EPS,
    LAMBDA,
    NBV,
)
from .hashing import DRNG
from .linalg import Vector
from .types import Block, BValue, Clamp


def t2_schedule() -> list[float]:
    """1.0, 0.9, 0.81, ... down to 0.1 inclusive of the floor."""
    out: list[float] = []
    t = CAST_T2_START
    while t > CAST_T2_END:
        out.append(t)
        t *= CAST_T2_DECAY
    out.append(CAST_T2_END)
    return out


@dataclass(slots=True)
class CastResult:
    block_id: str
    commitment: dict[str, BValue]
    sweeps: int
    final_t2: float
    reason: str


def may_cast(block: Block, clamps: Sequence[Clamp]) -> bool:
    """v0 casting policy: only blocks whose fiber includes a kernel clamp.

    Note this is strictly narrower than gate 3's clamp-eligibility. A CI receipt grounds
    a clamp but does not license casting at v0; only a Lean kernel-accept does, because
    the kernel-checked theorems are the arm PREREG actually runs restatement loops over.
    """
    from .types import WarrantTier

    members = set(block.slots)
    return any(
        c.slot in members and c.warrant.tier is WarrantTier.KERNEL for c in clamps
    )


def cast(
    block: Block,
    p: Mapping[str, Vector],
    seed_hash: str,
    clamps: Sequence[Clamp] = (),
    allow: bool = False,
) -> CastResult:
    """Commit a block to discrete b-values. Deterministic given `seed_hash` and inputs."""
    if not allow:
        raise GateViolation(
            0,
            f"casting withheld at v0 for block {block.id}: no kernel clamp in its fiber. "
            "Report soft state instead (KICKOFF section 3, P3).",
        )

    clamp_map: dict[str, BValue] = {c.slot: c.value for c in clamps if c.slot in block.slots}
    adj = block.neighbours()
    order = sorted(block.slots)
    rng = DRNG("cast", seed_hash, block.id)

    commitment: dict[str, BValue] = dict(clamp_map)
    schedule = t2_schedule()

    for t2 in schedule:
        for slot in order:
            if slot in clamp_map:
                continue
            ps = p[slot]
            base = [math.log(max(ps[k], EPS)) for k in range(NBV)]
            for neighbour, weight in adj.get(slot, ()):
                committed = commitment.get(neighbour)
                if committed is None:
                    continue
                base[BVALUES.index(committed)] += LAMBDA * weight

            best_k, best_score = 0, -math.inf
            for k in range(NBV):
                score = base[k] + t2 * rng.gumbel()
                if score > best_score:
                    best_k, best_score = k, score
            commitment[slot] = BVALUES[best_k]

    return CastResult(
        block_id=block.id,
        commitment=commitment,
        sweeps=len(schedule),
        final_t2=schedule[-1],
        reason="kernel-clamp-in-fiber",
    )
