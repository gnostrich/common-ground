"""Acceptance controls for the conversation chart (session item B).

The bar (operator, restated as the acceptance check): the conversation chart produces
BOTH outputs on the fixtures —

  1. speaker-attributed claims (the segmentation gap closed), and
  2. a listable proposal -> verdict {accepted | rejected | sharpened} record (the
     load-bearing one — the fast-tape calibration signal a future K and proposer consume).

Plus the move-1 hygiene: it is a manifest row + behavior registration (no dispatch edit),
it addresses idempotently like every chart, it routes, and the chart plug-in audit stays
PASS.

The synthetic fixture is authored so all three verdict kinds materialize, with one proposal
left open (no one takes it up).
"""

from __future__ import annotations

import unittest

from engine.conversation import (
    as_fast_tape_entries,
    parse_transcript,
    proposal_verdict_ledger,
    speaker_claims,
)
from engine.normalize import address, nu

# Alice proposes; Bob accepts one, Carol rejects one, Alice sharpens one, and the last
# proposal is never taken up (open).
FIXTURE = """\
Alice: The cone is positive under composition.
Bob: Yes, agreed, the cone stays positive under composition.
Alice: The spectral radius equals the largest eigenvalue.
Carol: No, that is wrong; the spectral radius is the maximum modulus eigenvalue.
Bob: The transfer defect is first order in the perturbation.
Alice: More precisely, the transfer defect is first order only to leading order.
Carol: The state-space system is observable.
"""


class SpeakerAttributedClaims_Output1(unittest.TestCase):
    def test_every_claim_carries_its_speaker_and_turn(self):
        claims = speaker_claims(FIXTURE)
        self.assertTrue(claims)
        speakers = {c.speaker for c in claims}
        self.assertEqual(speakers, {"Alice", "Bob", "Carol"})
        for c in claims:
            self.assertTrue(c.claim)
            self.assertIn(c.speaker, c.locator, "the locator must name the speaker")
            self.assertTrue(c.locator.startswith(f"turn:{c.turn}:"))

    def test_parse_is_seven_turns(self):
        self.assertEqual(len(parse_transcript(FIXTURE)), 7)

    def test_a_continuation_line_extends_the_previous_turn(self):
        t = parse_transcript("Alice: first part\nand the same turn continues.\nBob: reply here.")
        self.assertEqual(len(t), 2)
        self.assertIn("continues", t[0].text)


class ProposalVerdictLedger_Output2(unittest.TestCase):
    """The load-bearing output: proposal -> {accepted | rejected | sharpened | open}."""

    def _verdict_for(self, ledger, needle):
        hits = [pv for pv in ledger if needle in pv.proposal.casefold()]
        self.assertTrue(hits, f"no proposal matches {needle!r}")
        return hits[0]

    def test_all_three_verdict_kinds_materialize(self):
        ledger = proposal_verdict_ledger(FIXTURE)
        kinds = {pv.verdict for pv in ledger}
        for required in ("accepted", "rejected", "sharpened"):
            self.assertIn(required, kinds, f"{required} must appear on the fixture")

    def test_accepted_case(self):
        pv = self._verdict_for(proposal_verdict_ledger(FIXTURE), "cone is positive")
        self.assertEqual(pv.verdict, "accepted")
        self.assertEqual(pv.decided_by, "Bob")
        self.assertEqual(pv.proposer, "Alice")

    def test_rejected_case(self):
        pv = self._verdict_for(proposal_verdict_ledger(FIXTURE), "spectral radius equals")
        self.assertEqual(pv.verdict, "rejected")
        self.assertEqual(pv.decided_by, "Carol")

    def test_sharpened_case(self):
        pv = self._verdict_for(proposal_verdict_ledger(FIXTURE), "transfer defect is first order")
        self.assertEqual(pv.verdict, "sharpened")
        self.assertEqual(pv.decided_by, "Alice")

    def test_untaken_proposal_is_open(self):
        pv = self._verdict_for(proposal_verdict_ledger(FIXTURE), "observable")
        self.assertEqual(pv.verdict, "open")
        self.assertIsNone(pv.decided_by)

    def test_ledger_is_deterministic(self):
        a = proposal_verdict_ledger(FIXTURE)
        b = proposal_verdict_ledger(FIXTURE)
        self.assertEqual([(x.proposal, x.verdict, x.decided_by) for x in a],
                         [(x.proposal, x.verdict, x.decided_by) for x in b])

    def test_fast_tape_marks_accepted_and_sharpened_as_promotion_candidates(self):
        entries = as_fast_tape_entries(proposal_verdict_ledger(FIXTURE))
        by_verdict = {e["verdict"]: e["promotion_candidate"] for e in entries}
        self.assertTrue(by_verdict["accepted"])
        self.assertTrue(by_verdict["sharpened"])
        self.assertFalse(by_verdict["rejected"])
        self.assertFalse(by_verdict["open"])


class ConversationChartIsAMoveOneChart(unittest.TestCase):
    def test_it_is_a_declared_chart_with_its_own_tag(self):
        from engine.charts import chart_names, chart_spec, is_chart

        self.assertTrue(is_chart("conversation"))
        self.assertIn("conversation", chart_names())
        self.assertEqual(chart_spec("conversation").tag_id, "cv")

    def test_nu_is_idempotent_and_tagged(self):
        s = "The cone is POSITIVE under  composition."
        once = nu("conversation", s)
        self.assertEqual(once, nu("conversation", once), "nu(nu(x)) != nu(x)")
        self.assertTrue(once.startswith("\x01cv\x01"), "the cv tag rides inside the address")

    def test_a_conversation_claim_addresses_distinctly_from_the_same_prose(self):
        # Same claim text, different chart => different address space (additive morphism).
        c_slot, _ = address("conversation", "the cone is positive", "assert")
        e_slot, _ = address("english", "the cone is positive", "assert")
        self.assertNotEqual(c_slot, e_slot)

    def test_the_belonging_audit_now_marks_it_built(self):
        from engine.three_moves import EXTENSIONS

        conv = [e for e in EXTENSIONS if "conversation" in e.name][0]
        self.assertEqual(conv.move, "swap-base")
        self.assertEqual(conv.status, "built")


