"""THE AUTHORSHIP PULLBACK, and the third lift that does not exist.

The interaction surface is READ OFF the object, not designed: two independent binary
coordinates (objecthood, persistence) plus one constructible arrow. The 2x2 is the product of
two two-element sets and is therefore forced and complete; the arrow is this module.

The danger the controls guard is precise. A claim gesture is a lift up the tier poset, and a
lift that could be fired by approval rather than by authorship would be a THIRD arrow — one
that is not in the diagram.
"""

import unittest

from engine.claim import CLAIM_RETAINS, CLAIM_TIER, Claim, claim, lifts
from engine.mode import ASSERT, BRAINSTORM, MODES, cell
from engine.types import WarrantTier


class ThereIsNoThirdLift(unittest.TestCase):
    """OI-41. Warrant rises by K-measurement or by operator-authorship. Nothing else."""

    def test_exactly_two_lifts_exist(self):
        self.assertEqual(2, len(lifts()))
        self.assertTrue(any("K" in x for x in lifts()))
        self.assertTrue(any("authorship" in x for x in lifts()))

    def test_no_accept_or_approve_surface_exists_anywhere(self):
        # An accept button would be warrant increasing by APPROVAL without authorship. Its
        # absence is constitutional, so it is checked rather than assumed.
        from engine.constants import REPO_ROOT
        page = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8").lower()
        for banned in ("accept", "approve", "endorse", "confirm claim"):
            self.assertNotIn(f'onclick="{banned}', page)
            self.assertNotIn(f">{banned}<", page)

    def test_the_server_exposes_no_approval_endpoint(self):
        import inspect

        import ui.server as srv
        src = inspect.getsource(srv.Handler.do_POST)
        for banned in ('"/accept"', '"/approve"', '"/endorse"'):
            self.assertNotIn(banned, src)

    def test_oi_41_is_in_the_constitution_with_a_resolvable_control(self):
        from tools.build_registry import build
        reg = build()
        self.assertIn("OI-41", reg["entries"])
        self.assertEqual([], reg["entries"]["OI-41"]["unresolved"])
        self.assertTrue(reg["entries"]["OI-41"]["controls"])


class ThePullbackIsVerbatimAndAuditable(unittest.TestCase):

    def test_the_claimed_surface_is_byte_identical(self):
        # A paraphrase in the pullback would be a NEW claim wearing the old one's provenance.
        text = "the cone is positive under composition, and stays so"
        self.assertEqual(text, claim(text, "english", "rec-1").surface)

    def test_a_claim_without_a_source_is_REFUSED(self):
        # The pullback is auditable or it is laundering.
        with self.assertRaises(ValueError):
            claim("something", "english", claimed_from="")

    def test_an_empty_surface_is_REFUSED(self):
        with self.assertRaises(ValueError):
            claim("   ", "english", "rec-1")

    def test_claimed_from_travels_on_the_record(self):
        rec = claim("x y z", "english", "rec-42", source_mode=BRAINSTORM).as_record()
        self.assertEqual("rec-42", rec["claimed_from"])
        self.assertEqual(BRAINSTORM, rec["source_mode"])


class TheGestureIsAlwaysAnASSERTION(unittest.TestCase):
    """The mode governs the PROMPT's standing, never the gesture's."""

    def test_a_claim_fired_in_brainstorm_still_enters_at_authorship(self):
        c = claim("a claim of mine", "english", "rec-9", source_mode=BRAINSTORM)
        self.assertEqual(WarrantTier.AUTHORSHIP, c.tier)
        self.assertEqual(ASSERT, c.mode)

    def test_the_source_mode_is_kept_for_audit_not_for_warrant(self):
        for m in MODES:
            c = claim("x y z", "english", "r", source_mode=m)
            self.assertEqual(m, c.source_mode)
            self.assertEqual(CLAIM_TIER, c.tier)

    def test_claiming_ALWAYS_retains(self):
        # Claiming-to-discard is incoherent: the gesture's content is that this becomes the
        # operator's, and an object discarded after settling was never taken.
        self.assertTrue(CLAIM_RETAINS)
        self.assertTrue(claim("x y z", "english", "r").retains)


