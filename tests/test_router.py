"""Controls for the ingestion router (item 3): one per routing rule, plus the header counts.

Every rule the spec names has a control that would fail if the router stopped honouring it.
The Lean-elaboration rule is tested with both the conservative default (shelf) and an
injected predicate (Lean chart), since the real elaborator needs D6.
"""

from __future__ import annotations

import unittest

from engine.router import (
    ENGLISH,
    LEAN,
    SHELF,
    TABULAR,
    VERBATIM,
    route,
    route_all,
)


class VerbatimArtifacts(unittest.TestCase):
    """Rule 1: code / logs / traces are pinned and not extracted."""

    def test_a_fenced_code_block_is_verbatim(self):
        r = route("notes.md", "Here is code:\n```\nx = 1\n```\n")
        self.assertEqual(r.destination, VERBATIM)
        self.assertIsNone(r.document, "a verbatim artifact must not reach an extractor")
        self.assertTrue(r.content_hash, "it is pinned by content hash")

    def test_a_stack_trace_is_verbatim(self):
        trace = ('Traceback (most recent call last):\n'
                 '  File "x.py", line 3, in <module>\n    boom()\nValueError: boom')
        self.assertEqual(route("err.log", trace).destination, VERBATIM)

    def test_a_log_is_verbatim(self):
        self.assertEqual(route("app.log", "2026-07-31 10:00:00 INFO started").destination,
                         VERBATIM)


class LeanRouting(unittest.TestCase):
    """Rules 2-3: elaborating .lean -> Lean; non-elaborating -> shelf, counted separately."""

    THM = "theorem foo (h : P) : Q := by simp\n"

    def test_non_elaborating_lean_is_shelved_with_a_reason(self):
        r = route("a.lean", self.THM)
        self.assertEqual(r.destination, SHELF)
        self.assertIn("elaboration-error", r.reason)
        self.assertIsNone(r.document, "an unverified proof must not become a Lean slot")

    def test_elaborating_lean_reaches_the_lean_chart(self):
        r = route("a.lean", self.THM, lean_elaborates=lambda _t: (True, "kernel-accepted"))
        self.assertEqual(r.destination, LEAN)
        self.assertIsNotNone(r.document)
        self.assertEqual(r.document.chart, LEAN)

    def test_the_default_cannot_verify_without_a_toolchain(self):
        r = route("a.lean", self.THM)
        self.assertIn("D6", r.reason, "the shelf reason names the missing toolchain")


class TableRouting(unittest.TestCase):
    """Rules 4-5: well-formed table -> tabular; malformed -> prose, tagged."""

    def test_a_well_formed_table_reaches_the_tabular_chart(self):
        table = "| lemma | status |\n|---|---|\n| cone_pos | proved |\n"
        r = route("t.md", table)
        self.assertEqual(r.destination, TABULAR)
        self.assertEqual(r.document.chart, TABULAR)

    def test_a_malformed_table_falls_back_to_prose(self):
        # Pipes but no separator row -> malformed -> prose.
        broken = "| lemma | status\n cone_pos proved |\n"
        r = route("t.md", broken)
        self.assertEqual(r.destination, ENGLISH)
        self.assertIn("malformed-table", r.reason)
        self.assertEqual(r.document.chart, ENGLISH)


class ProseAndMath(unittest.TestCase):
    """Rule 6: prose -> English, inline math preserved as opaque hashed tokens."""

    def test_plain_prose_reaches_english(self):
        r = route("doc.md", "The cone is positive under composition.")
        self.assertEqual(r.destination, ENGLISH)
        self.assertEqual(r.document.chart, ENGLISH)

    def test_inline_math_becomes_a_stable_opaque_token(self):
        r1 = route("a.md", "We know $x^2 + 1 > 0$ holds.")
        r2 = route("b.md", "Recall $x^2 + 1 > 0$ again.")
        self.assertTrue(r1.math_tokens, "the formula must be tokenized")
        self.assertNotIn("x^2", r1.document.text, "raw math must not reach the prose body")
        self.assertEqual(r1.math_tokens, r2.math_tokens,
                         "the same formula must tokenize to the same opaque hash")

    def test_math_token_survives_into_the_document_text(self):
        r = route("a.md", "We know $x^2$ holds.")
        self.assertIn(f"math_{r.math_tokens[0]}", r.document.text)


class Shelving(unittest.TestCase):
    """Rule 7: everything else -> shelf, counted."""

    def test_empty_input_is_shelved_unclassified(self):
        r = route("empty.md", "   \n  ")
        self.assertEqual(r.destination, SHELF)
        self.assertEqual(r.reason, "unclassified")


class TheReportHeaderCarriesCounts(unittest.TestCase):
    def test_counts_and_header_tally_every_destination(self):
        report = route_all([
            ("doc.md", "The cone is positive."),
            ("t.md", "| a | b |\n|---|---|\n| 1 | 2 |\n"),
            ("a.lean", "theorem t : P := by simp"),
            ("err.log", "Traceback (most recent call last):\n  boom"),
            ("empty.md", "  "),
        ])
        counts = report.counts()
        self.assertEqual(counts[ENGLISH], 1)
        self.assertEqual(counts[TABULAR], 1)
        self.assertEqual(counts[VERBATIM], 1)
        self.assertEqual(counts["shelf:unclassified"], 1)
        self.assertEqual(sum(1 for k in counts if k.startswith("shelf:elaboration-error")), 1)

        # to_charts excludes verbatim and shelved.
        charts = report.to_charts()
        self.assertEqual(len(charts), 2, "only english + tabular reach a chart")
        self.assertEqual({d.chart for d in charts}, {ENGLISH, TABULAR})

        header = report.header()
        self.assertTrue(header.startswith("routing:"))
        self.assertIn("english=1", header)

    def test_nfc_is_applied_at_the_boundary(self):
        # A decomposed 'é' (e + combining acute) must be NFC-composed before charting.
        decomposed = "café is nice"
        r = route("d.md", decomposed)
        self.assertIn("café", r.document.text, "the router must apply NFC once, pinned")


class RoutedChartsAreValid(unittest.TestCase):
    def test_every_charted_destination_is_a_declared_chart(self):
        report = route_all([
            ("doc.md", "The cone is positive."),
            ("t.md", "| a | b |\n|---|---|\n| 1 | 2 |\n"),
        ])
        for doc in report.to_charts():
            self.assertTrue(is_chart(doc.chart))


def is_chart(name):
    from engine.charts import is_chart as _is
    return _is(name)


if __name__ == "__main__":
    unittest.main()
