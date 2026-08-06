"""THE META-CONTROL'S OWN CONTROL. A sweep that cannot fail is decoration.

Three referees were built out of word bags before anything swept for them. This file asserts
the sweep is green NOW, that it goes red on the shape when the shape is planted, that every
exemption states a reason, and that the exemption list cannot be used to silence a real hit.
"""

import ast
import textwrap
import unittest
from pathlib import Path

from engine.referee_sweep import (ALLOWED, ENGINE, REFEREES, Finding, render, sweep,
                                  sweep_module)


class NoRefereeDecidesByResemblance(unittest.TestCase):

    def test_the_sweep_is_green(self):
        found = sweep()
        self.assertEqual([], found, "\n" + render(found))

    def test_every_registered_referee_exists(self):
        missing = [n for n in REFEREES if not (ENGINE / n).exists()]
        self.assertEqual([], missing, f"registered but absent: {missing}")

    def test_the_registry_covers_the_modules_that_grade(self):
        # A referee that is not registered is not swept. Anything whose name says it judges
        # must be in the registry — the check that notices a new guard slipping in unswept.
        judging = sorted(p.name for p in ENGINE.glob("*.py")
                         if any(k in p.name for k in ("audit", "sweep", "check", "gate",
                                                      "probe", "meter", "quarantine")))
        unregistered = [n for n in judging if n not in REFEREES and n != "referee_sweep.py"]
        self.assertEqual([], unregistered, f"guard modules outside the registry: {unregistered}")


class ThePlantedShapesAreCaught(unittest.TestCase):

    def _plant(self, body: str) -> list[Finding]:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "grounded.py"          # a name that IS in the registry
            f.write_text(textwrap.dedent(body))
            return sweep_module(f)

    def test_a_letter_class_tokenizer_is_caught(self):
        found = self._plant('''
            import re
            def check(answer):
                return set(re.findall(r"[a-z]+", answer))
        ''')
        self.assertTrue(any(f.shape == "TOKENIZE" for f in found), found)

    def test_a_bare_split_is_caught(self):
        found = self._plant('''
            def check(answer):
                return set(answer.split())
        ''')
        self.assertTrue(any(f.shape == "TOKENIZE" for f in found), found)

    def test_case_folding_is_caught(self):
        found = self._plant('''
            def check(answer):
                return answer.casefold()
        ''')
        self.assertTrue(any(f.shape == "FOLD" for f in found), found)

    def test_a_set_difference_between_two_word_bags_is_caught(self):
        found = self._plant('''
            def check(answer_words, ground_words):
                return answer_words - ground_words
        ''')
        self.assertTrue(any(f.shape == "BAG-OP" for f in found), found)

    def test_the_exact_shape_that_shipped_is_caught(self):
        # `loose = sorted(words(sentence) - ground - LICENSED)` — the faithfulness checker
        # as it actually shipped. If this ever passes, the sweep has stopped working.
        found = self._plant('''
            def check_answer(sentence, ground, LICENSED):
                return sorted(words(sentence) - ground - LICENSED)
        ''')
        self.assertTrue(any(f.shape == "BAG-OP" for f in found), found)

    def test_the_keyword_intersection_that_shipped_is_caught(self):
        # `p_keys & _keywords(r.claim)` — engine/conversation.py as it actually shipped.
        found = self._plant('''
            def ledger(p_keys, claim):
                return p_keys & _keywords(claim)
        ''')
        self.assertTrue(any(f.shape == "BAG-OP" for f in found), found)


class TheExemptionsCarryReasons(unittest.TestCase):

    def test_no_exemption_is_a_bare_name(self):
        for key, reason in ALLOWED.items():
            self.assertTrue(reason and len(reason) > 60,
                            f"{key} is exempted without a real reason")

    def test_every_exemption_says_why_it_is_a_declared_grammar_or_our_own_text(self):
        # The distinction that makes an exemption legitimate is stated in the module: a
        # CLOSED, DECLARED vocabulary, or text this project wrote. An exemption that argues
        # neither is an exemption granted to make the suite green.
        for key, reason in ALLOWED.items():
            low = reason.lower()
            ok = any(t in low for t in ("declared", "closed", "pinned", "we wrote",
                                        "our own", "cardinality", "enum"))
            self.assertTrue(ok, f"{key} exempted without naming a declared grammar: {reason}")

    def test_an_exemption_cannot_be_added_without_editing_this_file_too(self):
        self.assertEqual(7, len(ALLOWED),
                         "an exemption was added or removed — state its reason here")


class TheDeletedBagsStayDeleted(unittest.TestCase):

    def test_the_conversation_keyword_bag_is_gone_with_its_stoplist(self):
        src = (ENGINE / "conversation.py").read_text()
        tree = ast.parse(src)
        names = {f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
        self.assertNotIn("_keywords", names)
        self.assertNotIn("_STOP = frozenset", src,
                         "an orphaned calibration artifact outlived the thing it calibrated")

    def test_the_faithfulness_licensed_list_is_gone(self):
        # AST NAMES, NOT THE SOURCE TEXT. The module's docstring QUOTES the deleted code in
        # order to explain why it went; a grep cannot tell a name asserted from a name
        # quoted, and this exact trap has caught a control in this repo before.
        tree = ast.parse((ENGINE / "grounded.py").read_text())
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {t.id for a in ast.walk(tree) if isinstance(a, ast.Assign)
                  for t in a.targets if isinstance(t, ast.Name)}
        names |= {f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)}
        for gone in ("LICENSED", "MIN_CONTENT", "words", "ground_of", "corpus_words"):
            self.assertNotIn(gone, names, f"{gone} was the lexical method")


if __name__ == "__main__":
    unittest.main()
