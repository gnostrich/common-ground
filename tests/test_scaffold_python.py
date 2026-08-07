"""DEPENDS_ON for the Python chart: `ast`-driven, every control exercising the real runtime.

Mirrors `tests/test_scaffold.py` (the Lean battery). Each PLANTED test constructs the exact
scenario a naive or regressed implementation would get wrong, and asserts the real module
gets it right — a test that only ever calls the correct path proves nothing about the guard.
"""

import unittest

from engine.scaffold import DEPENDS_ON, REFERENCE_TIER, SCAFFOLD_KINDS, Scaffold, holonomy_excluded
from engine.scaffold_python import (bound_names, declaration_index, declared_name, parse,
                                    references)


class _Rec:
    def __init__(self, nu, chart="python", type_="define"):
        self.nu, self.chart, self.type, self.docs = nu, chart, type_, ("f.py",)


class _Snap:
    def __init__(self, m):
        self.slots = {k: _Rec(v) for k, v in m.items()}
        self.arrows = []


class ItIsNotACorrespondenceAndCannotBeMisKinded(unittest.TestCase):
    """The containment lesson, enforced by the type system, not a rule someone remembers."""

    def test_a_dependency_cannot_be_stored_as_an_equivalence_kind(self):
        for bad in ("same_claim", "refines", "instance_of"):
            with self.assertRaises(ValueError):
                Scaffold(chart="python", src_slot="a", dst_slot="b", kind=bad)

    def test_an_intra_chart_correspondence_is_still_refused(self):
        from engine.correspondence import Correspondence
        with self.assertRaises(Exception):
            Correspondence(src_chart="python", src_slot="a", dst_chart="python", dst_slot="b",
                           kind="same_claim")

    def test_a_python_scaffold_edge_carries_the_python_chart_and_reference_tier(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1)"})
        edges = parse(snap).edges
        self.assertEqual(1, len(edges))
        self.assertEqual("python", edges[0].chart)
        self.assertEqual(DEPENDS_ON, edges[0].kind)
        self.assertEqual(REFERENCE_TIER, edges[0].tier)

    def test_the_kind_family_is_closed(self):
        # TWO MEMBERS NOW, and the family is still CLOSED — which is what this asserts. A new
        # member needs its own ruling in seed/SCAFFOLD.md before it appears here; what the
        # control refuses is a kind arriving in code with no declaration behind it.
        from engine.scaffold import FORKED_FROM

        self.assertEqual({DEPENDS_ON, FORKED_FROM}, set(SCAFFOLD_KINDS))


class ItIsHolonomyEXCLUDEDByConstruction(unittest.TestCase):

    def test_a_python_scaffold_has_no_loop_eligibility_to_set_wrongly(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1)"})
        edge = parse(snap).edges[0]
        self.assertFalse(hasattr(edge, "loop_eligible"))
        self.assertTrue(holonomy_excluded(edge))

    def test_a_loop_computed_over_python_scaffolds_finds_nothing(self):
        # PLANTED: feed scaffolds where correspondences are expected. `loop_pairs` reads
        # `loop_eligible`, which a Scaffold does not have, so it raises rather than silently
        # contributing zero pairs and reading as a clean floor.
        from engine.correspondence import loop_pairs
        s = Scaffold(chart="python", src_slot="a", dst_slot="b")
        with self.assertRaises(AttributeError):
            loop_pairs([s])


