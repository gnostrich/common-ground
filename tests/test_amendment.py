"""The amendment is binding, not advisory — and this is where "binding" is cashed out.

`seed/OBJECT-AMENDED.md` supersedes `seed/OBJECT.md`. Two clauses in it are enforced in code
rather than trusted, in the same shape as the rest of the gate suite:

  * **A mechanism fix cites its MOVE and its Q.** A change to the object itself must say which
    of the three legal moves it is and which diagnostic question motivated it. The check does
    not verify the citation is TRUE — no static check could — it verifies the author was made
    to answer before landing, which is the failure the protocol was written for: refining a
    wrong mechanism instead of asking the diagram whether it can work at all.

  * **A docstring may not describe a call graph that does not exist.** Three files in one day
    claimed mechanisms they did not contain, including `engine/inbound.py` asserting that
    settlement ran with the input as soft evidence, from the day it was written, while calling
    `settle` nowhere.

Both are planted against, because a gate nobody has watched fail is a gate nobody knows works.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from engine.constants import REPO_ROOT
from engine.static_checks import (
    DIAGNOSTIC_QUESTIONS,
    LEGAL_MOVES,
    MECHANISM_CLAIMS,
    MECHANISM_MODULES,
    _mechanism_claims_in,
    check_claim_discipline,
    check_move_citation,
)


class TheAmendmentIsCanonical(unittest.TestCase):
    def test_the_amended_document_exists_and_supersedes_the_old_one(self):
        amended = REPO_ROOT / "seed" / "OBJECT-AMENDED.md"
        old = REPO_ROOT / "seed" / "OBJECT.md"
        self.assertTrue(amended.exists())
        self.assertIn("SUPERSEDED", old.read_text(encoding="utf-8"),
                      "OBJECT.md must say it is superseded, or two documents both read as "
                      "canonical and the reader picks")
        self.assertIn("OBJECT-AMENDED.md", old.read_text(encoding="utf-8"))

    def test_it_states_the_attachment_law(self):
        text = (REPO_ROOT / "seed" / "OBJECT-AMENDED.md").read_text(encoding="utf-8")
        self.assertIn("IDENTITY and ATTACHMENT are different questions", text)
        self.assertIn("binding, not advisory", text)

    def test_it_states_the_three_moves_the_code_enforces(self):
        text = (REPO_ROOT / "seed" / "OBJECT-AMENDED.md").read_text(encoding="utf-8")
        for move in LEGAL_MOVES:
            self.assertIn(move, text,
                          f"{move!r} is enforced in code but not stated in the document")

    def test_the_diagnostic_protocol_is_present_in_full(self):
        text = (REPO_ROOT / "seed" / "OBJECT-AMENDED.md").read_text(encoding="utf-8")
        for q in sorted(DIAGNOSTIC_QUESTIONS):
            self.assertIn(f"**{q}.**", text, f"{q} is accepted by the check but not documented")


class EveryMechanismModuleCitesItsMove(unittest.TestCase):
    def test_the_repository_is_clean(self):
        result = check_move_citation()
        self.assertEqual([str(v) for v in result.violations], [])
        self.assertEqual(result.checked_files, len(MECHANISM_MODULES))

    def test_planted_a_mechanism_module_with_no_citation_is_red(self):
        """PLANTED: the default state of every file before this gate existed."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in MECHANISM_MODULES:
                target = root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('"""Does a thing."""\n', encoding="utf-8")
            result = check_move_citation(root)
            self.assertEqual(len(result.violations), len(MECHANISM_MODULES))
            self.assertIn("no MOVE cited", str(result.violations[0]))

    def test_planted_a_fourth_move_is_creep_and_is_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = sorted(MECHANISM_MODULES)[0]
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('"""MOVE: ADD A HEURISTIC\nQ2 motivated it."""\n',
                              encoding="utf-8")
            result = check_move_citation(root)
            self.assertTrue(any("illegal MOVE" in str(v) for v in result.violations),
                            "a move outside the three is creep and must be REJECTED")

    def test_planted_a_move_with_no_diagnostic_question_is_red(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rel = sorted(MECHANISM_MODULES)[0]
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('"""MOVE: ADD A MORPHISM\nBecause it seemed good."""\n',
                              encoding="utf-8")
            result = check_move_citation(root)
            self.assertTrue(any("no diagnostic question" in str(v)
                                for v in result.violations))

    def test_planted_a_listed_module_that_does_not_exist_is_red(self):
        """PLANTED: the first draft of MECHANISM_MODULES named `engine/mint.py`, which does
        not exist. The check skipped it silently and reported eight files while covering
        seven — a gate that quietly stops covering what it names."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            result = check_move_citation(Path(tmp))
            self.assertEqual(len(result.violations), len(MECHANISM_MODULES))
            self.assertIn("does not exist", str(result.violations[0]))

    def test_each_citation_names_a_question_the_protocol_defines(self):
        import ast
        import re

        for rel in sorted(MECHANISM_MODULES):
            doc = ast.get_docstring(ast.parse(
                (REPO_ROOT / rel).read_text(encoding="utf-8"))) or ""
            found = set(re.findall(r"\b(Q[1-5])\b", doc))
            self.assertTrue(found <= DIAGNOSTIC_QUESTIONS, f"{rel} cites {found - DIAGNOSTIC_QUESTIONS}")
            self.assertTrue(found, rel)


class ADocstringMayNotDescribeACallGraphThatDoesNotExist(unittest.TestCase):
    """Gate 10, extended to mechanism claims. Three files in one day, one of them for its
    entire life."""

    def test_planted_settlement_runs_over_a_function_with_no_settle_call(self):
        """PLANTED, verbatim: the sentence `engine/inbound.py` carried from the day it was
        written while its call graph contained no settle, no FreeEnergy and no anneal."""
        got = _mechanism_claims_in("settlement runs with the input as soft evidence",
                                   "engine/fake.py", set())
        self.assertTrue(got, "the historical sentence must go RED with no machinery present")
        self.assertIn("settlement", {kind for kind, _ in got})

    def test_the_same_sentence_passes_where_settle_is_actually_called(self):
        self.assertEqual(
            _mechanism_claims_in("settlement runs with the input as soft evidence",
                                 "engine/fake.py", {"settle"}), [])

    def test_each_named_category_is_planted_against(self):
        """Every phrase the operator named: settlement, relaxation, energy, index-driven."""
        cases = [
            ("settlement runs on the corpus", {"settle"}),
            ("the relaxation runs to stationarity", {"relax"}),
            ("the typed text enters the corpus energy", {"FreeEnergy"}),
            ("anchoring is index-driven", {"defaultdict"}),
        ]
        for phrase, machinery in cases:
            self.assertTrue(_mechanism_claims_in(phrase, "engine/fake.py", set()),
                            f"{phrase!r} must be RED with no machinery")
            self.assertEqual(_mechanism_claims_in(phrase, "engine/fake.py", machinery), [],
                             f"{phrase!r} must pass where {machinery} is referenced")

    def test_a_descriptive_mention_is_not_a_claim(self):
        """A gate that cries wolf gets ignored, which is how the first one survived."""
        for benign in ("the cast/settle split: settling produces a distribution",
                       "a tree-shaped contest settles to floor exactly 0",
                       "ingest -> address -> prior -> block -> settle -> meter"):
            self.assertEqual(_mechanism_claims_in(benign, "engine/fake.py", set()), [])

    def test_the_repository_is_clean_under_both_gates(self):
        self.assertEqual([str(v) for v in check_claim_discipline().violations], [])
        self.assertEqual([str(v) for v in check_move_citation().violations], [])

    def test_the_categories_cover_what_the_amendment_names(self):
        kinds = {k for k, _, _ in MECHANISM_CLAIMS}
        for expected in ("settlement", "energy", "index"):
            self.assertIn(expected, kinds)


if __name__ == "__main__":
    unittest.main()
