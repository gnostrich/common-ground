"""THE GATE THAT LICENSES ANSWER-FIRST, with its planted violation.

The answer moved to the top of the page. What makes that warranted rather than a layout
preference is that an answer asserting anything outside the trace goes RED — so the RED case
is planted here, and if it ever passes the hierarchy is unlicensed.
"""

import unittest

from engine.grounded import LICENSED, MIN_CONTENT, check_answer, ground_of, words


def _compiled(nus, typed="is the cone positive", attached=(), silence=""):
    return {
        "typed": typed,
        "field_status": "RELAXED",
        "relaxation": {"silence": silence,
                       "rows": [{"nu": f"\x01english\x01{n}", "chart": "english",
                                 "type": "claim", "path": []} for n in nus]},
        "attachment": {"proposed": [{"dst_nu": f"\x01english\x01{a}", "kind": "corresponds",
                                     "accepted": True, "dst_chart": "english",
                                     "evidence": ""} for a in attached]},
    }


class TheGroundIsWhatTheFieldSupplied(unittest.TestCase):

    def test_moved_claims_and_attachments_both_ground(self):
        g = ground_of(_compiled(["the cone is positive under the metric"],
                                attached=["curvature bounds the spectrum"]))
        self.assertIn("metric", g)
        self.assertIn("curvature", g)

    def test_the_typed_question_grounds_its_own_words(self):
        self.assertIn("cone", ground_of(_compiled([], typed="is the cone positive")))

    def test_a_silence_reason_grounds_the_words_it_uses(self):
        g = ground_of(_compiled([], silence="no declared correspondence carried it further"))
        self.assertIn("carried", g)

    def test_the_ground_is_built_from_full_nu_strings_not_trimmed_ones(self):
        long_nu = "alpha " * 60 + "omegaword"
        self.assertIn("omegaword", ground_of(_compiled([long_nu])))


class APlantedViolationIsRED(unittest.TestCase):

    def test_an_answer_importing_a_claim_the_field_never_moved_goes_red(self):
        c = _compiled(["the cone is positive under the metric"])
        v = check_answer("This follows from the Riemann hypothesis.", c)
        self.assertFalse(v.ok)
        self.assertIn("riemann", v.violations[0].ungrounded)

    def test_the_convicting_words_are_named_not_just_counted(self):
        c = _compiled(["the cone is positive"])
        v = check_answer("Perelman settled it.", c)
        self.assertIn("perelman", v.violations[0].ungrounded)

    def test_one_bad_sentence_among_good_ones_is_still_red(self):
        c = _compiled(["the cone is positive under the metric"])
        v = check_answer("The cone is positive under the metric. "
                         "Perelman proved the Poincare conjecture.", c)
        self.assertFalse(v.ok)
        self.assertEqual(1, len(v.violations))
        self.assertEqual(2, v.checked)

    def test_a_number_the_field_did_not_supply_is_an_importation(self):
        c = _compiled(["the cone is positive"])
        self.assertFalse(check_answer("It holds for 1729 cases.", c).ok)


class AGroundedAnswerPasses(unittest.TestCase):

    def test_an_answer_built_from_the_moved_claim_is_green(self):
        c = _compiled(["the cone is positive under the metric"])
        v = check_answer("The field moved one claim: the cone is positive under the metric. "
                         "Nothing else responded.", c)
        self.assertTrue(v.ok, v.violations and v.violations[0].render())

    def test_the_machines_own_vocabulary_does_not_convict(self):
        c = _compiled(["the cone is positive"])
        v = check_answer("Nothing in the field responded, and the relation is unmeasured "
                         "rather than absent.", c)
        self.assertTrue(v.ok, v.violations and v.violations[0].render())

    def test_quoting_a_long_moved_claim_verbatim_is_green(self):
        nu = ("the second fundamental form of the boundary controls the spectral gap "
              "whenever the ambient curvature is bounded below by a positive constant")
        v = check_answer(f"The field moved this claim: {nu}.", _compiled([nu]))
        self.assertTrue(v.ok, v.violations and v.violations[0].render())


class TheGreenIsNotOverclaimed(unittest.TestCase):

    def test_an_empty_answer_reports_zero_checked_so_it_cannot_read_as_a_pass(self):
        v = check_answer("", _compiled(["the cone is positive"]))
        self.assertEqual(0, v.checked)
        self.assertEqual(0, len(v.violations))

    def test_the_licensed_list_holds_no_topic_word(self):
        # A topic word here would silently license importation of that topic forever. The
        # check is that nothing in the list is a term a corpus would be ABOUT.
        planted = {"riemann", "curvature", "manifold", "spectrum", "perelman", "cone"}
        self.assertEqual(set(), planted & LICENSED)

    def test_content_threshold_is_stated_not_incidental(self):
        self.assertEqual(4, MIN_CONTENT)
        self.assertEqual(set(), words("is it in on at a of to"))


class TheVerdictTravelsAsData(unittest.TestCase):

    def test_the_record_carries_the_sentences_and_the_words(self):
        rec = check_answer("Perelman settled it.", _compiled(["the cone is positive"])).as_record()
        self.assertFalse(rec["ok"])
        self.assertEqual(1, rec["checked"])
        self.assertIn("perelman", rec["violations"][0]["ungrounded"])


if __name__ == "__main__":
    unittest.main()
