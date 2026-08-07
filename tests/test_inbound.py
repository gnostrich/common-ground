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
        # THE FLOOR IS SCOPE DATA. It describes the MEASUREMENT, not the field,
        # and a model handed it recites it. It stays on the record.
        self.assertIn("floor", (out.field_status or "") + str(out.as_record()))
        self.assertIn("GAP", str(out.as_record()),
                      "an unmeasured floor must be named a GAP on the record")


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


class TheRefereeReadsTheSameSheetAsTheMedium(unittest.TestCase):
    """THE NAMED DEFECT CLASS, mechanized: a rule the medium cannot comply with is a rule that
    only ever convicts.

    Fourth instance, and the sharpest. The medium is seated in front of the whole region — every
    object labelled and printed with its claim text — and answers by citing those labels. The
    compiled record registered only the objects that ATTACHED or MOVED, so `engine.grounded`
    resolved against three labels while the medium had been shown sixty. On the frozen fixture
    it ruled [e20], [e49] and [e50] UNRESOLVED: three real corpus claims, printed to the medium
    by `_region_block` itself, called fabrications by the checker downstream of it.

    The general form of the fix is the assertion in the first test below, and it is the one that
    generalizes past this bug: FOR EVERY LABEL THE CHECKER WILL ACCEPT, THE PROMPT MUST CONTAIN
    THAT LABEL, AND CONVERSELY. Stated as an equality between two sets, so any future divergence
    fails here rather than in an operator's verdict line.
    """

    def _region_corpus(self, n: int = 12):
        """A corpus with declared arrows, so a perturbation has an arrow-rich place to land."""
        from engine.correspondence import Correspondence
        from engine.corpus_state import SlotRecord
        from engine.normalize import address
        from engine.types import WarrantTier

        slots, arrows, docs = {}, [], {}
        for i in range(n):
            chart = "english" if i % 2 == 0 else "python"
            sid, nu = address(chart, f"claim number {i} about the cone", "assert")
            slots[sid] = SlotRecord(slot=sid, chart=chart, type="assert", nu=nu,
                                    value="true", confidence=1.0, tier="EXTRACTION",
                                    docs=(f"repo||dir/file{i // 4}.md",))
            docs[i] = sid
        for i in range(0, n - 1, 2):
            arrows.append(Correspondence(
                src_chart="english", src_slot=docs[i], dst_chart="python", dst_slot=docs[i + 1],
                kind="same_claim", tier=WarrantTier.EXTRACTION, proposer="lm",
                prompt_hash="t", evidence=("seed",)))
        return CorpusSnapshot(slots=slots, arrows=tuple(arrows))

    def _compiled(self):
        def transport(system: str, user: str):
            return "0 -bears_on-> 1", {"cost": 0.0}

        return compile_input("what is the common thread", self._region_corpus(),
                             transport=transport)

    def test_every_citable_label_appears_in_the_prompt_the_medium_reads(self):
        """THE EQUALITY. Not a subset in either direction — the two sheets are one sheet."""
        import re

        from engine.grounded import citable_numbers

        out = self._compiled()
        accepted = citable_numbers(out.as_record())
        printed = set(re.findall(r"\[([a-z]?\d+)\]", out.compiled))
        self.assertTrue(accepted, "fixture must produce citable objects")
        self.assertEqual(accepted - printed, set(),
                         "the checker would accept a label the medium was never shown")
        # THE DIRECTION THAT WAS BROKEN. Every label printed to the medium is one the checker
        # resolves. Without it a prompt may show sixty objects while the referee holds three,
        # which is not a subtle divergence — it is a verdict of RED on a correct answer.
        self.assertEqual(printed - accepted, set(),
                         "the medium was shown a label the checker convicts it for citing")

    def test_every_label_TURN_ONE_was_shown_is_a_label_the_checker_resolves(self):
        """THE DIRECTION THAT WAS ACTUALLY BROKEN, against the sheet turn 1 actually reads.

        Turn 1's prompt is not the compiled block — it is `region.render_region`, the sixty
        labelled objects. Asserting against the compiled block alone would have stayed green
        through the whole defect, because the compiled block was exactly the three-label sheet
        the referee held. The set under test is therefore the REGION's labels, read off the
        attachment record, which is what the medium was handed.
        """
        from engine.grounded import citable_numbers
        from engine.region import BIAS_CHART, label

        out = self._compiled()
        shown = set(out.attachment.as_record()["labels"]) - {label(BIAS_CHART, 0)}
        self.assertTrue(shown, "fixture must seat corpus objects")
        self.assertEqual(shown - citable_numbers(out.as_record()), set(),
                         "turn 1 was shown labels the checker would convict it for citing")

    def test_a_seated_object_is_citable_even_though_it_did_not_attach(self):
        """THE REGRESSION, planted at the shape the fixture found it in."""
        from engine.grounded import check_answer, citable_numbers

        out = self._compiled()
        rec = out.as_record()
        kinds = {c["kind"] for c in rec["citations"]}
        self.assertIn("seated", kinds, "no object was registered as shown-but-not-attached")
        seated = next(c["n"] for c in rec["citations"] if c["kind"] == "seated")
        self.assertIn(seated, citable_numbers(rec))
        v = check_answer(f"The corpus holds a claim about the cone [{seated}].", rec)
        self.assertEqual([x["kind"] for x in v.as_record()["violations"]], [],
                         "a citation to an object the medium was SHOWN was convicted")

    def test_a_label_the_region_never_held_is_STILL_unresolved(self):
        """The other direction, or the fix is just a checker that accepts everything."""
        from engine.grounded import check_answer, citable_numbers

        out = self._compiled()
        rec = out.as_record()
        absent = next(f"e{i}" for i in range(900, 999)
                      if f"e{i}" not in citable_numbers(rec))
        v = check_answer(f"The corpus holds something else entirely [{absent}].", rec)
        self.assertEqual([x["kind"] for x in v.as_record()["violations"]], ["unresolved"])

    def test_the_boundary_condition_itself_is_not_citable(self):
        """[b0] is the question. An answer resting on the question rests on nothing."""
        from engine.grounded import citable_numbers
        from engine.region import BIAS_CHART, label

        rec = self._compiled().as_record()
        self.assertNotIn(label(BIAS_CHART, 0), citable_numbers(rec))

    def test_a_seated_line_says_it_is_not_an_attachment(self):
        """Seating is a sample, not a relation. If the line read like an attachment the medium
        would have been handed sixty relations to the boundary condition and no way to tell."""
        out = self._compiled()
        self.assertIn("SEATED", out.compiled)
        self.assertIn("shown, not attached to", out.compiled)


if __name__ == "__main__":
    unittest.main()
