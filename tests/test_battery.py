"""THE INTERACTION LAW, as CI. Four properties that were prose, and drifted three times.

The perturbation path has fallen to a lookup shape three separate times, and each time the
thing that was supposed to prevent it was a paragraph. A paragraph does not run. These are the
same four properties, executable, gated on every build the daemon deploys.

WHAT IS HERMETIC HERE AND WHAT IS NOT, stated plainly because a control that overstates its
reach is worse than none. Three of the four properties are pure mechanism and are fully gated
below: no-silent-zero, statefulness, one-code-path. The fourth, GRADED, is a joint property of
the medium and the mechanism — the medium decides that a bare topic can only `bears_on`, and
the mechanism's job is to carry that distinction through to the compiled input without
flattening it. So the stub medium here supplies the grade by input shape, and what is gated is
that the mechanism PRESERVES it. The live ordering is measured by `engine.battery.run_live`
against the real corpus and the real model, which is what a deployed build runs.

The stub is deliberately crude — it decides by the shape of the boundary condition's own text
and knows nothing about the corpus. It is not a model of the medium and is not pretending to
be one; it is a fixed grader, so that a change in the MECHANISM is the only thing that can
change the verdict.
"""

from __future__ import annotations

import unittest

from engine import battery
from engine.battery import GREEN, RED
from engine.corpus_state import CorpusSnapshot, SlotRecord
from engine.correspondence import Correspondence
from engine.types import WarrantTier


def _corpus(n: int = 24) -> CorpusSnapshot:
    """A corpus with cross-chart arrows and several provenance directories."""
    from engine.normalize import address

    charts = ("english", "python", "lean", "go")
    slots, arrows, ids = {}, [], []
    for i in range(n):
        chart = charts[i % len(charts)]
        sid, nu = address(chart, f"claim {i} concerning the cloud decoder and the cone", "assert")
        slots[sid] = SlotRecord(slot=sid, chart=chart, type="assert", nu=nu, value="true",
                                confidence=1.0, tier="EXTRACTION",
                                docs=(f"repo||dir{i // 8}/file{i // 4}.md",))
        ids.append((sid, chart))
    for i in range(0, n - 1, 2):
        arrows.append(Correspondence(
            src_chart=ids[i][1], src_slot=ids[i][0], dst_chart=ids[i + 1][1],
            dst_slot=ids[i + 1][0], kind="same_claim", tier=WarrantTier.EXTRACTION,
            proposer="lm", prompt_hash="t", evidence=("seed",)))
    return CorpusSnapshot(slots=slots, arrows=tuple(arrows)), ids


def _spec() -> dict:
    """The battery's shape with fixture wording. The PINNED wording lives in seed/BATTERY.json
    and is exercised by `run_live`; a hermetic corpus cannot hold the operator's real claims."""
    return {
        "inputs": [
            {"id": "sharp", "text": "claim 0 concerning the cloud decoder and the cone"},
            {"id": "question", "text": "how do the cloud decoder and the cone relate"},
            {"id": "vague", "text": "common structure across the lean work"},
        ],
        "paraphrase_pair": {
            "a": "how do the cloud decoder and the cone relate",
            "b": "how does the cloud decoder relate to the cone",
        },
    }


