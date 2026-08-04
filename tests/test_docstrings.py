"""Lean docstrings enter the English chart, attached to their declaration's provenance —
and the Lean address does not move.

264 of 407 .lean files carry `/-- ... -/` docstrings: 292,633 characters, 15.8% of all Lean
text. They are natural-language statements sitting ON the declaration — the most perfectly
co-located prose that can exist — and they used to be discarded at the boundary, stripped
from the Lean address and never routed as English.

This change is ADDITIVE and NON-PLASTIC: the Lean surface, and therefore every Lean slot id,
is byte-identical before and after. No re-anneal.
"""

from __future__ import annotations

import unittest

from engine.normalize import address, nu
from engine.router import ENGLISH, LEAN, lean_docstrings, route, route_all

_SRC = (
    "/-- The cone is positive under composition. -/\n"
    "theorem comp_pos (f g : Cone) : IsPositive (f ∘ g) := by simp\n"
    "\n"
    "/-- Spectral radius is the largest modulus eigenvalue. -/\n"
    "noncomputable def spectralRadius (M : Matrix) : R := sSup (spectrum M)\n"
    "\n"
    "/-! ### Section notes, owned by no single declaration -/\n"
)


class ADocstringBecomesAnEnglishClaim(unittest.TestCase):
    def test_it_reaches_the_english_chart(self):
        comps = route("Cone.lean", _SRC).companions
        self.assertTrue(comps)
        self.assertTrue(all(c.chart == ENGLISH for c in comps))

    def test_its_provenance_points_at_its_declaration(self):
        by_decl = {c.meta.get("declaration"): c for c in lean_docstrings("Cone.lean", _SRC)}
        self.assertIn("comp_pos", by_decl)
        self.assertIn("spectralRadius", by_decl)
        self.assertIn("positive under composition", by_decl["comp_pos"].text)
        self.assertEqual(by_decl["comp_pos"].meta["lean_file"], "Cone.lean")
        self.assertEqual(by_decl["comp_pos"].meta["declaration_head"], "theorem")
        self.assertIn("#doc:comp_pos", by_decl["comp_pos"].doc_id,
                      "the doc_id must name the declaration it documents")

    def test_a_modifier_does_not_hide_the_owner(self):
        # `noncomputable def spectralRadius` — the owner is found past the modifier.
        owners = {c.meta.get("declaration") for c in lean_docstrings("Cone.lean", _SRC)}
        self.assertIn("spectralRadius", owners)

    def test_a_section_doc_is_attributed_to_the_file_not_a_declaration(self):
        section = [c for c in lean_docstrings("Cone.lean", _SRC)
                   if "#sectiondoc" in c.doc_id]
        self.assertEqual(len(section), 1)
        self.assertIsNone(section[0].meta.get("declaration"),
                          "a /-! doc owns no single declaration and must not claim one")

    def test_companions_reach_to_charts(self):
        report = route_all([("Cone.lean", _SRC)])
        charts = {d.chart for d in report.to_charts()}
        self.assertEqual(charts, {LEAN, ENGLISH})


class TheLeanAddressDoesNotMove(unittest.TestCase):
    """Non-plastic: no address moves, so no re-anneal (gate 4)."""

    def test_nu_still_strips_docstrings_from_the_lean_surface(self):
        self.assertEqual(nu("lean", _SRC), nu("lean", _SRC.replace(
            "/-- The cone is positive under composition. -/\n", "")))

    def test_the_lean_slot_id_is_byte_identical_with_and_without_the_docstring(self):
        decl = "theorem comp_pos (f g : Cone) : IsPositive (f ∘ g) := by simp"
        with_doc = "/-- Anything at all. -/\n" + decl
        a, _ = address("lean", decl, "assert")
        b, _ = address("lean", with_doc, "assert")
        self.assertEqual(a, b, "adding a docstring must not move a Lean address")

    def test_the_lean_document_text_is_unchanged_by_companion_extraction(self):
        r = route("Cone.lean", _SRC)
        self.assertIn("/--", r.document.text,
                      "the Lean document keeps its raw text; only nu strips the docstring")


if __name__ == "__main__":
    unittest.main()


