"""Small dense linear algebra, pure stdlib.

Only what the engine needs: simplex operations for settlement, and a singular value
decomposition for the mint tape's Hankel spectrum. The SVD is one-sided Jacobi, which is
deterministic, needs no pivoting choices, and is accurate on the small, tall matrices a
64-wide Hankel window produces.
"""

from __future__ import annotations

import math
from typing import Sequence

Vector = list[float]
Matrix = list[list[float]]


# --- simplex ----------------------------------------------------------------------


def normalize_simplex(v: Sequence[float], eps: float = 1e-12) -> Vector:
    """Project onto the probability simplex by clipping and rescaling.

    Not the Euclidean projection: the entropic mirror map keeps iterates strictly
    positive, so clipping at eps is only guarding underflow, not doing real work.
    """
    clipped = [x if x > eps else eps for x in v]
    total = math.fsum(clipped)
    if total <= 0.0:
        n = len(clipped)
        return [1.0 / n] * n
    return [x / total for x in clipped]


def uniform_simplex(n: int) -> Vector:
    return [1.0 / n] * n


def total_variation(p: Sequence[float], q: Sequence[float]) -> float:
    """Total variation distance. In [0, 1]; 0 iff the distributions agree."""
    return 0.5 * math.fsum(abs(a - b) for a, b in zip(p, q))


def l2sq(p: Sequence[float], q: Sequence[float]) -> float:
    return math.fsum((a - b) ** 2 for a, b in zip(p, q))


def entropy(p: Sequence[float], eps: float = 1e-12) -> float:
    return -math.fsum(x * math.log(x) for x in p if x > eps)


def mix(p: Sequence[float], q: Sequence[float], alpha: float) -> Vector:
    """(1 - alpha) * p + alpha * q."""
    return [(1.0 - alpha) * a + alpha * b for a, b in zip(p, q)]


# --- SVD --------------------------------------------------------------------------


def singular_values(matrix: Matrix, max_sweeps: int = 60, tol: float = 1e-12) -> Vector:
    """Singular values of a dense matrix, descending.

    One-sided Jacobi: orthogonalize the columns of A by a sequence of plane rotations
    until every pair is orthogonal to within `tol`; the column norms are then the
    singular values. Column count is small here (a Hankel window), so the O(n^2) sweep
    is cheap and the result is bit-reproducible.
    """
    if not matrix or not matrix[0]:
        return []

    rows = len(matrix)
    cols = len(matrix[0])
    # Work on columns; transpose once so a column is a contiguous list.
    a: Matrix = [[matrix[r][c] for r in range(rows)] for c in range(cols)]

    for _ in range(max_sweeps):
        off = 0.0
        for i in range(cols - 1):
            for j in range(i + 1, cols):
                ci, cj = a[i], a[j]
                alpha = math.fsum(x * x for x in ci)
                beta = math.fsum(x * x for x in cj)
                gamma = math.fsum(x * y for x, y in zip(ci, cj))
                if abs(gamma) <= tol * math.sqrt(alpha * beta) or gamma == 0.0:
                    continue
                off = max(off, abs(gamma) / math.sqrt(alpha * beta) if alpha * beta > 0 else 0.0)

                # Rotation that annihilates the (i, j) inner product.
                zeta = (beta - alpha) / (2.0 * gamma)
                t = math.copysign(1.0, zeta) / (abs(zeta) + math.sqrt(1.0 + zeta * zeta))
                c = 1.0 / math.sqrt(1.0 + t * t)
                s = c * t
                for k in range(rows):
                    xi, xj = ci[k], cj[k]
                    ci[k] = c * xi - s * xj
                    cj[k] = s * xi + c * xj
        if off <= tol:
            break

    svs = sorted((math.sqrt(math.fsum(x * x for x in col)) for col in a), reverse=True)
    return svs


def hankel(stream: Sequence[float], window: int) -> Matrix:
    """Hankel matrix of the given window size.

    Row r is `stream[r : r + window]`. An input shorter than `window + 1` yields an empty
    matrix rather than a padded one; padding would invent structure the stream does not
    have, and the tape's whole purpose is to report structure faithfully.
    """
    n = len(stream)
    if n < window + 1:
        return []
    rows = n - window + 1
    return [list(stream[r : r + window]) for r in range(rows)]


def effective_rank(svs: Sequence[float], rel_tol: float = 1e-9) -> int:
    """Count of singular values above `rel_tol` times the largest."""
    if not svs:
        return 0
    top = svs[0]
    if top <= 0.0:
        return 0
    return sum(1 for s in svs if s > rel_tol * top)
