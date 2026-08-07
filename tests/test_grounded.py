"""THE REFEREE, AND THE CONTROL THAT KEEPS IT STRUCTURAL.

The answer moved to the top of the page. What makes that warranted is a gate that can convict
it — and the FIRST gate built for the job was term overlap, the move this codebase records as
deleted, reintroduced inside the referee where it does the most damage. So this file plants
both the ordinary REDs and the return of the lexical method itself.
"""

import ast
import unittest
from pathlib import Path

from engine.grounded import (MIN_SENTENCE_CHARS, WARRANTS, Verdict, check_answer,
                             citable_numbers, sentences, warrants_held)

MODULE = Path(__file__).resolve().parent.parent / "engine" / "grounded.py"


def _compiled(ns):
    return {"citations": [{"n": n, "kind": "moved", "chart": "english",
                           "slot": f"s{n}", "nu": f"claim {n}"} for n in ns]}


#: THE CITATION IS A LABEL, NOT AN INTEGER — since the region-numbering collapse.
#:
#: These assertions moved deliberately, and the distinction matters: a FIXTURE change is cheap
#: bookkeeping, while an ASSERTION change means the property itself moved. It did. `resolved`
#: and `unresolved[].numbers` now carry the label strings the medium actually wrote, because
#: the label space is the region's — `[e1]`, `[l45]` — and it survives end-to-end with no
#: renumbering step between what the medium said and what this checker verifies.
#:
#: THE ANTI-SIMILARITY PROPERTY IS UNCHANGED. It read "resolution is integer membership, no
#: text is compared"; it now reads "resolution is EXACT MEMBERSHIP IN A DECLARED LABEL SET".
#: Same property — in the set or not, no partial match, no nearest neighbour, no distance — and
#: integers were never the safer case: `engine/region._ARROW_RE` records a real defect where
#: `1.0 -same_claim-> 2` matched the `1` out of `1.0`.

class CitationsResolveOrTheyDoNot(unittest.TestCase):

    def test_a_fully_cited_answer_is_green(self):
        v = check_answer("I read your question as bearing on the metric cone [1]. "
                         "The field also moved a claim about the boundary term [2].",
                         _compiled([1, 2, 3]))
        self.assertTrue(v.ok, [x.render() for x in v.uncited + v.unresolved])
        self.assertEqual(2, v.cited)
        self.assertEqual(["1", "2"], v.as_record()["resolved"])

    def test_one_sentence_may_cite_several_lines_of_ONE_group(self):
        """Co-citing faces of one quotient asserts no relation the field lacks.

        This control used to read "The two claims disagree about the sign of the term [1][2]"
        over two UNGROUPED objects, and the weld rule now convicts it — correctly, because
        "disagree" is a relation and nothing declared it. That is the rule working on a
        fixture written before it existed, not a regression: the property being defended is
        that several lines may be cited at once, and inside a declared group they may.
        """
        c = _compiled([1, 2])
        for cite in c["citations"]:
            cite["group"] = "fiber-A"
        v = check_answer("Both of these state the same proposition in different charts [1][2].", c)
        self.assertTrue(v.ok, v.violations)
        self.assertEqual(["1", "2"], v.as_record()["resolved"])

    def test_an_uncited_sentence_is_red_and_named(self):
        v = check_answer("Perelman settled the Poincare conjecture some years ago.",
                         _compiled([1, 2]))
        self.assertFalse(v.ok)
        self.assertEqual(1, len(v.uncited))
        self.assertIn("UNCITED", v.uncited[0].render())

    def test_a_citation_to_a_number_never_emitted_is_red(self):
        v = check_answer("The cone is positive under the ambient metric here [99].",
                         _compiled([1, 2]))
        self.assertFalse(v.ok)
        self.assertEqual(["99"], v.unresolved[0].numbers)

    def test_one_bad_sentence_among_good_ones_is_still_red(self):
        v = check_answer("The boundary term moved when the bias was applied [1]. "
                         "Perelman settled the Poincare conjecture some years ago.",
                         _compiled([1]))
        self.assertFalse(v.ok)
        self.assertEqual(2, v.checked)
        self.assertEqual(1, len(v.uncited))

    def test_a_short_fragment_is_scaffolding_not_a_proposition(self):
        # "Yes." carries no proposition; demanding a citation on it produces noise.
        v = check_answer("Yes.", _compiled([1]))
        self.assertEqual(0, v.checked)
        self.assertEqual(MIN_SENTENCE_CHARS, 25)

    def test_an_empty_answer_reports_zero_checked_so_it_cannot_read_as_a_pass(self):
        v = check_answer("", _compiled([1]))
        self.assertEqual(0, v.checked)
        self.assertTrue(v.ok)
        self.assertEqual(1, v.as_record()["citable"])


