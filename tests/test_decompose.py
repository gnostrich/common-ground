"""OI-30, MECHANIZED: a known cause must not absorb an unknown one.

A total gets explained by causes; the named causes fall short; the remainder goes somewhere.
Two of the three places it can go are lies — folded into the largest named cause, which
overstates a real mechanism, or silently dropped, so the parts do not sum and nobody can tell
by looking. Only the third is true, and `engine.decompose` offers only the third.

WHERE IT WAS ACTUALLY WRONG. `Journal.totals()` reported `asked`, derived from the ANSWER
counters, beside `calls`, derived from the call log. Two denominators, and nothing named the
gap: a call that produced no parseable answer — a refusal, a truncation, a malformed reply —
counted in one and not the other. `call_errors` named part of it and the rest was invisible.
That is a known cause absorbing an unknown one, sitting in the totals the operator reads to
decide whether the daemon is working.

THE CONTROLS BELOW check the vocabulary and the site. They also check the composition with
OI-24, which is the subtle half: a decomposition of a ZERO total reports every cause at zero
and a remainder of zero, which reads as "everything is explained". Nothing was explained
because nothing happened, and those are different facts.
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from engine.decompose import (NotDecomposed, OverAttributed, UNATTRIBUTED, attributed,
                              decompose, sums)


class TheRemainderIsALWAYSNamed(unittest.TestCase):

    def test_an_unexplained_remainder_is_reported_not_dropped(self):
        r = decompose("calls", 100, {"answered": 90, "errored": 4}, unit="call")
        self.assertEqual(r[UNATTRIBUTED], 6)
        self.assertTrue(sums(r))
        self.assertFalse(attributed(r))

    def test_the_key_is_present_even_at_ZERO(self):
        """A missing key and a zero read identically to somebody skimming a table. That is
        the whole reason the key is never omitted."""
        r = decompose("calls", 10, {"answered": 10}, unit="call")
        self.assertIn(UNATTRIBUTED, r)
        self.assertEqual(r[UNATTRIBUTED], 0)
        self.assertTrue(attributed(r))

    def test_the_note_says_the_remainder_is_a_MEASUREMENT(self):
        """An unattributed count is not a rounding error, and the prose must not let a reader
        treat it as one."""
        r = decompose("calls", 100, {"answered": 90}, unit="call")
        self.assertIn("NOT", r["note"])
        self.assertIn("measurement", r["note"])

    def test_over_attribution_RAISES_rather_than_going_negative(self):
        """A negative remainder would be arithmetic covering a double count."""
        with self.assertRaises(OverAttributed) as cm:
            decompose("calls", 5, {"answered": 4, "errored": 3}, unit="call")
        self.assertIn("double count", str(cm.exception))

    def test_a_plain_counts_dict_CANNOT_be_asked_whether_it_attributes(self):
        """The refusal is the mechanism. Answering True for a dict that simply has no
        remainder key is exactly the silent-drop case this module exists to prevent."""
        with self.assertRaises(NotDecomposed):
            attributed({"answered": 90, "errored": 4})


class OI24LivesInsideOI30(unittest.TestCase):
    """A decomposition of nothing is not a clean decomposition."""

    def test_a_zero_total_is_REFUSED(self):
        r = decompose("calls", 0, {"answered": 0}, unit="call")
        self.assertTrue(r["refused"])
        self.assertIn("empty one", r["note"])

    def test_a_refused_decomposition_cannot_be_asked_if_it_attributes(self):
        with self.assertRaises(NotDecomposed):
            attributed(decompose("calls", 0, {"answered": 0}, unit="call"))

    def test_a_real_total_is_not_refused(self):
        """Not vacuous: the same call over a real population answers."""
        self.assertFalse(decompose("calls", 3, {"answered": 3}, unit="call")["refused"])


class TheJournalNAMESWhatItsCallsDid(unittest.TestCase):
    """The site the invariant was actually violated at."""

    def _journal(self):
        from engine.journal import Journal

        self._d = tempfile.TemporaryDirectory()
        return Journal(pathlib.Path(self._d.name) / "j.jsonl")

    def tearDown(self):
        d = getattr(self, "_d", None)
        if d is not None:
            d.cleanup()

    def test_totals_carries_a_decomposition_of_the_calls(self):
        t = self._journal().totals()
        self.assertIn("calls_by_outcome", t,
                      "the totals must say what every call did, not only how many there were")
        self.assertIn(UNATTRIBUTED, t["calls_by_outcome"])

    def test_an_empty_journal_REFUSES_rather_than_reporting_all_explained(self):
        t = self._journal().totals()
        self.assertTrue(t["calls_by_outcome"]["refused"],
                        "no calls is not a finding that every call is accounted for")

    def test_the_raw_counters_are_still_there(self):
        """Reported BESIDE the counters, never replacing them — other code reads those, and a
        decomposition that swallowed them would be its own known-cause-absorbs-unknown."""
        t = self._journal().totals()
        for k in ("asked", "answers", "calls", "call_errors"):
            self.assertIn(k, t)

    def test_the_decomposition_SUMS_on_a_journal_with_real_calls(self):
        j = self._journal()
        j.calls.extend([1.0, 2.0, 3.0, 4.0])
        j.counts["answer:same_claim"] = 2
        t = j.totals()
        d = t["calls_by_outcome"]
        self.assertEqual(d["total"], 4)
        self.assertTrue(sums(d), d)
        self.assertEqual(d[UNATTRIBUTED], 2,
                         "four calls, two answers, no errors: two calls did something nothing "
                         "here accounts for, and that must be visible")


class PlantedAbsorption(unittest.TestCase):
    """The control's own control: rebuild the defect and show it reads as clean."""

    def test_folding_the_remainder_into_a_named_cause_is_indistinguishable_by_eye(self):
        honest = decompose("calls", 100, {"answered": 90, "errored": 4}, unit="call")
        absorbed = {"answered": 96, "errored": 4}          # remainder folded into the big one
        self.assertEqual(sum(absorbed.values()), honest["total"])
        # Both "add up". Only one of them says which part nothing explains.
        self.assertEqual(honest["by_cause"]["answered"], 90)
        self.assertEqual(absorbed["answered"], 96)
        with self.assertRaises(NotDecomposed):
            attributed(absorbed)

    def test_dropping_the_remainder_fails_the_SUM_check(self):
        dropped = dict(decompose("calls", 100, {"answered": 90}, unit="call"))
        dropped[UNATTRIBUTED] = 0                          # the silent drop
        self.assertFalse(sums(dropped),
                         "a dropped remainder must be visible in the arithmetic")


if __name__ == "__main__":
    unittest.main()