class IdentifiersSurviveTheAddress(unittest.TestCase):
    """Gate-4 plastic fix: `_` between word characters is an IDENTIFIER, not emphasis.

    Stripping it mangled `gershgorin_wall` to `gershgorinwall`, so prose naming a declaration
    could never share a token with the declaration itself — destroying the bridge signal for
    571 of 1,113 identifier-shaped declarations that ARE named in the corpus's prose.
    """

    def test_an_identifier_in_prose_keeps_its_underscore(self):
        self.assertIn("gershgorin_wall", nu("english", "The theorem gershgorin_wall is certified."))

    def test_prose_naming_a_declaration_shares_a_token_with_the_declaration(self):
        prose = nu("english", "wall_sigmaMin_half gives the lower bound.")
        lean = nu("lean", "theorem wall_sigmaMin_half : SigmaMinGE (toReal wallA) (1 / 2)")
        prose_tokens = set(prose.replace("\x01en\x01", "").split())
        lean_tokens = set(lean.replace("\x01lean\x01", "").split())
        shared = {t.casefold() for t in prose_tokens} & {t.casefold() for t in lean_tokens}
        self.assertIn("wall_sigmamin_half", shared,
                      "prose naming a declaration must share a token with it")

    def test_markdown_emphasis_still_strips(self):
        self.assertNotIn("_", nu("english", "this is _emphasised_ text"))
        self.assertNotIn("*", nu("english", "this is **bold** text"))
        self.assertNotIn("`", nu("english", "use `code` here"))

    def test_a_leading_or_trailing_underscore_is_emphasis_not_identity(self):
        self.assertNotIn("_", nu("english", "_private is internal"))
        self.assertNotIn("_", nu("english", "trailing_ underscore"))

    def test_nu_is_still_idempotent(self):
        # Gate 1 depends on it: nu(nu(x)) == nu(x), or addressing breaks.
        for s in ("gershgorin_wall holds", "_emph_ and a_b and **x**", "a_b_c_d",
                  "_ _ _", "x_ _y", "*#\nr\t\x00\x01m -> $_\n="):
            once = nu("english", s)
            self.assertEqual(once, nu("english", once), f"not idempotent on {s!r}")


class DeclarationGranularityBounding(unittest.TestCase):
    """The tightest bound: a Lean declaration and the docstring written ON it.

    Directory bounding covered 13.6% of Lean slots; this covers 52.1%, and the pairing is
    given by where the author wrote the words — no ranking, no threshold, nothing to tune.
    """

    def _pipeline(self):
        from engine.constants import decisions
        from engine.energy import dedupe_deltas
        from engine.extract import build_k_extractors, slots_from_deltas
        from engine.pipeline import ingest
        from engine.router import route_all

        report = route_all([("Cone.lean", _SRC)])
        docs = report.to_charts()
        deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
        return slots_from_deltas(deltas), deltas

    def test_a_docstring_pairs_with_its_own_declaration(self):
        from engine.holes import holes_by_declaration

        slots, deltas = self._pipeline()
        bounded = holes_by_declaration(slots, deltas)
        self.assertTrue(bounded, "the docstring and its declaration must pair")
        for src, holes in bounded.items():
            for h in holes:
                self.assertEqual(h.src_chart, "lean")
                self.assertEqual(h.dst_chart, "english")

    def test_it_pairs_nothing_when_the_docstring_is_removed(self):
        from engine.constants import decisions
        from engine.energy import dedupe_deltas
        from engine.extract import build_k_extractors, slots_from_deltas
        from engine.holes import holes_by_declaration
        from engine.pipeline import ingest
        from engine.router import route_all

        stripped = _SRC.replace("/-- The cone is positive under composition. -/\n", "")
        stripped = stripped.replace(
            "/-- Spectral radius is the largest modulus eigenvalue. -/\n", "")
        docs = route_all([("Cone.lean", stripped)]).to_charts()
        deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
        bounded = holes_by_declaration(slots_from_deltas(deltas), deltas)
        self.assertEqual(bounded, {},
                         "with no docstring there is no declaration-level co-location")

    def test_a_docstring_does_not_pair_with_a_different_declaration(self):
        from engine.holes import holes_by_declaration

        slots, deltas = self._pipeline()
        nu_of = {s.id: s.nu for s in slots}
        for src, holes in holes_by_declaration(slots, deltas).items():
            lean_nu = nu_of[src]
            for h in holes:
                # the paired english slot must come from THIS declaration's docstring
                if "comp_pos" in lean_nu:
                    self.assertNotIn("eigenvalue", h.dst_nu,
                                     "comp_pos must not pair with spectralRadius's docstring")


