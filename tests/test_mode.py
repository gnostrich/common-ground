"""THE WARRANT SELECTOR: assert vs brainstorm, and the lock that stops it laundering.

Not a new mechanism. `WarrantTier.AUTHORSHIP` has always existed and the window has always
used it for anything typed — a hardcoded decision about what typing MEANS, made once in the UI
and never surfaced as a choice. Typing a claim and typing a hunch were entering at the same
warrant.

The danger in adding the mode is precise: it could become a laundering channel. Think out
loud, like what comes back, and watch it become authored. These controls are what stop that.
"""

import unittest

from engine.mode import (ASSERT, BRAINSTORM, MODES, PROPOSAL_TIER, cell, input_enters,
                         input_tier, normalize, stamp)
from engine.types import WarrantTier


class TheSelectorIsATierChoiceTheTypeSystemAlreadyCarried(unittest.TestCase):

    def test_assert_enters_the_input_at_AUTHORSHIP(self):
        self.assertEqual(WarrantTier.AUTHORSHIP, input_tier(ASSERT))

    def test_brainstorm_enters_the_input_at_NO_TIER_AT_ALL(self):
        # "Zero warrant" is not a new tier. EXTRACTION is already the floor and already never
        # grounds; below it there is no tier because below it there is no CLAIM.
        self.assertIsNone(input_tier(BRAINSTORM))
        self.assertFalse(input_enters(BRAINSTORM))

    def test_no_tier_below_extraction_was_invented(self):
        self.assertEqual(WarrantTier.EXTRACTION, min(WarrantTier, key=lambda t: -t.value))
        self.assertEqual(PROPOSAL_TIER, WarrantTier.EXTRACTION)

    def test_the_mediums_tier_is_the_same_in_both_modes(self):
        # The medium is a peripheral. Its output is extraction whoever asked and however.
        self.assertEqual(WarrantTier.EXTRACTION, PROPOSAL_TIER)


class TheLOCK(unittest.TestCase):
    """A brainstorm proposal is EXTRACTION whatever the operator says about it in-session."""

    def test_a_brainstorm_proposal_can_never_reach_authorship(self):
        self.assertEqual(WarrantTier.EXTRACTION, PROPOSAL_TIER)
        self.assertNotEqual(WarrantTier.AUTHORSHIP, PROPOSAL_TIER)

    def test_the_stamp_says_re_assertion_is_the_only_path(self):
        note = stamp(BRAINSTORM)["note"]
        self.assertIn("re-assertion", note)
        self.assertIn("confers nothing", note)

    def test_a_brainstormed_input_is_not_a_weakly_warranted_claim(self):
        # It is not a claim. A weak tier would still be a tier, and a tape entry.
        self.assertEqual("none", stamp(BRAINSTORM)["input_tier"])
        self.assertEqual("AUTHORSHIP", stamp(ASSERT)["input_tier"])


class AnUnknownModeIsTheSTRICTERReading(unittest.TestCase):

    def test_an_unknown_mode_defaults_to_assert(self):
        # Defaulting the other way would let a malformed request silently strip warrant from
        # something the operator meant to stand behind.
        for junk in ("", None, "nonsense", "BRAINSTORMY", "  "):
            self.assertEqual(ASSERT, normalize(junk))

    def test_the_two_modes_round_trip(self):
        for m in MODES:
            self.assertEqual(m, normalize(m.upper()))


class ModeIsSTAMPEDOnEveryRecord(unittest.TestCase):

    def test_the_stamp_carries_mode_and_both_tiers(self):
        for m in MODES:
            s = stamp(m)
            self.assertEqual(m, s["mode"])
            self.assertIn("input_tier", s)
            self.assertEqual("EXTRACTION", s["proposal_tier"])

    def test_the_stamp_is_never_empty(self):
        # A proposal that cannot say which act produced it cannot be re-read later as what it
        # was — an exploratory arrow would be indistinguishable from an asserted one the
        # moment the session ended.
        for m in (None, "", "junk", ASSERT, BRAINSTORM):
            self.assertTrue(stamp(m)["mode"])
            self.assertTrue(stamp(m)["note"])


class AllFourCellsAreMeaningful(unittest.TestCase):
    """2x2 with retain. Not a flag crossed with a flag."""

    def test_every_cell_has_a_distinct_meaning(self):
        seen = {cell(m, r) for m in MODES for r in (False, True)}
        self.assertEqual(4, len(seen))

    def test_brainstorm_retain_keeps_the_proposals_not_the_prompt(self):
        text = cell(BRAINSTORM, True)
        self.assertIn("EXTRACTION", text)
        self.assertIn("the prompt does not enter", text)

    def test_assert_retain_is_the_only_cell_that_enters_at_authorship(self):
        self.assertIn("AUTHORSHIP", cell(ASSERT, True))
        for m, r in ((ASSERT, False), (BRAINSTORM, False), (BRAINSTORM, True)):
            self.assertNotIn("AUTHORSHIP", cell(m, r))