class TheTraceSetIsExactlyWhatWasEmitted(unittest.TestCase):

    def test_citable_numbers_come_from_the_record_not_from_a_range(self):
        self.assertEqual({"1", "4", "9"}, citable_numbers(_compiled([1, 4, 9])))

    def test_an_attachment_is_citable_so_it_cannot_convict_a_correct_answer_twice(self):
        compiled = {"citations": [{"n": 1, "kind": "bears_on", "chart": "english",
                                   "slot": "a", "nu": "an attached claim"}]}
        self.assertTrue(check_answer("The input was read as bearing on that claim [1].",
                                     compiled).ok)

    def test_no_citations_emitted_means_every_cited_sentence_is_unresolved(self):
        v = check_answer("Something moved in the field when this was applied [1].",
                         {"citations": []})
        self.assertFalse(v.ok)
        self.assertEqual(0, v.as_record()["citable"])


class TheRefereeIsNotALEXICALMECHANISM(unittest.TestCase):
    """THE PLANTED RETURN OF THE DELETED MOVE.

    Term overlap in the answer path is ledgered as deleted, and it came back inside the
    referee anyway. A control that only tested behaviour would not have caught it — the
    lexical version passed its own tests. So this reads the module's source: the referee may
    match integers and may split sentences, and it may not tokenize, lowercase, stem, or
    difference bags of words.
    """

    def _src(self) -> str:
        return MODULE.read_text(encoding="utf-8")

    def test_the_module_holds_no_word_tokenizer(self):
        src = self._src()
        for banned in ("[a-z0-9]+", "[a-zA-Z]+", "\\w+", ".lower()", ".split()", ".casefold()"):
            self.assertNotIn(banned, src,
                             f"a tokenizer is back in the referee: {banned!r}")

    def test_the_only_regex_matches_citations_and_sentence_ends(self):
        tree = ast.parse(self._src())
        patterns = [n.args[0].value for n in ast.walk(tree)
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "compile" and n.args
                    and isinstance(n.args[0], ast.Constant)]
        # THREE, and every one of them is named. A count with no enumeration would let a
        # tokenizer in as long as something else was removed.
        self.assertEqual(3, len(patterns), f"unexpected regexes: {patterns}")
        # A CITATION IS A LABEL: an optional single chart letter and an index. The letter is
        # `[a-z]?` and never `[a-z]+` — one character is a chart tag, and a RUN of them is a
        # word, which is the thing this whole class exists to keep out of the referee.
        self.assertIn(r"\[([a-z]?\d+)\]", patterns)                # a citation
        # THE SCOPE GROUP TAKES LABELS. It was `[\\d,\\s]+` and `[∅:e3,e7]` was invisible,
        # so an honest scoped negative naming two tagged lines came back UNCITED — convicting
        # the careful answer and passing the vague one.
        self.assertIn("\\[\\u2205(?::([a-z\\d,\\s]+))?([a-z_]+)?\\]", patterns)   # an absence
        # The third is the sentence splitter; none of the three matches a word.
        for pat in patterns:
            self.assertNotIn("a-z0-9", pat)
            self.assertNotIn("\\w+", pat)
            # NO ALPHABETIC RUN, anywhere. `[a-z]+` or `[a-z]{2,}` in a referee's regex is a
            # word matcher however it got there, and the chart tag is the one place a letter
            # is now legal at all — so the boundary is asserted rather than trusted.
            self.assertNotIn("[a-z]+", pat)
            self.assertNotIn("[a-z]*", pat)

    def test_a_chart_TAG_is_one_letter_and_a_word_does_not_resolve(self):
        """The tag opened the door to letters. This is the doorstop.

        A citation may carry one chart letter. `[same]`, `[refines]`, `[cone]` — anything with
        an alphabetic run — must not parse as a citation at all, or the referee would start
        accepting names, and a name is a thing text can be matched against.
        """
        from engine.grounded import _CITE

        for good in ("[e1]", "[l45]", "[b0]", "[7]"):
            with self.subTest(good=good):
                self.assertTrue(_CITE.findall(good), good)
        for bad in ("[same]", "[refines]", "[cone]", "[ee1]", "[e]", "[]"):
            with self.subTest(bad=bad):
                self.assertEqual(_CITE.findall(bad), [], f"{bad} parsed as a citation")

    def test_no_set_difference_survives_anywhere_in_the_module(self):
        tree = ast.parse(self._src())
        subs = [n for n in ast.walk(tree)
                if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub)]
        self.assertEqual([], subs, "a set difference is how the lexical version matched")

    def test_the_deleted_names_do_not_come_back(self):
        names = {n.id for n in ast.walk(ast.parse(self._src())) if isinstance(n, ast.Name)}
        names |= {f.name for f in ast.walk(ast.parse(self._src()))
                  if isinstance(f, ast.FunctionDef)}
        for gone in ("words", "LICENSED", "ground_of", "corpus_words", "vocab", "MIN_CONTENT"):
            self.assertNotIn(gone, names, f"{gone} was the lexical method")

    def test_the_verdict_declares_its_method(self):
        self.assertEqual("citation-resolution",
                         check_answer("x", _compiled([1])).as_record()["method"])


