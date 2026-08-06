"""THE MEDIUM CHART: its firewall, its behavioural gate, and its planted defects.

A gloss is the one kind of claim in this system that is about the INTERFACE rather than about
the world. That makes it useful and makes it dangerous in a specific way: a translation note
promoted into the slow corpus would be knowledge conferred on how a model happens to read a
word. Two doors stay shut, and both are planted here.
"""

import unittest

from engine.medium import (CONTENT_CHARTS, FAILED, LEAD, LEG_KINDS, MAX_LABEL_CHARS,
                           MEDIUM_CHART, METRICS, PROPOSED, VALIDATED, Gloss, Term,
                           admits_to_content, firewall_violations, is_interface_claim,
                           label_fiber, label_prompt, terms_from, validate)


def _term(charts=("english", "lean"), n=3):
    return Term(fiber_id="f1", charts=tuple(charts), members=tuple(f"s{i}" for i in range(n)),
                claims=tuple(f"the floor is the level nothing settles below {i}"
                             for i in range(n)))


def _gloss(model="google/gemini-2.5-flash", status=VALIDATED):
    return Gloss(term=_term(), label="convergence bound", model=model, status=status)


class TheChartIsRegisteredLikeAnyOther(unittest.TestCase):

    def test_medium_is_a_declared_chart(self):
        from engine.charts import chart_names, chart_spec
        self.assertIn("medium", chart_names())
        self.assertEqual("med", chart_spec("medium").tag_id)

    def test_it_reuses_the_prose_behavior_rather_than_minting_one(self):
        from engine.charts import chart_spec
        self.assertEqual("prose", chart_spec("medium").behavior)

    def test_same_claim_is_NOT_a_legal_leg_kind(self):
        # A `same_claim` leg asserts the term IS the concept, which collapses the span back to
        # the flat gloss this design replaced. Its absence is the correction, in the constant.
        self.assertNotIn("same_claim", LEG_KINDS)
        self.assertEqual(("refines", "instance_of", "bears_on"), LEG_KINDS)


class TheFirewallIsConstitutional(unittest.TestCase):

    def test_a_gloss_may_not_enter_content_settlement(self):
        v = firewall_violations(settled_charts=["english", MEDIUM_CHART])
        self.assertEqual(1, len(v))
        self.assertIn("CONTENT SETTLEMENT", v[0])

    def test_a_gloss_may_not_reach_Ks_candidate_set(self):
        v = firewall_violations(k_candidates=[{"chart": MEDIUM_CHART}])
        self.assertEqual(1, len(v))
        self.assertIn("K'S CANDIDATE SET", v[0])

    def test_both_doors_are_checked_in_one_call(self):
        # A caller that can check one door and forget the other is a firewall with a hole.
        self.assertEqual(2, len(firewall_violations(settled_charts=[MEDIUM_CHART],
                                                    k_candidates=[{"chart": MEDIUM_CHART}])))

    def test_ordinary_charts_pass_both_doors(self):
        self.assertEqual([], firewall_violations(
            settled_charts=list(CONTENT_CHARTS),
            k_candidates=[{"chart": c} for c in CONTENT_CHARTS]))

    def test_content_admission_is_a_POSITIVE_list(self):
        # A deny-list admits the next chart somebody forgets to add. The medium chart's
        # absence from CONTENT_CHARTS IS the firewall.
        self.assertNotIn(MEDIUM_CHART, CONTENT_CHARTS)
        self.assertFalse(admits_to_content(MEDIUM_CHART))
        self.assertFalse(admits_to_content("some_chart_invented_next_week"))

    def test_the_interface_predicate_is_exact_not_a_prefix_match(self):
        self.assertTrue(is_interface_claim(MEDIUM_CHART))
        self.assertFalse(is_interface_claim("medium_something"))

    def test_a_violation_is_REPORTED_not_silently_filtered(self):
        # A firewall that quietly drops what it should refuse is indistinguishable from a
        # firewall that is not running.
        self.assertTrue(firewall_violations(settled_charts=[MEDIUM_CHART])[0].strip())


class TermSelectionIsStructural(unittest.TestCase):
    """A term is a FIBER. No word counting, no frequency heuristic, no tokenizer."""

    class _Snap:
        slots = {f"s{i}": type("S", (), {"chart": ("english" if i % 2 else "lean"),
                                         "nu": f"claim {i}"})() for i in range(12)}
        fibers = [tuple(f"s{i}" for i in range(4)),          # 4 members, 2 charts
                  ("s5", "s7"),                              # a pair — an arrow, not a term
                  ("s8", "s9", "s10")]                       # 3 members

    def test_a_pair_is_an_arrow_not_a_term(self):
        got = terms_from(self._Snap())
        self.assertTrue(all(t.size >= 3 for t in got))
        self.assertEqual(2, len(got))

    def test_chart_span_ranks_above_member_count(self):
        # A proposition carried in four charts is more load-bearing than one carried by more
        # claims inside a single chart: the span is what makes it a TRANSLATION.
        class S:
            slots = {"a": type("S", (), {"chart": "english", "nu": "x"})(),
                     "b": type("S", (), {"chart": "lean", "nu": "y"})(),
                     "c": type("S", (), {"chart": "python", "nu": "z"})()}
            slots.update({f"m{i}": type("S", (), {"chart": "english", "nu": "q"})()
                          for i in range(9)})
            fibers = [("a", "b", "c"), tuple(f"m{i}" for i in range(9))]
        got = terms_from(S())
        self.assertEqual(3, len(got[0].charts), "the wider span must rank first")

    def test_the_defining_claims_travel_verbatim_into_the_label_prompt(self):
        t = _term()
        prompt = label_prompt(t)
        self.assertIn(t.claims[0], prompt)

    def test_the_module_holds_no_tokenizer(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "medium.py").read_text()
        for banned in ("[a-z0-9]+", "\\w+", ".casefold()", "Counter("):
            self.assertNotIn(banned, src, f"a frequency heuristic is back: {banned!r}")


