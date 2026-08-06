"""One mechanism reaches the field, and it is the sampler's.

The defect these controls exist for was a Q5 violation running in production: the window ran a
candidate list (degree-ordered, budget-capped, twelve pairs a call) while the walk ran region
relaxation. Two mechanisms doing one job. The controls below are mostly about SAMENESS — that
the perturb path and the walk go out on the same wire, through the same parser, under the same
reading discipline — because that is the property that was false and could silently become
false again the next time somebody needs the window to behave a little differently.
"""

from __future__ import annotations

import unittest

from engine.corpus_state import CorpusSnapshot, SlotRecord
from engine.correspondence import Correspondence
from engine.perturb import Attachment, perturb
from engine.region import (BEARS_ON, BIAS_CHART, REGION_SYSTEM, arrows_from, build_region,
                           parse_region, render_region, residuals)
from engine.types import WarrantTier


def _corpus(n: int = 12) -> CorpusSnapshot:
    """A corpus with declared arrows, so a perturbation has an arrow-rich place to land."""
    from engine.normalize import address

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


def _transport(reply: str):
    seen = {}

    def t(system: str, user: str):
        seen["system"], seen["user"] = system, user
        seen["calls"] = seen.get("calls", 0) + 1
        return reply, {"cost": 0.001}

    return t, seen


