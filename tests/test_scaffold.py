"""DEPENDS_ON: the anti-cobble battery, every one a planted RED.

The scaffolds were free and discarded — 12,466 Lean slots flat while their dependency graph
sat in the material. The risk in taking them is the one that cost a week: a relation stored
under the wrong kind, or an edge inferred where the source declares none. These controls make
both structurally impossible rather than forbidden.
"""

import unittest

from engine.scaffold import (DEPENDS_ON, REFERENCE_TIER, SCAFFOLD_KINDS, Scaffold,
                             ScaffoldParse, holonomy_excluded)
from engine.scaffold_lean import declaration_index, declared_name, parse


class _Rec:
    def __init__(self, nu, chart="lean"):
        self.nu, self.chart, self.type, self.docs = nu, chart, "assert", ("d.lean",)


class _Snap:
    def __init__(self, m):
        self.slots = {k: _Rec(v) for k, v in m.items()}
        self.arrows = []


class ItIsNotACorrespondenceAndCannotBeMisKinded(unittest.TestCase):
    """The containment lesson, enforced by the type system rather than by a rule."""

    def test_a_dependency_cannot_be_stored_as_an_equivalence_kind(self):
        for bad in ("same_claim", "refines", "instance_of"):
            with self.assertRaises(ValueError):
                Scaffold(chart="lean", src_slot="a", dst_slot="b", kind=bad)

    def test_an_intra_chart_correspondence_is_still_refused(self):
        # The guard this design exists to avoid weakening: exact addressing owns intra-chart
        # identity, so an intra-chart correspondence would re-introduce similarity. Every
        # scaffold edge is intra-chart, which is why it is a different type.
        from engine.correspondence import Correspondence
        with self.assertRaises(Exception):
            Correspondence(src_chart="lean", src_slot="a", dst_chart="lean", dst_slot="b",
                           kind="same_claim")

    def test_a_scaffold_IS_intra_chart_legal(self):
        s = Scaffold(chart="lean", src_slot="a", dst_slot="b")
        self.assertEqual("lean", s.chart)
        self.assertEqual(DEPENDS_ON, s.kind)

    def test_it_carries_the_reference_tier(self):
        self.assertEqual(REFERENCE_TIER, Scaffold(chart="lean", src_slot="a",
                                                  dst_slot="b").tier)

    def test_the_kind_family_is_closed(self):
        self.assertEqual({DEPENDS_ON}, set(SCAFFOLD_KINDS))


class ItIsHolonomyEXCLUDEDByConstruction(unittest.TestCase):

    def test_a_scaffold_has_no_loop_eligibility_to_set_wrongly(self):
        s = Scaffold(chart="lean", src_slot="a", dst_slot="b")
        self.assertFalse(hasattr(s, "loop_eligible"))
        self.assertTrue(holonomy_excluded(s))

    def test_a_loop_computed_over_scaffolds_finds_nothing(self):
        # PLANTED: feed scaffolds where correspondences are expected. `loop_pairs` reads
        # `loop_eligible`, which a Scaffold does not have, so it contributes no pair at all.
        from engine.correspondence import loop_pairs
        with self.assertRaises(AttributeError):
            loop_pairs([Scaffold(chart="lean", src_slot="a", dst_slot="b")])

    def test_a_correspondence_kind_is_never_a_scaffold_kind(self):
        from engine.correspondence import KINDS
        self.assertEqual(frozenset(), KINDS & SCAFFOLD_KINDS)


