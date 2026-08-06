"""INBOUND controls: the field conditions the LM's input, and the difference is visible.

The typed text is a BOUNDARY CONDITION. The field supplies the content. If that difference
were invisible, this would be indistinguishable from retrieval-with-receipts.
"""

from __future__ import annotations

import unittest

from engine.constants import decisions
from engine.corpus_state import CorpusSnapshot, build_snapshot
from engine.energy import dedupe_deltas
from engine.extract import build_k_extractors
from engine.inbound import compile_input, land
from engine.pipeline import ingest, ledger_from_deltas
from engine.types import Document

_TEXT_A = ("The cone is positive under composition. "
           "The kernel accepts every checked statement.")
_TEXT_B = ("The spectral radius equals the largest modulus eigenvalue. "
           "The transfer defect is first order in the perturbation.")


def _snapshot(texts, arrows=()):
    docs = [Document(f"d{i}", "english", t, "src") for i, t in enumerate(texts)]
    deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
    return build_snapshot(ledger_from_deltas(deltas), arrows)


class TheFieldConditions(unittest.TestCase):
    def test_same_input_two_corpus_states_two_compiled_inputs(self):
        """The control that separates this from retrieval: the FIELD decides the content."""
        typed = "The cone is positive under composition."
        a = compile_input(typed, _snapshot([_TEXT_A]))
        b = compile_input(typed, _snapshot([_TEXT_B]))
        self.assertNotEqual(a.compiled, b.compiled,
                            "identical text against different fields must compile differently")
        self.assertTrue(a.conditioned, "corpus A contains this claim, so it conditions")
        self.assertFalse(b.conditioned, "corpus B does not, so it must degrade and say so")

    def test_richer_field_compiles_more(self):
        typed = "The cone is positive under composition."
        thin = compile_input(typed, _snapshot([_TEXT_A]))
        rich = compile_input(typed, _snapshot([_TEXT_A, _TEXT_A + " However, the cone is not "
                                               "positive in the degenerate case."]))
        self.assertGreaterEqual(len(rich.facts), len(thin.facts))


class AnEmptyFieldDegradesAndSaysSo(unittest.TestCase):
    def test_it_reports_no_field_rather_than_behaving_like_a_prompt(self):
        out = compile_input("anything at all", CorpusSnapshot())
        self.assertFalse(out.conditioned)
        self.assertIn("THE FIELD DID NOT RESPOND", out.compiled)
        self.assertIn("corpus is empty", out.compiled)
        self.assertIn("passthrough", out.compiled)

    def test_novel_phrasing_moves_nothing_and_the_reason_is_structural(self):
        """What the read path reports about novel phrasing, and why the wording moved twice.

        This control first asserted "NO FIELD TO CONDITION ON", then "NOTHING ADDRESSED".
        Both were prose about a lookup. The property now under test is the one that matters:
        an uncoupled bias moves nothing, `conditioned` is False, no fact is emitted, and the
        silence names a STRUCTURAL reason rather than a failed match.
        """
        out = compile_input("a sentence that appears in no corpus whatsoever",
                            _snapshot([_TEXT_A]))
        self.assertFalse(out.conditioned)
        self.assertEqual(out.reached, 0)
        self.assertEqual(out.facts, [])
        self.assertIn("THE FIELD DID NOT RESPOND", out.compiled)
        self.assertIn("no declared arrow touching it", out.compiled)
        self.assertIn("no words were compared", out.compiled)
        self.assertNotIn("MOVED [", out.compiled)

    def test_landing_is_exact_not_similar(self):
        snap = _snapshot([_TEXT_A])
        near = land("The cone is positive under compositions.", snap)   # one letter different
        self.assertFalse(any(l.hit for l in near),
                         "near-miss must NOT land — landing is gate-1 exact, never similar")


class ContestIsCarriedIntoTheCompiledInput(unittest.TestCase):
    def test_a_planted_contested_region_shows_up(self):
        # One document asserting and negating the same claim gives that slot two values.
        planted = ("The cone is positive. "
                   "However, the cone is not positive in the degenerate case.")
        snap = _snapshot([planted])
        contested_nu = next((r.nu for sid, r in snap.slots.items() if sid in snap.contested), None)
        if contested_nu is None:
            self.skipTest("fixture produced no contested slot")
        typed = contested_nu.split("\x01en\x01")[-1]
        out = compile_input(typed, snap)
        self.assertTrue(out.conditioned)
        self.assertIn("CONTESTED", out.compiled,
                      "input landing near a contested region must carry the contest")

    def test_the_floor_status_is_always_stated(self):
        out = compile_input("The cone is positive under composition.", _snapshot([_TEXT_A]))
        self.assertIn("floor:", out.compiled)
        self.assertIn("GAP", out.compiled, "an unmeasured floor must be named a GAP")


class EveryFactTracesToTheField(unittest.TestCase):
    def test_provenance_walk(self):
        snap = _snapshot([_TEXT_A])
        out = compile_input("The cone is positive under composition.", snap)
        self.assertTrue(out.facts)
        for fact in out.facts:
            if fact["kind"] in ("landing", "neighbour"):
                self.assertIn(fact["slot"], snap.slots,
                              "every compiled fact must trace to a real slot")
            elif fact["kind"] == "arrow":
                self.assertIn(fact["slot"], snap.slots)

    def test_the_compiled_input_is_inspectable_beside_what_was_typed(self):
        out = compile_input("The cone is positive under composition.", _snapshot([_TEXT_A]))
        rec = out.as_record()
        self.assertIn("typed", rec)
        self.assertIn("compiled", rec)
        self.assertNotEqual(rec["typed"], rec["compiled"],
                            "the difference between the prompt and what the field made of it "
                            "IS the feature; it must be visible")


class InboundIsReadSideOnly(unittest.TestCase):
    def test_it_never_touches_the_tape(self):
        import ast
        import inspect

        import engine.inbound as mod

        tree = ast.parse(inspect.getsource(mod))
        calls = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr in ("propose", "append")
                 and getattr(n.func.value, "attr", "") == "_entries"]
        self.assertEqual(calls, [], "inbound must not write to the tape")
        self.assertNotIn(".propose(", inspect.getsource(mod),
                         "inbound is read-side; proposing is the operator's explicit choice")


class TheChartTagIsStrippedForReadingOnly(unittest.TestCase):
    """`\x01en\x01the cone` must render as `the cone`, and ONLY when rendering."""

    def test_the_tag_is_removed_from_display(self):
        from engine.inbound import display
        from engine.normalize import nu

        raw = nu("english", "The cone is positive")
        self.assertTrue(raw.startswith("\x01"), "the tag is what makes charts disjoint")
        self.assertEqual(display(raw), "the cone is positive")
        self.assertNotIn("\x01", display(raw))

    def test_addressing_still_uses_the_tagged_form(self):
        """PLANTED: if display leaked into addressing, two charts would collide."""
        from engine.inbound import display
        from engine.normalize import address, nu, slot_id

        a, _ = address("english", "IsPositive c", "assert")
        b, _ = address("lean", "IsPositive c", "assert")
        self.assertNotEqual(a, b)
        self.assertEqual(slot_id(display(nu("english", "x")), "assert"),
                         slot_id(display(nu("lean", "x")), "assert"),
                         "stripped forms DO collide — which is why stripping is display-only")


if __name__ == "__main__":
    unittest.main()
