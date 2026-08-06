"""THE MEDIUM CHART: its firewall, its behavioural gate, and its planted defects.

A gloss is the one kind of claim in this system that is about the INTERFACE rather than about
the world. That makes it useful and makes it dangerous in a specific way: a translation note
promoted into the slow corpus would be knowledge conferred on how a model happens to read a
word. Two doors stay shut, and both are planted here.
"""

import unittest

from engine.medium import (CONTENT_CHARTS, FAILED, GLOSS_KIND, LEAD, MEDIUM_CHART, METRICS,
                           PROPOSED, VALIDATED, Gloss, Term, admits_to_content,
                           firewall_violations, glossary_block, gloss_prompt,
                           is_interface_claim, terms_from, validate)


def _term(charts=("english", "lean"), n=3):
    return Term(fiber_id="f1", charts=tuple(charts), members=tuple(f"s{i}" for i in range(n)),
                claims=tuple(f"the floor is the level nothing settles below {i}"
                             for i in range(n)))


def _gloss(model="google/gemini-2.5-flash", status=VALIDATED):
    return Gloss(term=_term(), text="a lower bound on residual disagreement",
                 model=model, status=status)


class TheChartIsRegisteredLikeAnyOther(unittest.TestCase):

    def test_medium_is_a_declared_chart(self):
        from engine.charts import chart_names, chart_spec
        self.assertIn("medium", chart_names())
        self.assertEqual("med", chart_spec("medium").tag_id)

    def test_it_reuses_the_prose_behavior_rather_than_minting_one(self):
        from engine.charts import chart_spec
        self.assertEqual("prose", chart_spec("medium").behavior)

    def test_a_gloss_arrow_is_same_claim(self):
        # Not `refines` (a gloss adds no precision) and not `instance_of` (a sense is not an
        # instance). The kind is the claim that this term MEANS this concept.
        self.assertEqual("same_claim", GLOSS_KIND)


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

    def test_the_defining_claims_travel_verbatim(self):
        t = _term()
        prompt = gloss_prompt(t)
        for claim in t.claims:
            self.assertIn(claim, prompt)

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


class TheGlossaryBlockEmitsOnlyWhatItMay(unittest.TestCase):

    def _emit(self, glosses, serving):
        from engine.inbound import Citable
        cites = []
        return glossary_block(glosses, serving, set(), cites, Citable), cites

    def test_only_validated_glosses_are_emitted(self):
        lines, cites = self._emit([_gloss(status=PROPOSED), _gloss(status=FAILED)], "m")
        self.assertEqual([], lines)
        self.assertEqual([], cites)

    def test_a_validated_gloss_is_citable_like_everything_else(self):
        lines, cites = self._emit([_gloss()], "google/gemini-2.5-flash")
        self.assertEqual(1, len(cites))
        self.assertEqual("gloss", cites[0].kind)
        self.assertEqual(MEDIUM_CHART, cites[0].chart)

    def test_a_cross_medium_gloss_is_emitted_MARKED_not_dropped_and_not_promoted(self):
        lines, _ = self._emit([_gloss()], "anthropic/claude-opus-4")
        body = "\n".join(lines)
        self.assertIn("LEAD", body)
        self.assertIn("validated on google/gemini-2.5-flash", body)

    def test_an_unknown_serving_medium_demotes_rather_than_promotes(self):
        lines, _ = self._emit([_gloss()], "")
        self.assertIn("LEAD", "\n".join(lines))

    def test_the_block_says_a_gloss_is_about_the_interface_not_the_world(self):
        lines, _ = self._emit([_gloss()], "google/gemini-2.5-flash")
        self.assertIn("never about truth", "\n".join(lines))


class TheExportCarriesTheGlossary(unittest.TestCase):

    def test_a_gloss_citation_renders_in_the_sheet(self):
        from engine.export_sheet import sheet
        text = sheet({"typed": "q", "relaxation": {}, "attachment": {},
                      "citations": [{"n": 1, "kind": "gloss", "chart": MEDIUM_CHART,
                                     "slot": "f1", "nu": "a lower bound on disagreement"}]})
        self.assertIn("GLOSSARY", text)
        self.assertIn("a lower bound on disagreement", text)
        self.assertIn("never as claims themselves", text)

    def test_a_sheet_with_no_glosses_carries_no_glossary_heading(self):
        from engine.export_sheet import sheet
        self.assertNotIn("GLOSSARY", sheet({"typed": "q", "relaxation": {},
                                            "attachment": {}, "citations": []}))


if __name__ == "__main__":
    unittest.main()