class ResolveOrVoid(unittest.TestCase):

    def test_a_reference_to_a_declared_name_resolves(self):
        snap = _Snap({"d": "\x01lean\x01def Price := NNReal",
                      "t": "\x01lean\x01theorem p : Price = Price"})
        p = parse(snap)
        self.assertEqual(1, len(p.edges))
        self.assertEqual(("t", "d"), p.edges[0].pair)
        self.assertEqual("Price", p.edges[0].symbol)

    def test_an_undeclared_reference_is_VOID_not_a_dangling_edge(self):
        snap = _Snap({"t": "\x01lean\x01theorem p : Nat.succ_le_succ x"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(r == "undeclared" for _, _, r in p.void))

    def test_an_AMBIGUOUS_name_is_VOID_never_resolved_to_the_first(self):
        # Picking one would be a similarity mechanism wearing a parser's clothes.
        snap = _Snap({"a": "\x01lean\x01def Foo := 1",
                      "b": "\x01lean\x01def Foo := 2",
                      "t": "\x01lean\x01theorem p : Foo = Foo"})
        p = parse(snap)
        self.assertEqual([], p.edges)
        self.assertTrue(any(r == "ambiguous" for _, _, r in p.void))

    def test_voids_are_COUNTED_with_their_reasons(self):
        # A parser reporting only its successes cannot be told from one that made none.
        snap = _Snap({"t": "\x01lean\x01theorem p : Missing.thing y"})
        rec = parse(snap).as_record()
        self.assertGreater(rec["void"], 0)
        self.assertIn("undeclared", rec["void_by_reason"])
        self.assertIn("resolution_rate", rec)

    def test_a_declaration_never_depends_on_itself(self):
        snap = _Snap({"d": "\x01lean\x01def Price := Price"})
        self.assertEqual([], parse(snap).edges)

    def test_a_repeated_reference_makes_ONE_edge(self):
        snap = _Snap({"d": "\x01lean\x01def Price := NNReal",
                      "t": "\x01lean\x01theorem p : Price = Price ∧ Price > Price"})
        self.assertEqual(1, len(parse(snap).edges))


class NoInferenceOnlyParse(unittest.TestCase):

    def test_a_NEAR_MISS_name_does_not_resolve(self):
        # PLANTED SIMILARITY: `Prices` is not `Price`. An edit-distance or prefix matcher
        # would join them; exact declared-name matching does not.
        snap = _Snap({"d": "\x01lean\x01def Price := NNReal",
                      "t": "\x01lean\x01theorem p : Prices = 1"})
        self.assertEqual([], parse(snap).edges)

    def test_the_module_holds_no_similarity_machinery(self):
        from pathlib import Path
        src = (Path(__file__).resolve().parent.parent / "engine" / "scaffold_lean.py").read_text()
        for banned in ("difflib", "SequenceMatcher", "levenshtein", "ratio(", "startswith(name",
                       ".lower()", "casefold"):
            self.assertNotIn(banned, src, f"inference is back: {banned}")

    def test_a_line_declaring_nothing_yields_no_name(self):
        self.assertEqual("", declared_name("\x01lean\x01-- just a comment"))

    def test_the_declarer_list_is_leans_grammar_not_a_line_shape_guess(self):
        for kw, name in (("theorem", "foo"), ("lemma", "bar"), ("def", "baz"),
                         ("abbrev", "qux"), ("structure", "S"), ("instance", "I")):
            self.assertEqual(name, declared_name(f"\x01lean\x01{kw} {name} : True"))


class ReproducibleAndEraTagged(unittest.TestCase):

    def test_re_parsing_the_same_material_is_a_no_op(self):
        snap = _Snap({"d": "\x01lean\x01def Price := NNReal",
                      "t": "\x01lean\x01theorem p : Price = Price"})
        a = [e.as_record() for e in parse(snap, era="e1").edges]
        b = [e.as_record() for e in parse(snap, era="e1").edges]
        self.assertEqual(a, b)

    def test_the_era_travels_on_every_edge(self):
        snap = _Snap({"d": "\x01lean\x01def Price := NNReal",
                      "t": "\x01lean\x01theorem p : Price = Price"})
        self.assertEqual("lean-v0", parse(snap, era="lean-v0").edges[0].era)

    def test_a_changed_source_is_a_NEW_era_not_a_silent_mutation(self):
        snap = _Snap({"d": "\x01lean\x01def Price := NNReal",
                      "t": "\x01lean\x01theorem p : Price = Price"})
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
            self.assertNotIn(k, table["compose"].get("depends_on", {}))


if __name__ == "__main__":
    unittest.main()