class TheGrammarRequiresCitations(unittest.TestCase):

    def test_the_answer_prompt_states_the_citation_rule(self):
        """THE RULE, not its spelling.

        This asserted the literal strings "CITE" and "EVERY SENTENCE YOU WRITE MUST" — the
        shouting of a prompt that has since been stripped to grammar. A control pinned to
        wording is a fossil of an old implementation: it fails when the prose improves and
        passes when the rule is deleted, which is backwards on both counts. What matters is
        that the grammar states the rule and a checker enforces it.
        """
        from engine.grammar import BLOCKS
        from engine.inbound import INBOUND_SYSTEM
        self.assertIn("[4]", INBOUND_SYSTEM, "the citation form must be shown")
        self.assertTrue(any(k == "FORM" for k, _ in BLOCKS),
                        "the codomain's syntax must be stated — it is the type annotation")
        self.assertFalse(check_answer("This sentence rests on nothing at all whatsoever.",
                                      _compiled([1])).ok)

    def test_the_compiled_prompt_prints_a_number_on_every_citable_line(self):
        from engine.inbound import Citable
        c = Citable(n=3, kind="moved", chart="english", slot="abc", nu="a claim")
        self.assertEqual(3, c.as_record()["n"])

    def test_sentence_splitting_survives_a_trailing_citation_bracket(self):
        got = sentences("The boundary term moved when the bias landed [1]. "
                        "The second claim contested it in the same block [2].")
        self.assertEqual(2, len(got), got)


class TheVerdictTravelsAsData(unittest.TestCase):

    def test_the_record_carries_both_failure_kinds_distinctly(self):
        rec = check_answer("Perelman settled the Poincare conjecture some years ago. "
                           "The cone is positive under the ambient metric here [99].",
                           _compiled([1])).as_record()
        kinds = {v["kind"] for v in rec["violations"]}
        self.assertEqual({"uncited", "unresolved"}, kinds)

    def test_a_default_verdict_is_green_and_says_it_checked_nothing(self):
        v = Verdict()
        self.assertTrue(v.ok)
        self.assertEqual(0, v.checked)