class ThePerturbPathAndTheWalkShareOneRegionCodePath(unittest.TestCase):
    """The whole point. If these fail, there are two mechanisms again."""

    def test_the_system_prompt_is_byte_identical_to_the_walks(self):
        snap = _corpus()
        t, seen = _transport("")
        perturb("what is the common thread", snap, t)
        self.assertEqual(seen["system"], REGION_SYSTEM,
                         "the window must go out on the sampler's prompt, not one of its own")

    def test_the_body_is_the_regions_own_renderer(self):
        snap = _corpus()
        t, seen = _transport("")
        p = perturb("what is the common thread", snap, t)
        self.assertEqual(seen["user"], render_region(p.region))
        for header in ("OBJECTS", "ARROWS (declared)", "ARROWS (implied by composition)"):
            self.assertIn(header, seen["user"])

    def test_planted_exactly_one_call_and_no_budget_anywhere(self):
        """The old loop spent up to four calls over a truncated list. A region is one call."""
        snap = _corpus()
        t, seen = _transport("")
        p = perturb("what is the common thread", snap, t)
        self.assertEqual(seen["calls"], 1)
        self.assertEqual(p.calls, 1)
        for name in ("BATCH", "CALL_BUDGET", "budget_exhausted", "considered", "available"):
            self.assertFalse(hasattr(p, name),
                             f"{name} is candidate-list vocabulary; it must not have survived")

    def test_the_old_module_is_gone(self):
        with self.assertRaises(ImportError):
            import engine.attach  # noqa: F401

    def test_no_module_imports_the_deleted_loop(self):
        """Parsed, not grepped. A substring scan cannot tell a module that IMPORTS the loop
        from one that QUOTES its name in order to detect it — and `engine/battery.py` does
        exactly that, so the grep version failed on the control written to enforce the rule.
        Same lesson gate 10 taught: a check that cannot distinguish use from mention should be
        made able to, not worked around."""
        import ast
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        for path in list(root.glob("engine/*.py")) + list(root.glob("ui/*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module or "", ("attach", "engine.attach", ".attach"),
                                     f"{path.name} still imports the deleted loop")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotEqual(alias.name, "engine.attach",
                                            f"{path.name} still imports the deleted loop")


class TheBiasIsAnObjectInTheDiagram(unittest.TestCase):
    def test_it_is_index_zero_and_marked_bias(self):
        snap = _corpus()
        t, _ = _transport("")
        p = perturb("what is the common thread", snap, t)
        first = p.region.members[0]
        self.assertEqual(first.index, 0)
        self.assertEqual(first.chart, BIAS_CHART)
        self.assertIn("[b0]", render_region(p.region))   # chart-tagged label

    def test_planted_the_bias_costs_an_index_it_does_not_widen_the_region(self):
        """A diagram measured at sixty must stay sixty, or the acceptance guard drifts."""
        snap = _corpus()
        t, _ = _transport("")
        plain = build_region(snap, clamp="", size=6)
        p = perturb("x", snap, t, size=6)
        self.assertEqual(len(p.region.members), len(plain.members))

    def test_a_walk_region_is_unchanged_by_all_of_this(self):
        snap = _corpus()
        r = build_region(snap, clamp="", size=6)
        self.assertEqual(r.bias, "")
        self.assertIsNone(r.bias_member)
        self.assertNotIn(BIAS_CHART, {m.chart for m in r.members})


class ArrowsToTheBiasAreEphemeralByConstruction(unittest.TestCase):
    def test_planted_arrows_from_refuses_to_mint_one(self):
        """Not "the caller filters them" — the one place arrows are minted refuses."""
        snap = _corpus()
        t, _ = _transport("")
        p = perturb("what is the common thread", snap, t, size=6)
        raw = "0 -bears_on-> 1\n0 -same_claim-> 2"
        props = parse_region(raw, p.region)
        self.assertTrue([x for x in props if x.ok], "the fixture must produce live proposals")
        self.assertEqual(arrows_from(props), [],
                         "an arrow to a boundary condition became a Correspondence")

    def test_they_are_routed_out_of_the_five_outcomes(self):
        snap = _corpus()
        t, _ = _transport("")
        p = perturb("q", snap, t, size=6)
        res = residuals(parse_region("0 -bears_on-> 1", p.region), p.region)
        self.assertEqual(len(res.attachment), 1)
        self.assertEqual(res.novel, [], "attachment must not enter the extraction stream")

    def test_the_record_says_ephemeral(self):
        a = Attachment(kind=BEARS_ON, dst_slot="s" * 40, dst_chart="python", dst_nu="n",
                       evidence="")
        self.assertTrue(a.as_record()["ephemeral"])
        self.assertEqual(a.as_record()["tier"], "EXTRACTION")


class BearsOnIsNotACorpusMorphism(unittest.TestCase):
    def test_planted_it_is_void_between_two_corpus_objects(self):
        """Letting it through would put a fourth kind into the base by the back door."""
        snap = _corpus()
        r = build_region(snap, clamp="", size=6)
        props = parse_region("1 -bears_on-> 2", r)
        self.assertEqual(len(props), 1)
        self.assertFalse(props[0].ok)
        self.assertIn("bears_on is legal only", props[0].void)

    def test_it_is_accepted_against_the_bias_object(self):
        snap = _corpus()
        t, _ = _transport("")
        p = perturb("q", snap, t, size=6)
        props = parse_region("0 -bears_on-> 1", p.region)
        self.assertTrue(props[0].ok, props[0].void)

    def test_the_corpus_kinds_are_still_exactly_three(self):
        from engine.correspondence import KINDS

        self.assertEqual(set(KINDS), {"same_claim", "refines", "instance_of"})


class TheRegionIsASampleAndSaysSo(unittest.TestCase):
    """The claim that must never be made: that these sixty are the relevant sixty."""

    def test_the_choice_reads_no_text(self):
        """A hash is not a similarity: two near-identical inputs land in unrelated places."""
        from engine.region import anchor_for
        from engine.normalize import address

        snap = _corpus(40)
        # NOT a punctuation variant: `nu` normalizes those to ONE address, which is gate 1
        # working, and two inputs at the same address must land in the same region. These
        # differ by a word, so they are two claims that share almost all their vocabulary.
        a, _ = address("english", "the cone is positive under composition", "assert")
        b, _ = address("english", "the cone is negative under composition", "assert")
        self.assertNotEqual(a, b, "the fixture must be two distinct addresses")
        self.assertNotEqual(anchor_for(snap, a), anchor_for(snap, b),
                            "two inputs sharing every word but one landed in the same "
                            "neighbourhood — which is what lexical steering would look like")

    def test_the_same_input_gets_the_same_region_so_a_run_can_be_replayed(self):
        from engine.region import anchor_for
        from engine.normalize import address

        snap = _corpus(40)
        a, _ = address("english", "the cone is positive", "assert")
        self.assertEqual(anchor_for(snap, a), anchor_for(snap, a))

    def test_the_compiled_input_states_that_it_is_a_sample(self):
        from engine.inbound import compile_input

        snap = _corpus()
        t, _ = _transport("0 -bears_on-> 1")
        out = compile_input("what is the common thread", snap, transport=t)
        self.assertIn("UNMEASURED", out.compiled)
        self.assertIn("NOT the part of the corpus that matches", out.compiled)

    def test_planted_the_budget_disclaimer_is_gone(self):
        """There is no candidate list, so a sentence about how much of one was reached would
        be describing a mechanism that no longer exists."""
        from engine.inbound import compile_input

        snap = _corpus()
        t, _ = _transport("0 -bears_on-> 1")
        out = compile_input("what is the common thread", snap, transport=t)
        for phrase in ("call budget", "type-compatible candidates", "candidate(s) asked"):
            self.assertNotIn(phrase, out.compiled)


class TheWindowExtracts(unittest.TestCase):
    def test_corpus_to_corpus_arrows_come_back_from_the_same_call(self):
        snap = _corpus()
        t, _ = _transport("")
        p = perturb("q", snap, t, size=8)
        charts = {m.index: m.chart for m in p.region.members}
        pair = next(((i, j) for i in charts for j in charts
                     if i and j and charts[i] == "english" and charts[j] == "python"), None)
        self.assertIsNotNone(pair, "fixture must contain a cross-chart pair")
        res = residuals(parse_region(f"{pair[0]} -same_claim-> {pair[1]}", p.region), p.region)
        arrows = arrows_from(res.novel)
        self.assertEqual(len(arrows), 1)
        self.assertEqual(arrows[0].tier, WarrantTier.EXTRACTION)


class SilenceIsStillAResult(unittest.TestCase):
    def test_no_arrow_to_the_bias_is_reported_as_the_medium_declining(self):
        from engine.inbound import compile_input

        snap = _corpus()
        t, _ = _transport("")                    # the medium names nothing at all
        out = compile_input("what is the common thread", snap, transport=t)
        self.assertFalse(out.conditioned)
        self.assertIn("THE FIELD DID NOT RESPOND", out.field_status)
        self.assertIn("drew no arrow to it", out.field_status)

    def test_a_transport_error_is_reported_not_swallowed(self):
        def boom(system, user):
            raise RuntimeError("upstream 502")

        p = perturb("q", _corpus(), boom)
        self.assertIn("upstream 502", p.error)
        self.assertEqual(p.calls, 0)

    def test_an_empty_corpus_says_so(self):
        p = perturb("q", CorpusSnapshot(), lambda s, u: ("", {}))
        self.assertIn("corpus is empty", p.error)

    def test_empty_input_says_so(self):
        p = perturb("   ", _corpus(), lambda s, u: ("", {}))
        self.assertIn("nothing was typed", p.error)


class TheTypedTextReachesTheMediumRaw(unittest.TestCase):
    def test_planted_no_extractor_gate_in_front_of_the_proposer(self):
        """A bare topic yields no claim spans. It must still reach the field."""
        snap = _corpus()
        t, seen = _transport("")
        p = perturb("holonomy", snap, t)
        self.assertEqual(seen.get("calls"), 1, "a bare topic was filtered before the call")
        self.assertIn("holonomy", seen["user"])
        self.assertEqual(p.error, "")


if __name__ == "__main__":
    unittest.main()