def _grader(flatten: str = ""):
    """A fixed medium. It grades by the boundary condition's SHAPE and nothing else.

    `flatten` plants a regression: 'kind' makes it attach the SAME BREADTH to everything (the
    mechanism must then report a flattened grade rather than inventing one), 'silent' makes it
    name nothing at all.

    THE PLANT MOVED WITH THE LAW. It used to flatten the KIND — `bears_on` for every input
    where a claim would otherwise get `same_claim` — and that plant died the moment the bias
    began admitting only `bears_on`: the degenerate medium became indistinguishable from the
    healthy one, and the control would have passed forever without testing anything. What the
    grade is measured by is TIGHTNESS, so that is what the plant now flattens.
    """
    def t(system: str, user: str):
        lines = user.splitlines()
        bias = next((l for l in lines if l.startswith("[b0]")), "")
        n = sum(1 for l in lines if l.startswith("[") and "|" in l)
        if flatten == "silent":
            return "", {"cost": 0.0}
        # Labels are chart-tagged now; the stub answers in the same vocabulary the renderer
        # emits, which is the point of the change — an untagged answer still parses, but a
        # fixture that pretends the old format is the only one tests the compatibility path
        # instead of the live one.
        labels = [l[1:l.index("]")] for l in lines if l.startswith("[") and "]" in l]
        b = labels[0] if labels else "b0"
        rest = labels[1:]
        if flatten == "kind":
            return "\n".join(f"{b} -bears_on-> {x}" for x in rest[:8]), {"cost": 0.0}
        if "claim 0 concerning" in bias:
            # BEARS_ON, NOT SAME_CLAIM, and that is the ruling rather than a fixture tweak: the
            # bias admits only `bears_on`, unconditionally. The alternative — the three kinds
            # apply "if the bias really is a claim" — requires deciding whether an utterance
            # asserts, which is a reading of prose and is the one judgement resolve-or-void
            # forbids. The property under test here is attachment TIGHTNESS, one point against
            # eight, and the kind was never what carried it.
            #
            return f"{b} -bears_on-> {rest[0]}", {"cost": 0.0}   # a claim: tight, one point
        if "how do" in bias or "how does" in bias:
            return "\n".join(f"{b} -bears_on-> {x}" for x in rest[:3]), {"cost": 0.0}
        return "\n".join(f"{b} -bears_on-> {x}" for x in rest[:8]), {"cost": 0.0}

    return t


def _extra_arrow(ids) -> Correspondence:
    """One more arrow, landed between the two state reads."""
    return Correspondence(
        src_chart=ids[0][1], src_slot=ids[0][0], dst_chart=ids[3][1], dst_slot=ids[3][0],
        kind="refines", tier=WarrantTier.EXTRACTION, proposer="lm", prompt_hash="t",
        evidence=("landed between the reads",))


class TheBatteryIsGreenOnThisBuild(unittest.TestCase):
    """The gate itself. If this goes red the perturbation path does not deploy."""

    def test_all_four_properties_hold(self):
        snap, ids = _corpus()
        r = battery.run(snap, _grader(), battery=_spec(), extra_arrow=_extra_arrow(ids))
        self.assertEqual(r.verdict, GREEN,
                         "\n".join(f"{k}: {v} — {r.reasons[k]}"
                                   for k, v in r.properties.items() if v == RED))

    def test_every_property_is_actually_evaluated(self):
        """A battery that skips a property and reports GREEN is worse than a red one."""
        snap, ids = _corpus()
        r = battery.run(snap, _grader(), battery=_spec(), extra_arrow=_extra_arrow(ids))
        self.assertEqual(set(r.properties), {"no_silent_zero", "graded", "no_cliff",
                                             "stateful", "one_code_path"})
        for k, why in r.reasons.items():
            self.assertTrue(why.strip(), f"{k} gave a verdict with no reason")


class NoSilentZero(unittest.TestCase):
    def test_planted_a_medium_that_names_nothing_still_leaves_a_trace(self):
        snap, _ = _corpus()
        r = battery.run(snap, _grader("silent"), battery=_spec())
        self.assertEqual(r.properties["no_silent_zero"], GREEN,
                         "a decline must be distinguishable from a filter")
        for reading in r.readings:
            self.assertTrue(reading.consulted, f"{reading.id} was never put to the medium")
            self.assertTrue(reading.trace["seated"], f"{reading.id} seated no objects")
            self.assertIn("question", reading.trace)

    def test_planted_an_input_that_never_reached_the_medium_is_red(self):
        snap, _ = _corpus()

        def gated(system, user):
            raise AssertionError("must not be called")

        readings = [battery.Reading(id="sharp", text="x", consulted=False, conditioned=False)]
        verdict, why = battery.check_no_silent_zero(readings)
        self.assertEqual(verdict, RED)
        self.assertIn("never called", why)

    def test_the_trace_names_the_question_and_the_seating(self):
        snap, _ = _corpus()
        reading = battery.read_one("holonomy", "vague", snap, _grader("silent"))
        self.assertIn("complete the diagram", reading.trace["question"])
        self.assertGreater(reading.trace["corpus_objects"], 0)
        self.assertEqual(reading.trace["attached"], 0)