if __name__ == "__main__":
    unittest.main()


class HonestNegativesHaveALegalForm(unittest.TestCase):
    """An absence claim cannot cite a line, because there is no line.

    Three of eleven sentences in a live answer were "the relation is not measured here" —
    permanently RED under a grammar with only positive citations. An engine that can only
    report what it found will always find something, so the negatives are not an exception to
    the grammar; they are part of it, with their own checkable marker.
    """

    def _c(self, ns=(1, 2), **rel):
        att = rel.pop("attachment", [{"kind": "bears_on"}])
        return {"citations": [{"n": n} for n in ns],
                "relaxation": {"rows": rel.pop("rows", [{"hops": 1}]), **rel},
                "attachment": {"attachment": att}}

    def test_a_whole_trace_absence_claim_is_green(self):
        v = check_answer("The relation between the two quantities is not measured here [\u2205].",
                         self._c())
        self.assertTrue(v.ok, [x.render() for x in v.uncited + v.vacuous])
        self.assertEqual(1, v.asserted_absent)

    def test_a_scoped_absence_resolves_like_a_citation(self):
        v = check_answer("Neither moved claim relates them directly [\u2205:1,2].", self._c())
        self.assertTrue(v.ok)
        self.assertEqual(["1", "2"], v.as_record()["resolved"])

    def test_a_scoped_absence_over_a_line_never_shown_is_unresolved(self):
        v = check_answer("Neither moved claim relates them directly [\u2205:1,99].", self._c())
        self.assertFalse(v.ok)
        self.assertEqual(["99"], v.unresolved[0].numbers)

    def test_an_absence_over_an_empty_trace_is_VACUOUS(self):
        # Nothing was shown, so there is nothing for the claim to be absent FROM. The honest
        # sentence there is the silence statement, not a negative about nothing.
        v = check_answer("The relation between them is not measured here [\u2205].",
                         {"citations": []})
        self.assertFalse(v.ok)
        self.assertEqual("vacuous", v.violations[0]["kind"])

    def test_a_warrant_the_field_reports_is_green(self):
        c = self._c(rows=[{"hops": 0}])                   # nothing reached over an arrow
        self.assertIn("gap", warrants_held(c))
        v = check_answer("No declared correspondence carried it further [\u2205gap].", c)
        self.assertTrue(v.ok, [x.render() for x in v.unwarranted])
        self.assertEqual(["gap"], v.as_record()["warrants"])

    def test_a_warrant_the_field_does_NOT_report_is_UNWARRANTED(self):
        # This is the only check that can convict an INVENTED negative: the model claiming the
        # field reports a silence it does not report.
        c = self._c(rows=[{"hops": 1}])
        v = check_answer("The region could not be aimed at anything [\u2205anchor].", c)
        self.assertFalse(v.ok)
        self.assertEqual("unwarranted", v.violations[0]["kind"])
        self.assertEqual("anchor", v.violations[0]["warrant"])

    def test_every_warrant_name_has_a_predicate_that_decides_it(self):
        # A warrant with no predicate is a vocabulary of excuses. Each name must be decidable
        # from the record — asserted here by constructing the state that holds it.
        cases = {
            "gap": self._c(rows=[{"hops": 0}]),
            "cap": self._c(blocks_skipped=2),
            "cut": self._c(moved_dropped=5),
            "attach": self._c(attachment=[]),
            "void": {"citations": [{"n": 1}], "relaxation": {"rows": [{"hops": 1}]},
                     "attachment": {"attachment": [{"kind": "x"}], "void": 3}},
            "anchor": {"citations": [{"n": 1}], "relaxation": {"rows": [{"hops": 1}]},
                       "attachment": {"attachment": [{"kind": "x"}], "unanchored": True}},
            "indiscriminate": {"citations": [{"n": 1}], "relaxation": {"rows": [{"hops": 1}]},
                               "attachment": {"attachment": [{"kind": "x"}],
                                              "discrimination": {"red": True}}},
        }
        self.assertEqual(set(WARRANTS), set(cases), "a warrant with no test state")
        for name, compiled in cases.items():
            self.assertIn(name, warrants_held(compiled), f"{name} is not decidable")

    def test_a_warrant_outside_the_closed_list_does_not_resolve(self):
        v = check_answer("Nothing here relates to that at all [\u2205whatever].", self._c())
        self.assertFalse(v.ok)
        self.assertEqual("unwarranted", v.violations[0]["kind"])

    def test_positives_and_negatives_are_counted_separately(self):
        # An instrument whose answers are all positives is a different instrument from one
        # that reports what it could not find. The operator must be able to see which.
        rec = check_answer("The boundary term moved when the bias landed [1]. "
                           "The second relation is not measured in this trace [\u2205].",
                           self._c()).as_record()
        self.assertTrue(rec["ok"])
        self.assertEqual(1, rec["cited"])
        self.assertEqual(1, rec["asserted_absent"])
        self.assertEqual(2, rec["checked"])

    def test_a_sentence_may_carry_both_a_citation_and_an_absence(self):
        v = check_answer("Claim one moved but says nothing about the second quantity "
                         "[1][\u2205:2].", self._c())
        self.assertTrue(v.ok, [x.render() for x in v.uncited + v.unresolved])

    def test_every_warrant_the_checker_accepts_RESOLVES_against_the_record(self):
        """The real property, and the one that outlived the prompt listing them.

        This asserted that every `[∅gap]`-style form appears in the prompt. It cannot: the
        grammar spec was REMOVED from the visible prompt because the model recited it, and
        what remains states the codomain's syntax — `[n]` per sentence, `[∅]` for absence —
        not the full warrant vocabulary. Listing seven warrant names is grammar detail, and
        grammar detail in the prompt is exactly what got recited back as an answer.

        The warrants are still ACCEPTED, and this is what makes accepting them honest: every
        name resolves against something `warrants_held` reads off the relaxation record. A
        model that names one the field does not report is flagged; a model that never names
        one is fine, and the bare `[∅]` the prompt does state is always available.
        """
        from engine.grounded import WARRANTS, warrants_held
        compiled = {"relaxation": {"rows": [], "responded": False, "blocks_skipped": 1,
                                   "moved_dropped": 1},
                    "attachment": {"attachment": [], "void": 1, "unanchored": True,
                                   "discrimination": {"red": True}},
                    "conditioned": False}
        held = warrants_held(compiled)
        for name in WARRANTS:
            if name == "rel":
                continue        # licensed by the weld rule itself, not by a field statistic
            self.assertIn(name, held,
                          f"the checker accepts [∅{name}] but nothing on the record can hold it")

    def test_the_prompt_states_the_absence_form_it_expects(self):
        from engine.inbound import INBOUND_SYSTEM
        self.assertIn("[∅]", INBOUND_SYSTEM,
                      "a model cannot write an absence marker it has never been shown")


