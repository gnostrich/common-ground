"""THE BATTERY'S ACCEPTANCE, and it is not "the checks pass".

A battery is accepted when it TRIPS on the defects that were already caught by hand. Each of
the three below was found by the operator reading a live transcript, after a green suite of
sixteen hundred tests. Each is replayed here from the recorded run — bracket skeleton, corpus
prose redacted by `tools/redact_run.py`, because this repository is public — and each must
produce a finding naming its class.

THE STANDING RULE THIS FILE ENCODES: a defect the operator catches that the battery did not is
a MISSING CHECK, and the fix is two commits — the defect, and the check that would have caught
it. This file is where the second commit lands.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.livefire import (CHECKS, audit, check_a_red_verdict_names_a_compliable_rule,
                            check_no_mechanism_prose_on_the_wire, check_panel_hashes_verify,
                            probes, shown_labels)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "livefire"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def kinds(name: str) -> set:
    return {f.check for f in audit(name, load(name))}


class TheBatteryTripsOnEveryDefectTheOperatorCaught(unittest.TestCase):
    """THE ACCEPTANCE. All three, or the battery is incomplete and the battery is fixed first."""

    def test_defect_A_the_empty_answer(self):
        """Four turns, fifty resolved arrows, and nothing on the page. The residual whose only
        job is that case did not fire, because it and `Dialogue.answer` disagreed about what
        "answered" means. Planted from ledger row 528: that run's capture was truncated."""
        self.assertIn("no-degenerate-turn-left-unretried", kinds("defect-a-empty-answer"))

    def test_defect_B_the_residual_asked_three_times(self):
        """The interrogator re-asked a discharged residual and got the same reply byte for
        byte. Replayed from the served run on build 6bc9309592bd."""
        self.assertIn("no-question-asked-twice-with-the-same-reply",
                      kinds("defect-b-repeated-residual"))

    def test_defect_C_the_delimiter_conviction(self):
        """Ten sentences ruled UNCITED while every one carried `[e40, e21]` — citations the
        referee could not read because of a comma. Replayed from the served run on build
        6bc9309592bd."""
        self.assertIn("citations-resolve-against-the-shown-sheet",
                      kinds("defect-c-comma-conviction"))

    def test_all_three_at_once_because_that_is_the_acceptance(self):
        got = {"A": kinds("defect-a-empty-answer"),
               "B": kinds("defect-b-repeated-residual"),
               "C": kinds("defect-c-comma-conviction")}
        self.assertTrue(all(got.values()), f"a defect passed the battery clean: {got}")


class TheBatteryDoesNotFireOnAHEALTHYRun(unittest.TestCase):
    """The other direction, or the battery is a machine that always says yes."""

    HEALTHY = {
        "answer": "The work establishes positivity [e3].",
        "dialogue": {"question": "q", "turn_count": 1, "stopped": "nothing to ask",
                     "records": 1, "resolved_records": 1,
                     "turns": [{"turn": 1, "ask": "q",
                                "prose": "The work establishes positivity [e3].",
                                "resolved": 1, "interrogation": ""}],
                     "residuals": []},
        "faithful": {"ok": True, "checked": 1, "cited": 1, "asserted_absent": 0,
                     "citable": 2, "violations": []},
        "compiled": {"scope": "", "attachment": {"labels": ["b0", "e3", "l7"]},
                     "citations": [{"n": "e3", "kind": "attached", "chart": "english"},
                                   {"n": "l7", "kind": "seated", "chart": "lean"}]},
        # THE ARROW COUNT IS PART OF A HEALTHY RESPONSE, not decoration. A run that cannot say
        # how many arrows were under it cannot be compared to any other environment's run.
        "corpus_header": {"slots": 80566, "arrows": 19385},
        "transcript": [],
    }

    def test_a_clean_run_produces_no_findings(self):
        self.assertEqual(audit("healthy", self.HEALTHY), [])

    def test_a_run_with_a_legal_absence_answer_is_clean(self):
        run = json.loads(json.dumps(self.HEALTHY))
        run["answer"] = "The field does not hold anything about this [∅]."
        run["dialogue"]["turns"][0]["prose"] = run["answer"]
        run["faithful"] = {"ok": True, "checked": 1, "cited": 0, "asserted_absent": 1,
                           "citable": 2, "violations": []}
        self.assertEqual(audit("thin", run), [])


