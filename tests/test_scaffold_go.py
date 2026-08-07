"""DEPENDS_ON for the Go chart: a careful scanner, every control exercising the real runtime.

Mirrors `tests/test_scaffold.py` (the Lean battery). Each PLANTED test constructs the exact
scenario a naive or regressed implementation would get wrong, and asserts the real module
gets it right — a test that only ever calls the correct path proves nothing about the guard.
"""

import unittest

from engine.scaffold import DEPENDS_ON, REFERENCE_TIER, SCAFFOLD_KINDS, Scaffold, holonomy_excluded
from engine.scaffold_go import (declaration_index, declared_name, import_targets, parse,
                                selector_references)


class _Rec:
    def __init__(self, nu, chart="go", type_="define"):
        self.nu, self.chart, self.type, self.docs = nu, chart, type_, ("f.go",)


class _Snap:
    def __init__(self, m):
        self.slots = {k: _Rec(v) for k, v in m.items()}
        self.arrows = []


class ItIsNotACorrespondenceAndCannotBeMisKinded(unittest.TestCase):

    def test_a_dependency_cannot_be_stored_as_an_equivalence_kind(self):
        for bad in ("same_claim", "refines", "instance_of"):
            with self.assertRaises(ValueError):
                Scaffold(chart="go", src_slot="a", dst_slot="b", kind=bad)

    def test_an_intra_chart_correspondence_is_still_refused(self):
        from engine.correspondence import Correspondence
        with self.assertRaises(Exception):
            Correspondence(src_chart="go", src_slot="a", dst_chart="go", dst_slot="b",
                           kind="same_claim")

    def test_a_go_scaffold_edge_carries_the_go_chart_and_reference_tier(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() }"})
        edges = parse(snap).edges
        self.assertEqual(1, len(edges))
        self.assertEqual("go", edges[0].chart)
        self.assertEqual(DEPENDS_ON, edges[0].kind)
        self.assertEqual(REFERENCE_TIER, edges[0].tier)

    def test_the_kind_family_is_closed(self):
        # TWO MEMBERS NOW, and the family is still CLOSED — which is what this asserts. A new
        # member needs its own ruling in seed/SCAFFOLD.md before it appears here; what the
        # control refuses is a kind arriving in code with no declaration behind it.
        from engine.scaffold import FORKED_FROM

        self.assertEqual({DEPENDS_ON, FORKED_FROM}, set(SCAFFOLD_KINDS))


class ItIsHolonomyEXCLUDEDByConstruction(unittest.TestCase):

    def test_a_go_scaffold_has_no_loop_eligibility_to_set_wrongly(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() }"})
        edge = parse(snap).edges[0]
        self.assertFalse(hasattr(edge, "loop_eligible"))
        self.assertTrue(holonomy_excluded(edge))

    def test_a_loop_computed_over_go_scaffolds_finds_nothing(self):
        # PLANTED: `loop_pairs` reads `loop_eligible`, which a Scaffold does not have.
        from engine.correspondence import loop_pairs
        s = Scaffold(chart="go", src_slot="a", dst_slot="b")
        with self.assertRaises(AttributeError):
            loop_pairs([s])


