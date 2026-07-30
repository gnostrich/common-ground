"""The free energy F, and its gradient.

    F(p) = sum_i <p_i, e_i>                        evidence energy (from deltas)
         + lambda2 * sum_i <p_i, r_i>              lexicon-prior energy   [gate 2]
         + (lambda/2) * sum_(u,v) w_uv ||p_u-p_v||^2   equivalence-prior energy [gate 2]
         - (1/beta) * sum_i H(p_i)                 entropic regularizer

Both prior terms are additive energies. There is no code path from a prior to a clamp;
the clamp set is a separate argument, and `Clamp` can only be constructed from a
clamp-eligible warrant (gate 3). That is gate 2 discharged structurally rather than by
convention.

F is convex in p: the first two terms are linear, the coupling term is a positive
semidefinite quadratic, and negative entropy is convex. Mirror descent under the entropic
map therefore converges, and the monotone certificate in `settle.py` is a real check on
the implementation rather than a hope about the objective.

beta is the inverse temperature. The PREREG arms are beta in {1x, 4x}: larger beta means
less entropic smoothing, so the settled state is sharper and contest is less easily
dissolved into uncertainty.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .constants import BVALUE_INDEX, EPS, LAMBDA, LAMBDA2, NBV
from .linalg import Vector
from .types import BValue, Delta, QEdge


def evidential_identity(d: Delta) -> tuple[str, str, str, str]:
    """What makes two deltas the same piece of evidence.

    Slot, value, which extractor said it, and the *content* hash of the document it came
    from — deliberately not the document's id or source label. Re-ingesting one corpus
    under a second provenance label therefore adds no evidence (null cell v: zero cold
    residue, zero rank growth), while two genuinely distinct documents asserting the same
    claim keep distinct content hashes and both count. Corroboration survives;
    double-counting does not.
    """
    return (d.slot, d.value, d.provenance.extractor_id, d.provenance.content_hash)


def dedupe_deltas(deltas: Sequence[Delta]) -> list[Delta]:
    """Collapse deltas that carry the same evidence. Keeps the first, deterministically."""
    seen: dict[tuple[str, str, str, str], Delta] = {}
    for d in sorted(deltas, key=lambda x: (x.slot, x.value, x.provenance.extractor_id, x.provenance.content_hash, x.provenance.locator)):
        seen.setdefault(evidential_identity(d), d)
    return list(seen.values())


def evidence_from_deltas(deltas: Sequence[Delta]) -> dict[str, Vector]:
    """Accumulate per-slot evidence energy from candidate deltas.

    Supporting a value *lowers* its energy, weighted by the extractor's confidence and
    the warrant tier. Two extractors that disagree leave a slot with two low-energy
    values, which is exactly the shape that produces a settled distribution with mass on
    `B` (contested) rather than a spurious winner.

    Deduplication happens here rather than at the call site so that no ingestion path can
    forget it and silently double-count a re-ingested source.
    """
    e: dict[str, Vector] = {}
    for d in dedupe_deltas(deltas):
        vec = e.setdefault(d.slot, [0.0] * NBV)
        vec[BVALUE_INDEX[d.value]] -= d.confidence * d.warrant.weight
    return e


def lexicon_prior(slots: Sequence[str], leaning: Mapping[str, BValue] | None = None) -> dict[str, Vector]:
    """Per-slot lexicon-prior energy.

    With no lexicon present the prior is flat (all zeros), which contributes a constant
    to F and nothing to the gradient. A pre-minted entry supplies a `leaning`, which
    tilts the prior without ever fixing it — a heavy tilt is still only energy.
    """
    leaning = leaning or {}
    out: dict[str, Vector] = {}
    for s in slots:
        vec = [0.0] * NBV
        v = leaning.get(s)
        if v is not None:
            vec[BVALUE_INDEX[v]] -= 1.0
        out[s] = vec
    return out


@dataclass(slots=True)
class FreeEnergy:
    """F over one block, with its gradient. Stateless apart from its inputs."""

    slots: tuple[str, ...]
    evidence: dict[str, Vector]
    priors: dict[str, Vector]
    edges: tuple[QEdge, ...]
    beta: float
    clamped: frozenset[str] = frozenset()

    def _e(self, s: str) -> Vector:
        return self.evidence.get(s) or [0.0] * NBV

    def _r(self, s: str) -> Vector:
        return self.priors.get(s) or [0.0] * NBV

    def value(self, p: Mapping[str, Vector]) -> float:
        total = 0.0

        for s in self.slots:
            ps = p[s]
            e, r = self._e(s), self._r(s)
            total += math.fsum(ps[k] * (e[k] + LAMBDA2 * r[k]) for k in range(NBV))
            # Entropic regularizer: -(1/beta) * H(p) = +(1/beta) * sum p log p.
            total += (1.0 / self.beta) * math.fsum(
                ps[k] * math.log(max(ps[k], EPS)) for k in range(NBV)
            )

        for edge in self.edges:
            pu, pv = p.get(edge.u), p.get(edge.v)
            if pu is None or pv is None:
                continue
            total += 0.5 * LAMBDA * edge.weight * math.fsum(
                (pu[k] - pv[k]) ** 2 for k in range(NBV)
            )

        return total

    def gradient(self, p: Mapping[str, Vector]) -> dict[str, Vector]:
        """dF/dp_i, computed only for unclamped slots."""
        grad: dict[str, Vector] = {}
        for s in self.slots:
            if s in self.clamped:
                continue
            ps = p[s]
            e, r = self._e(s), self._r(s)
            grad[s] = [
                e[k]
                + LAMBDA2 * r[k]
                + (1.0 / self.beta) * (math.log(max(ps[k], EPS)) + 1.0)
                for k in range(NBV)
            ]

        for edge in self.edges:
            pu, pv = p.get(edge.u), p.get(edge.v)
            if pu is None or pv is None:
                continue
            coef = LAMBDA * edge.weight
            gu, gv = grad.get(edge.u), grad.get(edge.v)
            if gu is not None:
                for k in range(NBV):
                    gu[k] += coef * (pu[k] - pv[k])
            if gv is not None:
                for k in range(NBV):
                    gv[k] += coef * (pv[k] - pu[k])

        return grad

    def stationarity(self, p: Mapping[str, Vector], grad: Mapping[str, Vector]) -> float:
        """Mirror-flow stationarity residual.

        The plain gradient norm is the wrong reading on a simplex: any component along
        the all-ones direction is absorbed by renormalization and does not move the
        iterate. This is the norm of the mirror (replicator) vector field,
        `p_k * (g_k - <p, g>)`, which vanishes exactly at a constrained stationary point.
        It is what `settle.py` compares against `SETTLE_GRAD_TOL`.
        """
        worst = 0.0
        for s, g in grad.items():
            ps = p[s]
            mean = math.fsum(ps[k] * g[k] for k in range(NBV))
            for k in range(NBV):
                worst = max(worst, abs(ps[k] * (g[k] - mean)))
        return worst