class EachCheckDiscriminates(unittest.TestCase):
    """One planted failure per check, so none of them is decoration."""

    def _base(self):
        return json.loads(json.dumps(TheBatteryDoesNotFireOnAHEALTHYRun.HEALTHY))

    def test_an_unasked_turn_is_caught(self):
        run = self._base()
        run["dialogue"]["turns"].append({"turn": 2, "ask": "a question nobody raised",
                                         "prose": "x [e3].", "resolved": 0,
                                         "interrogation": ""})
        self.assertIn("no-turn-without-a-preceding-question",
                      {f.check for f in audit("planted", run)})

    def test_an_interrogation_a_prior_turn_DID_raise_is_legal(self):
        run = self._base()
        run["dialogue"]["turns"][0]["interrogation"] = "the raised question"
        run["dialogue"]["turns"].append({"turn": 2, "ask": "the raised question",
                                         "prose": "x [e3].", "resolved": 0,
                                         "interrogation": ""})
        self.assertNotIn("no-turn-without-a-preceding-question",
                         {f.check for f in audit("planted", run)})

    def test_a_residual_naming_an_unshown_object_is_caught(self):
        run = self._base()
        # LABEL-SHAPED but not shown. `zz9` would not have worked and that is the chart-tag
        # doorstop doing its job one layer up: a two-letter run is a word, not a label, so it
        # is not scoped against the citable set at all.
        run["dialogue"]["residuals"] = [{"residual": ["e99"], "question": "?", "turn": 2,
                                         "outcome": "unanswered"}]
        self.assertIn("residuals-are-scoped-to-the-perturbation",
                      {f.check for f in audit("planted", run)})

    def test_a_lexical_residual_naming_a_GROUP_is_not_a_stray_label(self):
        run = self._base()
        run["dialogue"]["residuals"] = [{"residual": ["lex", "s1abc"], "question": "?",
                                         "turn": 2, "outcome": "resolved"}]
        self.assertNotIn("residuals-are-scoped-to-the-perturbation",
                         {f.check for f in audit("planted", run)})

    def test_scope_prose_reaching_a_prompt_is_caught(self):
        run = self._base()
        leak = ("WHICH REGION: sampled by declared structure, an arrow-rich neighbourhood "
                "chosen by a hash of the input's address.")
        run["compiled"]["scope"] = leak
        run["transcript"] = [{"system": "S", "user": f"FIELD\n{leak}\n", "reply": "r",
                              "system_sha": "", "user_sha": "", "reply_sha": ""}]
        self.assertIn("no-mechanism-prose-on-the-wire",
                      {f.check for f in check_no_mechanism_prose_on_the_wire("planted", run)})

    def test_a_broken_panel_digest_is_caught(self):
        run = self._base()
        run["transcript"] = [{"system": "S", "user": "U", "reply": "R",
                              "system_sha": "deadbeefdeadbeef", "user_sha": "x",
                              "reply_sha": "y"}]
        found = check_panel_hashes_verify("planted", run)
        self.assertEqual(len(found), 3, "every side of the call must be verified")

    def test_a_verdict_whose_licence_is_absent_from_a_prompt_is_caught(self):
        run = self._base()
        run["faithful"]["violations"] = [{"kind": "welded", "numbers": ["e3", "l7"],
                                          "sentence": "x [e3][l7].", "warrant": ""}]
        run["transcript"] = [{"system": "a prompt that never mentions the escape",
                              "user": "U", "reply": "R", "system_sha": "", "user_sha": "",
                              "reply_sha": ""}]
        found = check_a_red_verdict_names_a_compliable_rule("planted", run)
        self.assertEqual(len(found), 1)
        self.assertIn("rel", found[0].detail)

    def test_a_verdict_whose_licence_IS_present_is_not_caught(self):
        run = self._base()
        run["faithful"]["violations"] = [{"kind": "welded", "numbers": ["e3", "l7"],
                                          "sentence": "x [e3][l7].", "warrant": ""}]
        run["transcript"] = [{"system": 'write [∅rel] when the field declares no relation',
                              "user": "U", "reply": "R", "system_sha": "", "user_sha": "",
                              "reply_sha": ""}]
        self.assertEqual(check_a_red_verdict_names_a_compliable_rule("planted", run), [])

    def test_a_broken_check_is_REPORTED_not_swallowed(self):
        """A battery that silently drops a raising check is a battery that goes quiet the day
        a response shape changes."""
        found = audit("planted", {"dialogue": {"turns": [{"turn": 1}]}, "faithful": None})
        self.assertTrue(found, "a malformed run produced no finding at all")


