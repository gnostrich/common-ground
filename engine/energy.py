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

beta is the **verification budget** — how much checking effort an arm spends — NOT an
inverse temperature. The PREREG arms are 1x and 4x. It enters F as the coefficient on the
entropic term, so a larger budget resolves more of the contest and leaves less mass
undetermined, while a smaller budget keeps more of it open. The mechanism is unchanged by
the reading; the reading is what the number means.

-- THE AMENDMENT (seed/OBJECT-AMENDED.md), cited because this is mechanism --
MOVE: ADD A MEASURE — E itself, the Gibbs energy the state is scored by.
Q1 motivated its boundary. Priors and correspondences are ENERGY, never clamps (gate 2);
confusing a term in E with a boundary condition is the constitutional error this file
exists to make impossible.

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


def evidence_from_deltas(deltas: Sequence[Delta], dedupe: bool = True) -> dict[str, Vector]:
    """Accumulate per-slot evidence energy from candidate deltas.

    Supporting a value *lowers* its energy, weighted by the extractor's confidence and
    the warrant tier. Two extractors that disagree leave a slot with two low-energy
    values, which is exactly the shape that produces a settled distribution with mass on
    `B` (contested) rather than a spurious winner.

    Deduplication happens here rather than at the call site so that no ingestion path can
    forget it and silently double-count a re-ingested source.

    `dedupe=False` exists solely for null cell (v)'s positive control. It was added after
    the control found that a `dedupe=False` flag on `build_ledger` alone did nothing: this
    function deduplicated unconditionally, so the evidence was identical either way and
    cell (v) could not fail no matter how broken the deduplication was. The switch has to
    reach the accumulator, or the cell is testing nothing.
    """
    e: dict[str, Vector] = {}
    for d in (dedupe_deltas(deltas) if dedupe else deltas):
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
    #: THE APEX IS NOT A VARIABLE. It has no initial state, no prior, no entropy and no update
    #: rule of its own — it is the DERIVED CONSENSUS of its faces, recomputed from the current
    #: marginals every time this energy is evaluated. Zero new parameters.
    #:
    #: The first version of this made it a latent node with a uniform seed, its own entropy
    #: term and its own gradient. That is three degrees of freedom the faces do not determine,
    #: sitting in the energy core — a tuned knob in exactly the place this project deletes
    #: them. A coequalizer is not an independent unknown; it is what the faces already agree
    #: on, and the floor must come from face-to-face frustration MEDIATED through it, never
    #: from an apex's own settled state.
    #:
    #: With p_bar = (1/k) sum_j p_j the coupling is
    #:
    #:     (lambda*w/2) * (k/(k-1)) * sum_i ||p_i - p_bar||^2
    #:
    #: and its gradient is lambda*w*(k/(k-1))*(p_i - p_bar), because sum_j (p_j - p_bar)
    #: vanishes identically. No latent appears in either expression.
    #:
    #: THE k/(k-1) IS DERIVED, NOT TUNED, and leaving it out was a real physics error caught
    #: by the k=2 case. The identity sum_i ||p_i - p_bar||^2 = (1/k) sum_{i<j} ||p_i - p_j||^2
    #: means the bare consensus form is all-pairs divided by k — which is the de-duplication
    #: wanted at k=120 and an OVER-correction at k=2, where a fiber is exactly one declared
    #: pair and the two factorizations must agree exactly. Normalising by k/(k-1) makes k=2
    #: reproduce the declared pair term and leaves the per-face coefficient tending to
    #: lambda*w as k grows, which is the k-independence the whole change is for.

    def _stars(self, p: Mapping[str, Vector]) -> list[tuple[float, list[str], Vector]]:
        """(weight, faces, consensus) per apex. Read off the edges; nothing is stored."""
        from .blocks import is_apex

        groups: dict[str, tuple[float, list[str]]] = {}
        for edge in self.edges:
            apex = edge.u if is_apex(edge.u) else (edge.v if is_apex(edge.v) else None)
            if apex is None:
                continue
            face = edge.v if apex == edge.u else edge.u
            if p.get(face) is None:
                continue
            w, faces = groups.get(apex, (edge.weight, []))
            faces.append(face)
            groups[apex] = (w, faces)
        out = []
        for _apex, (w, faces) in groups.items():
            if len(faces) < 2:
                continue           # a star with one face couples nothing to anything
            k = float(len(faces))
            bar = [math.fsum(p[f][i] for f in faces) / k for i in range(NBV)]
            out.append((w, faces, bar))
        return out

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

        # The equivalence-prior coupling. It degrades honestly on the empty registry: with no
        # DECLARED correspondence there are no fibers, so `self.edges` is empty, this loop adds
        # nothing, and F is evidence + lexicon prior + entropy alone. There is no default
        # coupling and no similarity fallback — an unpopulated correspondence contributes
        # exactly zero coupling energy, not a silent stand-in — which is why the floor over
        # such a ledger is a genuine GAP (no cycle to measure) rather than a measured zero.
        for edge in self.edges:
            pu, pv = p.get(edge.u), p.get(edge.v)
            if pu is None or pv is None:
                continue
            total += 0.5 * LAMBDA * edge.weight * math.fsum(
                (pu[k] - pv[k]) ** 2 for k in range(NBV)
            )

        # APEX-STAR, as derived consensus. Each face is pulled toward what its fiber currently
        # agrees on, not toward each of its siblings separately — so a member's coupling does
        # not grow with how many siblings it has, and a large fiber cannot rigidify itself.
        for w, faces, bar in self._stars(p):
            norm = len(faces) / (len(faces) - 1.0)
            total += 0.5 * LAMBDA * w * norm * math.fsum(
                (p[f][k] - bar[k]) ** 2 for f in faces for k in range(NBV))

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

        # d/dp_i of (lambda*w/2) sum_j ||p_j - p_bar||^2 is lambda*w*(p_i - p_bar): the
        # cross-terms cancel because sum_j (p_j - p_bar) is identically zero. There is no
        # apex gradient because there is no apex variable.
        for w, faces, bar in self._stars(p):
            coef = LAMBDA * w * (len(faces) / (len(faces) - 1.0))
            for f in faces:
                g = grad.get(f)
                if g is None:
                    continue
                pf = p[f]
                for k in range(NBV):
                    g[k] += coef * (pf[k] - bar[k])

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
