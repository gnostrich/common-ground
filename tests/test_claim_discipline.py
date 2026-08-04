"""Gate 10: docstrings are not warrants.

Three instances of a claim the implementation did not honour were found in one build — a
partition described as "provably identical", a confidence described as span-keyed, and an
anchoring described as index-driven that scanned every face. That is a pattern, not three
accidents, so the check is shaped to the FORM: any function claiming a complexity bound, an
index, an exactness property or an equivalence must have that property enforced by a named
control, or must not claim it.
"""

from __future__ import annotations

import pathlib
import shutil
import tempfile
import unittest

from engine.static_checks import (
    CLAIMED_PROPERTY_SITES,
    check_claim_discipline,
)


class TheEngineMakesNoUnwarrantedClaims(unittest.TestCase):
    def test_the_check_is_green(self):
        r = check_claim_discipline()
        self.assertEqual(r.violations, [],
                         f"unwarranted claims: {[str(v) for v in r.violations]}")
        self.assertGreater(r.checked_functions, 100, "the walk must actually cover the engine")

    def test_every_registered_claim_cites_a_control_that_exists(self):
        root = pathlib.Path(__file__).resolve().parent.parent
        for row in CLAIMED_PROPERTY_SITES:
            control = row["control"]
            self.assertTrue(control, f"{row['site']} cites no control")
            test_file = control.split(":", 1)[0]
            self.assertTrue((root / test_file).exists(),
                            f"{row['site']} cites missing control file {test_file}")


class PlantedClaimsMakeItRed(unittest.TestCase):
    """The mandated control: a claim with no control must go RED."""

    def _planted(self, snippet: str):
        tmp = pathlib.Path(tempfile.mkdtemp())
        try:
            shutil.copytree("engine", tmp / "engine")
            # The registered sites cite controls under tests/; copy them so an existing,
            # legitimate claim is not reported as "control missing" by the planted scan.
            shutil.copytree("tests", tmp / "tests")
            (tmp / "engine" / "planted_claim.py").write_text(snippet, encoding="utf-8")
            return check_claim_discipline(root=tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_an_on_indexed_claim_over_a_nested_loop_is_red(self):
        # The operator's exact shape: prose says "O(n), indexed"; the body is a nested scan.
        r = self._planted(
            'def lookup(items, keys):\n'
            '    """Index-driven: O(n) lookup, not a scan — cost is independent of the '
            'total item count."""\n'
            '    out = []\n'
            '    for k in keys:\n'
            '        for it in items:\n'
            '            if it == k:\n'
            '                out.append(it)\n'
            '    return out\n'
        )
        self.assertTrue(r.violations, "an unwarranted index/complexity claim must be RED")
        self.assertTrue(any("gate 10" in v.attr for v in r.violations))

    def test_an_exactness_claim_with_no_control_is_red(self):
        r = self._planted(
            'def partition(xs):\n'
            '    """Provably identical to the global build — no element is dropped."""\n'
            '    return xs\n'
        )
        self.assertTrue(r.violations, "an unwarranted exactness claim must be RED")

    def test_a_claim_in_a_COMMENT_is_caught_too(self):
        # The span defect hid in a comment, not a docstring. Both count.
        r = self._planted(
            'def f(xs):\n'
            '    """Ordinary description."""\n'
            '    # bit-identical to the reference implementation\n'
            '    return xs\n'
        )
        self.assertTrue(r.violations, "a claim in a comment must be RED too")

    def test_a_function_making_no_claim_is_fine(self):
        r = self._planted(
            'def g(xs):\n'
            '    """Return the items, sorted by id."""\n'
            '    return sorted(xs)\n'
        )
        self.assertEqual(r.violations, [], "plain description must not trip the check")


if __name__ == "__main__":
    unittest.main()
