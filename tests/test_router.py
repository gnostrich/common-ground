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
    """Rule 1: code / logs / traces are pinned and not extracted — at SPAN level.

    Updated 2026-08-04 with the span-level repair. The fenced BLOCK is still never extracted;
    what changed is that the prose around it no longer goes down with it. The old assertion
    (whole document -> verbatim on one fence) encoded the defect, so it is replaced rather
    than kept: on the real repositories it discarded 226 of 742 markdown files.
    """

    def test_a_fenced_code_block_is_pinned_and_never_extracted(self):
        r = route("notes.md", "Here is code:\n```\nx = 1\n```\n")
        self.assertEqual(r.destination, "english", "the prose around the fence survives")
        self.assertEqual(len(r.verbatim_spans), 1, "the fence is pinned by content hash")
        self.assertNotIn("x = 1", r.document.text, "fence content must not reach an extractor")
        self.assertIn("Here is code", r.document.text)
        self.assertTrue(r.content_hash, "the whole artifact is still pinned by content hash")

    def test_a_document_that_is_only_a_fence_is_wholly_verbatim(self):
        r = route("snippet.md", "```\nx = 1\n```\n")
        self.assertEqual(r.destination, VERBATIM)
        self.assertIsNone(r.document, "a verbatim artifact must not reach an extractor")

    def test_a_stack_trace_is_verbatim(self):
        trace = ('Traceback (most recent call last):\n'
                 '  File "x.py", line 3, in <module>\n    boom()\nValueError: boom')
        self.assertEqual(route("err.log", trace).destination, VERBATIM)

    def test_a_log_is_verbatim(self):
        self.assertEqual(route("app.log", "2026-07-31 10:00:00 INFO started").destination,
                         VERBATIM)


class LeanRouting(unittest.TestCase):
    """Rules 2-3: .lean ALWAYS enters the Lean chart; elaboration decides clamp eligibility.

    INVERTED. These tests used to assert that a non-elaborating .lean was shelved. That was
    the defect: GATES sentence 3 governs GROUNDING ("only top-tier warrants ground
    (clamp-eligible)"), not chart ENTRY, and shelving conflated the two — costing the GitHub
    corpus all 407 of its .lean files while the Aristotle corpus ran 12,041 Lean slots at
    extraction tier with zero clamps through the adapter's (correct) rule.
    """

    THM = "theorem foo (h : P) : Q := by simp\n"

    def test_non_elaborating_lean_still_enters_the_chart_not_clamp_eligible(self):
        r = route("a.lean", self.THM)
        self.assertEqual(r.destination, LEAN, "entry does not require kernel-acceptance")
        self.assertIn("NOT clamp-eligible", r.reason)
        self.assertIsNotNone(r.document, "an unverified proof is readable; it just grounds nothing")

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
        # No elaboration-error shelf any more: .lean enters the chart, not clamp-eligible.
        self.assertEqual(sum(1 for k in counts if k.startswith("shelf:elaboration-error")), 0)
        self.assertEqual(counts[LEAN], 1)

        # to_charts excludes verbatim and shelved — lean now reaches a chart.
        charts = report.to_charts()
        self.assertEqual(len(charts), 3, "english + tabular + lean reach a chart")
        self.assertEqual({d.chart for d in charts}, {ENGLISH, TABULAR, LEAN})

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


class VerbatimIsASpanNotADocument(unittest.TestCase):
    """A README's prose is not forfeit because a usage example sits beside it.

    The old rule shelved the whole artifact on one fence: 226 of 742 real markdown files,
    2.21M characters of prose discarded to avoid extracting 225k of code.
    """

    DOC = (
        "# Positivity checker\n\n"
        "The cone is positive under composition.\n\n"
        "```python\n"
        "def is_positive(cone):\n"
        "    return cone.det > 0\n"
        "```\n\n"
        "Every generator is checked before the cone is accepted.\n"
    )

    def test_prose_reaches_english_and_the_fence_does_not(self):
        from engine.extract import DeterministicExtractor

        routed = route("repo||README.md", self.DOC, "repo")
        self.assertEqual(routed.destination, "english")
        self.assertIsNotNone(routed.document)
        self.assertEqual(len(routed.verbatim_spans), 1, "the fenced block must be pinned")

        surfaces = " ".join(
            d.surface for d in DeterministicExtractor("t", "p").extract(routed.document))
        self.assertIn("cone is positive under composition", surfaces.casefold())
        self.assertIn("every generator is checked", surfaces.casefold())
        for token in ("def is_positive", "cone.det", "return cone"):
            self.assertNotIn(token, surfaces,
                             f"{token!r} came from inside the fence; it must be pinned only")

    def test_zero_claims_come_from_inside_the_fence(self):
        """PLANTED: the fence body is a sentence-shaped claim, so a leak would be visible."""
        from engine.extract import DeterministicExtractor

        doc = ("Real prose about the cone.\n\n```\n"
               "The fenced sentence is a decoy and must never become a claim.\n```\n")
        routed = route("repo||d.md", doc, "repo")
        self.assertEqual(routed.destination, "english")
        surfaces = [d.surface.casefold()
                    for d in DeterministicExtractor("t", "p").extract(routed.document)]
        self.assertTrue(any("real prose about the cone" in s for s in surfaces))
        self.assertFalse(any("decoy" in s for s in surfaces),
                         "a fenced sentence became a claim")

    def test_a_file_that_is_only_a_fence_is_still_a_whole_artifact(self):
        routed = route("repo||snippet.md", "```\nprint(1)\n```\n", "repo")
        self.assertEqual(routed.destination, "verbatim-artifact")
        self.assertIsNone(routed.document)
        self.assertEqual(len(routed.verbatim_spans), 1)

    def test_an_unclosed_fence_runs_to_the_end(self):
        routed = route("repo||trunc.md", "Prose first.\n\n```python\ndef f():\n    pass\n", "repo")
        self.assertEqual(routed.destination, "english")
        self.assertIn("Prose first", routed.document.text)
        self.assertNotIn("def f()", routed.document.text)

    def test_log_and_trace_keep_document_level_treatment_and_say_why(self):
        """No delimiter exists for these, so the extent would have to be guessed."""
        doc = "Notes.\n\nTraceback (most recent call last)\n  File \"x.py\", line 3\nBoom\n"
        routed = route("repo||crash.md", doc, "repo")
        self.assertEqual(routed.destination, "verbatim-artifact")
        self.assertIn("no span delimiter", routed.reason)

    def test_existing_addresses_do_not_move(self):
        """ADDITIVE, not plastic: a document with no fence addresses byte-identically."""
        from engine.extract import DeterministicExtractor

        plain = "The cone is positive under composition. Every generator is checked.\n"
        routed = route("repo||plain.md", plain, "repo")
        ids = [d.slot for d in DeterministicExtractor("t", "p").extract(routed.document)]
        self.assertTrue(ids)
        # the same prose, now with a fence appended, must produce the SAME slot ids
        withfence = plain + "\n```\ncode()\n```\n"
        routed2 = route("repo||plain2.md", withfence, "repo")
        ids2 = [d.slot for d in DeterministicExtractor("t", "p").extract(routed2.document)]
        self.assertEqual(ids, ids2, "removing a fence must not move a prose address")
