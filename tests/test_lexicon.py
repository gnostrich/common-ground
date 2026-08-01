"""Lexicon layer: hub invariant, collision policy, import order, and cells vi-ix."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from adapters.lexicon_imports import (
    import_all,
    import_convention_table,
    import_mathlib,
    import_nlab,
    import_preminted,
    import_wordnet,
    lemma_of,
)
from engine import EngineError, GateViolation
from engine.constants import SOURCE_ORDER
from engine.lexicon import (
    ABSTAIN,
    Face,
    Registry,
    infer_frames,
    make_sense,
    merge_senses,
    select_sense,
    sense_key,
    tokens,
)
from engine.nulls import (
    cell_vi_hub_coverage,
    cell_vii_shadow,
    cell_viii_no_clamp_grep,
    cell_ix_binding_sanity,
)
from engine.rmap import render, render_batch, render_disambiguated, segments
from engine.static_checks import DISPLAY_ATTRS, check_no_display_on_f_path
from engine.types import Document, NullStatus


MATHLIB_FIXTURE = {
    "commit": "abc123def456",
    "declarations": [
        {"name": "Mathlib.Order.Cone.IsPositive", "type": "Set E -> Prop", "doc": "positive cone"},
        {"name": "Mathlib.Topology.Basic.IsCompact", "type": "Set X -> Prop", "doc": "compact set"},
        {"name": "Mathlib.Algebra.Group.Defs.MonoidHom.ker", "type": "(G ->* H) -> Subgroup G", "doc": "kernel"},
        {"name": "Mathlib.LinearAlgebra.Basic.LinearMap.ker", "type": "(M ->l N) -> Submodule R M", "doc": "kernel"},
        {"name": "Mathlib.Order.Basic.PartialOrder", "type": "Type -> Type", "doc": "partial order"},
    ],
}


def _mathlib_dump(tmp: Path) -> Path:
    path = tmp / "mathlib.json"
    path.write_text(json.dumps(MATHLIB_FIXTURE), encoding="utf-8")
    return path


class RMap(unittest.TestCase):
    def test_segments_preserve_the_namespace_verbatim(self):
        self.assertEqual(
            segments("Mathlib.Order.Cone.IsPositive"),
            ["Mathlib", "Order", "Cone", "IsPositive"],
        )

    def test_camel_case_and_underscores_split(self):
        self.assertEqual(render("Mathlib.Order.IsPositive"), "is positive")
        self.assertEqual(render("Foo.comp_pos"), "composition positive")

    def test_declared_abbreviations_expand(self):
        self.assertEqual(render("Mathlib.Algebra.MonoidHom.ker"), "kernel")

    def test_collision_widens_leftward_through_the_namespace(self):
        a = "Mathlib.Algebra.Group.MonoidHom.ker"
        b = "Mathlib.LinearAlgebra.LinearMap.ker"
        faces = render_batch([a, b])
        self.assertNotEqual(faces[a], faces[b], "two kernels must not share one face")
        self.assertTrue(any("(" in f for f in faces.values()))

    def test_batch_is_order_independent(self):
        names = ["B.b.Foo", "A.a.Foo", "C.c.Bar"]
        self.assertEqual(render_batch(names), render_batch(list(reversed(names))))

    def test_disambiguation_terminates_on_a_fully_taken_namespace(self):
        face = render_disambiguated("A.B.Foo", taken={"foo", "foo (b)", "foo (a.b)"})
        self.assertTrue(face)


class HubInvariant(unittest.TestCase):
    """Warrant never flows through the English face."""

    def test_english_face_is_mandatory(self):
        with self.assertRaises(GateViolation) as ctx:
            make_sense(lemma="x", english_face="   ", source="mathlib")
        self.assertIn("only in a formal chart", str(ctx.exception))

    def test_sense_core_carries_no_display_strings(self):
        sense = make_sense(
            lemma="cone", english_face="convex cone", source="convention",
            gloss="closed under non-negative scaling",
        )
        fields = set(getattr(type(sense.core), "__dataclass_fields__", {}))
        self.assertFalse(fields & DISPLAY_ATTRS, f"SenseCore leaks display fields: {fields & DISPLAY_ATTRS}")
        self.assertIn("english_slot", fields)
        self.assertNotIn("english_face", fields)

    def test_the_address_survives_even_though_the_string_does_not(self):
        a = make_sense(lemma="cone", english_face="convex cone", source="convention")
        b = make_sense(lemma="cone", english_face="  Convex   Cone.  ", source="nlab")
        self.assertEqual(a.core.english_slot, b.core.english_slot,
                         "the hub addresses by normalized face, so these coincide")
        self.assertNotEqual(a.core.sense_id, b.core.sense_id,
                            "...but they remain distinct senses (different source)")

    def test_unknown_source_is_refused(self):
        with self.assertRaises(EngineError):
            make_sense(lemma="x", english_face="x", source="hearsay")


class CollisionPolicy(unittest.TestCase):
    def test_senses_are_keyed_by_lemma_type_sig_and_source(self):
        a = sense_key("field", "Type -> Type", "mathlib")
        b = sense_key("field", "Type -> Type", "general")
        c = sense_key("field", "M -> V", "mathlib")
        self.assertEqual(len({a, b, c}), 3)

    def test_same_lemma_from_three_sources_gives_three_senses(self):
        registry = Registry()
        for source, type_sig in (("mathlib", "Type -> Type"), ("convention", "M -> V"), ("general", None)):
            registry.add(make_sense(lemma="field", english_face=f"field ({source})",
                                    source=source, type_sig=type_sig))
        self.assertEqual(len(registry.senses_for("field")), 3)

    def test_re_adding_an_identical_sense_is_idempotent(self):
        registry = Registry()
        for _ in range(3):
            registry.add(make_sense(lemma="cone", english_face="convex cone", source="convention"))
        self.assertEqual(len(registry.senses), 1)

    def test_merging_is_refused_at_import_time(self):
        with self.assertRaises(EngineError) as ctx:
            merge_senses("a", "b")
        self.assertIn("mint", str(ctx.exception).lower())

    def test_lemma_index_finds_a_sense_by_any_face_token(self):
        registry = Registry()
        registry.add(make_sense(lemma="kernel", english_face="integral kernel", source="convention"))
        index = registry.lemma_index()
        self.assertIn("kernel", index)
        self.assertIn("integral", index)


class SenseSelection(unittest.TestCase):
    def _registry(self):
        registry = Registry()
        registry.add(make_sense(lemma="ring", english_face="ring", source="convention",
                                frames=["algebra", "ring_theory"], sense_id="tech"))
        registry.add(make_sense(lemma="ring", english_face="ring (jewellery)", source="general",
                                frames=["general"], sense_id="gen"))
        return registry

    def test_technical_context_picks_the_technical_sense(self):
        registry = self._registry()
        text = "Let R be a commutative ring with an ideal I."
        sel = select_sense("ring", registry.candidates_for("ring"),
                           infer_frames(text), tokens(text))
        self.assertEqual(sel.chosen, "tech")

    def test_general_context_picks_the_general_sense(self):
        registry = self._registry()
        text = "She wore a silver ring."
        sel = select_sense("ring", registry.candidates_for("ring"),
                           infer_frames(text), tokens(text))
        self.assertEqual(sel.chosen, "gen")

    def test_undecidable_context_returns_an_honest_fiber_not_a_coin_flip(self):
        registry = Registry()
        for i in (1, 2):
            registry.add(make_sense(lemma="x", english_face=f"x{i}", source="convention",
                                    frames=["algebra"], sense_id=f"s{i}"))
        sel = select_sense("x", registry.candidates_for("x"), ["algebra"])
        self.assertFalse(sel.decided)
        self.assertIn(ABSTAIN, sel.fiber)
        self.assertEqual(len(sel.fiber), 3)

    def test_selection_is_deterministic(self):
        registry = self._registry()
        text = "Let R be a commutative ring with an ideal I."
        a = select_sense("ring", registry.candidates_for("ring"), infer_frames(text), tokens(text))
        b = select_sense("ring", registry.candidates_for("ring"), infer_frames(text), tokens(text))
        self.assertEqual(a.chosen, b.chosen)
        self.assertEqual(a.scores, b.scores)

    def test_source_beta_cannot_overturn_frame_evidence(self):
        """The guard that stops WordNet, imported last, from shadowing a technical sense."""
        registry = self._registry()
        text = "Let R be a commutative ring with an ideal I."
        sel = select_sense("ring", registry.candidates_for("ring"), infer_frames(text), tokens(text))
        scores = dict(sel.scores)
        self.assertGreater(scores["tech"], scores["gen"])


class FrameInference(unittest.TestCase):
    def test_cue_matching_respects_word_boundaries(self):
        """The bug that made 'a perfectly normal Tuesday' read as analysis."""
        self.assertNotIn("analysis", infer_frames("It was a perfectly normal Tuesday."))

    def test_plurals_still_match(self):
        frames = infer_frames("Disjoint closed sets have disjoint open neighbourhoods.")
        self.assertIn("topology", frames)

    def test_an_ambiguous_word_is_not_its_own_cue(self):
        self.assertEqual(infer_frames("She is a leading researcher in her field."), frozenset({"general"}))
        self.assertEqual(infer_frames("She wore a silver ring."), frozenset({"general"}))

    def test_no_cue_hit_falls_back_to_general(self):
        self.assertEqual(infer_frames("qqq zzz"), frozenset({"general"}))


class ImportOrder(unittest.TestCase):
    def test_import_all_runs_the_five_sources_in_the_fixed_order(self):
        _, results = import_all({})
        self.assertEqual([r.source for r in results],
                         ["mathlib", "convention", "nlab", "preminted", "wordnet"])
        self.assertEqual(len(SOURCE_ORDER), 5)

    def test_unresolved_pins_block_rather_than_fake_a_result(self):
        _, results = import_all({})
        blocked = {r.source for r in results if r.status == "blocked"}
        self.assertEqual(blocked, {"mathlib", "nlab", "preminted", "wordnet"})

    def test_convention_table_always_imports(self):
        _, results = import_all({})
        convention = next(r for r in results if r.source == "convention")
        self.assertEqual(convention.status, "imported")
        self.assertGreater(convention.added, 100)

    def test_registry_is_byte_identical_across_runs_at_the_same_pins(self):
        """SPEC section 3: any diff is a bug."""
        a, _ = import_all({})
        b, _ = import_all({})
        self.assertEqual(a.serialize(), b.serialize())
        self.assertEqual(a.digest(), b.digest())

    def test_mathlib_import_is_pre_bound_and_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry()
            result = import_mathlib(registry, _mathlib_dump(Path(tmp)), "abc123def456")
            self.assertEqual(result.status, "imported")
            self.assertEqual(result.added, 5)
            self.assertTrue(all(s.display.face_warrant == "rendered" for s in registry.senses))
            self.assertTrue(all(s.core.formal_faces for s in registry.senses))

    def test_mathlib_formal_faces_keep_case_and_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry()
            import_mathlib(registry, _mathlib_dump(Path(tmp)), "abc")
            surfaces = {f.surface for s in registry.senses for f in s.core.formal_faces}
            self.assertIn("Mathlib.Order.Cone.IsPositive", surfaces,
                          "no silent normalization: case and namespace path survive")

    def test_convention_table_drops_unbacked_formal_candidates(self):
        registry = Registry()
        result = import_convention_table(registry)
        self.assertGreater(len(result.stats["dropped_formal_candidates"]), 0)
        self.assertTrue(all(not s.core.formal_faces for s in registry.senses),
                        "with no Mathlib import, no candidate resolves and none is invented")

    def test_convention_table_binds_when_mathlib_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry()
            import_mathlib(registry, _mathlib_dump(Path(tmp)), "abc")
            import_convention_table(registry)
            compact = [s for s in registry.senses_for("compact") if s.core.formal_faces]
            self.assertTrue(compact, "IsCompact is in the dump, so compact_Anglo should bind")

    def test_convention_senses_keep_their_declared_tier(self):
        registry = Registry()
        import_convention_table(registry)
        sources = {s.core.source for s in registry.senses}
        self.assertIn("general", sources, "hand-seeded general senses stay general-tier")
        self.assertIn("convention", sources)

    def test_nlab_contributes_edges_not_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nlab.json"
            path.write_text(json.dumps({
                "aliases": [{"canonical": "convex cone", "aliases": ["positive cone"],
                             "frames": ["convexity"]}]
            }), encoding="utf-8")
            registry = Registry()
            result = import_nlab(registry, path, "2026-07-01")
            self.assertEqual(result.status, "imported")
            self.assertGreater(result.edges, 0)
            for sense in registry.senses:
                if sense.core.source == "nlab":
                    self.assertEqual(sense.display.gloss, "",
                                     "nLab glosses are perspectival: edges and aliases, not authority")

    def test_wordnet_reports_gap_fill_versus_coexisting(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wn.json"
            path.write_text(json.dumps({"entries": [
                {"lemma": "ring", "senses": [{"english_face": "ring (jewellery)", "gloss": "circular band"}]},
                {"lemma": "banana", "senses": [{"english_face": "banana", "gloss": "a fruit"}]},
            ]}), encoding="utf-8")
            registry = Registry()
            import_convention_table(registry)
            result = import_wordnet(registry, path, "3.1")
            self.assertEqual(result.status, "imported")
            self.assertEqual(result.stats["gap_fill_lemmas"], 1)
            self.assertGreaterEqual(len(registry.senses_for("ring")), 4,
                                    "the general sense coexists; it never replaces the technical ones")

    def test_preminted_senses_are_not_merged_into_general_ones(self):
        registry = Registry()
        doc = Document("preminted:GLOSSARY.md", "english",
                       "- **fiber** — a co-reference hypothesis over at most five slots\n", "seed")
        result = import_preminted(registry, [doc])
        self.assertEqual(result.added, 1)
        self.assertEqual(registry.senses_for("fiber")[0].core.source, "preminted")

    def test_lemma_of_skips_leading_function_words(self):
        self.assertEqual(lemma_of("is positive"), "positive")
        self.assertEqual(lemma_of("kernel"), "kernel")


class StaticChecks(unittest.TestCase):
    def test_the_real_tree_is_clean(self):
        self.assertTrue(check_no_display_on_f_path().ok)

    def test_a_planted_violation_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            (root / "adapters").mkdir()
            for rel in ("energy", "settle", "meter", "cast", "blocks", "pipeline", "mint_tape", "linalg"):
                (root / "engine" / f"{rel}.py").write_text("x = 1\n", encoding="utf-8")
            # The violation: an F-path module reaching for a display string.
            (root / "engine" / "energy.py").write_text(
                "def f(sense):\n    return sense.display.gloss\n", encoding="utf-8"
            )
            (root / "engine" / "lexicon.py").write_text(
                "def select_sense():\n    pass\n\ndef q_edges():\n    pass\n", encoding="utf-8"
            )
            result = check_no_display_on_f_path(root)
            self.assertFalse(result.ok)
            self.assertTrue(any(v.attr in {"gloss", "display"} for v in result.violations))

    def test_a_subscript_dodge_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "engine").mkdir()
            for rel in ("energy", "settle", "meter", "cast", "blocks", "pipeline", "mint_tape", "linalg"):
                (root / "engine" / f"{rel}.py").write_text("x = 1\n", encoding="utf-8")
            (root / "engine" / "meter.py").write_text(
                "def f(d):\n    return d['english_face']\n", encoding="utf-8"
            )
            (root / "engine" / "lexicon.py").write_text(
                "def select_sense():\n    pass\n\ndef q_edges():\n    pass\n", encoding="utf-8"
            )
            self.assertFalse(check_no_display_on_f_path(root).ok)


class LexiconNullCells(unittest.TestCase):
    def test_cell_vi_passes_on_the_convention_table(self):
        registry = Registry()
        import_convention_table(registry)
        cell = cell_vi_hub_coverage(registry)
        self.assertIs(cell.status, NullStatus.PASS)
        self.assertEqual(cell.stats["faceless"], [])

    def test_cell_vi_fails_when_a_sense_has_no_face(self):
        registry = Registry()
        sense = make_sense(lemma="x", english_face="x", source="mathlib")
        import dataclasses
        broken = dataclasses.replace(sense, display=dataclasses.replace(sense.display, english_face=""))
        registry.add(broken)
        self.assertIs(cell_vi_hub_coverage(registry).status, NullStatus.FAIL)

    def test_cell_vi_blocked_without_a_registry(self):
        self.assertIs(cell_vi_hub_coverage(None).status, NullStatus.BLOCKED)

    def test_cell_vii_passes_on_the_pre_registered_probes(self):
        registry = Registry()
        import_convention_table(registry)
        cell = cell_vii_shadow(registry)
        self.assertIs(cell.status, NullStatus.PASS, cell.detail)
        self.assertEqual(cell.stats["shadowing"], [])
        self.assertEqual(cell.stats["overreach"], [])

    def test_cell_vii_detects_shadowing(self):
        """A general sense engineered to win a technical context must fail the cell.

        Merely *matching* the technical sense's frames is not enough — that ties, and a
        tie is an abstention, which is the designed honest-fiber outcome rather than a
        failure. A general sense shadows when it claims a strictly *tighter* frame match
        than the technical sense: here `{measure_theory}` exactly, against the real
        sense's `{measure_theory, probability}`, in a context that fires only the former.
        """
        registry = Registry()
        import_convention_table(registry)
        registry.add(make_sense(
            lemma="measure", english_face="measure (shadow)", source="general",
            frames=["measure_theory"], sense_id="shadow_measure",
        ))
        cell = cell_vii_shadow(registry)
        self.assertIs(cell.status, NullStatus.FAIL)
        self.assertTrue(cell.stats["shadowing"])
        self.assertEqual(cell.stats["shadowing"][0]["chosen"], "shadow_measure")
        self.assertIn("rejects the seed", cell.detail)

    def test_a_tie_abstains_rather_than_shadowing(self):
        """The complement: equal frames must not be read as shadowing — they abstain.

        `source_beta` is not a term in the selection score, so a general-tier twin of
        `ring_unital` with identical frames ties with it. A tie emits the fiber; the
        engine then resolves it inside F with `source_beta` as prior energy. Nothing is
        decided by authority outside F.
        """
        registry = Registry()
        import_convention_table(registry)
        registry.add(make_sense(
            lemma="ring", english_face="ring (twin)", source="general",
            frames=["algebra", "ring_theory", "unital"], sense_id="twin_ring",
        ))
        cell = cell_vii_shadow(registry)
        self.assertEqual(cell.stats["shadowing"], [])
        self.assertTrue(any(u["lemma"] == "ring" for u in cell.stats["undecided"]))

    def test_cell_viii_always_runs(self):
        cell = cell_viii_no_clamp_grep()
        self.assertIn(cell.status, {NullStatus.PASS, NullStatus.FAIL})
        self.assertIsNot(cell.status, NullStatus.BLOCKED)

    def test_cell_ix_round_trips_mathlib_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry()
            import_mathlib(registry, _mathlib_dump(Path(tmp)), "abc123")
            cell = cell_ix_binding_sanity(registry, "seed", sample=50)
            self.assertIs(cell.status, NullStatus.PASS, cell.detail)
            self.assertEqual(cell.stats["rate"], 0.0)

    def test_cell_ix_blocked_without_mathlib_senses(self):
        registry = Registry()
        import_convention_table(registry)
        self.assertIs(cell_ix_binding_sanity(registry, "seed").status, NullStatus.BLOCKED)

    def test_cell_ix_fails_above_the_five_percent_bar(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = Registry()
            import_mathlib(registry, _mathlib_dump(Path(tmp)), "abc123")
            # Break every binding: swap each face for one that addresses nowhere.
            import dataclasses
            for lemma, entry in list(registry.entries.items()):
                senses = tuple(
                    dataclasses.replace(
                        s, display=dataclasses.replace(s.display, english_face=f"broken {s.sense_id}")
                    )
                    for s in entry.senses
                )
                registry.entries[lemma] = dataclasses.replace(entry, senses=senses)
            cell = cell_ix_binding_sanity(registry, "seed")
            self.assertIs(cell.status, NullStatus.FAIL)
            self.assertIn("importer bug", cell.detail)


class LexiconQEdges(unittest.TestCase):
    def test_synonym_edges_become_equivalence_priors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nlab.json"
            path.write_text(json.dumps({
                "aliases": [{"canonical": "convex cone", "aliases": ["positive cone"]}]
            }), encoding="utf-8")
            registry = Registry()
            import_nlab(registry, path, "2026-07-01")
            edges = registry.q_edges()
            self.assertTrue(edges)
            self.assertTrue(all(e.origin == "lexicon" for e in edges))
            self.assertTrue(all(e.u < e.v for e in edges), "edges are canonically ordered")


if __name__ == "__main__":
    unittest.main()
