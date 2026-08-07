"""B2's six pre-registered controls, from seed/DIALOGIC.md — written before any code existed.

The spec listed them as "all planted, none written". They are written here against the same
numbering, so a reader can hold the spec beside the file and check that the thing built is the
thing designed. That is OI-28's shape: reasoning designs, measurement tripwires.

  1. No arrow from words.
  2. Testimony never grounds.
  3. Turns come from structure.
  4. The budget binds.
  5. Trajectory kept, counted correctly.
  6. The daemon is untouched.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.dialogue import (ARROW, DIALOGUE_KINDS, TESTIMONY, TURN_BUDGET, Proposal, Turn,
                             arrows_from, implied_unaddressed, interrogate)

REPO = Path(__file__).resolve().parent.parent
MODULE = REPO / "engine" / "dialogue.py"

CITABLE = {1, 2, 3, 7, 12}


def _compiled(citations):
    return {"citations": citations}


class C1_NoArrowFromWords(unittest.TestCase):
    """Spec control 1. The whole protocol rests on this and nothing else does the work."""

    def test_persuasive_prose_with_no_coordinates_yields_NOTHING(self):
        for prose in (
            "These two are obviously the same claim, as anyone can see.",
            "Certified positivity clearly refines the general positivity result.",
            "I am highly confident that object one is an instance of object seven.",
            "same_claim refines instance_of bears_on",          # the tokens, no coordinates
        ):
            with self.subTest(prose=prose[:40]):
                self.assertEqual(arrows_from(prose, CITABLE), [])

    def test_an_arrow_needs_BOTH_coordinates_and_a_kind(self):
        self.assertEqual(arrows_from("[1] and [7] are related.", CITABLE), [])
        self.assertEqual(arrows_from("[1] refines [7]", CITABLE), [],
                         "without the arrow syntax this is prose about a relation")
        self.assertTrue([p for p in arrows_from("[1] -refines-> [7]", CITABLE) if p.ok])

    def test_the_extractor_contains_NO_similarity_machinery(self):
        """AST sweep, as the spec ordered. No tokenizer, no scoring, no fluency judgement —
        and this reads the parsed module rather than grepping text, so a mention inside a
        docstring explaining the prohibition does not trip it."""
        tree = ast.parse(MODULE.read_text())
        banned = {"lower", "casefold", "split", "difflib", "SequenceMatcher", "ratio",
                  "similarity", "token", "tokenize", "stem", "embed", "score"}
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in banned:
                hits.append(node.attr)
            if isinstance(node, ast.Name) and node.id in banned:
                hits.append(node.id)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in getattr(node, "names", []):
                    if a.name.split(".")[0] in banned:
                        hits.append(a.name)
        self.assertEqual(hits, [], f"resemblance machinery in the dialogic extractor: {hits}")

    def test_a_PLANTED_word_reader_would_be_caught(self):
        """The sweep's own control: it must fire on the shape it hunts."""
        tree = ast.parse("def f(prose):\n    return 'refines' in prose.lower()\n")
        self.assertTrue(any(isinstance(n, ast.Attribute) and n.attr == "lower"
                            for n in ast.walk(tree)))


class C2_TestimonyNeverGrounds(unittest.TestCase):
    """Spec control 2. Zero warrant is the ABSENCE of a tier, not a low one."""

    def test_testimony_is_not_a_warrant_tier(self):
        """A testimony comparable to EXTRACTION on the poset is a testimony that could be
        promoted, and the point is that it cannot be."""
        from engine.types import WarrantTier

        names = {t.name for t in WarrantTier}
        self.assertNotIn("TESTIMONY", names)
        self.assertNotIn(TESTIMONY.upper(), names)

    def test_a_turn_records_its_prose_with_NO_warrant(self):
        rec = Turn(n=1, ask="q", prose="the medium said this").as_record()
        self.assertEqual(rec["record_kind"], TESTIMONY)
        self.assertIsNone(rec["warrant"], "testimony carries no warrant at all")

    def test_the_prose_is_KEPT_because_the_trajectory_matters(self):
        """Zero warrant is not a reason to discard it."""
        rec = Turn(n=1, ask="q", prose="what the medium said").as_record()
        self.assertEqual(rec["prose"], "what the medium said")

    def test_the_module_confers_no_tier_anywhere(self):
        body = MODULE.read_text()
        for tier in ("EXTRACTION", "AUTHORSHIP", "KERNEL", "CI_RECEIPT", "PREMINTED"):
            self.assertNotIn(f"WarrantTier.{tier}", body,
                             "the dialogic path must not confer a tier on anything")


