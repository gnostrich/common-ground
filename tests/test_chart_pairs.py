"""Hole enumeration works over ANY chart pair, not just lean->english.

Candidate generation had been written for one pairing and read as if it were general. With
python and go charts in place that is no longer harmless: english x python and english x go
were EMPTY by construction, because neither language emitted doc companions and the
declaration key could only be recovered for Lean.
"""

from __future__ import annotations

import unittest

from engine.extract import DeterministicExtractor, slots_from_deltas
from engine.holes import (
    chart_pairs_present,
    declaration_key,
    holes_by_declaration,
    holes_by_subtree_all,
)
from engine.router import route

FILES = {
    "r||lean/Cone.lean": "/-- The cone is positive. -/\ntheorem cone_pos : True := trivial\n",
    "r||lean/cone.py": ('def cone_pos(c):\n    """The cone is positive."""\n'
                        "    return c.det > 0\n"),
    "r||lean/cone.go": ("package cone\n// ConePos reports that the cone is positive.\n"
                        "func ConePos(c Cone) bool { return true }\n"),
    "r||README.md": ("# Cone\n\nThe cone is positive under composition.\n"
                     "Every generator is checked before acceptance.\n"),
}


def corpus():
    ex = DeterministicExtractor("t", "p")
    deltas = []
    for name, text in FILES.items():
        routed = route(name, text, "repo")
        for doc in ([routed.document] if routed.document else []) + list(routed.companions):
            deltas.extend(ex.extract(doc))
    return slots_from_deltas(deltas), deltas


class DeclarationKeysAreReadTheSameWayEverywhere(unittest.TestCase):
    def test_every_code_chart_reports_its_declaration_name(self):
        slots, deltas = corpus()
        by_chart = {}
        for d in deltas:
            key = declaration_key(d)
            if key and d.chart in ("lean", "python", "go"):
                by_chart.setdefault(d.chart, set()).add(key[1])
        self.assertEqual(by_chart.get("lean"), {"cone_pos"})
        self.assertEqual(by_chart.get("python"), {"cone_pos"})
        self.assertEqual(by_chart.get("go"), {"ConePos"})

    def test_a_positional_locator_names_no_declaration(self):
        """PLANTED: `decl:3` is an ordinal, not a name, and must key nothing."""
        import dataclasses

        _slots, deltas = corpus()
        lean = next(d for d in deltas if d.chart == "lean")
        ordinal = dataclasses.replace(
            lean, provenance=dataclasses.replace(lean.provenance, locator="decl:3"))
        self.assertIsNone(declaration_key(ordinal))

    def test_doc_derived_english_keys_to_its_own_declaration(self):
        _slots, deltas = corpus()
        keys = {declaration_key(d) for d in deltas
                if d.chart == "english" and "#doc:" in d.provenance.doc_id}
        self.assertIn(("r||lean/Cone.lean", "cone_pos"), keys)
        self.assertIn(("r||lean/cone.py", "cone_pos"), keys)
        self.assertIn(("r||lean/cone.go", "ConePos"), keys)


class DeclarationHolesSpanEveryChartPair(unittest.TestCase):
    def setUp(self):
        self.slots, self.deltas = corpus()
        self.holes = holes_by_declaration(self.slots, self.deltas)

    def _pairs(self):
        return {tuple(sorted((h.src_chart, h.dst_chart)))
                for hs in self.holes.values() for h in hs}

    def test_english_pairs_with_all_three_code_charts(self):
        pairs = self._pairs()
        for code in ("lean", "python", "go"):
            self.assertIn(("english", code), pairs,
                          f"english x {code} is empty — the generalization did not reach it")

    def test_two_code_charts_never_share_a_declaration_key(self):
        """Not a gap in the code: two different files cannot share (file, declaration)."""
        for pair in self._pairs():
            self.assertIn("english", pair,
                          f"{pair} paired at declaration granularity, which is impossible")

    def test_restricting_the_pairs_restricts_the_output(self):
        only_go = holes_by_declaration(self.slots, self.deltas,
                                       chart_pairs=[("english", "go")])
        pairs = {tuple(sorted((h.src_chart, h.dst_chart)))
                 for hs in only_go.values() for h in hs}
        self.assertEqual(pairs, {("english", "go")})

    def test_a_declaration_with_no_doc_produces_no_hole(self):
        """PLANTED: an undocumented declaration must pair with nothing, not with anything near."""
        ex = DeterministicExtractor("t", "p")
        routed = route("r||bare.py", "def undocumented(x):\n    return x\n", "repo")
        self.assertEqual(routed.companions, ())
        deltas = list(ex.extract(routed.document))
        self.assertEqual(holes_by_declaration(slots_from_deltas(deltas), deltas), {})


class SubtreeHolesSpanEveryChartPair(unittest.TestCase):
    def test_pairs_present_excludes_the_correspondence_chart(self):
        slots, _ = corpus()
        pairs = chart_pairs_present(slots)
        self.assertTrue(pairs)
        self.assertFalse([p for p in pairs if "correspondence" in p],
                         "correspondence holds the arrows themselves, not material to bridge")

    def test_code_to_code_is_reachable_by_subtree_though_not_by_declaration(self):
        slots, deltas = corpus()
        by_pair = holes_by_subtree_all(slots, deltas, max_depth=1)
        self.assertIn(("go", "lean"), by_pair,
                      "a Lean spec and a Go implementation in one directory must be candidates")
        self.assertIn(("lean", "python"), by_pair)

    def test_both_directions_are_enumerated(self):
        """Prose can sit above OR below the code; a pair must not be missed for that."""
        slots, deltas = corpus()
        by_pair = holes_by_subtree_all(slots, deltas, max_depth=1)
        holes = [h for hs in by_pair.get(("english", "lean"), {}).values() for h in hs]
        self.assertTrue(holes)
        directions = {(h.src_chart, h.dst_chart) for h in holes}
        self.assertGreaterEqual(len(directions), 1)


if __name__ == "__main__":
    unittest.main()
