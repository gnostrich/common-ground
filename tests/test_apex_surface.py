"""THE DOORLESS RULING's controls. A surface is DERIVED, and nothing waits on a signature.

The ruling deleted the nomination-offer-signature flow as a gate on vocabulary. What has to
hold afterwards: no code path requires operator action for an apex to be called something, the
derivation is a total order rather than a score, the two-mouth law still binds SLOTS, and no
mechanism anywhere treats a term the medium coined as special.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.apex_surface import (AUTHORED, GLOSS, KERNEL, RANKS, SHORTEST, Surface,
                                 surface_of)

MODULE = Path(__file__).resolve().parents[1] / "engine" / "apex_surface.py"
ENGINE = Path(__file__).resolve().parents[1] / "engine"


class _M:
    def __init__(self, slot, tier, nu):
        self.slot, self.tier, self.nu = slot, tier, nu


class _G:
    def __init__(self, reading):
        self.reading = reading


def _plain(*pairs):
    return [_M(slot, "EXTRACTION", f"\x01en\x01{text}") for slot, text in pairs]


class C1NoGateAnywhere(unittest.TestCase):
    """Nothing waits on the operator for an apex to carry a surface."""

    def test_an_apex_with_ordinary_members_ALREADY_has_a_surface(self):
        got = surface_of(_plain(("s2", "a longer claim about the cone"), ("s1", "short one")))
        self.assertIsNotNone(got, "an apex needed a signature to be called anything")
        self.assertEqual(got.rank, SHORTEST)

    def test_there_is_no_PENDING_state_to_be_in(self):
        """PLANTED: the state should not exist. A rank outside the declared four would be one.

        AST, NOT GREP — for the third time in this project a control written this way convicted
        the docstring that STATES the property it enforces. This module's prose says "no offer,
        no signature, no ceremony", and a text scan reads that as the ceremony being present.
        What must not exist is a NAME: a rank, a field or a branch called any of these.
        """
        got = surface_of(_plain(("s1", "a claim")))
        self.assertIn(got.rank, RANKS)
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  for t in n.targets if isinstance(t, ast.Name)}
        for banned in ("pending", "nomination", "signature", "claimed", "awaiting", "offer"):
            self.assertNotIn(banned, {x.lower() for x in names},
                             f"a gate survived in the surface rule as a name: {banned}")
        self.assertEqual(set(RANKS), {AUTHORED, KERNEL, GLOSS, SHORTEST})

    def test_only_an_EMPTY_apex_has_no_surface_and_that_is_not_an_apex(self):
        self.assertIsNone(surface_of([]))
        self.assertIsNone(surface_of(None))


class C2TheRuleIsATotalOrderNotAScore(unittest.TestCase):
    def test_the_four_ranks_apply_in_the_declared_order(self):
        base = _plain(("s2", "a longer claim about the cone"), ("s1", "short one"))
        self.assertEqual(surface_of(base).rank, SHORTEST)

        glossed = surface_of(base, glosses={"s1": _G("the cone is positive")})
        self.assertEqual(glossed.rank, GLOSS)
        self.assertEqual(glossed.text, "the cone is positive")

        kernel = base + [_M("s3", "KERNEL", "\x01lean\x01theorem cone_positive : X")]
        self.assertEqual(surface_of(kernel, glosses={"s1": _G("x")}).rank, KERNEL)

        authored = kernel + [_M("s0", "AUTHORSHIP", "\x01en\x01the operator's own words")]
        self.assertEqual(surface_of(authored, glosses={"s1": _G("x")}).rank, AUTHORED)

    def test_the_same_membership_yields_the_SAME_surface_every_time(self):
        members = _plain(("s3", "gamma claim"), ("s1", "alpha claim"), ("s2", "beta claim"))
        first = surface_of(members)
        for _ in range(5):
            self.assertEqual(surface_of(list(reversed(members))), first,
                             "the surface depends on iteration order, so it is not byte-stable")

    def test_a_tie_inside_a_rank_breaks_by_SLOT_not_by_arrival(self):
        """Two members of equal length would otherwise resolve by whichever the loop reached
        first, and a surface that depends on that is not stable across processes."""
        members = _plain(("s9", "aaa bbb"), ("s1", "ccc ddd"))
        self.assertEqual(surface_of(members).slot, "s1")
        self.assertEqual(surface_of(list(reversed(members))).slot, "s1")

    def test_no_scoring_and_no_similarity_in_the_module(self):
        """AST for the names, text only for the operations a name cannot hide."""
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for banned in ("score", "weight", "rank_score", "similarity", "distance", "lower",
                       "casefold"):
            self.assertNotIn(banned, {x.lower() for x in names},
                             f"the surface rule gained a {banned}")
        src = MODULE.read_text(encoding="utf-8")
        for banned in ("difflib", "SequenceMatcher", "levenshtein", "jaccard"):
            self.assertNotIn(banned, src, f"the surface rule imported {banned}")

    def test_no_LM_call_at_read_time(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else
                  getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for banned in ("complete", "LMClient", "perturb", "converse", "transport"):
            self.assertNotIn(banned, called, f"the surface rule called {banned}")


class C3TheTwoMouthLawStillBindsSLOTS(unittest.TestCase):
    """The ruling touched vocabulary SURFACES. A surface is what an apex is called; a slot is a
    claim the corpus holds, and only the second was ever the two-mouth law's business."""

    def test_the_surface_rule_creates_no_slot_no_arrow_no_delta(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else
                  getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for banned in ("propose", "extract", "mint", "promote", "commit", "SlotRecord",
                       "Correspondence", "Delta", "Scaffold", "add"):
            self.assertNotIn(banned, called, f"the surface rule called {banned}")

    def test_the_mint_attempt_control_still_stands(self):
        """Re-asserted post-change: the fourth door's tombstone is unaffected by the ruling."""
        from engine.synthesis import SYNTHESIS_CANDIDATE, synthesis_candidates

        verdict = {"violations": [{"kind": "welded", "numbers": ["e3", "l4"],
                                   "sentence": "These jointly imply X."}]}
        got = synthesis_candidates(verdict, {"citations": [
            {"n": "e3", "kind": "seated", "slot": "s1", "group": "g1"},
            {"n": "l4", "kind": "seated", "slot": "s2", "group": "g2"}]}, turn=1)
        self.assertEqual(len(got), 1)
        rec = got[0].as_record()
        self.assertEqual(rec["kind"], SYNTHESIS_CANDIDATE)
        self.assertIsNone(rec["warrant"])
        self.assertIn("nothing", rec["entered"])


class C4NoCodePathTreatsAMediumCoinageSpecially(unittest.TestCase):
    """VOCABULARY ADOPTION IS BY USE, which is not a mechanism and must not become one.

    A term the medium coins is ordinary testimony. If the operator re-uses it, it enters as
    THEIR record through the normal inlet, because they said it. There is nothing to build, and
    this is the assertion that keeps it that way.
    """

    def test_the_ceremony_is_GONE_from_where_it_LIVED(self):
        """Scoped to the two modules that held it. A repo-wide scan is wrong here and proved
        it: `engine/medium.py` has its own `terms_from`, which reads the load-bearing
        vocabulary off FIBER STRUCTURE and has nothing to do with the deleted nomination — a
        control that cannot tell two functions apart by their name alone is a control that
        will eventually delete the wrong one."""
        for module in ("synthesis.py", "dialogue.py"):
            src = (ENGINE / module).read_text(encoding="utf-8")
            for name in ("NAME_FORM", "TERM_CANDIDATE", "def stress(", "class Lexicon",
                         "def inform(", "_harvest"):
                with self.subTest(module=module, name=name):
                    self.assertNotIn(name, src,
                                     f"{name} survived the doorless ruling in {module}")

    def test_the_UNRELATED_terms_from_in_medium_py_is_untouched(self):
        """Named so nobody re-broadens the scan above and deletes it by mistake."""
        from engine.medium import terms_from as medium_terms

        self.assertTrue(callable(medium_terms))
        self.assertIn("fiber", (medium_terms.__doc__ or "").lower())

    def test_no_engine_module_carries_a_signature_gate_for_vocabulary(self):
        for path in sorted(ENGINE.glob("*.py")):
            src = path.read_text(encoding="utf-8").lower()
            for banned in ("awaiting signature", "pending nomination", "claim_gesture",
                           "operator_signature"):
                with self.subTest(module=path.name, banned=banned):
                    self.assertNotIn(banned, src)

    def test_the_lexical_residual_SURVIVED_the_deletion(self):
        """Measurement pressure stays; only the ceremony downstream of it went."""
        from engine.synthesis import apexless, lexical_question

        compiled = {"citations": [
            {"n": "l1", "kind": "moved", "slot": "s2", "group": "s2"},
            {"n": "l2", "kind": "moved", "slot": "s9", "group": "s2"}]}
        ident, members = apexless(compiled, set())
        self.assertEqual(ident, ("lex", "s2"))
        q = lexical_question(members)
        self.assertIn("[l1]", q)
        self.assertIn("[∅]", q, "the question must still offer its own legal exit")
        self.assertNotIn("NAME", q, "the NAME ceremony survived in the question")


if __name__ == "__main__":
    unittest.main()