class C3_TurnsComeFromStructure(unittest.TestCase):
    """Spec control 3. Never 'that answer seemed thin, ask again'."""

    def test_interrogate_CANNOT_see_the_prose(self):
        """Impossibility by construction: the reply is not a parameter, so no future edit can
        quietly start reading it without changing the signature."""
        import inspect

        params = set(inspect.signature(interrogate).parameters)
        self.assertEqual(params, {"compiled", "asked"})
        for forbidden in ("prose", "reply", "answer", "text", "turn"):
            self.assertNotIn(forbidden, params)

    def test_it_asks_about_an_implied_pair_nobody_has_measured(self):
        c = _compiled([{"n": 1}, {"n": 7},
                       {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        q = interrogate(c, asked=set())
        self.assertIn("[1]", q)
        self.assertIn("[7]", q)
        self.assertIn("Composition implies", q)

    def test_it_does_not_re_ask_a_pair_already_put(self):
        c = _compiled([{"n": 1}, {"n": 7},
                       {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        self.assertEqual(interrogate(c, asked={(1, 7)}), "",
                         "asking the same pair twice is an interrogation loop, not a measure")

    def test_it_falls_through_to_a_CONTESTED_object(self):
        c = _compiled([{"n": 3, "contested": True}])
        self.assertIn("[3]", interrogate(c, asked=set()))
        self.assertIn("more than one value", interrogate(c, asked=set()))

    def test_it_returns_EMPTY_rather_than_inventing_a_question(self):
        """No structure left to ask about ends the dialogue. Manufacturing one more turn
        because the budget allows it is the candidate list with better manners."""
        self.assertEqual(interrogate(_compiled([{"n": 1}]), asked=set()), "")


class C4_TheBudgetBinds(unittest.TestCase):
    """Spec control 4. An unbounded interrogation is what Q5 deleted once already."""

    def test_the_budget_is_declared_and_small(self):
        self.assertIsInstance(TURN_BUDGET, int)
        self.assertGreaterEqual(TURN_BUDGET, 1)
        self.assertLessEqual(TURN_BUDGET, 8, "a large budget is an unbounded loop with a cap")

    def test_the_budget_carries_a_provenance_entry(self):
        """Every constant argues for itself or confesses. engine/constants_sweep.py enforces
        this; asserting it here means the dialogue lane fails on its own terms first."""
        import json

        d = json.loads((REPO / "seed" / "CONSTANT_PROVENANCE.json").read_text())
        self.assertIn("TURN_BUDGET", d["constants"])


class C5_TrajectoryKeptCountedCorrectly(unittest.TestCase):
    """Spec control 5. The unit is the distinct claim, not the utterance."""

    def test_five_restatements_are_ONE_claim_and_FIVE_records(self):
        prose = " ".join(["[1] -same_claim-> [7]."] * 5)
        ps = arrows_from(prose, CITABLE, turn=2)
        self.assertEqual(len(ps), 5, "every utterance is recorded")
        self.assertEqual(sum(1 for p in ps if p.ok), 1, "they are one claim")
        self.assertEqual([p.void for p in ps[1:]], ["restated in this turn"] * 4)

    def test_the_record_says_WHICH_it_is_counting(self):
        t = Turn(n=2, ask="q", proposals=arrows_from("[1] -same_claim-> [7]. " * 3, CITABLE))
        rec = t.as_record()
        self.assertEqual(len(rec["arrows"]), 3)
        self.assertEqual(rec["resolved"], 1)
        self.assertEqual(rec["void"], 2)

    def test_every_proposal_carries_its_TURN(self):
        """Both survive with their turn recorded — a revision at turn 6 does not erase turn 2."""
        for p in arrows_from("[1] -refines-> [7]", CITABLE, turn=6):
            self.assertEqual(p.turn, 6)

    def test_a_direction_flip_is_a_DIFFERENT_record_but_the_same_pair(self):
        """`refines` is directed, so [1]->[7] and [7]->[1] are different assertions. The
        dedupe is on the unordered pair AND the kind, so the second is a restatement of the
        pair — recorded, not silently dropped — and the operator can see both."""
        ps = arrows_from("[1] -refines-> [7]. [7] -refines-> [1].", CITABLE)
        self.assertEqual(len(ps), 2)
        self.assertEqual(sum(1 for p in ps if p.ok), 1)


class C6_TheDaemonIsUntouched(unittest.TestCase):
    """Spec control 6. Two paths, and only the interactive one is conversational."""

    def test_no_unattended_module_imports_the_dialogue(self):
        for rel in ("engine/continuous.py", "engine/walk.py", "engine/propose_correspondence.py",
                    "proposerd.py"):
            p = REPO / rel
            if not p.exists():
                continue
            with self.subTest(module=rel):
                self.assertNotIn("dialogue", p.read_text(),
                                 f"{rel} is on the unattended path and must never run a dialogue")

    def test_the_walks_region_prompt_carries_no_dialogic_grammar(self):
        from engine.region import REGION_SYSTEM

        self.assertNotIn("-refines-> [", REGION_SYSTEM,
                         "the coordinate wire must not learn the prose form")


if __name__ == "__main__":
    unittest.main()