class GradedResponse(unittest.TestCase):
    def test_the_mechanism_carries_the_grade_it_is_given(self):
        """SUPERSEDED PROPERTY, recorded rather than deleted.

        This asserted `by["sharp"].corresponds > 0` — "a claim must be able to correspond" —
        and that property is GONE by ruling: the bias admits only `bears_on`, unconditionally.
        The old law required deciding whether an utterance really asserts before choosing which
        kinds may touch it, and that decision is a reading of prose, which is the one judgement
        resolve-or-void exists to refuse. Measured on a served transcript before the ruling:
        turn 1 wrote `e3 -same_claim-> b0` and `e7 -refines-> b0`, and the window reported two
        CORRESPONDENCE attachments for a question.

        WHAT THE GRADE IS NOW MEASURED BY is unchanged and was never the kind: TIGHTNESS. A
        sharp claim attaches to one point, a bare topic attaches diffusely, and the distance
        between them is the graded property. `corresponds` is now zero for every input, which
        is the law rather than a flattened medium — so the flattening control below tests the
        distinction that still exists.
        """
        snap, _ = _corpus()
        r = battery.run(snap, _grader(), battery=_spec())
        by = {x.id: x for x in r.readings}
        self.assertEqual(by["sharp"].corresponds, 0,
                         "the bias admits only bears_on; nothing may correspond to it")
        self.assertEqual(by["vague"].corresponds, 0, "a topic asserts nothing")
        self.assertGreater(by["vague"].bears_on, by["sharp"].bears_on,
                           "a bare topic must attach more diffusely than a sharp claim")
        self.assertGreater(by["vague"].bears_on, by["question"].bears_on,
                           "a bare topic must attach more diffusely than a targeted question")
        self.assertEqual(r.properties["graded"], GREEN, r.reasons["graded"])

    def test_planted_a_flattened_grade_is_reported_not_invented(self):
        """If the medium answers one kind for everything, the battery must say so — the
        mechanism must not manufacture a distinction the medium did not draw."""
        snap, _ = _corpus()
        r = battery.run(snap, _grader("kind"), battery=_spec())
        by = {x.id: x for x in r.readings}
        self.assertEqual(by["sharp"].corresponds, 0,
                         "the mechanism invented a correspondence the medium did not name")
        # THE FLATTENING ITSELF, which is what this test is for. A medium that reaches for the
        # same breadth on a sharp claim and on a bare topic has drawn no distinction, and the
        # battery must report that rather than manufacture one. The counts differ by at most
        # one because two regions are not the same sixty objects — what must not survive is the
        # ORDERING the healthy fixture produces, where vague attaches to eight and sharp to one.
        self.assertLessEqual(abs(by["sharp"].bears_on - by["vague"].bears_on), 1,
                             "the fixture must actually be flattened for this to test anything")
        self.assertGreater(by["sharp"].bears_on, 1,
                           "the sharp reading kept its tight attachment; nothing was flattened")

    def test_planted_identical_shapes_across_all_three_is_red(self):
        rs = [battery.Reading(id=i, text=i, consulted=True, attached=3, bears_on=3)
              for i in ("sharp", "question", "vague")]
        verdict, why = battery.check_graded(rs)
        self.assertEqual(verdict, RED)
        self.assertIn("same attachment shape", why)

    def test_planted_an_inverted_grade_is_red(self):
        rs = [battery.Reading(id="sharp", text="s", consulted=True, attached=1, bears_on=1),
              battery.Reading(id="question", text="q", consulted=True, attached=2, bears_on=2),
              battery.Reading(id="vague", text="v", consulted=True, attached=3, corresponds=3)]
        verdict, why = battery.check_graded(rs)
        self.assertEqual(verdict, RED)
        self.assertIn("inverted", why)


class NoCliff(unittest.TestCase):
    def test_two_phrasings_of_one_question_both_reach_the_field(self):
        snap, _ = _corpus()
        r = battery.run(snap, _grader(), battery=_spec())
        a = next(x for x in r.readings if x.id == "paraphrase_a")
        b = next(x for x in r.readings if x.id == "paraphrase_b")
        self.assertTrue(a.consulted and b.consulted)
        self.assertEqual(r.properties["no_cliff"], GREEN, r.reasons["no_cliff"])

    def test_planted_full_response_versus_nothing_is_red(self):
        a = battery.Reading(id="paraphrase_a", text="a", consulted=True, conditioned=True)
        b = battery.Reading(id="paraphrase_b", text="b", consulted=True, conditioned=False)
        verdict, why = battery.check_no_cliff(a, b)
        self.assertEqual(verdict, RED)
        self.assertIn("cliff", why)

    def test_planted_one_phrasing_filtered_before_the_call_is_red(self):
        a = battery.Reading(id="paraphrase_a", text="a", consulted=True)
        b = battery.Reading(id="paraphrase_b", text="b", consulted=False)
        verdict, why = battery.check_no_cliff(a, b)
        self.assertEqual(verdict, RED)
        self.assertIn("exact is gating", why)