class SubtreeBounding(unittest.TestCase):
    """A prose document describes the subtree BELOW it — docs at top, code below.

    certified-positivity keeps STATEMENTS.md ("the exact formal claims, verbatim from the
    named source file") at the repo root while 75 of its 77 .lean files sit in lean/.
    Declaration-granularity cannot see that (a STATEMENTS.md entry is not a docstring) and
    directory-granularity cannot either (one level apart). This relation can, and it is the
    many-to-one shape a CYCLE needs: a docstring belongs to exactly one declaration, so
    declaration-granularity yields only stars and holonomy is zero by path-debt forever.
    """

    def _build(self, files):
        from engine.constants import decisions
        from engine.energy import dedupe_deltas
        from engine.extract import build_k_extractors, slots_from_deltas
        from engine.pipeline import ingest
        from engine.router import route_all

        docs = route_all(files, "repo").to_charts()
        deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
        return slots_from_deltas(deltas), deltas

    _ROOT_DOC = ("The cone is positive under composition. "
                 "The spectral radius equals the largest modulus eigenvalue.")
    # Binder-free, so they classify `assert` like their English restatements. A theorem WITH
    # binders classifies `conditional` and is rejected by the type filter — see
    # TypeCompatibilityIsAntiCorrelatedAcrossCharts below.
    _LEAN_A = "theorem comp_pos : IsPositive compose := by simp"
    _LEAN_B = "theorem spec_rad : SpectralRadius equals sSup := by simp"

    def test_a_root_doc_pairs_with_lean_below_it(self):
        from engine.holes import holes_by_subtree

        slots, deltas = self._build([
            ("r||STATEMENTS.md", self._ROOT_DOC),
            ("r||lean/A.lean", self._LEAN_A),
            ("r||lean/B.lean", self._LEAN_B),
        ])
        sub = holes_by_subtree(slots, deltas)
        self.assertTrue(sub, "a root prose doc must reach .lean in a subdirectory")

    def test_it_does_not_pair_across_repos(self):
        from engine.holes import holes_by_subtree

        slots, deltas = self._build([
            ("r1||STATEMENTS.md", self._ROOT_DOC),
            ("r2||lean/A.lean", self._LEAN_A),
        ])
        self.assertEqual(holes_by_subtree(slots, deltas), {},
                         "a document describes its own repo, not someone else's")

    def test_a_deep_doc_does_not_reach_a_sibling_subtree(self):
        from engine.holes import holes_by_subtree

        slots, deltas = self._build([
            ("r||docs/notes.md", self._ROOT_DOC),
            ("r||other/A.lean", self._LEAN_A),
        ])
        self.assertEqual(holes_by_subtree(slots, deltas), {},
                         "docs/ describes what is below docs/, not a sibling tree")

    def test_it_can_produce_the_many_to_one_shape_a_cycle_needs(self):
        from engine.holes import holes_by_subtree

        slots, deltas = self._build([
            ("r||STATEMENTS.md", self._ROOT_DOC),
            ("r||lean/A.lean", self._LEAN_A),
            ("r||lean/B.lean", self._LEAN_B),
        ])
        by_english = {}
        for src, holes in holes_by_subtree(slots, deltas).items():
            for h in holes:
                by_english.setdefault(h.dst_slot, set()).add(h.src_slot)
        self.assertTrue(any(len(v) >= 2 for v in by_english.values()),
                        "one prose document restating two theorems must give an english "
                        "slot two lean candidates — the precondition for a closed cycle")

    def test_docstring_derived_english_is_excluded_from_the_subtree_relation(self):
        from engine.holes import holes_by_subtree

        slots, deltas = self._build([("r||lean/A.lean", "/-- Doc for A. -/\n" + self._LEAN_A)])
        for holes in holes_by_subtree(slots, deltas).values():
            for h in holes:
                self.assertNotIn("#doc:", h.dst_nu,
                                 "docstrings are already paired at declaration granularity")


class TypeCompatibilityIsAntiCorrelatedAcrossCharts(unittest.TestCase):
    """FINDING, pinned not fixed: requiring equal claim-form across charts rejects exactly
    the true correspondences.

    A Lean theorem that binds hypotheses classifies `conditional`; its English restatement is
    almost always phrased as an `assert`. Claim-form is a property of the SURFACE FORM, and a
    correspondence is precisely a translation BETWEEN surface forms — so equality of
    claim-form is the wrong compatibility test cross-chart, however right it is within a
    chart (where it keeps `assert` and `define` readings of one surface in separate blocks).

    Recorded for the operator's ruling. `holes_by_declaration` does NOT apply the filter;
    `holes_by_subtree` and `enumerate_holes` DO. That inconsistency is real and is named here
    rather than resolved unilaterally.
    """

    def test_a_lean_theorem_with_binders_and_its_english_restatement_disagree_on_type(self):
        from engine.normalize import classify

        lean = "theorem comp_pos (f g : Cone) : IsPositive (f ∘ g)"
        english = "The cone is positive under composition."
        self.assertEqual(classify("lean", lean), "conditional")
        self.assertEqual(classify("english", english), "assert")
        self.assertNotEqual(classify("lean", lean), classify("english", english),
                            "the true pair disagrees on claim-form — so a type-equality "
                            "filter drops it")

    def test_no_bounding_relation_type_filters_cross_chart(self):
        """RESOLVED by operator ruling: the filter is OFF cross-chart, consistently."""
        import inspect

        from engine.holes import enumerate_holes, holes_by_declaration, holes_by_subtree

        filter_expr = "type_of.get(src_slot) != type_of.get(dst_slot)"
        for fn in (holes_by_declaration, holes_by_subtree):
            self.assertNotIn(filter_expr, inspect.getsource(fn),
                             f"{fn.__name__} must not type-filter cross-chart")
        src = inspect.getsource(enumerate_holes)
        self.assertIn("for a in types_a for b in types_b", src,
                      "enumerate_holes must pair across claim-forms cross-chart")