class NoArtifactCarriesCorpusProse(unittest.TestCase):
    """THE ARTIFACTS ARE PUBLISHED. They are committed, and they attach to issues.

    A finding's evidence is the one place raw corpus prose reaches an artifact: `sentence` and
    `lines` are copied straight off the served response. Two of them did exactly that and were
    caught on the way into git — by a scan, not by design. So the redaction moved to the
    Finding's own constructor, where every present and future check passes through it, instead
    of to the boundary, where the next check to be written would have forgotten.
    """

    def test_a_finding_redacts_its_evidence_sentence_at_construction(self):
        from tools.livefire import Finding

        f = Finding("c", "p", "detail", {"sentence": "The cone is positive [e3][l7]."})
        self.assertNotIn("cone", f.evidence["sentence"])
        self.assertIn("[e3]", f.evidence["sentence"], "the brackets must survive")
        self.assertIn("[l7]", f.evidence["sentence"])

    def test_a_finding_redacts_its_evidence_LINES(self):
        from tools.livefire import Finding

        f = Finding("c", "p", "d", {"lines": ["A claim about the spectral gap [e9]."]})
        self.assertNotIn("spectral", f.evidence["lines"][0])
        self.assertIn("[e9]", f.evidence["lines"][0])

    def test_evidence_that_is_not_prose_is_left_alone(self):
        from tools.livefire import Finding

        f = Finding("c", "p", "d", {"labels": ["e3", "l7"], "shown": 60, "citable": 59})
        self.assertEqual(f.evidence, {"labels": ["e3", "l7"], "shown": 60, "citable": 59})

    def test_every_check_that_puts_prose_in_evidence_goes_through_Finding(self):
        """PLANTED AGAINST A BYPASS. A check that builds its record dict by hand would skip the
        constructor entirely, which is the only way this protection can be lost."""
        src = (Path(__file__).resolve().parents[1] / "tools" / "livefire.py").read_text()
        self.assertNotIn('"check":', src.split("def as_record")[0],
                         "a finding record was built without going through Finding()")


class AnEscapedArrowLineIsNotAnUncitedSentence(unittest.TestCase):
    """The check the auditor's first report earned, at the shapes it found by execution."""

    def _uncited(self, sentence):
        run = json.loads(json.dumps(TheBatteryDoesNotFireOnAHEALTHYRun.HEALTHY))
        run["faithful"] = {"ok": False, "checked": 1, "cited": 0, "asserted_absent": 0,
                           "citable": 2,
                           "violations": [{"kind": "uncited", "numbers": [],
                                           "sentence": sentence, "warrant": ""}]}
        return {f.check for f in audit("planted", run)}

    def test_every_decoration_the_auditor_found_is_caught(self):
        for shape in ("- [e3] -relates-> [l7]", "* [e3] -relates-> [l7]",
                      "1. [e3] -relates-> [l7]", "[e3] --relates--> [l7]",
                      "e3 -relates-> l7"):
            with self.subTest(shape=shape):
                self.assertIn("uncited-sentences-are-not-escaped-arrow-lines",
                              self._uncited(shape))

    def test_real_unsupported_prose_is_NOT_reported_as_an_arrow(self):
        """The other direction. An uncited sentence that is genuinely a claim resting on
        nothing is the checker working, and must not be excused as a stray arrow."""
        self.assertNotIn("uncited-sentences-are-not-escaped-arrow-lines",
                         self._uncited("The work establishes positivity everywhere."))

    def test_an_arrow_INSIDE_a_sentence_leaves_the_sentence_alone(self):
        self.assertNotIn(
            "uncited-sentences-are-not-escaped-arrow-lines",
            self._uncited("This refines that, [e3] -refines-> [l7], as the field records."))