class Statefulness(unittest.TestCase):
    def test_an_arrow_landed_between_the_reads_changes_the_compilation(self):
        snap, ids = _corpus()
        r = battery.run(snap, _grader(), battery=_spec(), extra_arrow=_extra_arrow(ids))
        self.assertEqual(r.properties["stateful"], GREEN, r.reasons["stateful"])

    def test_planted_a_frozen_response_is_red(self):
        same = dict(consulted=True, conditioned=True, seated=10, moved=3, reached=1,
                    extracted=0, region_id="abc")
        verdict, why = battery.check_stateful(battery.Reading(id="a", text="x", **same),
                                              battery.Reading(id="b", text="x", **same))
        self.assertEqual(verdict, RED)
        self.assertIn("frozen", why)

    def test_planted_not_measuring_it_is_red_not_green(self):
        """An unmeasured property must never report as a passing one."""
        snap, _ = _corpus()
        r = battery.run(snap, _grader(), battery=_spec())      # no extra_arrow
        self.assertEqual(r.properties["stateful"], RED)
        self.assertIn("not measured", r.reasons["stateful"])


class OneCodePath(unittest.TestCase):
    def test_the_perturb_path_is_the_samplers(self):
        verdict, why = battery.check_one_code_path()
        self.assertEqual(verdict, GREEN, why)

    def test_planted_a_reintroduced_candidate_loop_is_red(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "ui").mkdir()
            (root / "engine" / "attach.py").write_text("# the loop, back", encoding="utf-8")
            (root / "engine" / "perturb.py").write_text("REGION_SYSTEM", encoding="utf-8")
            (root / "engine" / "inbound.py").write_text("", encoding="utf-8")
            (root / "ui" / "current.py").write_text("", encoding="utf-8")
            verdict, why = battery.check_one_code_path(root)
            self.assertEqual(verdict, RED)
            self.assertIn("candidate-list loop was reintroduced", why)

    def test_planted_a_perturb_path_with_its_own_prompt_is_red(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "ui").mkdir()
            (root / "engine" / "perturb.py").write_text(
                "MY_OWN_SYSTEM = 'ask about each candidate'", encoding="utf-8")
            (root / "engine" / "inbound.py").write_text("", encoding="utf-8")
            (root / "ui" / "current.py").write_text("", encoding="utf-8")
            verdict, why = battery.check_one_code_path(root)
            self.assertEqual(verdict, RED)
            self.assertIn("stopped sharing", why)