class TheGateIsBehavioural(unittest.TestCase):
    """A gloss's warrant is its measured effect, never the medium's opinion of its own gloss."""

    def test_a_gloss_that_improves_discrimination_survives(self):
        g = validate(_gloss(status=PROPOSED), {"discrimination": 0.9, "citation": 0.7},
                     {"discrimination": 0.5, "citation": 0.7})
        self.assertEqual(VALIDATED, g.status)
        self.assertEqual(-0.4, g.deltas["discrimination"])

    def test_a_gloss_that_improves_citation_survives(self):
        g = validate(_gloss(status=PROPOSED), {"discrimination": 0.5, "citation": 0.7},
                     {"discrimination": 0.5, "citation": 0.9})
        self.assertEqual(VALIDATED, g.status)

    def test_a_PLANTED_NONSENSE_gloss_fails_and_decays(self):
        # No improvement anywhere: the gloss said something, and the medium behaved no better.
        g = validate(_gloss(status=PROPOSED), {"discrimination": 0.5, "citation": 0.8},
                     {"discrimination": 0.5, "citation": 0.8})
        self.assertEqual(FAILED, g.status)
        self.assertIn("no metric improved", g.note)

    def test_a_gloss_that_helps_one_metric_and_hurts_another_does_NOT_survive(self):
        # Not a gain with a cost — unvalidated. A translation that trades attachment quality
        # for citation compliance has aligned nothing.
        g = validate(_gloss(status=PROPOSED), {"discrimination": 0.9, "citation": 0.9},
                     {"discrimination": 0.5, "citation": 0.7})
        self.assertEqual(FAILED, g.status)

    def test_the_metrics_are_EXISTING_invariant_ones(self):
        # No new metric ships without its invariance asserted. Both of these have theirs
        # asserted where they live: discrimination dedupes by target slot, citation counts
        # sentences rather than words.
        self.assertEqual({"discrimination", "citation"}, set(METRICS))

    def test_the_verdict_states_the_deltas_that_produced_it(self):
        g = validate(_gloss(status=PROPOSED), {"discrimination": 0.9, "citation": 0.7},
                     {"discrimination": 0.5, "citation": 0.7})
        self.assertIn("discrimination", g.note)


class GlossesArePerMedium(unittest.TestCase):
    """The quarantine pattern, fourth application."""

    def test_validated_on_the_serving_medium_is_a_fact(self):
        self.assertEqual(VALIDATED, _gloss().for_medium("google/gemini-2.5-flash"))

    def test_validated_elsewhere_is_a_LEAD_not_a_fact(self):
        self.assertEqual(LEAD, _gloss().for_medium("anthropic/claude-opus-4"))

    def test_an_unvalidated_gloss_is_not_promoted_by_a_matching_medium(self):
        self.assertEqual(PROPOSED, _gloss(status=PROPOSED).for_medium("google/gemini-2.5-flash"))

    def test_a_record_with_no_status_reads_as_proposed_never_validated(self):
        # Same rule as the verdict eras and staleness: a tag that defaults forward launders
        # exactly what the tag exists to hold back.
        import json
        import tempfile
        from pathlib import Path

        from engine.medium import load_glosses
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "g.jsonl"
            p.write_text(json.dumps({"term": {"fiber_id": "f", "charts": ["english"]},
                                     "text": "x", "model": "m"}) + "\n")
            self.assertEqual(PROPOSED, load_glosses(str(p))[0].status)




