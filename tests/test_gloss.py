"""THE LEXICON LANE's controls, c1-c11, planted as the spec numbered them.

What they are all one control for: A GLOSS IS AN ANNOTATION, NOT AN OBJECT, and it is found by
exact whole-string membership or not at all. Every other property here is a way for one of those
two to fail quietly — a fragment match creeping into the lookup, or a handle acquiring a label,
a group, or a vote.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.gloss import (AUTHORED, GLOSSED_CHART, RENDERED, UNAUTHORED_TAG, Gloss,
                          authored_faces, coverage, gloss_for, glosses_for)
from engine.region import Member, Region, render_region

MODULE = Path(__file__).resolve().parents[1] / "engine" / "gloss.py"
LEAN_NU = "\x01lean\x01theorem true_kernel_grid_posdef : IsPDq M"


def _region():
    return Region(clamp="s1", members=[
        Member(index=0, slot="s1", chart="english", type="assert",
               nu="\x01en\x01the true kernel grid is positive definite", attached=False),
        Member(index=1, slot="s2", chart="lean", type="assert", nu=LEAN_NU, attached=False),
        Member(index=2, slot="s3", chart="lean", type="assert",
               nu="\x01lean\x01-- a comment declaring nothing", attached=False)])


class C1NoSimilarityAnywhere(unittest.TestCase):
    def test_the_module_holds_no_tokenizer_no_distance_no_case_folding(self):
        src = MODULE.read_text(encoding="utf-8")
        for banned in ("[a-z0-9]+", "[a-zA-Z]+", "\\w+", ".lower()", ".casefold()", "difflib",
                       "SequenceMatcher", "levenshtein", "jaccard", "startswith(", "endswith(",
                       " in name", "fuzzy", "score"):
            self.assertNotIn(banned, src, f"a similarity path reached the lane: {banned}")

    def test_the_lookup_is_a_DICT_HIT_and_nothing_else(self):
        """AST: the authored lookup may index a mapping. It may not iterate one comparing
        keys, which is where a fragment match would have to live."""
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for banned in ("find", "index", "split", "replace", "strip", "lower", "casefold"):
            self.assertNotIn(banned, called, f"the lookup called {banned}")


class C2CaseSensitivity(unittest.TestCase):
    def test_a_name_differing_only_in_CASE_does_not_hit_the_authored_face(self):
        """Mathlib names keep their case on purpose — `lexicon.Face` stores a surface verbatim.
        Folding here would be the matching this lane exists to avoid."""
        faces = {"true_kernel_grid_posdef": "the authored reading"}
        self.assertEqual(gloss_for(LEAN_NU, faces).tier, AUTHORED)
        wrong = {"True_Kernel_Grid_PosDef": "the authored reading"}
        self.assertIsNone(gloss_for(LEAN_NU, wrong),
                          "a case variant hit the authored face")
        # AND WITH TIER B ASKED FOR EXPLICITLY, so the miss is shown to be a miss rather than
        # the withdrawal swallowing it: the case variant lands on the rendering, not the face.
        got = gloss_for(LEAN_NU, wrong, rendered=True)
        self.assertEqual(got.tier, RENDERED, "a case variant hit the authored face")


class C3ResolveOrVoid(unittest.TestCase):
    def test_a_line_declaring_NO_NAME_gets_no_gloss(self):
        self.assertIsNone(gloss_for("\x01lean\x01-- a comment declaring nothing"))
        self.assertIsNone(gloss_for(""))

    def test_an_unauthored_name_falls_to_the_RENDERING_and_says_so(self):
        got = gloss_for(LEAN_NU, {}, rendered=True)
        self.assertEqual(got.tier, RENDERED)
        self.assertIn(UNAUTHORED_TAG, got.line)

    def test_an_authored_face_does_NOT_wear_the_unauthored_tag(self):
        got = gloss_for(LEAN_NU, {"true_kernel_grid_posdef": "the authored reading"})
        self.assertNotIn(UNAUTHORED_TAG, got.line)
        self.assertIn("the authored reading", got.line)


class C4TheGroupFieldIsNeverTouched(unittest.TestCase):
    """THE SHARPEST RISK. A gloss reaching `Citable.group` would forge a fiber — the weld rule
    licenses co-citation inside a group, so a fabricated group licenses a fabricated relation."""

    def test_the_module_never_READS_OR_WRITES_a_group(self):
        """AST, not grep. The first version searched the source text and convicted the
        docstring sentence that says the lane never touches a group — a control convicting the
        prose that states the property it enforces, which is the trap class one layer in."""
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for banned in ("group", "fiber", "fibers", "contested", "value", "tier_of"):
            self.assertNotIn(banned, attrs, f"the lane reached for .{banned}")
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for banned in ("Citable", "apex_id", "is_apex"):
            self.assertNotIn(banned, names, f"the lane named {banned}")

    def test_a_gloss_records_that_it_ENTERED_NOTHING(self):
        rec = gloss_for(LEAN_NU, {}, rendered=True).as_record()
        self.assertFalse(rec["citable"])
        self.assertIn("nothing", rec["entered"])


class C5OneInletAndNoMint(unittest.TestCase):
    def test_no_code_path_here_creates_a_slot_an_arrow_or_a_delta(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else
                  getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for banned in ("propose", "extract", "mint", "promote", "commit", "Correspondence",
                       "SlotRecord", "Delta", "Scaffold", "clamp", "Clamp"):
            self.assertNotIn(banned, called, f"the lane called {banned}")


class C6TheWalksWireIsUNCHANGED(unittest.TestCase):
    """Checklist item (e) of the convergence baseline, which outranks this lane."""

    def test_the_default_render_is_INVARIANT_to_the_glosses(self):
        r = _region()
        self.assertEqual(render_region(r), render_region(r, glosses=None))
        self.assertNotIn("reads as", render_region(r),
                         "the unattended walk's wire gained a dialogue-only handle")

    def test_the_gloss_appears_only_when_ASKED_FOR(self):
        r = _region()
        wire = render_region(r, glosses=glosses_for(r, {}, rendered=True))
        self.assertIn("reads as", wire)
        self.assertIn(UNAUTHORED_TAG, wire)


class C7ItIsAnANNOTATIONNotAnObject(unittest.TestCase):
    def test_the_gloss_line_carries_NO_LABEL(self):
        import re

        r = _region()
        wire = render_region(r, glosses=glosses_for(r, {}, rendered=True))
        self.assertIn("reads as", wire, "the control inspected a wire with no glosses on it")
        for line in wire.splitlines():
            if "reads as" in line:
                self.assertIsNone(re.match(r"\s*\[[a-z]?\d+\]", line),
                                  f"a gloss line looks like a citable object: {line!r}")

    def test_the_object_count_is_unchanged_by_glossing(self):
        import re

        r = _region()
        bare = len(re.findall(r"^\[[a-z]?\d+\]", render_region(r), re.M))
        glossed = len(re.findall(
            r"^\[[a-z]?\d+\]",
            render_region(r, glosses=glosses_for(r, {}, rendered=True)), re.M))
        self.assertEqual(bare, glossed, "glossing changed how many objects were shown")


class C8OnlyTheGlossedChart(unittest.TestCase):
    def test_an_english_member_is_never_glossed(self):
        got = glosses_for(_region(), {}, rendered=True)
        self.assertNotIn("s1", got, "an english object was glossed")
        self.assertIn("s2", got)
        self.assertEqual(GLOSSED_CHART, "lean")


class C9CoverageTravels(unittest.TestCase):
    """MANDATORY. Flat attachment over zero authored coverage is a fact about the DATA."""

    def test_coverage_splits_authored_from_rendered(self):
        r = _region()
        c = coverage(r, glosses_for(r, {"true_kernel_grid_posdef": "authored"}))
        self.assertEqual((c["shown"], c["glossed"], c["authored"], c["rendered"]), (2, 1, 1, 0))
        self.assertEqual(c["authored_fraction"], 0.5)

    def test_zero_authored_coverage_is_VISIBLE_not_absent(self):
        r = _region()
        c = coverage(r, glosses_for(r, {}, rendered=True))
        self.assertEqual(c["glossed"], 1, "the control read a coverage row with nothing in it")
        self.assertEqual(c["authored"], 0)
        self.assertEqual(c["authored_fraction"], 0.0)
        self.assertIn("DATA", c["note"])


class C10ImportProvenance(unittest.TestCase):
    def test_an_absent_registry_is_a_COVERAGE_fact_not_a_crash(self):
        from engine.inbound import lexicon_registry

        self.assertEqual(authored_faces(None), {})
        self.assertIsNotNone(lexicon_registry())

    def test_authored_faces_reads_only_FORMAL_surfaces_as_keys(self):
        class _F:
            def __init__(self, kind, surface):
                self.kind, self.surface = kind, surface

        class _C:
            lemma = "positive definite"
            formal_faces = (_F("formal", "IsPDq"), _F("english", "is positive definite"))

        class _S:
            core = _C()

        class _R:
            senses = [_S()]

        self.assertEqual(authored_faces(_R()), {"IsPDq": "is positive definite"})


class C11AGlossDoesNotSILENCETheLexicalResidual(unittest.TestCase):
    """THE FOURTH DOOR'S FIRST REGRESSION, if it happened — planted so it cannot.

    `synthesis.named()` decides whether a declared cluster already has an apex name, and an
    unnamed cluster becomes an interrogation. A GLOSS IS NOT AN APEX NAME: it is a reading of
    one Lean declaration, not a name for a proposition the field says several claims share. If
    a gloss could satisfy `named()`, the lexical residual would go quiet exactly where the
    vocabulary gap is real.
    """

    def test_a_glossed_cluster_with_no_apex_STILL_raises_the_residual(self):
        from engine.synthesis import apexless

        # REACHED KINDS. `apexless` is scoped to what THIS perturbation touched, by the same
        # law the contested residual obeys — a cluster nothing reached is a fact about the
        # corpus, not a residual this question raised. A `seated` fixture raises nothing and
        # would have made this control pass for the wrong reason.
        compiled = {"citations": [
            {"n": "l1", "kind": "moved", "slot": "s2", "group": "s2"},
            {"n": "l2", "kind": "moved", "slot": "s9", "group": "s2"}]}
        ident, members = apexless(compiled, set())
        self.assertEqual(ident, ("lex", "s2"),
                         "a declared cluster with no apex stopped raising a residual")
        self.assertEqual(members, ("l1", "l2"))

    def test_named_does_not_consult_the_gloss_lane_at_all(self):
        """AST on the fourth door: `named` reads the gloss REGISTRY (fiber labels) and must not
        gain a path to this lane's per-declaration handles."""
        src = (Path(__file__).resolve().parents[1] / "engine" / "synthesis.py").read_text(
            encoding="utf-8")
        for banned in ("from .gloss", "import gloss", "gloss_for", "glosses_for"):
            self.assertNotIn(banned, src, f"the fourth door reached the lexicon lane: {banned}")