class TheCurveMeasuresTheDaemonsClaim(unittest.TestCase):
    """Do daemon-hours turn into perturbation richness? The series either shows it or it does not."""

    def _sample(self, at: str, snap, ids):
        r = battery.run(snap, _grader(), battery=_spec(), extra_arrow=_extra_arrow(ids))
        return battery.sample_from(r, snap, at)

    def test_a_point_carries_both_numbers_and_the_corpus_size(self):
        snap, ids = _corpus()
        s = self._sample("2026-08-05", snap, ids)
        self.assertEqual(set(s.attachments), {"sharp", "question", "vague"})
        self.assertEqual(s.attachments_total, sum(s.attachments.values()))
        self.assertEqual(s.attachments_total, s.bears_on_total + s.corresponds_total)
        self.assertGreater(s.corpus_slots, 0)
        self.assertEqual(s.corpus_arrows, len(snap.arrows))

    def test_planted_attachments_alone_cannot_be_read_as_daemon_progress(self):
        """The structural number must be recorded beside the outcome number, or a rise from a
        better model is indistinguishable from a rise from a richer corpus."""
        snap, ids = _corpus()
        s = self._sample("2026-08-05", snap, ids)
        self.assertIn("mean_arrow_density", s.as_record())
        self.assertGreater(s.mean_arrow_density, 0.0,
                           "a region with declared arrows must report nonzero density")

    def test_the_series_round_trips_through_the_walk_log(self):
        import tempfile
        from pathlib import Path

        snap, ids = _corpus()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "walk.jsonl"
            battery.log_sample(self._sample("2026-08-05", snap, ids), p)
            battery.log_sample(self._sample("2026-08-12", snap, ids), p)
            series = battery.curve(p)
            self.assertEqual([r["at"] for r in series], ["2026-08-05", "2026-08-12"])

    def test_planted_a_step_record_is_not_mistaken_for_a_curve_point(self):
        """The walk log holds both. Step records predate the `record` key entirely."""
        import json as _json
        import tempfile
        from pathlib import Path

        snap, ids = _corpus()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "walk.jsonl"
            p.write_text(_json.dumps({"n": 1, "kind": "residual", "clamp": "x"}) + "\n",
                         encoding="utf-8")
            battery.log_sample(self._sample("2026-08-05", snap, ids), p)
            self.assertEqual(len(battery.curve(p)), 1, "a step leaked into the curve")

    def test_t0_is_always_due_and_a_fresh_point_is_not(self):
        import tempfile
        from pathlib import Path

        snap, ids = _corpus()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "walk.jsonl"
            self.assertTrue(battery.due("2026-08-05", p), "an empty curve must record t0")
            battery.log_sample(self._sample("2026-08-05", snap, ids), p)
            self.assertFalse(battery.due("2026-08-06", p))
            self.assertFalse(battery.due("2026-08-11", p))
            self.assertTrue(battery.due("2026-08-12", p), "weekly means weekly")

    def test_planted_an_unparseable_last_point_does_not_silence_the_curve(self):
        """A corrupt tail must make the next sample DUE, not skip it forever."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "walk.jsonl"
            p.write_text('{"record": "battery", "at": "not-a-date"}\n', encoding="utf-8")
            self.assertTrue(battery.due("2026-08-05", p))


class TheBatterySpecIsPinned(unittest.TestCase):
    """Wording that drifts measures a different thing each run and detects no regression."""

    def test_the_three_shapes_and_the_pair_are_on_disk(self):
        spec = battery.load_battery()
        self.assertEqual([i["id"] for i in spec["inputs"]], ["sharp", "question", "vague"])
        self.assertIn("pinned", spec)
        for item in spec["inputs"]:
            self.assertTrue(item["text"].strip())
            self.assertTrue(item["expect"].strip(), "an input with no expectation tests nothing")
        pair = spec["paraphrase_pair"]
        self.assertNotEqual(pair["a"], pair["b"])

    def test_the_paraphrases_are_two_addresses_not_one(self):
        """If they normalize to one address the cliff test is vacuous — gate 1 already made
        them the same claim, and of course they behave identically."""
        from engine.normalize import address

        pair = battery.load_battery()["paraphrase_pair"]
        a, _ = address("english", pair["a"], "assert")
        b, _ = address("english", pair["b"], "assert")
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()


class ARateBelowMinimumNIsAReadingNotAFinding(unittest.TestCase):
    """Derived from the flips, not chosen.

    Every per-model rate stated in one session moved decisively when n grew tenfold:
    `same_claim` read 21% at n=24, 7.2% at n=2,872, 12.07% at n=23,992; repetition read 2.12
    at n=2,872 and 8.98 at n=23,992 — back to the value it was said to have improved on.
    Twice, in the same direction: a reading reported as a finding.
    """

    def test_the_minimum_is_ten_times_where_the_flips_happened(self):
        from engine.battery import MIN_RATE_N

        self.assertEqual(MIN_RATE_N, 10_000)

    def test_planted_a_small_sample_refuses_to_be_a_finding(self):
        from engine.battery import rate

        r = rate(207, 2872, "same_claim")
        self.assertFalse(r["stated"])
        self.assertEqual(r["standing"], "reading")
        self.assertIn("flipped when n grew tenfold", r["note"])

    def test_a_large_sample_is_a_finding(self):
        from engine.battery import rate

        r = rate(2895, 23992, "same_claim")
        self.assertTrue(r["stated"])
        self.assertEqual(r["standing"], "finding")
        self.assertEqual(r["note"], "")

    def test_the_n_always_travels_with_the_value(self):
        """Returning the number alone is how a reading becomes a finding: the value gets
        quoted and the sample size does not travel with it."""
        from engine.battery import rate

        for n in (0, 1, 24, 2872, 23992):
            self.assertIn("n", rate(1, n))
