"""Hashing, canonical serialization, and the deterministic RNG.

The RNG is counter-based over SHA-256 rather than `random.Random`. Two reasons: the draw
sequence is a pure function of the seed material (so a run is replayable from its logged
seed_hash alone), and it does not depend on the interpreter's PRNG implementation.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence, TypeVar

T = TypeVar("T")

NUL = b"\x00"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_digest(path: Path) -> str:
    """Content hash of a pinned import artifact — one file or a whole directory.

    A directory hashes as its sorted map of relative path -> file hash, so the digest
    depends on the *set of files and their contents* and not on walk order or on where the
    tree happens to be mounted. Dotfiles are skipped: a `.git` inside a checked-out dump
    would otherwise make the digest depend on fetch history rather than on content.

    This is the pin that does the work. `mathlib_commit` and `nlab_scrape_date` record
    where an artifact came from, which is provenance; the digest records what it *is*,
    which is what makes a run replayable. A label like "latest stable" resolves to a
    different artifact next week and so pins nothing; a digest cannot.
    """
    if path.is_file():
        return sha256_file(path)
    files = sorted(
        p for p in path.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(path).parts)
    )
    return hash_obj({
        str(p.relative_to(path)).replace("\\", "/"): sha256_file(p) for p in files
    })


def canonical_json(obj: Any) -> str:
    """Serialization that is stable across runs, platforms, and dict insertion order."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def hash_obj(obj: Any) -> str:
    return sha256_text(canonical_json(obj))


def join_hash(*parts: str) -> str:
    """Hash a tuple of strings with an unambiguous separator.

    NUL cannot appear in any of the inputs the engine hashes (normalized surfaces have
    all control characters removed except the chart tag, which is bracketed), so this is
    injective and two different tuples cannot collide by concatenation.
    """
    return sha256_bytes(NUL.join(p.encode("utf-8") for p in parts))


class DRNG:
    """Counter-based deterministic RNG.

    Constructed from string parts; the same parts always produce the same stream. Used
    for Gumbel draws in casting and for surrogate resampling, both of which must be
    replayable from the run log.
    """

    __slots__ = ("_seed", "_counter")

    def __init__(self, *parts: str) -> None:
        self._seed = NUL.join(p.encode("utf-8") for p in parts)
        self._counter = 0

    def _block(self) -> bytes:
        block = hashlib.sha256(
            self._seed + NUL + self._counter.to_bytes(8, "big")
        ).digest()
        self._counter += 1
        return block

    def random(self) -> float:
        """Uniform in [0, 1). 53 bits, matching float64's mantissa."""
        raw = int.from_bytes(self._block()[:8], "big") >> 11
        return raw / float(1 << 53)

    def uniform(self, low: float, high: float) -> float:
        return low + (high - low) * self.random()

    def gumbel(self) -> float:
        """Standard Gumbel(0, 1) via inverse CDF, guarded away from the log poles."""
        u = self.random()
        if u <= 0.0:
            u = 5e-324
        return -math.log(-math.log(u) if u < 1.0 else 1e-300)

    def randrange(self, n: int) -> int:
        if n <= 0:
            raise ValueError("randrange needs n > 0")
        return int(self.random() * n) % n

    def shuffled(self, seq: Sequence[T]) -> list[T]:
        """Fisher-Yates over a copy. Does not mutate the input."""
        out = list(seq)
        for i in range(len(out) - 1, 0, -1):
            j = self.randrange(i + 1)
            out[i], out[j] = out[j], out[i]
        return out

    def sample_mask(self, n: int, drop_rate: float) -> list[bool]:
        """Independent keep/drop mask. True means keep."""
        return [self.random() >= drop_rate for _ in range(n)]


def quantile(values: Iterable[float], q: float) -> float:
    """Linear-interpolated quantile. Empty input is 0.0, matching an absent null band."""
    xs = sorted(values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    pos = q * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac
