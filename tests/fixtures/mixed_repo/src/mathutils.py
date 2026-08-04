"""Small arithmetic helpers used by the mixed-language fixture repo."""


def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def is_positive(x):
    """True when x is strictly greater than zero."""
    assert isinstance(x, (int, float))
    return x > 0


class Accumulator:
    """Accumulates a running total, one add() at a time."""

    def __init__(self):
        self.total = 0

    def add(self, x):
        self.total = add(self.total, x)
        return self.total