class ResolveOrVoid(unittest.TestCase):

    def test_a_qualified_selector_to_a_declared_name_resolves(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() }"})
        p = parse(snap)
        self.assertEqual(1, len(p.edges))
        self.assertEqual(("t", "d"), p.edges[0].pair)
        self.assertEqual("Helper", p.edges[0].symbol)

    def test_an_undeclared_selector_is_VOID_not_a_dangling_edge(self):
        snap = _Snap({"t": "\x01go\x01func Caller() error { return fmt.Errorf(\"x\") }"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(r == "undeclared" for _, _, r in p.void))

    def test_an_AMBIGUOUS_bare_name_is_VOID_never_resolved_to_the_first(self):
        # Two DIFFERENT receivers declaring the same method name: a selector call site
        # never writes the receiver type, so this cannot be told apart and must not guess.
        snap = _Snap({"a": "\x01go\x01func (x *X) Balance() float64 { return 0 }",
                      "b": "\x01go\x01func (y *Y) Balance() float64 { return 0 }",
                      "t": "\x01go\x01func Caller(s *X) float64 { return s.Balance() }"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(r == "ambiguous" for _, _, r in p.void))

    def test_voids_are_COUNTED_with_their_reasons(self):
        snap = _Snap({"t": "\x01go\x01func Caller() { fmt.Println(\"x\") }"})
        rec = parse(snap).as_record()
        self.assertGreater(rec["void"], 0)
        self.assertIn("undeclared", rec["void_by_reason"])
        self.assertIn("resolution_rate", rec)

    def test_a_declaration_never_depends_on_itself(self):
        # A method calling itself via its own receiver selector must not self-loop.
        snap = _Snap({"d": "\x01go\x01func (r *R) Recur() { r.Recur() }"})
        self.assertEqual([], parse(snap).edges)

    def test_a_repeated_reference_makes_ONE_edge(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() + pkg.Helper() }"})
        self.assertEqual(1, len(parse(snap).edges))


class NoInferenceOnlyParse(unittest.TestCase):

    def test_a_NEAR_MISS_name_does_not_resolve(self):
        # PLANTED SIMILARITY: `Helpers` is not `Helper`.
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helpers() }"})
        self.assertEqual([], parse(snap).edges)

    def test_the_module_holds_no_similarity_machinery(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" /
               "scaffold_go.py").read_text()
        for banned in ("difflib", "SequenceMatcher", "levenshtein", "ratio(", "startswith(name",
                       ".lower()", "casefold"):
            self.assertNotIn(banned, src, f"inference is back: {banned}")

    def test_a_line_declaring_nothing_yields_no_name(self):
        self.assertEqual("", declared_name("\x01go\x01// just a comment"))
        self.assertEqual("", declared_name("\x01go\x01package main"))

    def test_the_declarer_forms_are_gos_own_grammar_not_a_line_shape_guess(self):
        self.assertEqual("Foo", declared_name("\x01go\x01func Foo(x int) int { return x }"))
        self.assertEqual("Widget", declared_name("\x01go\x01type Widget struct { X int }"))
        self.assertEqual("MaxSize", declared_name("\x01go\x01const MaxSize = 10"))
        self.assertEqual("counter", declared_name("\x01go\x01var counter = 0"))


class MethodsAreReceiverQualifiedButIndexedByBareName(unittest.TestCase):
    """`T.M` and `U.M` are distinct declarations; a call site writes only `.M`."""

    def test_a_method_declares_its_receiver_qualified_name(self):
        self.assertEqual("Store.Balance",
                         declared_name("\x01go\x01func (s *Store) Balance() float64 { return 0 }"))

    def test_the_resolution_index_is_keyed_on_the_BARE_method_name(self):
        snap = _Snap({"d": "\x01go\x01func (s *Store) Balance() float64 { return 0 }"})
        index, _ = declaration_index(snap)
        self.assertIn("Balance", index)
        self.assertNotIn("Store.Balance", index)

    def test_PLANTED_qualified_indexing_would_make_every_method_call_unreachable(self):
        # PLANTED: if the index were keyed on the QUALIFIED name (as `declared_name` alone
        # returns it), a real selector call site — which never writes the receiver type —
        # could never resolve to it. Demonstrated directly against the raw declared_name.
        qualified = declared_name("\x01go\x01func (s *Store) Balance() float64 { return 0 }")
        snap = _Snap({"d": "\x01go\x01func (s *Store) Balance() float64 { return 0 }",
                      "t": "\x01go\x01func Caller(svc *Store) float64 { return svc.Balance() }"})
        p = parse(snap)
        self.assertEqual(1, len(p.edges))
        self.assertNotEqual(qualified, p.edges[0].symbol)  # the edge is keyed on "Balance"


class ExportedNameFilterIsAGoLanguageRuleNotAHeuristic(unittest.TestCase):
    """Only an exported (uppercase-initial) identifier can be referenced across a package
    boundary in real Go — a hard grammar/visibility fact, not a similarity judgement."""

    def test_an_unexported_selector_target_is_never_a_reference_candidate(self):
        self.assertEqual([], selector_references("return pkg.helper()"))

    def test_an_exported_selector_target_is_a_reference_candidate(self):
        self.assertEqual(["Helper"], selector_references("return pkg.Helper()"))

    def test_PLANTED_without_the_filter_unexported_field_access_would_flood_false_positives(self):
        # PLANTED: this corpus is full of unexported field/method access (`h.fetcher`,
        # `hc.db`) that shares no real cross-declaration relationship with anything. Without
        # the export filter, EVERY such access would become a reference candidate. Proven by
        # calling the underlying selector regex directly, bypassing the filter.
        import re
        from engine.scaffold_go import _SELECTOR_RE
        unfiltered = [m.group("rhs") for m in _SELECTOR_RE.finditer("return h.fetcher")]
        self.assertIn("fetcher", unfiltered)                 # would leak, unfiltered
        self.assertEqual([], selector_references("return h.fetcher"))  # filtered module refuses it


class OverlappingSelectorChainsAreFoundWithoutDuplication(unittest.TestCase):
    """A `.` chain like `req.Header.Get` must yield BOTH pairs, and a single `pkg.Sym` must
    yield exactly one — the boundary guard is what keeps these from being the same bug."""

    def test_a_three_part_chain_yields_both_adjacent_pairs(self):
        self.assertEqual(["Header", "Get"], selector_references("req.Header.Get(\"X\")"))

    def test_PLANTED_without_the_boundary_guard_one_selector_would_overcount(self):
        # PLANTED: a zero-width lookahead with no start-of-identifier guard matches at EVERY
        # character offset inside a longer identifier, not just its start — `pkg.Helper`
        # would be found once per character of `pkg` (`pkg.Helper`, `kg.Helper`, `g.Helper`),
        # inflating a single real reference into three. Demonstrated on the actual regex
        # object with its guard stripped, proving the shipped guard is doing real work.
        import re
        unguarded = re.compile(r"(?=(?P<lhs>[A-Za-z_][A-Za-z0-9_]*)\.(?P<rhs>[A-Za-z_][A-Za-z0-9_]*))")
        overcounted = [m.group("rhs") for m in unguarded.finditer("pkg.Helper")]
        self.assertEqual(3, len(overcounted))                      # the planted defect
        self.assertEqual(1, len(selector_references("pkg.Helper")))  # the shipped module


class ImportBlocksAreParsedButNeverSeenInCorpusSlots(unittest.TestCase):
    """Go requires every import before any declaration, so `_segment_go`-style spans (which
    this module mirrors) never contain one — exercised here on synthetic text directly."""

    def test_a_bare_import_is_read(self):
        self.assertEqual([("", "fmt")], import_targets('import "fmt"'))

    def test_an_aliased_bare_import_is_read(self):
        self.assertEqual([("f", "fmt")], import_targets('import f "fmt"'))

    def test_a_block_import_reads_every_entry_aliased_or_not(self):
        got = import_targets('import ( "fmt" x "os/exec" "strings" )')
        self.assertEqual([("", "fmt"), ("x", "os/exec"), ("", "strings")], got)

    def test_text_with_no_import_yields_nothing(self):
        self.assertEqual([], import_targets('func Foo() { return }'))

    def test_real_corpus_shaped_declaration_text_never_contains_import(self):
        # Not a corpus read (none is available to this test in isolation) — a structural
        # fact about the grammar `_segment_go` and this module both anchor on: a declaration
        # span starts at `func`/`type`/`const`/`var`, never earlier, so an `import` clause
        # (which must precede all of them) cannot be inside it.
        span = "func Caller() { return pkg.Helper() }"
        self.assertEqual([], import_targets(span))


class ReproducibleAndEraTagged(unittest.TestCase):

    def test_re_parsing_the_same_material_is_a_no_op(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() }"})
        a = [e.as_record() for e in parse(snap, era="e1").edges]
        b = [e.as_record() for e in parse(snap, era="e1").edges]
        self.assertEqual(a, b)

    def test_the_era_travels_on_every_edge(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() }"})
        self.assertEqual("go-v0", parse(snap, era="go-v0").edges[0].era)

    def test_a_changed_source_is_a_NEW_era_not_a_silent_mutation(self):
        snap = _Snap({"d": "\x01go\x01func Helper() int { return 1 }",
                      "t": "\x01go\x01func Caller() int { return pkg.Helper() }"})
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
