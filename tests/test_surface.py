"""Controls for the usable surface (item A): report + query over a fixture run.

A is the first openable thing — it runs the real pipeline on a synthetic four-chart corpus
and renders it. These controls assert it (a) exercises all four charts end to end, (b)
answers each query, (c) renders both formats with the P3-held honesty on the page, and (d)
is a *view*, not an extension — it carries no three-moves registry entry.
"""

from __future__ import annotations

import unittest

from engine.surface import build_report, html_page, query, render_markdown


class TheReportRunsTheWholePipeline(unittest.TestCase):
    def setUp(self):
        self.r = build_report()

    def test_all_four_charts_are_present(self):
        self.assertEqual(set(self.r.by_chart()), {"english", "lean", "tabular", "conversation"})

    def test_the_object_summary_is_non_trivial(self):
        s = self.r.ledger_summary
        self.assertEqual(s["documents"], 4)
        self.assertGreater(s["deltas"], 0)
        self.assertGreater(s["slots"], 0)
        self.assertGreater(s["blocks"], 0)

    def test_holonomy_floors_are_measured_on_both_beta_arms(self):
        self.assertTrue(self.r.arms)
        for a in self.r.arms:
            self.assertGreaterEqual(a.mean_floor, 0.0)
            self.assertGreaterEqual(a.loops, 0)

    def test_the_conversation_ledger_carries_all_verdict_kinds(self):
        kinds = {v.verdict for v in self.r.verdicts}
        for required in ("accepted", "rejected", "sharpened"):
            self.assertIn(required, kinds)

    def test_deterministic(self):
        a, b = build_report(), build_report()
        self.assertEqual(a.ledger_summary, b.ledger_summary)
        self.assertEqual([v.verdict for v in a.verdicts], [v.verdict for v in b.verdicts])


class TheQuerySurfaceAnswers(unittest.TestCase):
    def setUp(self):
        self.r = build_report()

    def test_verdicts(self):
        out = query(self.r, "verdicts")
        self.assertTrue(any(line.startswith("accepted") for line in out))

    def test_floors(self):
        self.assertTrue(all("floor=" in line for line in query(self.r, "floors")))

    def test_find_cross_chart(self):
        out = query(self.r, "find", "cone")
        charts = {line.split()[0] for line in out}
        self.assertGreaterEqual(len(charts), 2, "the same claim should surface in >=2 charts")

    def test_chart_selector(self):
        self.assertTrue(query(self.r, "chart", "lean"))

    def test_unknown_query_raises(self):
        with self.assertRaises(ValueError):
            query(self.r, "nonsense")


class TheReportRenders(unittest.TestCase):
    def setUp(self):
        self.r = build_report()

    def test_markdown_has_the_sections_and_the_honesty_note(self):
        md = render_markdown(self.r)
        for section in ("Routing", "Holonomy floors", "Conversation ledger", "Status"):
            self.assertIn(section, md)
        self.assertIn("HELD on D5", md)
        self.assertIn("SYNTHETIC", md)

    def test_html_is_self_contained_and_theme_aware(self):
        page = html_page(self.r)
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn("prefers-color-scheme", page)
        self.assertNotIn("http://", page)   # no external resources
        self.assertNotIn("https://", page)
        self.assertIn("held on d5", page.lower())


class AIsAViewNotAnExtension(unittest.TestCase):
    def test_the_surface_carries_no_three_moves_entry(self):
        # A report/query reads the object; it adds no base, measure, or morphism. The
        # belonging audit is about extensions, so the surface must NOT be registered as one.
        from engine.three_moves import EXTENSIONS

        names = " ".join(e.name.lower() for e in EXTENSIONS)
        for view_word in ("report", "query", "surface", "view"):
            self.assertNotIn(view_word, names,
                             "a read-only view must not be registered as an extension")


if __name__ == "__main__":
    unittest.main()