class TheProbeSetIsTheONeTheOrderNamed(unittest.TestCase):
    def test_the_six_frozen_prompts_the_fixture_and_the_dialogue_era_probes(self):
        names = [n for n, _t, _w in probes()]
        self.assertEqual(len([n for n in names if n.startswith("battery-")]), 3)
        self.assertEqual(len([n for n in names if n.startswith("operator-")]), 3)
        self.assertIn("fixture-certified-positivity", names)
        for probe in ("residual-rich", "residual-free", "thin-material"):
            self.assertIn(probe, names)
        self.assertEqual(len(names), len(set(names)), "two probes share a name")

    def test_every_probe_states_WHY_it_is_in_the_battery(self):
        for name, text, why in probes():
            with self.subTest(probe=name):
                self.assertTrue(text.strip(), f"{name} has no question")
                self.assertTrue(why.strip(), f"{name} does not say why it is here")

    def test_every_check_is_reachable_from_the_registry(self):
        """A check defined and not registered runs on nothing."""
        self.assertEqual(len(CHECKS), 12)
        self.assertEqual(len(CHECKS), len({c.__name__ for c in CHECKS}))

    def test_a_degenerate_attachment_is_caught_at_BOTH_poles(self):
        """Column F's degeneracy, planted at both ends. 59 of 59 read as the cross-chart
        boundary finally falling; it was 19 of 19 lean because EVERYTHING was 59 of 59."""
        from tools.livefire import check_discrimination_is_in_the_sane_band as chk

        def run(attached, shown):
            return {"compiled": {"attachment": {"discrimination": {
                "attached": attached, "shown": shown, "fraction": attached / shown,
                "red": attached / shown >= 0.9}}}}

        self.assertTrue(chk("planted", run(59, 59)), "fraction 1.0 passed as a crossing")
        self.assertTrue(chk("planted", run(0, 59)), "a field that did not respond passed")
        self.assertEqual(chk("planted", run(34, 59)), [], "the baseline's own figure convicted")

    def test_a_THIN_region_is_not_a_degeneracy(self):
        """Attaching to all of a five-object field is a small field, not a machine that stopped
        discriminating. Without this the check fires on every narrow question."""
        from tools.livefire import check_discrimination_is_in_the_sane_band as chk

        self.assertEqual(chk("planted", {"compiled": {"attachment": {"discrimination": {
            "attached": 5, "shown": 5, "fraction": 1.0, "red": True}}}}), [])

    def test_a_violation_that_lost_its_KIND_is_caught(self):
        """A count without its composition is not a measurement — 60 with a composition is an
        understood state, and 60 bare is a number nobody can read."""
        from tools.livefire import check_a_violation_count_carries_its_composition as chk

        self.assertTrue(chk("planted", {"faithful": {"violations": [{"sentence": "x"}]}}))
        self.assertEqual(chk("planted", {"faithful": {"violations": [{"kind": "welded"}]}}), [])

    def test_a_measurement_without_its_ARROW_COUNT_is_caught(self):
        """The read view is pickle PLUS journal arrows, and the journal is deployment-local.
        Measured: 0 arrows locally against 19,385 served over an identical 80,566-slot base,
        turn 1's system prompt byte-identical and its user body 6,921 chars against 42,235."""
        from tools.livefire import check_a_fraction_carries_its_ARROW_COUNT as chk

        self.assertTrue(chk("planted", {"corpus_header": {"slots": 80566}}),
                        "a measurement with no arrow count passed as comparable")
        self.assertEqual(chk("planted", {"corpus_header": {"slots": 80566, "arrows": 0}}), [],
                         "zero arrows is a FACT about the read view, not a missing one")

    def test_the_baseline_is_declared_in_SEED_not_in_the_tool(self):
        """A baseline a tool could edit is not one."""
        from tools.livefire import BASELINE_PATH, baseline

        self.assertEqual(BASELINE_PATH.parent.name, "seed")
        b = baseline()
        self.assertEqual(b.get("build"), "b484b945d8af")
        self.assertEqual(b["fixture"]["composition"],
                         {"welded": 31, "uncontested": 28, "unresolved": 1})
        self.assertLess(b["bands"]["discrimination_low"], b["fixture"]["discrimination"])
        self.assertGreater(b["bands"]["discrimination_high"], b["fixture"]["discrimination"])

    def test_shown_labels_unions_both_sheets_and_EXCLUDES_the_question(self):
        """[b0] is shown and is deliberately not citable: an answer resting on the question
        rests on nothing, so a conviction for citing it is the referee working."""
        run = TheBatteryDoesNotFireOnAHEALTHYRun.HEALTHY
        self.assertEqual(shown_labels(run), {"e3", "l7"})

    def test_identical_findings_fold_and_keep_their_count(self):
        """One finding seen N times is one finding. A report that lists twenty-seven copies of
        the same licence gap buries the other four classes."""
        run = json.loads(json.dumps(TheBatteryDoesNotFireOnAHEALTHYRun.HEALTHY))
        run["faithful"]["violations"] = [
            {"kind": "welded", "numbers": ["e3", "l7"], "sentence": f"x{i} [e3][l7].",
             "warrant": ""} for i in range(4)]
        run["transcript"] = [{"system": "no escape here", "user": "U", "reply": "R",
                              "system_sha": "", "user_sha": "", "reply_sha": ""}]
        found = [f for f in audit("planted", run)
                 if f.check == "a-red-verdict-names-a-compliable-rule"]
        self.assertEqual(len(found), 1, "identical findings were not folded")
        self.assertEqual(found[0].seen, 4, "the fold lost the count")


if __name__ == "__main__":
    unittest.main()