class TheDECOMPOSITIONIsThePRESENTATION(unittest.TestCase):
    """The grouping IS the glossary. No stored spans, no generated legs, no call.

    The corpus's fiber structure was in the snapshot the whole time and was flattened away on
    the way into the prompt — `_relaxed_block` rendered a numbered list, and a medium shown a
    pile attaches to the pile. Grouping the compiled sheet by fiber, with the declared arrows
    leaving each group, is the span. Live structure, formatted honestly.
    """

    class _Snap:
        class _S:
            def __init__(self, chart, nu):
                self.chart, self.nu = chart, nu

        class _A:
            def __init__(self, kind, src, dst):
                self.kind, self.src_slot, self.dst_slot = kind, src, dst
                self.src_chart = self.dst_chart = "english"

        def __init__(self):
            self.slots = {"a": self._S("english", "the term itself"),
                          "b": self._S("lean", "the term in lean"),
                          "x": self._S("python", "an elaborating claim")}
            self.fibers = [("a", "b")]
            self.arrows = [self._A("refines", "a", "x"), self._A("same_claim", "a", "b")]

    class _Moved:
        def __init__(self, slot, chart, nu):
            self.slot, self.chart, self.nu = slot, chart, nu
            self.type, self.value, self.tier = "assert", "T", "EXTRACTION"
            self.contested, self.shift, self.hops = False, 0.4, 0
            self.weakest_tier, self.path = "EXTRACTION", []

        def as_record(self):
            return {"slot": self.slot, "nu": self.nu, "chart": self.chart}

    class _Rel:
        def __init__(self, moved):
            self.moved = moved
            self.moved_dropped = self.blocks_skipped = 0

    def _block(self):
        from engine.inbound import _relaxed_block
        snap = self._Snap()
        rel = self._Rel([self._Moved("a", "english", "the term itself"),
                         self._Moved("b", "lean", "the term in lean")])
        lines, _ = _relaxed_block(rel, snap, [])
        return "\n".join(lines)

    def test_members_of_one_fiber_land_in_ONE_group(self):
        body = self._block()
        self.assertEqual(1, body.count("== ONE PROPOSITION"))
        self.assertIn("2 claim(s)", body)

    def test_the_group_names_the_charts_it_spans(self):
        self.assertIn("[english+lean]", self._block())

    def test_the_declared_arrows_leaving_the_fiber_are_shown(self):
        body = self._block()
        self.assertIn("WHAT THIS PROPOSITION IS LINKED TO", body)
        self.assertIn("-refines->", body)
        self.assertIn("an elaborating claim", body)

    def test_a_same_claim_arrow_is_not_shown_as_a_link_out(self):
        # It is what makes the fiber the fiber; following one leads back inside the apex.
        self.assertNotIn("-same_claim->", self._block())

    def test_a_claim_in_no_fiber_is_its_own_group_and_says_so(self):
        from engine.inbound import _relaxed_block
        rel = self._Rel([self._Moved("z", "english", "an unfibered claim")])
        body = "\n".join(_relaxed_block(rel, self._Snap(), [])[0])
        self.assertIn("A CLAIM in no declared fiber", body)

    def test_the_block_states_that_a_group_is_the_unit_to_relate_to(self):
        # The presentation has to SAY what the grouping means, or a medium reads it as
        # decoration. Attaching to every member of one fiber is attaching once.
        self.assertIn("attaching once, not several times", self._block())

    def test_grouping_needs_no_stored_glossary_and_no_call(self):
        # If this ever needs a transport or a glossary file, the design has drifted back to
        # storing what the corpus already carries.
        self.assertTrue(self._block())


class TheLabelIsTheIrreducibleResidue(unittest.TestCase):
    """One optional cached line per fiber. The medium names an endpoint; it supplies nothing."""

    def test_a_concept_name_is_taken(self):
        g = label_fiber(_term(), lambda s, u: ("convergence bound", {}), "m")
        self.assertEqual("convergence bound", g.label)
        self.assertEqual(PROPOSED, g.status)

    def test_a_SENTENCE_is_VOID_rather_than_truncated(self):
        g = label_fiber(_term(), lambda s, u: ("x" * (MAX_LABEL_CHARS + 1), {}), "m")
        self.assertEqual(FAILED, g.status)
        self.assertIn("VOID rather than truncated", g.note)
        self.assertEqual("", g.label)

    def test_an_honest_decline_is_recorded_not_turned_into_an_empty_label(self):
        g = label_fiber(_term(), lambda s, u: ("NONE", {}), "m")
        self.assertEqual(FAILED, g.status)
        self.assertIn("declined", g.note)

    def test_a_dead_call_is_reported_never_silent(self):
        def boom(s, u):
            raise RuntimeError("no")
        self.assertIn("the label call failed", label_fiber(_term(), boom, "m").note)

    def test_an_unvalidated_label_is_not_shown(self):
        import engine.medium as m
        m._LOADED, m._LABELS = True, {"f1": Gloss(term=_term(), label="x", model="m",
                                                  status=PROPOSED)}
        self.assertEqual("", m.fiber_label("f1", "m"))

    def test_a_cross_medium_label_is_shown_MARKED_never_bare(self):
        import engine.medium as m
        m._LOADED, m._LABELS = True, {"f1": Gloss(term=_term(), label="x", model="other",
                                                  status=VALIDATED)}
        self.assertIn("LEAD", m.fiber_label("f1", "google/gemini-2.5-flash"))

    def test_an_absent_label_is_the_ordinary_case_not_a_failure(self):
        import engine.medium as m
        m._LOADED, m._LABELS = True, {}
        self.assertEqual("", m.fiber_label("nothing-cached", "m"))