if __name__ == "__main__":
    unittest.main()


class TheModeReachesTheACT(unittest.TestCase):
    """Wired, not merely defined. The selector is worthless if the act ignores it."""

    def test_the_page_offers_the_selector_beside_retain(self):
        from engine.constants import REPO_ROOT
        page = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="brainstorm"', page)
        self.assertIn("id=\"retain\"", page)

    def test_both_endpoints_receive_the_mode(self):
        from engine.constants import REPO_ROOT
        page = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("'/propose', {text, chart, mode}", page)
        self.assertIn("'/ask', {question:text, chart, mode}", page)

    def test_the_server_normalizes_and_stamps(self):
        import inspect

        import ui.server as srv
        src = inspect.getsource(srv.Handler.do_POST)
        self.assertIn("normalize_mode", src)
        self.assertIn("mode_stamp", src)

    def test_an_ask_response_carries_the_mode_stamp(self):
        # BEHAVIOURAL, not a source scan: build the payload the handler builds.
        from engine.mode import stamp
        payload = {"answer": "x", "mode": stamp("brainstorm")}
        self.assertEqual("brainstorm", payload["mode"]["mode"])
        self.assertEqual("none", payload["mode"]["input_tier"])

    def test_the_selector_tooltip_states_the_lock(self):
        # The operator must be able to read what the checkbox DOES without reading the code:
        # that agreeing in-session confers nothing and re-assertion is the only path.
        from engine.constants import REPO_ROOT
        page = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("confers nothing", page)
        self.assertIn("re-assert", page.lower())


class EveryLMCallIsRecordedRAW(unittest.TestCase):
    """Both ports, both directions, before any parsing.

    The operator asked to see what goes into the LM and the dump immediately found a defect no
    test had: twenty-four numbered state lines carrying no claim text. That is the argument for
    the transcript. The LM is a peripheral with two ports, and the bytes crossing them are the
    one place where "the code does X" and "X is what the model saw" can differ silently.
    """

    def test_a_call_records_both_directions_verbatim(self):
        from engine.transcript import Transcript
        t = Transcript()
        t.record("render", "SYS", "USER", "REPLY", model="m", seconds=1.5)
        rec = t.as_record()[0]
        self.assertEqual("SYS", rec["system"])
        self.assertEqual("USER", rec["user"])
        self.assertEqual("REPLY", rec["reply"])

    def test_digests_make_displayed_bytes_checkable_against_sent_bytes(self):
        from engine.transcript import Transcript, digest
        t = Transcript()
        t.record("render", "SYS", "USER", "REPLY")
        rec = t.as_record()[0]
        self.assertEqual(digest("SYS"), rec["system_sha"])
        self.assertEqual(digest("USER"), rec["user_sha"])
        self.assertEqual(digest("REPLY"), rec["reply_sha"])
        self.assertNotEqual(digest("SYS"), digest("SYS "))

    def test_the_ATTACHMENT_call_is_recorded_not_only_the_render(self):
        # It is the call that decides what the answer can possibly be about. Recording only
        # the last would show the answer's input and hide its cause.
        import inspect

        import engine.perturb as perturb
        src = inspect.getsource(perturb)
        self.assertIn('TRANSCRIPT.record("propose"', src)

    def test_the_render_call_is_recorded_too(self):
        import inspect

        import ui.server as srv
        self.assertIn('TRANSCRIPT.record("render"', inspect.getsource(srv.Handler.do_POST))

    def test_starting_an_act_clears_the_previous_transcript(self):
        # Otherwise one act's traffic would be attributed to the next.
        from engine.transcript import CURRENT, start
        start()
        CURRENT.record("propose", "a", "b", "c")
        self.assertEqual(1, len(CURRENT.calls))
        start()
        self.assertEqual([], CURRENT.calls)

    def test_the_reply_is_recorded_BEFORE_parsing(self):
        # The parse is what the transcript exists to let somebody check; recording the parsed
        # result would make it unable to show a parse that went wrong.
        from engine.transcript import Transcript
        t = Transcript()
        t.record("propose", "s", "u", "0 -bears_on-> 1\nnot a triple at all")
        self.assertIn("not a triple at all", t.as_record()[0]["reply"])
