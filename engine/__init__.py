"""Minimal-faithful reconciliation engine, v0.

Every module here is pure stdlib. That is deliberate: the run's verdict is a function of
the seed hash, and a seed hash that depends on a linked LAPACK build or a third-party
release is not reproducible. Singular values, hashes, and random draws are all computed
here so that the same seed yields the same numbers on any platform.
"""

__all__ = ["GateViolation", "EngineError"]


class EngineError(Exception):
    """Base for engine errors."""


class GateViolation(EngineError):
    """A constitutional gate in seed/GATES.md was violated.

    This is never caught internally. A gate violation means the run is invalid, and the
    correct response is to stop and report, not to recover.
    """

    def __init__(self, gate: int, message: str) -> None:
        super().__init__(f"GATE {gate} VIOLATED: {message}")
        self.gate = gate
