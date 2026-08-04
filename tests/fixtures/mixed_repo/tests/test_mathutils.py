import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mathutils import Accumulator, add, is_positive  # noqa: E402


class MathUtilsTest(unittest.TestCase):
    def test_add_returns_the_sum(self):
        assert add(2, 3) == 5

    def test_is_positive_true_for_positive_numbers(self):
        assert is_positive(1) is True

    def test_is_positive_false_for_negative_numbers(self):
        assert is_positive(-1) is False

    def test_deliberately_failing_control(self):
        """Planted failure: proves clamps_from_receipts clamps only PASSING tests."""
        assert add(2, 2) == 5, "planted failure control"


class AccumulatorTest(unittest.TestCase):
    def test_accumulator_running_total(self):
        acc = Accumulator()
        acc.add(1)
        acc.add(2)
        assert acc.total == 3


if __name__ == "__main__":
    unittest.main()
