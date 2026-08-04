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