class ConversationRoutes(unittest.TestCase):
    def test_a_transcript_routes_to_the_conversation_chart(self):
        from engine.router import CONVERSATION, route

        r = route("dialogue.md", FIXTURE)
        self.assertEqual(r.destination, CONVERSATION)
        self.assertIsNotNone(r.document)
        self.assertEqual(r.document.chart, CONVERSATION)

    def test_ordinary_prose_with_a_colon_does_not_read_as_conversation(self):
        from engine.router import ENGLISH, route

        prose = "Note: the cone is positive. This is a single-author paragraph, not a dialogue."
        self.assertEqual(route("n.md", prose).destination, ENGLISH)


class TheChartAuditStaysPassWithConversation(unittest.TestCase):
    def test_adding_the_conversation_chart_kept_the_plugin_property(self):
        from engine.chart_plugin_audit import verdict

        v = verdict()
        self.assertTrue(v["manifest_only_possible"], v)
        self.assertEqual(v["blocking_sites"], [])


if __name__ == "__main__":
    unittest.main()


class VerdictsCarryTheEraThatPairedThem(unittest.TestCase):
    """THE QUARANTINE PATTERN, THIRD APPLICATION.

    Every verdict in every ledger built before `engine/referee_sweep.py` caught it was paired
    by `p_keys & _keywords(r.claim)` — a word-bag intersection. Those records are not
    known-wrong; they are UNCONFIRMED, the same status lite-era arrows carry. So they are
    tagged and held, not trusted and not deleted.
    """

    def _pv(self, era=None, verdict="accepted"):
        from engine.conversation import ADJACENCY_ERA, ProposalVerdict
        return ProposalVerdict("a claim", "A", 0, verdict, "B", 1, "i agree", "loc:0",
                               verdict_method=era or ADJACENCY_ERA)

    def test_a_freshly_built_ledger_is_adjacency_era(self):
        from engine.conversation import ADJACENCY_ERA, proposal_verdict_ledger
        led = proposal_verdict_ledger("A: the cone is positive.\nB: that is wrong.\n")
        self.assertTrue(led)
        self.assertTrue(all(pv.verdict_method == ADJACENCY_ERA for pv in led))

    def test_a_keyword_era_verdict_is_a_lead_not_a_promotion_candidate(self):
        from engine.conversation import KEYWORD_ERA, as_fast_tape_entries, is_lead
        pv = self._pv(KEYWORD_ERA)
        self.assertTrue(is_lead(pv))
        e = as_fast_tape_entries([pv])[0]
        self.assertFalse(e["promotion_candidate"])
        self.assertTrue(e["lead"])

    def test_the_same_verdict_under_adjacency_IS_a_candidate(self):
        # The verdict text is identical; only the pairing era differs. That is the whole
        # point of tagging rather than deleting.
        from engine.conversation import as_fast_tape_entries
        self.assertTrue(as_fast_tape_entries([self._pv()])[0]["promotion_candidate"])

    def test_a_held_record_says_why_so_absence_is_not_read_as_rejection(self):
        from engine.conversation import KEYWORD_ERA, as_fast_tape_entries
        e = as_fast_tape_entries([self._pv(KEYWORD_ERA)])[0]
        self.assertIn("re-run", e["held"])
        self.assertEqual("", as_fast_tape_entries([self._pv()])[0]["held"])

    def test_the_verdict_itself_survives_the_hold(self):
        # Held is not deleted: the verdict, its cue and its decider are all still readable.
        from engine.conversation import KEYWORD_ERA, as_fast_tape_entries
        e = as_fast_tape_entries([self._pv(KEYWORD_ERA)])[0]
        self.assertEqual("accepted", e["verdict"])
        self.assertEqual("i agree", e["cue"])
        self.assertEqual("B", e["decided_by"])

    def test_a_rejected_keyword_era_verdict_is_also_held(self):
        # The hold is on the PAIRING, not on the polarity — a wrongly-paired rejection is
        # exactly as unconfirmed as a wrongly-paired acceptance.
        from engine.conversation import KEYWORD_ERA, is_lead
        self.assertTrue(is_lead(self._pv(KEYWORD_ERA, verdict="rejected")))

    def test_a_record_read_back_without_a_tag_is_the_OLD_era(self):
        # The dataclass default is the NEW era, which is right for a record this build made
        # and exactly wrong for one persisted before the tag existed. A missing field is the
        # keyword era — never the current one. Same rule as `unknown` is not `fresh`.
        from engine.conversation import KEYWORD_ERA, era_of_record
        self.assertEqual(KEYWORD_ERA, era_of_record({"verdict": "accepted"}))
        self.assertEqual(KEYWORD_ERA, era_of_record({"verdict_method": None}))

    def test_a_tagged_record_keeps_its_tag(self):
        from engine.conversation import ADJACENCY_ERA, era_of_record
        self.assertEqual(ADJACENCY_ERA,
                         era_of_record({"verdict_method": ADJACENCY_ERA}))

    def test_the_rendered_surface_carries_the_era(self):
        from engine.conversation import ADJACENCY_ERA, ProposalVerdict
        pv = ProposalVerdict("c", "A", 0, "accepted", "B", 1, "i agree", "l")
        self.assertEqual(ADJACENCY_ERA, pv.verdict_method)
