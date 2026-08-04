"""Python and Go as the first test of the repaired seam, and receipts as the only ground.

Two questions this file answers with assertions rather than prose:

1. Did the charts go in as manifest + behaviors, with NO further engine edit? Asserted on
   `engine/router.py`'s source, so a future edit that re-hardcodes routing fails here.
2. Can anything below a passing test ground a code slot? Planted against four ways.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from engine import GateViolation
from engine.charts import chart_names, chart_spec
from engine.constants import REPO_ROOT
from engine.extract import DeterministicExtractor
from engine.languages import rule_for
from engine.normalize import address, nu
from engine.receipts import (
    Receipt,
    _resolve_python,
    clamps_from_receipts,
    declarations_from_deltas,
    go_receipts,
    pytest_receipts,
)
from engine.router import route
from engine.types import Clamp, Warrant, WarrantTier

PY_SRC = ("def positive(cone):  # comment\n    return cone.det > 0\n\n"
          "class Cone:\n    def check(self):\n        assert self.det > 0\n")
GO_SRC = ("package amm\n\n// Positive reports whether the cone is positive.\n"
          "func Positive(c Cone) bool {\n\treturn c.Det > 0\n}\n\n"
          "func (b *Book) Match(o Order) (Fill, error) {\n\treturn Fill{}, nil\n}\n\n"
          "type Cone struct{ Det float64 }\n")


class TheSeamHeld(unittest.TestCase):
    """Manifest + behaviors, and nothing else."""

    def test_both_charts_are_declared_with_their_own_tags(self):
        names = chart_names()
        self.assertIn("python", names)
        self.assertIn("go", names)
        tags = [chart_spec(n).tag_id for n in names]
        self.assertEqual(len(tags), len(set(tags)), "a new chart must not reuse a tag")
        self.assertEqual(chart_spec("python").tag_id, "py")
        self.assertEqual(chart_spec("go").tag_id, "go")

    def test_routing_came_from_a_manifest_row(self):
        self.assertEqual(rule_for("r||m.py").chart, "python")
        self.assertEqual(rule_for("r||m.go").chart, "go")
        self.assertEqual(route("r||m.py", PY_SRC).destination, "python")
        self.assertEqual(route("r||m.go", GO_SRC).destination, "go")

    def test_the_router_names_neither_chart_nor_either_extension(self):
        """The seam question, asserted on the source: no edit to router.py was needed."""
        import ast

        tree = ast.parse((REPO_ROOT / "engine" / "router.py").read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if (isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef))
                    and isinstance(body, list) and body
                    and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)):
                docstrings.add(id(body[0].value))
        literals = {n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)
                    and id(n) not in docstrings}
        for forbidden in ("python", "go", ".py", ".go"):
            self.assertNotIn(forbidden, literals,
                             f"engine/router.py names {forbidden!r} — the seam leaked")

    def test_addresses_are_chart_disjoint(self):
        a, _ = address("python", "def f(): pass", "define")
        b, _ = address("go", "def f(): pass", "define")
        self.assertNotEqual(a, b, "two charts must never share an address")

    def test_normalization_is_idempotent_and_case_preserving(self):
        for chart, src in (("python", PY_SRC), ("go", GO_SRC)):
            once = nu(chart, src)
            self.assertEqual(nu(chart, once), once, f"{chart}: nu(nu(x)) != nu(x)")
        self.assertNotEqual(nu("go", "func Foo() {}"), nu("go", "func foo() {}"),
                            "Go's exported/unexported distinction IS capitalization")

    def test_comments_do_not_reach_the_address(self):
        with_comment = nu("go", "func F() {} // this explains F")
        without = nu("go", "func F() {}")
        self.assertEqual(with_comment, without)
        self.assertEqual(nu("python", "def f(): pass  # note"), nu("python", "def f(): pass"))


class SegmentationIsPerDeclaration(unittest.TestCase):
    def test_python_spans_functions_classes_and_methods(self):
        doc = route("r||m.py", PY_SRC).document
        locators = [d.provenance.locator for d in DeterministicExtractor("t", "p").extract(doc)]
        self.assertIn("def:positive", locators)
        self.assertIn("class:Cone", locators)
        self.assertIn("def:Cone.check", locators)

    def test_go_spans_functions_methods_and_types(self):
        doc = route("r||m.go", GO_SRC).document
        locators = [d.provenance.locator for d in DeterministicExtractor("t", "p").extract(doc)]
        self.assertIn("func:Positive", locators)
        self.assertIn("type:Cone", locators)
        self.assertIn("func:Book.Match", locators,
                      "a method's receiver is part of its name: T.M and U.M differ")

    def test_malformed_source_yields_no_spans_rather_than_crashing(self):
        doc = route("r||broken.py", "def f(:\n  ???\n").document
        self.assertEqual(list(DeterministicExtractor("t", "p").extract(doc)), [])


class OnlyAPassingTestGrounds(unittest.TestCase):
    def setUp(self):
        doc = route("r||m.go", GO_SRC).document
        self.deltas = list(DeterministicExtractor("t", "p").extract(doc))
        self.slot_of = declarations_from_deltas(self.deltas, "go")

    def test_a_receipt_becomes_a_clamp_at_ci_receipt_tier(self):
        clamps = clamps_from_receipts(
            [Receipt("go", "TestPositive", "Positive", "amm")], self.slot_of)
        self.assertEqual(len(clamps), 1)
        self.assertEqual(clamps[0].warrant.tier, WarrantTier.CI_RECEIPT)
        self.assertTrue(clamps[0].warrant.clamp_eligible)
        self.assertEqual(clamps[0].slot, self.slot_of["Positive"])

    def test_a_receipt_cannot_enter_through_the_inlet(self):
        """PLANTED: warrant rises at the gate, never at the inlet — receipts are not proposals."""
        import dataclasses

        from engine.inlet import FastTape
        from engine import EngineError

        delta = dataclasses.replace(
            self.deltas[0], warrant=Warrant(tier=WarrantTier.CI_RECEIPT, detail="planted"))
        with self.assertRaises(EngineError):
            FastTape().propose(delta, "receipts")

    def test_a_non_receipt_warrant_cannot_become_a_clamp(self):
        """PLANTED: try to ground an EXTRACTION-tier claim directly."""
        with self.assertRaises(GateViolation):
            Clamp(slot=self.slot_of["Positive"], value="T",
                  warrant=Warrant(tier=WarrantTier.EXTRACTION, detail="planted"))

    def test_a_test_naming_no_declaration_grounds_nothing(self):
        """PLANTED: `TestQuux` with no `Quux`. Nearest-match would be the similarity defect."""
        clamps = clamps_from_receipts(
            [Receipt("go", "TestQuux", "Quux", "amm")], self.slot_of)
        self.assertEqual(clamps, [], "a test that names nothing grounded something")

    def test_python_resolution_is_longest_exact_prefix_never_nearest(self):
        decls = {"compute", "compute_spread"}
        self.assertEqual(_resolve_python("compute_spread_when_empty", decls), "compute_spread")
        self.assertEqual(_resolve_python("compute", decls), "compute")
        self.assertEqual(_resolve_python("totally_unrelated", decls), "",
                         "an unresolvable name must yield nothing, not a near miss")

    def test_an_unavailable_runner_reports_itself_rather_than_zero(self):
        empty = Path("/tmp/cg-no-such-tree-84619")
        empty.mkdir(exist_ok=True)
        for report in (go_receipts(empty, set()), pytest_receipts(empty, set())):
            self.assertFalse(report.ran)
            self.assertTrue(report.note, "an absent run must say why")
            self.assertEqual(report.receipts, [])

    def test_one_declaration_is_clamped_once_even_by_many_tests(self):
        many = [Receipt("go", f"TestPositive_{i}", "Positive", "amm") for i in range(5)]
        self.assertEqual(len(clamps_from_receipts(many, self.slot_of)), 1)


if __name__ == "__main__":
    unittest.main()