class C12TierBIsOffByDefaultBYMEASUREMENT(unittest.TestCase):
    """THE WITHDRAWAL, planted so it cannot be undone by accident.

    Tier B was specified, built, and measured, and the measurement withdrew it. Local A/B on
    one commit with the lane as the only variable, authored coverage 0%:

        lane OFF   attachment 8 of 59   discrimination 0.1356    0 violations
        lane ON    attachment 2 of 59   discrimination 0.0339   17 violations

    Lean attachment stayed 0 in BOTH arms at coverage 19 of 19, fraction 1.0. Nineteen
    mechanical readings bridged nothing and pushed attachment toward the empty pole. Nothing is
    deleted — tier A runs unchanged the day authored faces exist, and tier B stays reachable
    behind an explicit argument so the next person measures it rather than re-deriving it.
    """

    def test_an_unauthored_name_gets_NOTHING_unless_the_caller_asks(self):
        self.assertIsNone(gloss_for(LEAN_NU, {}))
        self.assertIsNone(gloss_for(LEAN_NU, None))
        self.assertEqual(glosses_for(_region(), {}), {})

    def test_an_AUTHORED_face_is_unaffected_by_the_withdrawal(self):
        """What was withdrawn is the mechanical rendering, not the lane."""
        faces = {"true_kernel_grid_posdef": "the authored reading"}
        self.assertEqual(gloss_for(LEAN_NU, faces).tier, AUTHORED)
        self.assertEqual(set(glosses_for(_region(), faces)), {"s2"})

    def test_the_default_is_a_DEFAULT_not_a_deletion(self):
        """AST on the signature: tier B is reachable, and its gate is a parameter defaulting
        to False — not a removed branch, and not a constant somebody has to edit."""
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        seen = {}
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef) and fn.name in ("gloss_for", "glosses_for"):
                args = fn.args.args
                self.assertEqual(args[-1].arg, "rendered", f"{fn.name} lost its tier-B gate")
                default = fn.args.defaults[-1]
                self.assertIsInstance(default, ast.Constant)
                self.assertIs(default.value, False, f"{fn.name} re-enabled tier B by default")
                seen[fn.name] = True
        self.assertEqual(set(seen), {"gloss_for", "glosses_for"})

    def test_the_withdrawal_carries_its_MEASUREMENT_in_the_module_itself(self):
        """A default with no number beside it is a preference. These are the two figures the
        A/B turned on, and the coverage fraction that makes them readable."""
        doc = ast.get_docstring(ast.parse(MODULE.read_text(encoding="utf-8"))) or ""
        for figure in ("0.1356", "0.0339", "19 of 19"):
            self.assertIn(figure, doc, f"the withdrawal dropped its measurement: {figure}")


if __name__ == "__main__":
    unittest.main()
