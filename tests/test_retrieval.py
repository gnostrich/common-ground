"""Retrieval is navigation, not addressing — and these controls are what keeps that true.

The read path used to answer every real question with "NO FIELD TO CONDITION ON", because it
applied one rule to two different questions. Addressing asks *is this the same claim* and must
stay a hash. Retrieval asks *which existing claims should be read* and asserts nothing. Adding
the second is safe exactly as long as it can never be mistaken for the first, so that is what
is planted against here:

  * a retrieved slot reported as a landing,
  * `conditioned=True` where nothing addressed,
  * retrieval leaking into the write path as a delta, an arrow, or a promotion.

The last one is the reason a similarity FIBER relation was deleted from this build and is not
coming back. Nothing in `engine/retrieval.py` may reach the tape.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.constants import REPO_ROOT
from engine.corpus_state import CorpusSnapshot, SlotRecord
from engine.inbound import compile_input
from engine.retrieval import DEFAULT_LIMIT, retrieve, terms


def _snap(rows) -> CorpusSnapshot:
    """A snapshot whose addresses are REAL — computed by the same extractor the corpus uses.

    An earlier version of this helper invented slot ids, which meant nothing could ever land
    on them and the exact-addressing controls passed for the wrong reason. Addressing is the
    thing under test here; it cannot be faked in the fixture.
    """
    from engine.extract import DeterministicExtractor
    from engine.types import Document

    snap = CorpusSnapshot()
    extractor = DeterministicExtractor("fixture", "test")
    for i, (chart, text) in enumerate(rows):
        for d in extractor.extract(Document(f"doc{i}", chart, text, "test")):
            snap.slots[d.slot] = SlotRecord(
                slot=d.slot, chart=chart, type=d.type, nu=d.nu, value="T",
                confidence=1.0, tier="EXTRACTION", docs=(f"doc{i}",))
    return snap


class RetrievedIsNeverReportedAsLanded(unittest.TestCase):
    """The one property that makes retrieval constitutionally safe."""

    def test_planted_a_paraphrase_retrieves_but_does_not_condition(self):
        """PLANTED: text that shares every content word with a claim and addresses to none."""
        snap = _snap([("english", "the funding rate curve is convex near the boundary")])
        got = compile_input("what does the funding curve do at a boundary", snap, "english")
        self.assertFalse(got.conditioned, "term overlap must NOT count as addressing")
        self.assertTrue(got.grounded, "but the material must still reach the model")
        self.assertTrue(got.retrieved)
        self.assertEqual(got.reached, 0)

    def test_the_compiled_text_labels_the_two_differently(self):
        snap = _snap([("english", "the funding rate curve is convex near the boundary")])
        got = compile_input("what does the funding curve do at a boundary", snap, "english")
        self.assertIn("RETRIEVED", got.compiled)
        self.assertNotIn("LANDED", got.compiled)
        self.assertIn("NOT an address match", got.compiled)

    def test_an_exact_surface_still_lands(self):
        surface = "the funding rate curve is convex near the boundary"
        got = compile_input(surface, _snap([("english", surface)]), "english")
        self.assertTrue(got.conditioned)
        self.assertIn("LANDED", got.compiled)

    def test_a_landed_slot_is_not_also_retrieved(self):
        """Otherwise the same claim appears twice under two different epistemic labels."""
        surface = "positivity fails at the third certificate"
        snap = _snap([("english", surface), ("english", "positivity holds elsewhere")])
        got = compile_input(surface, snap, "english")
        landed = {l.slot for l in got.landings if l.hit}
        self.assertTrue(landed)
        self.assertFalse(landed & {r.slot for r in got.retrieved})

    def test_the_record_reports_the_relation_it_actually_has(self):
        snap = _snap([("english", "the funding rate curve is convex near the boundary")])
        got = compile_input("funding curve boundary behaviour", snap, "english")
        rec = got.retrieved[0].as_record()
        self.assertIn("TERM OVERLAP ONLY", rec["relation_to_query"])
        self.assertIn("not a", rec["relation_to_query"])


class NothingRetrievedCanEnterTheCorpus(unittest.TestCase):
    def test_the_module_imports_nothing_that_writes(self):
        """PLANTED against the shape of the defect: retrieval reaching the tape.

        A similarity relation that can only be READ is navigation. The same relation able to
        mint a delta or an arrow is the fiber relation this build deleted. The difference is
        enforced here, on the import graph, rather than trusted.
        """
        tree = ast.parse((REPO_ROOT / "engine" / "retrieval.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.lstrip("."))
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
        forbidden = {"tape", "mint", "kernel", "pipeline", "correspondence", "energy"}
        self.assertEqual(imported & forbidden, set(),
                         "retrieval must not reach anything that can write or declare")

    def test_retrieval_produces_no_correspondence_objects(self):
        source = (REPO_ROOT / "engine" / "retrieval.py").read_text(encoding="utf-8")
        self.assertNotIn("Correspondence(", source)
        self.assertNotIn("Delta(", source)

    def test_a_retrieved_claim_keeps_its_own_warrant_and_contest_status(self):
        """Retrieval reorders; it never restates. A CONTESTED claim stays contested."""
        snap = _snap([("python", "def funding_rate(curve): return curve.boundary()")])
        sid = next(iter(snap.slots))
        snap.contested.add(sid)
        got = retrieve("funding rate curve boundary", snap)
        self.assertTrue(got[0].contested)
        self.assertEqual(got[0].tier, "EXTRACTION")


class RetrievalSurfacesTheWholeAtlas(unittest.TestCase):
    def test_it_crosses_charts_because_crossing_charts_is_the_point(self):
        snap = _snap([("english", "the funding rate curve is convex"),
                      ("python", "def funding_rate_curve(x): return x"),
                      ("go", "func FundingRateCurve(x float64) float64"),
                      ("lean", "theorem funding_rate_curve_convex : True")])
        got = retrieve("funding rate curve", snap, chart="english")
        self.assertGreaterEqual(len({r.chart for r in got}), 3,
                                "a question in one chart must be able to see the others")

    def test_planted_one_chart_cannot_monopolize_the_budget(self):
        """PLANTED: straight top-N returned fourteen English rows for a six-chart corpus."""
        rows = [("english", f"the funding rate curve variant {i}") for i in range(60)]
        rows.append(("go", "func FundingRateCurve(x float64) float64"))
        got = retrieve("funding rate curve", _snap(rows))
        self.assertLessEqual(len(got), DEFAULT_LIMIT)
        self.assertIn("go", {r.chart for r in got})

    def test_identifier_spellings_reach_each_other(self):
        snap = _snap([("python", "def order_book_depth(): pass"),
                      ("go", "func OrderBookDepth() int")])
        got = retrieve("order book depth", snap)
        self.assertEqual(len(got), 2, "snake_case and CamelCase must both be reachable "
                                      "from plain words")

    def test_the_same_surface_is_not_shown_twice(self):
        snap = _snap([("english", "the funding rate curve is convex"),
                      ("english", "the funding rate curve is convex")])
        # Two rows, same nu — distinct addresses in this fixture, one row of reading.
        got = retrieve("funding rate curve convex", snap)
        self.assertEqual(len({r.nu for r in got}), len(got))


class QueryTermsAreDiscriminating(unittest.TestCase):
    def test_stopwords_and_short_tokens_are_dropped(self):
        self.assertEqual(terms("what is the a of in"), [])

    def test_identifiers_split_both_ways_and_survive_whole(self):
        got = terms("OrderBook_depth")
        for expected in ("orderbook_depth", "orderbook", "order", "book", "depth"):
            self.assertIn(expected, got)

    def test_planted_a_single_common_word_does_not_flood(self):
        """A query with several terms must not match on one incidental word."""
        snap = _snap([("english", "the rate of the thing"),
                      ("english", "funding rate curve boundary convexity")])
        got = retrieve("funding rate curve boundary", snap)
        self.assertEqual(len(got), 1)
        self.assertIn("convexity", got[0].nu)

    def test_an_empty_or_stopword_only_query_retrieves_nothing(self):
        snap = _snap([("english", "the funding rate curve")])
        self.assertEqual(retrieve("", snap), [])
        self.assertEqual(retrieve("what is the", snap), [])


class NothingAddressedAndNothingRetrievedIsStillReported(unittest.TestCase):
    def test_a_query_with_no_overlap_is_a_reported_passthrough(self):
        snap = _snap([("english", "the funding rate curve is convex")])
        got = compile_input("quantum chromodynamics lattice spacing", snap, "english")
        self.assertFalse(got.conditioned)
        self.assertFalse(got.grounded)
        self.assertIn("Nothing was retrieved either", got.compiled)
        self.assertIn("near-passthrough", got.compiled)

    def test_an_empty_corpus_says_so_before_anything_else(self):
        got = compile_input("anything at all", CorpusSnapshot(), "english")
        self.assertFalse(got.grounded)
        self.assertIn("corpus is empty", got.compiled)


class TheModelIsToldTheDifference(unittest.TestCase):
    """Labelling the field is decorative if the system prompt does not carry the rule."""

    def test_the_system_prompt_distinguishes_landed_from_retrieved(self):
        from engine.inbound import INBOUND_SYSTEM

        self.assertIn("RETRIEVED", INBOUND_SYSTEM)
        self.assertIn("LANDED", INBOUND_SYSTEM)
        self.assertIn("asserts nothing", INBOUND_SYSTEM.replace("asserting nothing",
                                                                "asserts nothing"))

    def test_the_prompt_forbids_reading_co_occurrence_as_correspondence(self):
        from engine.inbound import INBOUND_SYSTEM

        self.assertIn("fact about a search", INBOUND_SYSTEM)


if __name__ == "__main__":
    unittest.main()
