"""Repo intake: `adapters/repo_adapter.py`, `adapters/language_registry.py`, and the
python-corpus CI-receipt clamp path — proven against `tests/fixtures/mixed_repo/`, a
synthetic multi-language repo. NEVER against any of the operator's real repositories: see
`seed/DECISIONS.md`'s REPO_INTAKE entry, real-repo ingestion is HELD.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from adapters.language_registry import all_rules, chart_worthy_charts, classify_path
from adapters.python_corpus import (
    clamps_from_receipts,
    load_python_corpus,
    run_test_receipts,
)
from adapters.repo_adapter import walk_repo
from engine.charts import chart_names, is_chart
from engine.types import WarrantTier

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mixed_repo"


class LanguageRegistryIsAPlugInSeam(unittest.TestCase):
    """Same shape as `engine/charts.py`: a manifest, not an `if ext == ...` chain."""

    def test_every_chart_worthy_rule_names_a_registered_chart(self):
        """A manifest drift here would mean routing a file to a chart nobody declared."""
        for chart in chart_worthy_charts():
            self.assertTrue(is_chart(chart), f"{chart!r} is chart-worthy in "
                            "seed/LANGUAGES.json but absent from seed/CHARTS.json")

    def test_filename_rules_win_over_extension_rules(self):
        """`package-lock.json` is shelf, not the generic `.json` reference-tier rule."""
        spec = classify_path("package-lock.json")
        self.assertEqual(spec.classification, "shelf")
        self.assertEqual(spec.rule, "filename:package-lock.json")

    def test_an_unregistered_extension_defaults_to_shelf_not_a_silent_guess(self):
        spec = classify_path("Makefile")
        self.assertEqual(spec.classification, "shelf")
        self.assertEqual(spec.rule, "default")
        self.assertTrue(spec.reason)

    def test_extension_match_is_case_insensitive(self):
        self.assertEqual(classify_path("Main.PY").classification, "chart-worthy")

    def test_python_and_lean_are_chart_worthy(self):
        self.assertEqual(classify_path("foo.py").chart, "python")
        self.assertEqual(classify_path("Foo.lean").chart, "lean")

    def test_markdown_and_go_and_js_are_reference_tier_not_shelf_and_not_ingested_now(self):
        for name in ("README.md", "main.go", "app.js", "notes.txt", "config.yaml"):
            spec = classify_path(name)
            self.assertEqual(spec.classification, "reference-tier", name)
            self.assertIsNone(spec.chart, name)

    def test_every_rule_carries_a_reason(self):
        """No silent classification anywhere in the manifest."""
        for rule in all_rules():
            self.assertTrue(rule.reason.strip(), rule)


class RepoAdapterWalksTheFixtureRepo(unittest.TestCase):
    """The whole `walk_repo` pass over the fixture: every file lands in exactly one
    bucket, nothing is silently dropped, and content only reaches a Document for
    chart-worthy files.
    """

    @classmethod
    def setUpClass(cls):
        cls.report = walk_repo(FIXTURE, "mixed-repo-fixture")

    def test_every_walked_file_is_classified(self):
        self.assertGreater(len(self.report.files), 0)
        for f in self.report.files:
            self.assertIn(f.classification, ("chart-worthy", "reference-tier", "shelf"))

    def test_counts_partition_the_whole_walk(self):
        counts = self.report.counts()
        self.assertEqual(sum(counts.values()), len(self.report.files))

    def test_chart_worthy_files_route_to_python_and_lean(self):
        by_chart = self.report.by_chart()
        self.assertEqual(by_chart.get("lean"), 1)
        self.assertGreaterEqual(by_chart.get("python", 0), 3)

    def test_reference_tier_files_are_held_not_ingested(self):
        held = self.report.held()
        self.assertGreater(len(held), 0)
        for f in held:
            self.assertIsNone(f.document, f"{f.path} is reference-tier but carries a Document")
            self.assertTrue(f.reason)
        held_paths = {f.path for f in held}
        self.assertIn("README.md", held_paths)
        self.assertIn("main.go", held_paths)

    def test_shelved_files_carry_no_document_and_no_decoded_text(self):
        shelved = self.report.shelved()
        self.assertGreater(len(shelved), 0)
        for f in shelved:
            self.assertIsNone(f.document)
        shelved_paths = {f.path for f in shelved}
        self.assertIn("package-lock.json", shelved_paths)
        self.assertIn("assets/logo.png", shelved_paths)

    def test_chart_worthy_files_carry_a_document_on_the_declared_chart(self):
        docs = self.report.to_documents()
        self.assertGreater(len(docs), 0)
        for d in docs:
            self.assertIn(d.chart, chart_names())
        # An empty __init__.py is realistic and must not be dropped from the walk — it is
        # still a chart-worthy file, just one with no candidate spans downstream.
        texts = {d.doc_id: d.text for d in docs}
        self.assertIn("repo:mixed-repo-fixture:src/mathutils.py", texts)
        self.assertIn("def add", texts["repo:mixed-repo-fixture:src/mathutils.py"])

    def test_header_reports_every_bucket(self):
        header = self.report.header()
        self.assertIn("chart-worthy=", header)
        self.assertIn("reference-tier=", header)
        self.assertIn("shelf=", header)

    def test_a_missing_repo_root_is_refused(self):
        with self.assertRaises(ValueError):
            walk_repo(FIXTURE / "does-not-exist", "nope")


class PythonCorpusCIReceiptClamps(unittest.TestCase):
    """The Python analogue of `LeanAdapter` in `tests/test_adapters_audit.py`: a receipt
    is not asserted, it comes from actually running the fixture's own unittest suite.
    """

    @classmethod
    def setUpClass(cls):
        cls.docs = load_python_corpus(FIXTURE)
        cls.receipts = run_test_receipts(FIXTURE)

    def test_loads_every_py_file_as_a_python_chart_document(self):
        self.assertGreaterEqual(len(self.docs), 3)
        for d in self.docs:
            self.assertEqual(d.chart, "python")
            self.assertEqual(len(d.meta["sha256"]), 64)

    def test_the_fixture_suite_actually_ran(self):
        """Not asserted: if this is empty, discovery silently found nothing and every
        other assertion in this class would be vacuously true."""
        self.assertGreater(len(self.receipts), 0)
        outcomes = {r.outcome for r in self.receipts}
        self.assertIn("pass", outcomes)

    def test_the_planted_failure_control_actually_failed(self):
        """Positive control: proves the receipt path can detect a real failure, mirroring
        the project-wide rule that a control which cannot fail is not evidence."""
        failing = [r for r in self.receipts if r.outcome == "fail"]
        self.assertEqual(len(failing), 1)
        self.assertIn("test_deliberately_failing_control", failing[0].qualname)

    def test_clamps_from_receipts_clamps_only_the_passing_tests(self):
        clamps = clamps_from_receipts(self.docs, self.receipts)
        passing = [r for r in self.receipts if r.outcome == "pass"]
        self.assertEqual(len(clamps), len(passing))
        self.assertEqual(len(clamps), 4)

    def test_every_clamp_is_ci_receipt_tier_and_clamp_eligible(self):
        clamps = clamps_from_receipts(self.docs, self.receipts)
        self.assertTrue(clamps)
        for c in clamps:
            self.assertIs(c.warrant.tier, WarrantTier.CI_RECEIPT)
            self.assertTrue(c.warrant.clamp_eligible)
            self.assertEqual(c.value, "T")

    def test_no_clamp_names_the_failing_test(self):
        clamps = clamps_from_receipts(self.docs, self.receipts)
        details = " ".join(c.warrant.detail for c in clamps)
        self.assertNotIn("test_deliberately_failing_control", details)

    def test_a_missing_dump_dir_is_refused(self):
        from engine import EngineError

        with self.assertRaises(EngineError):
            load_python_corpus(FIXTURE / "does-not-exist")


if __name__ == "__main__":
    unittest.main()
