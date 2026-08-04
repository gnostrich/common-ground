"""Controls for the three-moves belonging audit (completion of THE DELTA).

The audit asserts object-singularity: every registered extension reduces to exactly one of
{swap-base, add-measure, add-morphism}. The mandated positive control is a planted defect —
an injected extension that fits no move MUST turn the audit red — proving the audit can fail.
"""

from __future__ import annotations

import unittest

from engine.three_moves import (
    ADD_MEASURE,
    ADD_MORPHISM,
    EXTENSIONS,
    MOVES,
    SWAP_BASE,
    Extension,
    check_belonging,
    classify,
)


class ThereAreExactlyThreeMoves(unittest.TestCase):
    def test_the_moves_are_exactly_the_three(self):
        self.assertEqual(MOVES, {SWAP_BASE, ADD_MEASURE, ADD_MORPHISM})


class EveryRegisteredExtensionBelongs(unittest.TestCase):
    def test_the_standing_audit_is_green(self):
        result = check_belonging()
        self.assertTrue(result.ok, f"unclassified: {[e.name for e in result.unclassified]}")
        self.assertEqual(result.unclassified, ())
        self.assertEqual(result.bad_status, ())

    def test_every_extension_reduces_to_a_single_legal_move(self):
        for e in EXTENSIONS:
            self.assertIn(e.move, MOVES, f"{e.name} fits no legal move")


class TheNamedExtensionsHaveTheRuledMove(unittest.TestCase):
    """The ruling: charts=move-1, fast/slow=move-2, K=move-3, conversation=move-1, LM=move-3."""

    def _move_of(self, needle: str) -> str:
        hits = [e for e in EXTENSIONS if needle in e.name.lower()]
        self.assertTrue(hits, f"no registered extension matches {needle!r}")
        return hits[0].move

    def test_charts_are_swap_base(self):
        self.assertEqual(self._move_of("charts"), SWAP_BASE)

    def test_conversation_chart_is_swap_base(self):
        self.assertEqual(self._move_of("conversation"), SWAP_BASE)

    def test_fast_slow_is_add_measure(self):
        self.assertEqual(self._move_of("fast / slow"), ADD_MEASURE)

    def test_memory_kernel_K_is_add_morphism(self):
        self.assertEqual(self._move_of("memory kernel"), ADD_MORPHISM)

    def test_the_one_proposer_inlet_is_add_morphism(self):
        # The reframe: me/LM/instance are ONE proposer morphism (the inlet), not three.
        self.assertEqual(self._move_of("inlet"), ADD_MORPHISM)


class ThePlantedDefectControl(unittest.TestCase):
    """MANDATED: an extension that fits no move must make the audit FAIL.

    Without this, a green audit would be indistinguishable from an audit that cannot fail.
    """

    def test_an_unclassifiable_extension_turns_the_audit_red(self):
        creep = Extension(
            name="jack-of-all-trades feature",
            move="misc",                       # fits none of the three moves
            status="built",
            rationale="a new box that is neither base, measure, nor morphism",
            evidence="(injected control)",
        )
        planted = EXTENSIONS + (creep,)
        result = classify(planted)
        self.assertFalse(result.ok, "the audit must go red when creep is injected")
        self.assertIn(creep, result.unclassified)

    def test_a_blank_move_is_also_creep(self):
        creep = Extension("nameless drift", move="", status="built",
                          rationale="", evidence="")
        self.assertFalse(classify(EXTENSIONS + (creep,)).ok)

    def test_the_control_is_the_only_thing_that_broke_it(self):
        # Same registry without the injected creep is green — so it is the injection, not a
        # pre-existing failure, that turns it red.
        self.assertTrue(classify(EXTENSIONS).ok)


if __name__ == "__main__":
    unittest.main()
