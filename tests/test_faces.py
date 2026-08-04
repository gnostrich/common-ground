"""Controls for corpus-derived formal faces (the term-level anchor layer).

An anchor is a PRIOR ON CANDIDATE GENERATION — it decides which holes are worth asking
about. It never creates a correspondence, never enters the structure, never grounds
anything. These controls pin that, and pin that face generation contains no similarity.
"""

from __future__ import annotations

import unittest

from engine.faces import (
    FormalFace,
    anchors_for_english,
    anchors_for_lean,
    declarations,
    derive_faces,
    face_index,
)
from engine.types import Document, WarrantTier

_LEAN = (
    "theorem isPositive_comp (f g : Cone) : IsPositive (f ∘ g) := by simp\n"
    "def spectralRadius (M : Matrix) : R := sSup (spectrum M)\n"
    "example : True := trivial\n"          # anonymous — must not yield a face
)


def _doc(text: str = _LEAN, path: str = "Cone.lean") -> Document:
    d = Document("lean:Cone.lean", "lean", text, "lean_corpus")
    d.meta["path"] = path
    return d


class FacesDeriveOnlyThroughTheSeededRmap(unittest.TestCase):
    def test_a_name_renders_to_its_declared_face(self):
        faces = {f.formal_name: f.face for f in derive_faces([_doc()])}
        self.assertEqual(faces.get("isPositive_comp"), "is positive composition")
        self.assertEqual(faces.get("spectralRadius"), "spectral radius")

    def test_anonymous_declarations_yield_no_face(self):
        self.assertNotIn("example", {f.head for f in derive_faces([_doc()])})

    def test_generation_is_deterministic(self):
        a = [f.as_record() for f in derive_faces([_doc()])]
        b = [f.as_record() for f in derive_faces([_doc()])]
        self.assertEqual(a, b, "face generation must be a pure function of name + seed table")

    def test_there_is_no_similarity_in_face_generation(self):
        import inspect

        import engine.faces as mod

        # Strip docstrings and comments: the module DESCRIBES what it refuses to do, and
        # matching its own prose would make this control fire on the disclaimer.
        import ast
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
                node.body = node.body[1:]
        code = ast.unparse(tree)
        for banned in ("jaccard", "levenshtein", "edit_distance", "difflib",
                       "SequenceMatcher", "embedding", "cosine"):
            self.assertNotIn(banned, code,
                             f"{banned} would be similarity, not declared structure")


class FacesCarryProvenanceAndTheRightTier(unittest.TestCase):
    def test_each_face_names_the_file_it_came_from(self):
        for f in derive_faces([_doc(path="Order/Cone.lean")]):
            self.assertEqual(f.file, "Order/Cone.lean")
            self.assertTrue(f.formal_name and f.head)

    def test_a_derived_face_is_not_authorship_tier(self):
        for f in derive_faces([_doc()]):
            self.assertEqual(f.tier, WarrantTier.REPO_DOC)
            self.assertNotEqual(f.tier, WarrantTier.AUTHORSHIP,
                                "deriving a face is a mechanical transform, not confirmation")
            self.assertFalse(f.tier in (WarrantTier.KERNEL, WarrantTier.CI_RECEIPT),
                             "a derived face grounds nothing")


class AnchoringIsExactNotFuzzy(unittest.TestCase):
    def setUp(self):
        self.index = face_index([
            FormalFace("spectralRadius", "spectral radius", "def", "f.lean"),
            FormalFace("IsPositive", "is positive", "def", "f.lean"),
        ])

    def test_an_english_slot_anchors_on_exact_word_boundary_containment(self):
        hit = anchors_for_english("the spectral radius equals the largest eigenvalue", self.index)
        self.assertIn("spectral radius", hit)

    def test_a_substring_inside_a_longer_word_does_not_anchor(self):
        self.assertEqual(anchors_for_english("spectralradiusx is unrelated", self.index), [])

    def test_a_near_miss_does_not_anchor(self):
        # No stemming, no fuzz: "radii" is not "radius".
        self.assertEqual(anchors_for_english("the spectral radii differ", self.index), [])

    def test_a_lean_slot_anchors_from_its_own_declaration_name(self):
        self.assertIn("spectral radius",
                      anchors_for_lean("def spectralRadius (M : Matrix) : R := x", self.index))


class AnAnchorIsOnlyAPrior(unittest.TestCase):
    def test_faces_module_creates_no_correspondence_and_touches_no_tape(self):
        import inspect

        import engine.faces as mod

        src = inspect.getsource(mod)
        self.assertNotIn("Correspondence(", src, "an anchor must never create an arrow")
        self.assertNotIn(".propose(", src, "an anchor must never reach the tape")
        self.assertNotIn("Clamp(", src, "an anchor grounds nothing")


if __name__ == "__main__":
    unittest.main()