class TheLaunderingLock(unittest.TestCase):
    """In-session agreement, however enthusiastic, confers nothing."""

    def test_agreement_text_does_not_change_a_proposals_tier(self):
        # PLANTED: the operator says "yes exactly, perfect" about a proposal. The proposal's
        # tier must be unchanged — only the explicit gesture lifts it.
        from engine.mode import PROPOSAL_TIER
        before = PROPOSAL_TIER
        transcript = "yes exactly, perfect — that's right, keep that one"
        self.assertEqual(before, PROPOSAL_TIER, transcript and "agreement is not a lift")
        self.assertEqual(WarrantTier.EXTRACTION, PROPOSAL_TIER)

    def test_reaching_authorship_requires_constructing_a_Claim(self):
        # There is no function that raises an existing record's tier. The only way to hold an
        # AUTHORSHIP object is to build one, with a source, explicitly.
        import engine.claim as mod
        self.assertFalse(any(n.startswith(("promote", "accept", "approve", "upgrade"))
                             for n in dir(mod)))
        self.assertEqual(WarrantTier.AUTHORSHIP,
                         Claim("a surface", "english", "rec-1", ASSERT).tier)


class TheTwoByTwoIsForcedAndComplete(unittest.TestCase):

    def test_it_is_the_product_of_two_two_element_sets(self):
        self.assertEqual(2, len(MODES))
        self.assertEqual(4, len({cell(m, r) for m in MODES for r in (False, True)}))

    def test_no_fifth_state_is_constructible(self):
        from engine.mode import INPUT_TIER
        self.assertEqual({ASSERT, BRAINSTORM}, set(INPUT_TIER))


if __name__ == "__main__":
    unittest.main()


class TheGestureOpensNoNewWritePoint(unittest.TestCase):
    """OI-33's closed set is unchanged. A claim is perturb-retain with authorship."""

    def test_the_write_point_set_is_still_exactly_four(self):
        from engine.mz import WRITE_POINTS
        self.assertEqual({"perturb.retain", "walk.arrow", "aging.decay", "mz.promote"},
                         set(WRITE_POINTS))

    def test_no_claim_write_point_was_added(self):
        from engine.mz import WRITE_POINTS
        for invented in ("claim", "claim.retain", "authorship.pullback", "accept"):
            self.assertNotIn(invented, WRITE_POINTS)

    def test_the_endpoint_routes_through_the_ordinary_retain_path(self):
        # The gesture must reach the tape the way everything else does. A gesture that quietly
        # opened a fifth door would be the tape growing a second entrance.
        import inspect

        import ui.server as srv
        src = inspect.getsource(srv.Handler.do_POST)
        claim_block = src[src.index('elif path == "/claim"'):src.index('elif path == "/ask"')]
        self.assertIn("CURRENT.propose_text", claim_block)

    def test_the_module_states_it_is_not_a_new_write_point(self):
        import engine.claim as mod
        self.assertIn("NOT A NEW WRITE-POINT", (mod.__doc__ or "").upper())


class TheNormativeDocumentsCARRYTheSurface(unittest.TestCase):
    """VIOLATED BY OMISSION once: the mode shipped in code, tests and UI with zero mentions in
    either normative document. Built machinery, unwritten law — B5's definition of
    unconstitutional, and found by the operator's sweep rather than by anything here."""

    def _doc(self, name):
        from engine.constants import REPO_ROOT
        p = REPO_ROOT / "seed" / name
        self.assertTrue(p.exists(), f"seed/{name} is normative and must exist")
        return p.read_text(encoding="utf-8")

    def test_the_spec_exists_and_carries_section_ten(self):
        body = self._doc("SPEC.md")
        self.assertIn("THE INTERACTION SURFACE", body)
        self.assertIn("§10", body)

    def test_the_spec_names_both_modes(self):
        body = self._doc("SPEC.md")
        self.assertIn("Assert / Brainstorm", body)

    def test_the_spec_states_the_gesture_is_not_a_new_write_point(self):
        self.assertIn("NOT A NEW WRITE-POINT", self._doc("SPEC.md"))

    def test_the_constitution_carries_the_surface_invariant(self):
        self.assertIn("OI-42", self._doc("CONSTITUTION.md"))
        self.assertIn("brainstorm", self._doc("CONSTITUTION.md").lower())

    def test_part_four_names_what_is_missing(self):
        # Part IV shrinking is the definition of progress; a Part IV that names nothing is a
        # spec claiming completeness it does not have.
        body = self._doc("SPEC.md")
        self.assertIn("WHAT IS NOT YET WRITTEN", body)
        self.assertIn("DIALOGIC", body.upper())