class ThePromptIsWIREGrammarAndNothing(unittest.TestCase):
    """ITEM 3. Every block tagged, and a style instruction has no legal tag.

    The prompt reached 4,889 characters by answering each defect with another sentence:
    how to open, whose voice to prefer, what not to apologise for, an exhortation to report
    absences, and the citation rule three times over. None of it was enforceable. The blocks
    make "no editorial content" a control rather than an intention.
    """

    def test_every_block_is_wire_grammar_or_state(self):
        from engine.grammar import BLOCKS, illegal_blocks
        self.assertTrue(BLOCKS)
        self.assertEqual([], illegal_blocks())

    def test_a_planted_style_instruction_is_RED(self):
        from engine.grammar import illegal_blocks
        planted = (("STYLE", "Open with a line naming what the question bears on."),)
        self.assertEqual(1, len(illegal_blocks(planted)))

    def test_the_prompt_carries_no_voice_or_opening_instruction(self):
        # The corpus-voice preference and the answer-first phrasing rule were both ordered
        # dead; they were reactions to defects since fixed at the root.
        from engine.inbound import INBOUND_SYSTEM
        low = INBOUND_SYSTEM.lower()
        for banned in ("i read your question", "voice", "prefer", "apolog", "persona",
                       "open with", "not an inventory", "worth reading"):
            self.assertNotIn(banned, low, f"editorial content survived: {banned!r}")

    def test_every_grammar_rule_has_a_checker(self):
        # The claim that makes this prompt legitimate: each GRAMMAR block names a rule the
        # build enforces. A rule with no checker is prose.
        from engine.grammar import BLOCKS
        from engine.grounded import check_answer
        import inspect
        src = inspect.getsource(check_answer)
        for kind, text in BLOCKS:
            if kind != "GRAMMAR":
                continue
            self.assertTrue(
                any(tok in src for tok in ("uncited", "unresolved", "vacuous", "unwarranted",
                                           "welded", "uncontested")),
                f"no checker backs: {text[:50]}")