class ResolveOrVoid(unittest.TestCase):

    def test_a_reference_to_a_declared_name_resolves(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1)"})
        p = parse(snap)
        self.assertEqual(1, len(p.edges))
        self.assertEqual(("t", "d"), p.edges[0].pair)
        self.assertEqual("helper", p.edges[0].symbol)

    def test_an_undeclared_reference_is_VOID_not_a_dangling_edge(self):
        snap = _Snap({"t": "\x01py\x01def caller(): return numpy.array(1)"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(r == "undeclared" for _, _, r in p.void))

    def test_an_AMBIGUOUS_name_is_VOID_never_resolved_to_the_first(self):
        # Picking one would be a similarity mechanism wearing a parser's clothes.
        snap = _Snap({"a": "\x01py\x01def dup(): return 1",
                      "b": "\x01py\x01def dup(): return 2",
                      "t": "\x01py\x01def caller(): return dup()"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(r == "ambiguous" for _, _, r in p.void))

    def test_voids_are_COUNTED_with_their_reasons(self):
        snap = _Snap({"t": "\x01py\x01def caller(): return missing_thing(1)"})
        rec = parse(snap).as_record()
        self.assertGreater(rec["void"], 0)
        self.assertIn("undeclared", rec["void_by_reason"])
        self.assertIn("resolution_rate", rec)

    def test_a_declaration_never_depends_on_itself(self):
        snap = _Snap({"d": "\x01py\x01def rec(n): return rec(n - 1)"})
        self.assertEqual([], parse(snap).edges)

    def test_a_repeated_reference_makes_ONE_edge(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1) + helper(2) + helper(3)"})
        self.assertEqual(1, len(parse(snap).edges))


class NoInferenceOnlyParse(unittest.TestCase):

    def test_a_NEAR_MISS_name_does_not_resolve(self):
        # PLANTED SIMILARITY: `helpers` is not `helper`. An edit-distance or prefix matcher
        # would join them; exact declared-name matching does not.
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helpers(1)"})
        self.assertEqual([], parse(snap).edges)

    def test_the_module_holds_no_similarity_machinery_and_no_regex(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" /
               "scaffold_python.py").read_text()
        for banned in ("difflib", "SequenceMatcher", "levenshtein", "ratio(", "startswith(name",
                       ".lower()", "casefold", "import re", "\nimport re\n"):
            self.assertNotIn(banned, src, f"inference (or regex) is back: {banned}")

    def test_a_line_declaring_nothing_yields_no_name(self):
        self.assertEqual("", declared_name("\x01py\x01x = 1"))
        self.assertEqual("", declared_name("\x01py\x01# just a comment"))

    def test_the_declarer_forms_are_asts_own_grammar_not_a_line_shape_guess(self):
        self.assertEqual("foo", declared_name("\x01py\x01def foo(x): return x"))
        self.assertEqual("Bar", declared_name("\x01py\x01class Bar: pass"))
        self.assertEqual("afoo", declared_name("\x01py\x01async def afoo(): pass"))

    def test_a_parameter_shadowing_a_declared_name_is_never_a_spurious_reference(self):
        # PLANTED SHADOW: if bound-name exclusion were shape-based (e.g. "skip words that
        # look like locals") rather than reading `ast`'s own Store/Load contexts, a parameter
        # literally named after a declared function would either wrongly resolve to it (a
        # self-shadowing false edge) or leak through some other guess. It must do neither:
        # the parameter binds the name, structurally, so the body's use of it never becomes
        # a reference candidate at all.
        snap = _Snap({"helper_def": "\x01py\x01def helper(): return 1",
                      "t": "\x01py\x01def caller(helper): return helper"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertEqual(0, p.symbols)


class BoundNamesAreExcludedStructurally(unittest.TestCase):
    """Read off `ast`'s own binding forms — the Lean scaffold's `PXV` lesson, ast-native."""

    def test_a_function_parameter_is_bound_not_referenced(self):
        import ast
        tree = ast.parse("def f(x, y): return x + y")
        node = tree.body[0]
        self.assertEqual({"x", "y"}, bound_names(node))
        self.assertEqual([], references(node))

    def test_an_assignment_target_is_bound_not_referenced(self):
        import ast
        tree = ast.parse("def f(): total = compute(); return total")
        node = tree.body[0]
        self.assertIn("total", bound_names(node))
        self.assertIn("compute", references(node))
        self.assertNotIn("total", references(node))

    def test_a_for_loop_target_is_bound(self):
        import ast
        tree = ast.parse("def f(items):\n    for item in items:\n        use(item)")
        node = tree.body[0]
        self.assertIn("item", bound_names(node))
        refs = references(node)
        self.assertIn("use", refs)
        self.assertNotIn("item", refs)

    def test_WITHOUT_the_bound_name_filter_the_planted_defect_would_leak(self):
        # PLANTED: this constructs the UNFILTERED reference list directly (skipping
        # `bound_names`) to show what the module would produce if the exclusion were
        # removed — the parameter WOULD show up as a bare reference, and it does here,
        # proving the control in the module (which filters it) is doing real work.
        import ast
        from engine.scaffold_python import _References
        tree = ast.parse("def f(x): return x")
        unfiltered = _References(bound=set())
        unfiltered.visit(tree.body[0])
        self.assertIn("x", unfiltered.refs)
        # ... and the real, filtered path does not:
        self.assertNotIn("x", references(tree.body[0]))


class PrefixRecoveryUsesOnlyASTsOwnSignal(unittest.TestCase):
    """`nu` flattens every declaration to one line; most multi-statement bodies stop being
    valid Python. This is the module's central engineering fact, exercised directly."""

    def test_a_single_statement_body_parses_whole(self):
        self.assertEqual("f", declared_name("\x01py\x01def f(x): return x"))

    def test_a_multi_statement_body_recovers_a_PREFIX_via_the_compilers_own_error(self):
        # Two statements run together with no separator — invalid as a whole — but the
        # declared name and the first statement's reference are still recoverable because
        # they occur before the point the compiler first objects.
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): z = helper(1) return z"})
        p = parse(snap)
        self.assertEqual(1, len(p.edges))
        self.assertEqual("helper", p.edges[0].symbol)

    def test_content_AFTER_the_break_is_not_examined_not_guessed(self):
        # The reference sits AFTER the point recovery gives up: it is absent, not wrong.
        # This is the honest under-reporting direction, not a defect being covered up.
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): z = 1 return helper(z)"})
        p = parse(snap)
        self.assertEqual([], p.edges)

    def test_a_body_with_no_parseable_prefix_at_all_is_VOID_unparseable(self):
        snap = _Snap({"d": "\x01py\x01)))(((:::garbage"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertEqual([("d", "", "unparseable")], p.void)

    def test_PLANTED_a_naive_whole_body_only_parser_would_lose_this_edge(self):
        # PLANTED: proves the recovery loop is load-bearing. A direct `ast.parse` of the
        # full flattened body raises for this input (asserted here) — yet the module still
        # produces the edge, which is only possible because of the prefix-recovery step.
        import ast
        body = "def caller(): z = helper(1) return z"
        with self.assertRaises(SyntaxError):
            ast.parse(body)
        snap = _Snap({"d": "\x01py\x01def helper(x): return x", "t": "\x01py\x01" + body})
        self.assertEqual(1, len(parse(snap).edges))

    def test_unparseable_slots_are_excluded_from_the_declaration_index(self):
        # A declaration this module cannot recover a name for cannot be a resolution target
        # either — an invented name would be a fabrication, not a recovery.
        snap = _Snap({"garbage": "\x01py\x01)))(((:::",
                      "t": "\x01py\x01def caller(): return garbage(1)"})
        index, _ = declaration_index(snap)
        self.assertNotIn("garbage", index)


class ImportsResolveLikeAnyOtherReference(unittest.TestCase):

    def test_from_import_resolves_when_the_imported_name_is_declared(self):
        snap = _Snap({"d": "\x01py\x01def target(): pass",
                      "t": "\x01py\x01def caller(): from mypkg import target return target()"})
        p = parse(snap)
        self.assertEqual(1, len(p.edges))
        self.assertEqual("target", p.edges[0].symbol)

    def test_bare_import_of_an_undeclared_module_is_VOID(self):
        # This corpus addresses definitions, never modules — `import os` can only ever void.
        snap = _Snap({"t": "\x01py\x01def caller(): import os return 1"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(sym == "os" and reason == "undeclared" for _, sym, reason in p.void))

    def test_star_import_names_no_specific_symbol(self):
        snap = _Snap({"t": "\x01py\x01def caller(): from mypkg import * return 1"})
        p = parse(snap)
        self.assertNotIn("*", [sym for _, sym, _ in p.void])


class ReproducibleAndEraTagged(unittest.TestCase):

    def test_re_parsing_the_same_material_is_a_no_op(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1)"})
        a = [e.as_record() for e in parse(snap, era="e1").edges]
        b = [e.as_record() for e in parse(snap, era="e1").edges]
        self.assertEqual(a, b)

    def test_the_era_travels_on_every_edge(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1)"})
        self.assertEqual("py-v0", parse(snap, era="py-v0").edges[0].era)

    def test_a_changed_source_is_a_NEW_era_not_a_silent_mutation(self):
        snap = _Snap({"d": "\x01py\x01def helper(x): return x",
                      "t": "\x01py\x01def caller(): return helper(1)"})
        self.assertNotEqual(parse(snap, era="e1").edges[0].era,
                            parse(snap, era="e2").edges[0].era)


class CompositionIsSeededAndNarrow(unittest.TestCase):

    def _table(self):
        import json
        from pathlib import Path
        return json.loads((Path(__file__).resolve().parent.parent / "seed" /
                           "COMPOSITION.json").read_text())

    def test_depends_on_composes_with_itself_transitively(self):
        self.assertEqual("depends_on", self._table()["compose"]["depends_on"]["depends_on"])

    def test_cross_composition_with_every_equivalence_kind_is_UNDEFINED(self):
        table = self._table()
        undefined = " ".join(str(x) for x in table.get("undefined", []))
        for k in ("same_claim", "refines", "instance_of"):
            self.assertIn(f"depends_on o {k}", undefined)
            self.assertIn(f"{k} o depends_on", undefined)


if __name__ == "__main__":
    unittest.main()
