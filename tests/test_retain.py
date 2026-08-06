"""Ask and propose are one act with a persistence flag.

RETENTION IS NOT WIRED TO THE WINDOW BY THIS COMMIT, and that is deliberate. Retention without
decay is the tape becoming a second corpus by accretion, and the decay this must land on is
EVENT-QUANTIZED — weight drops only at measured events (visited-and-unconfirmed, superseded,
contradicted), with no N and no decay constant. An earlier N-based aging policy was built and
then superseded by that ruling before it ever acted; it was deleted rather than deprecated,
the same organ-removal discipline the candidate loop got.

So what lands here is the engine capability and its controls. The button lands when the
event-quantized decay does, because anything retained must be born subject to it.
"""

from __future__ import annotations

import unittest

from engine.inlet import FastTape
from engine.perturb import (MODES, RELEASE, RETAIN, Attachment, Perturbation, commit)
from engine.region import BEARS_ON
from engine.types import WarrantTier


def _pert(kinds=("same_claim", "bears_on")) -> Perturbation:
    p = Perturbation(typed_slot="a" * 64, typed_chart="english",
                     typed_nu="\x01en\x01the cone is positive under composition")
    charts = ("python", "lean", "go", "tabular")
    p.attachment = [
        Attachment(kind=k, dst_slot=chr(98 + i) * 64, dst_chart=charts[i % 4],
                   dst_nu=f"target {i}", evidence="because")
        for i, k in enumerate(kinds)]
    return p


class OneActOneFlag(unittest.TestCase):
    def test_the_only_difference_is_what_survives(self):
        p = _pert()
        rel = commit(p, FastTape(), RELEASE)
        ret = commit(p, FastTape(), RETAIN)
        self.assertIsNone(rel.claim)
        self.assertEqual(rel.arrows, ())
        self.assertIsNotNone(ret.claim)
        self.assertEqual(len(ret.arrows), 1)

    def test_planted_release_puts_nothing_on_the_tape(self):
        tape = FastTape()
        commit(_pert(), tape, RELEASE)
        self.assertEqual(len(tape.entries), 0,
                         "ask must leave no trace; that is what perturb-and-release means")

    def test_retain_puts_the_claim_on_the_tape_at_extraction(self):
        tape = FastTape()
        r = commit(_pert(), tape, RETAIN)
        self.assertEqual(len(tape.entries), 1)
        self.assertEqual(tape.entries[0].delta.warrant.tier, WarrantTier.EXTRACTION)
        self.assertEqual(tape.entries[0].delta.slot, r.claim.slot)

    def test_planted_the_retained_claim_is_index_zero_not_a_re_extraction(self):
        """Re-running the claim extractor would retain spans, not the object that was in the
        diagram — so the thing retained would not be the thing the relaxation was about."""
        p = _pert()
        r = commit(p, FastTape(), RETAIN)
        self.assertEqual(r.claim.slot, p.typed_slot)
        self.assertEqual(r.claim.nu, p.typed_nu)

    def test_a_retained_arrow_is_a_correspondence_at_extraction_tier(self):
        r = commit(_pert(), FastTape(), RETAIN)
        self.assertEqual(r.arrows[0].tier, WarrantTier.EXTRACTION)
        self.assertEqual(r.arrows[0].src_slot, "a" * 64)

    def test_corpus_arrows_are_kept_in_both_modes(self):
        p = _pert()
        p.extracted = [object(), object(), object()]
        self.assertEqual(commit(p, FastTape(), RELEASE).extracted, 3)
        self.assertEqual(commit(p, FastTape(), RETAIN).extracted, 3)

    def test_an_unknown_mode_is_refused_not_defaulted(self):
        from engine import EngineError

        with self.assertRaises(EngineError):
            commit(_pert(), FastTape(), "maybe")
        self.assertEqual(set(MODES), {RELEASE, RETAIN})


class BearsOnIsReleasedInBothModes(unittest.TestCase):
    """It is not a morphism of the base. Retaining one adds a fourth kind by the back door."""

    def test_planted_it_never_becomes_a_retained_arrow(self):
        r = commit(_pert(kinds=("bears_on", "bears_on")), FastTape(), RETAIN)
        self.assertEqual(r.arrows, ())
        self.assertEqual(len(r.released), 2)
        self.assertIn("not a morphism", r.released_reason)

    def test_the_claim_is_still_retained_and_its_isolation_is_stated(self):
        r = commit(_pert(kinds=("bears_on",)), FastTape(), RETAIN)
        self.assertIsNotNone(r.claim)
        self.assertIn("ISOLATED", r.note)

    def test_the_corpus_kinds_are_still_three(self):
        from engine.correspondence import KINDS

        self.assertEqual(set(KINDS), {"same_claim", "refines", "instance_of"})
        self.assertNotIn(BEARS_ON, KINDS)


if __name__ == "__main__":
    unittest.main()