class TheWeldRule(unittest.TestCase):
    """A sentence may not relate objects no arrow joins.

    MEASURED FAILURE: "certified positivity relates to mode spectrum measurement [21]" — two
    co-present claims fused by a conjunction, each half cited, the relation declared nowhere.
    """

    def _c(self):
        return {"citations": [{"n": 1}, {"n": 2}, {"n": 3},
                              {"n": 9, "kind": "arrow", "joins": [1, 2]},
                              {"n": 4, "contested": True}],
                "relaxation": {"rows": [{"hops": 1}]},
                "attachment": {"attachment": [{"kind": "x"}]}}

    def test_co_citing_unrelated_objects_is_WELDED(self):
        v = check_answer("Certified positivity relates to mode spectrum measurement "
                         "in this corpus [1][3].", self._c())
        self.assertFalse(v.ok)
        self.assertEqual("welded", v.violations[0]["kind"])

    def test_citing_the_ARROW_licenses_the_relation(self):
        self.assertTrue(check_answer("Both of these concern the settling floor and its "
                                     "measurement [1][2][9].", self._c()).ok)

    def test_the_absence_marker_licenses_it_too(self):
        self.assertTrue(check_answer("No declared arrow joins these two claims in this "
                                     "field [1][3][∅rel].", self._c()).ok)

    def test_one_object_per_sentence_is_never_welded(self):
        self.assertTrue(check_answer("The settling floor is measured over cycles here [1].",
                                     self._c()).ok)


class TheContestRule(unittest.TestCase):
    """A contest resolved in prose is the one thing the field refuses to do itself."""

    def _c(self):
        return {"citations": [{"n": 4, "contested": True}, {"n": 1}],
                "relaxation": {"rows": [{"hops": 1}]},
                "attachment": {"attachment": [{"kind": "x"}]}}

    def test_citing_a_contested_object_without_the_marker_is_RED(self):
        v = check_answer("The settled value of that claim is definitely true across the "
                         "field [4].", self._c())
        self.assertFalse(v.ok)
        self.assertEqual("uncontested", v.violations[0]["kind"])

    def test_the_marker_licenses_it(self):
        self.assertTrue(check_answer("The settled value of that claim is disputed across "
                                     "the field [4][!].", self._c()).ok)

    def test_an_uncontested_object_needs_no_marker(self):
        self.assertTrue(check_answer("The settling floor is measured over cycles here [1].",
                                     self._c()).ok)


