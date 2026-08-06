"""THE REFEREE, AND THE CONTROL THAT KEEPS IT STRUCTURAL.

The answer moved to the top of the page. What makes that warranted is a gate that can convict
it — and the FIRST gate built for the job was term overlap, the move this codebase records as
deleted, reintroduced inside the referee where it does the most damage. So this file plants
both the ordinary REDs and the return of the lexical method itself.
"""

import ast
import unittest
from pathlib import Path

from engine.grounded import (MIN_SENTENCE_CHARS, Verdict, check_answer, citable_numbers,
                             sentences)

MODULE = Path(__file__).resolve().parent.parent / "engine" / "grounded.py"


def _compiled(ns):
    return {"citations": [{"n": n, "kind": "moved", "chart": "english",
                           "slot": f"s{n}", "nu": f"claim {n}"} for n in ns]}


class CitationsResolveOrTheyDoNot(unittest.TestCase):

    def test_a_fully_cited_answer_is_green(self):
        v = check_answer("I read your question as bearing on the metric cone [1]. "
                         "The field also moved a claim about the boundary term [2].",
                         _compiled([1, 2, 3]))
        self.assertTrue(v.ok, [x.render() for x in v.uncited + v.unresolved])
        self.assertEqual(2, v.cited)
        self.assertEqual([1, 2], v.as_record()["resolved"])

    def test_one_sentence_may_cite_several_lines(self):
        v = check_answer("The two claims disagree about the sign of the term [1][2].",
                         _compiled([1, 2]))
        self.assertTrue(v.ok)
        self.assertEqual([1, 2], v.as_record()["resolved"])

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
        self.assertEqual([99], v.unresolved[0].numbers)

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
        self.assertEqual({1, 4, 9}, citable_numbers(_compiled([1, 4, 9])))

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
        self.assertEqual(2, len(patterns), f"unexpected regexes: {patterns}")
        self.assertIn(r"\[(\d+)\]", patterns)

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
        from engine.inbound import INBOUND_SYSTEM
        self.assertIn("CITE", INBOUND_SYSTEM)
        self.assertIn("EVERY SENTENCE YOU WRITE MUST", INBOUND_SYSTEM)

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
