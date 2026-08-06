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
        self.assertEqual(1, body.count("ONE PROPOSITION carried across"))
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


class GroupsAreFIBERSNotClusters(unittest.TestCase):
    """CONTROL 1. A grouping that produced the same groups by similarity would be a different
    mechanism wearing this one's output — identical on a demo, banned underneath."""

    def _snap(self):
        return TheDECOMPOSITIONIsThePRESENTATION._Snap()

    def test_group_membership_is_byte_identical_to_the_fiber_registry(self):
        from engine.inbound import _fiber_index
        snap = self._snap()
        idx = _fiber_index(snap)
        for fib in snap.fibers:
            for slot in fib:
                self.assertEqual(tuple(fib), idx[slot])

    def test_a_slot_in_no_fiber_maps_to_nothing_rather_than_being_placed(self):
        from engine.inbound import _fiber_index
        self.assertNotIn("x", _fiber_index(self._snap()))

    def test_the_compile_module_holds_no_similarity_machinery(self):
        """AST NAMES AND IMPORTS, never the source prose.

        A substring scan over the file convicts the module's own docstring for SAYING it does
        not cluster — the use-versus-mention trap, which has now caught three controls in this
        repository. What is checked is what the code REFERS TO.
        """
        import ast
        from pathlib import Path
        tree = ast.parse((Path(__file__).resolve().parent.parent / "engine"
                          / "inbound.py").read_text())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef,
                                                                   ast.AsyncFunctionDef))}
        mods = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                mods |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods.add(n.module.split(".")[0])
        for banned in ("difflib", "sklearn", "numpy", "scipy"):
            self.assertNotIn(banned, mods, f"similarity machinery imported: {banned!r}")
        for banned in ("SequenceMatcher", "jaccard", "cosine", "embedding", "similarity",
                       "ratio", "distance"):
            self.assertNotIn(banned, names, f"similarity machinery referenced: {banned!r}")

    def test_the_compile_module_is_swept_as_a_referee(self):
        from engine.referee_sweep import REFEREES, sweep_module, ENGINE
        self.assertIn("inbound.py", REFEREES)
        self.assertEqual([], sweep_module(ENGINE / "inbound.py"))


class HeadersAreREADNotComputed(unittest.TestCase):
    """CONTROL 2. A generated header would be medium-written prose in the operator's voice,
    sitting above the operator's own verbatim claims — where it is least visible."""

    def _block(self):
        return TheDECOMPOSITIONIsThePRESENTATION()._block()

    def test_the_header_names_the_fiber_by_its_id(self):
        self.assertIn("== FIBER ", self._block())

    def test_the_header_states_counts_and_charts_and_nothing_else(self):
        body = self._block()
        self.assertIn("ONE PROPOSITION carried across 2 claim(s) [english+lean]", body)

    def test_no_summarisation_call_exists_on_the_compile_path(self):
        """AST again. The header may be built from counts; it may not be WRITTEN by anything."""
        import ast
        from pathlib import Path
        tree = ast.parse((Path(__file__).resolve().parent.parent / "engine"
                          / "inbound.py").read_text())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
        for banned in ("summarise", "summarize", "describe_group", "headline",
                       "SUMMARY_SYSTEM", "GROUP_SYSTEM"):
            self.assertNotIn(banned, names, f"a generated header is back: {banned!r}")
        # And the ONE transport the compile may use is the region call, before settlement.
        self.assertNotIn("label_fiber", names,
                         "the compile must read a CACHED label, never request one")

    def test_group_headers_are_not_citable(self):
        from engine.inbound import _relaxed_block
        cls = TheDECOMPOSITIONIsThePRESENTATION
        rel = cls._Rel([cls._Moved("a", "english", "the term itself"),
                        cls._Moved("b", "lean", "the term in lean")])
        cites = []
        _relaxed_block(rel, cls._Snap(), cites)
        self.assertEqual({"moved"}, {c.kind for c in cites})
        self.assertEqual(2, len(cites), "one citable per MEMBER, none for the header")