class TheWorkflowsFourGaps(unittest.TestCase):
    """Found by an exhaustive blast-radius mapping, each verified by EXECUTION not by reading.

    All four were silent: none crashed, none turned the suite red, and three of them made the
    referee convict CORRECT answers — which is the worst direction for a faithfulness gate to
    be wrong in, because a false RED teaches the reader to stop believing the green.
    """

    def test_a_fibered_pair_co_cited_is_NOT_a_weld(self):
        """G2. `Citable.as_record()` dropped `group`, so two faces of ONE quotient came back
        WELDED — and the weld rule is precisely about claims from DIFFERENT groups. The
        quotient IS the declared relation between them."""
        from engine.inbound import Citable

        compiled = {"citations": [
            Citable(n="e1", kind="moved", chart="english", slot="s1", nu="a",
                    group="fiber-A").as_record(),
            Citable(n="l1", kind="moved", chart="lean", slot="s2", nu="b",
                    group="fiber-A").as_record()]}
        v = check_answer("Both state the same proposition in different charts [e1][l1].",
                         compiled)
        self.assertEqual([w.render() for w in v.welded], [])
        self.assertTrue(v.ok, v.as_record())

    def test_two_DIFFERENT_groups_co_cited_is_still_a_weld(self):
        """The other direction, or the fix would have deleted the rule instead of feeding it."""
        from engine.inbound import Citable

        compiled = {"citations": [
            Citable(n="e1", kind="moved", chart="english", slot="s1", nu="a",
                    group="fiber-A").as_record(),
            Citable(n="l1", kind="moved", chart="lean", slot="s2", nu="b",
                    group="fiber-B").as_record()]}
        self.assertTrue(check_answer("These two are related [e1][l1].", compiled).welded)

    def test_contested_and_joins_survive_the_record_too(self):
        from engine.inbound import Citable

        rec = Citable(n="e1", kind="arrow", chart="english", slot="s", nu="x",
                      contested=True, joins=("e1", "e2")).as_record()
        self.assertTrue(rec["contested"])
        self.assertEqual(rec["joins"], ["e1", "e2"])

    def test_a_scoped_absence_over_LABELS_resolves(self):
        """G4. `[∅:e3,e7]` was invisible to _ABSENT, so an honest scoped negative naming two
        tagged lines came back UNCITED — convicting the careful answer and passing the vague
        one."""
        compiled = _compiled(["e3", "e7"])
        v = check_answer("Neither moved claim relates them directly [∅:e3,e7].", compiled)
        self.assertEqual(v.uncited, [])
        self.assertEqual(v.unresolved, [])
        self.assertTrue(v.ok, v.as_record())

    def test_a_scoped_absence_over_a_LABEL_never_shown_is_still_unresolved(self):
        """Widening the scope group must not have widened what resolves."""
        v = check_answer("The field does not relate those two lines at all [∅:l99].",
                         _compiled(["e3"]))
        self.assertTrue(v.unresolved)

    def test_the_bare_number_form_still_resolves(self):
        """A field emitted before the collapse must still be readable."""
        self.assertTrue(check_answer("A claim [1].", _compiled([1])).ok)

    def test_NO_CITER_ANYWHERE_mints_a_bare_number(self):
        """G3, and this is the control that would have caught the whole class.

        Two of three Citable construction sites moved to tagged labels and the third did not,
        so a structural question produced forty `e11`-style citations and one `[41]` — an
        actual int — in the same bracket stream. It did not crash, because `[a-z]?\\d+` matches
        a bare number. Silent by construction, which is the shape of the half-collapse this
        label space exists to make impossible.
        """
        import re as _re

        from engine.corpus_state import CorpusSnapshot
        from engine.inbound import Citable
        from engine.structure_trace import structure_lines

        cites: list = []
        structure_lines(CorpusSnapshot(slots={}, arrows=()), cites, Citable)
        bare = [c.n for c in cites if not _re.match(r"^[a-z]\\d+$", str(c.n))]
        self.assertEqual(bare, [], f"a citer minted untagged numbers: {bare}")