class OrderCarriesNoSignal(unittest.TestCase):
    """CONTROL 3. Position is attention-salient and must not encode an undeclared ranking."""

    def _lines(self, salt):
        from engine.inbound import _relaxed_block
        cls = TheDECOMPOSITIONIsThePRESENTATION
        moved = [cls._Moved(f"s{i}", "english", f"claim {i}") for i in range(6)]
        return _relaxed_block(cls._Rel(moved), cls._Snap(), [], salt)[0]

    def test_two_sheets_of_the_same_region_differ_in_order(self):
        a, b = self._lines("saltone"), self._lines("salttwo")
        self.assertNotEqual(a, b, "the order is systematic — position is ranking something")

    def test_the_content_is_identical_across_orders(self):
        a, b = self._lines("saltone"), self._lines("salttwo")
        self.assertEqual(sorted(a), sorted(b))

    def test_the_same_salt_reproduces_the_same_sheet(self):
        # An unrecorded random order would make a sheet unreproducible; the salt is on the
        # record for exactly this.
        self.assertEqual(self._lines("fixed"), self._lines("fixed"))

    def test_the_salt_travels_on_the_compiled_record(self):
        import inspect

        from engine.inbound import CompiledInput
        self.assertIn("order_salt", inspect.getsource(CompiledInput))

    def test_order_is_not_alphabetical_or_by_size(self):
        from engine.inbound import _sheet_order
        keys = [f"s{i}" for i in range(12)]
        got = _sheet_order(keys, "some-salt")
        self.assertNotEqual(keys, got)
        self.assertNotEqual(sorted(keys), got)


class LabelsNeverSpeakContent(unittest.TestCase):
    """CONTROL 4. The label is garnish; the grouping is the mechanism."""

    def test_a_label_is_never_citable(self):
        from engine.inbound import _relaxed_block
        import engine.medium as m
        cls = TheDECOMPOSITIONIsThePRESENTATION
        m._LOADED, m._LABELS = True, {"a": Gloss(term=_term(), label="a concept",
                                                 model="", status=VALIDATED)}
        cites = []
        _relaxed_block(cls._Rel([cls._Moved("a", "english", "x")]), cls._Snap(), cites)
        self.assertTrue(all(c.kind != "gloss" for c in cites))

    def test_an_absent_label_changes_nothing_but_the_missing_line(self):
        import engine.medium as m
        cls = TheDECOMPOSITIONIsThePRESENTATION
        m._LOADED, m._LABELS = True, {}
        without = cls()._block()
        m._LABELS = {"a": Gloss(term=_term(), label="a concept", model="", status=VALIDATED)}
        with_ = cls()._block()
        m._LOADED, m._LABELS = True, {}
        self.assertEqual(len(without.splitlines()), len(with_.splitlines()))

    def test_a_label_in_content_settlement_or_K_is_RED(self):
        self.assertEqual(2, len(firewall_violations(settled_charts=[MEDIUM_CHART],
                                                    k_candidates=[{"chart": MEDIUM_CHART}])))


class TheEnergyPathIsUntouched(unittest.TestCase):
    """CONTROL 5. Grouping is a view over results, never an input to them."""

    def test_grouping_does_not_alter_the_moved_records(self):
        from engine.inbound import _relaxed_block
        cls = TheDECOMPOSITIONIsThePRESENTATION
        moved = [cls._Moved("a", "english", "x"), cls._Moved("b", "lean", "y")]
        before = [(m.slot, m.shift, m.hops) for m in moved]
        _relaxed_block(cls._Rel(moved), cls._Snap(), [], "s1")
        _relaxed_block(cls._Rel(moved), cls._Snap(), [], "s2")
        self.assertEqual(before, [(m.slot, m.shift, m.hops) for m in moved])

    def test_the_facts_are_identical_whatever_the_order(self):
        from engine.inbound import _relaxed_block
        cls = TheDECOMPOSITIONIsThePRESENTATION
        moved = [cls._Moved(f"s{i}", "english", f"c{i}") for i in range(5)]
        f1 = _relaxed_block(cls._Rel(moved), cls._Snap(), [], "a")[1]
        f2 = _relaxed_block(cls._Rel(moved), cls._Snap(), [], "b")[1]
        self.assertEqual(sorted(map(str, f1)), sorted(map(str, f2)))


class EveryGroupProducesItsArrows(unittest.TestCase):
    """CONTROL 7. A group that cannot produce its arrows is a group nobody can audit."""

    def test_a_fiber_group_lists_the_arrows_that_constitute_it(self):
        from engine.inbound import group_provenance
        cls = TheDECOMPOSITIONIsThePRESENTATION
        rel = cls._Rel([cls._Moved("a", "english", "x"), cls._Moved("b", "lean", "y")])
        prov = group_provenance(rel, cls._Snap())
        self.assertEqual(1, len(prov))
        self.assertFalse(prov[0]["singleton"])
        self.assertTrue(prov[0]["arrows"], "a fiber group produced no constituting arrow")

    def test_a_singleton_says_it_is_one_rather_than_producing_no_arrows_silently(self):
        from engine.inbound import group_provenance
        cls = TheDECOMPOSITIONIsThePRESENTATION
        prov = group_provenance(cls._Rel([cls._Moved("z", "english", "x")]), cls._Snap())
        self.assertTrue(prov[0]["singleton"])
        self.assertEqual([], prov[0]["arrows"])
