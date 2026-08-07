"""FORKED_FROM's controls, c1-c4, planted as seed/SCAFFOLD.md numbered them.

What they are all one control for: LINEAGE IS DECLARED, AND IT IS INFORMATION RATHER THAN
AUTHORITY. Every other property here is a way for one of those two to fail quietly — an edge
inferred from what an artifact resembles, or an edge that moves a value because a child said
it descended from a parent.
"""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from engine.corpus_state import CorpusSnapshot, SlotRecord
from engine.lineage import SCHEMA, Export, Manifest, admit, edges_from
from engine.normalize import address
from engine.scaffold import (COMMIT_ANCESTRY, FORKED_FROM, MANIFEST, Scaffold,
                             confers_authority, holonomy_excluded, k_eligible)

MODULE = Path(__file__).resolve().parents[1] / "engine" / "lineage.py"


def _snap(*texts, chart: str = "english") -> tuple:
    slots, ids = {}, []
    for t in texts:
        sid, nu = address(chart, t, "assert")
        slots[sid] = SlotRecord(slot=sid, chart=chart, type="assert", nu=nu, value="true",
                                confidence=1.0, tier="EXTRACTION", docs=("r||d/f.md",))
        ids.append(sid)
    return CorpusSnapshot(slots=slots, arrows=()), ids


class C1LineageIsDeclaredNeverInferred(unittest.TestCase):
    """The edge names a manifest or commit ancestry, or it cannot be constructed at all."""

    def test_an_edge_with_no_declared_source_CANNOT_BE_BUILT(self):
        with self.assertRaises(ValueError) as caught:
            Scaffold(chart="lean", src_slot="a", dst_slot="b", kind=FORKED_FROM,
                     provenance="looked similar")
        self.assertIn("DECLARED, never inferred", str(caught.exception))

    def test_the_two_declared_sources_are_accepted(self):
        for source in (MANIFEST, COMMIT_ANCESTRY):
            with self.subTest(source=source):
                e = Scaffold(chart="lean", src_slot="a", dst_slot="b", kind=FORKED_FROM,
                             provenance=f"{source}:ctx-1")
                self.assertEqual(e.kind, FORKED_FROM)

    def test_a_depends_on_edge_is_unaffected_by_the_lineage_rule(self):
        """The constraint is on the KIND, not on the class: a dependency parsed out of source
        has never carried a manifest and must not start needing one."""
        e = Scaffold(chart="lean", src_slot="a", dst_slot="b", provenance="lean-parse")
        self.assertEqual(e.kind, "depends_on")

    def test_the_parser_holds_no_tokenizer_no_similarity_no_comparison(self):
        src = MODULE.read_text(encoding="utf-8")
        for banned in ("[a-z0-9]+", "[a-zA-Z]+", "\\w+", ".lower()", ".casefold()", "difflib",
                       "SequenceMatcher", "levenshtein", "jaccard", "startswith(",
                       "in nu", "similar"):
            self.assertNotIn(banned, src, f"a similarity path reached lineage: {banned}")

    def test_the_parser_reads_ADDRESSES_and_never_content(self):
        """AST, not prose: the module may not touch a slot record's text. It looks up `.chart`
        to tag the edge and nothing else — a parser that read `nu` would be one edit from
        comparing it."""
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        self.assertNotIn("nu", attrs, "the lineage parser reached for claim text")
        self.assertIn("chart", attrs)


class C2UnresolvableParentVoidsTheEdgeNotTheArtifact(unittest.TestCase):
    def test_an_unknown_parent_address_voids_and_is_LEDGERED(self):
        snap, ids = _snap("the cone is positive", "the kernel accepts")
        m = Manifest(parents={ids[0]: ("an address this corpus does not carry",)})
        got = admit(m, snap, contributed=[ids[0]])
        self.assertEqual(got["edges"], [])
        self.assertEqual([v["reason"] for v in got["void"]], ["undeclared"])
        self.assertEqual(got["ledger"]["void"], 1)
        self.assertEqual(got["ledger"]["references_seen"], 1)

    def test_a_manifest_citing_an_UNKNOWN_CONTEXT_voids_by_name(self):
        snap, ids = _snap("a", "b")
        got = admit(Manifest(context_id="cg-nobody-has-this"), snap, contributed=[ids[0]])
        self.assertEqual([v["reason"] for v in got["void"]], ["unknown-context"])

    def test_a_child_that_never_ingested_voids_rather_than_inventing_it(self):
        snap, ids = _snap("a", "b")
        got = admit(Manifest(parents={"a slot nobody ingested": (ids[1],)}), snap,
                    contributed=[])
        self.assertEqual([v["reason"] for v in got["void"]], ["child-not-ingested"])

    def test_self_descent_voids(self):
        snap, ids = _snap("a", "b")
        got = admit(Manifest(parents={ids[0]: (ids[0],)}), snap, contributed=[ids[0]])
        self.assertEqual([v["reason"] for v in got["void"]], ["self-descent"])

    def test_THE_ARTIFACT_STILL_INGESTS_when_every_parent_voids(self):
        """The whole point of resolve-or-void here. A bad manifest costs the lineage; it must
        never cost the corpus the claims that arrived with it."""
        snap, ids = _snap("a", "b")
        got = admit(Manifest(parents={ids[0]: ("nonsense",)}), snap, contributed=[ids[0]])
        self.assertEqual(got["edges"], [])
        self.assertIn(ids[0], snap.slots, "the artifact's own slot was disturbed")
        self.assertIn("ingests as ordinary material", got["note"])

    def test_a_document_that_is_not_a_manifest_is_REFUSED_not_guessed_at(self):
        for bad in ({"context_id": "cg-1"}, {"schema": "something/else", "context_id": "x"}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    Manifest.parse(bad)

    def test_an_unknown_source_is_refused(self):
        with self.assertRaises(ValueError):
            Manifest.parse({"schema": SCHEMA, "source": "vibes"})


class C3ClassContainment(unittest.TestCase):
    """Holds by construction. Asserted anyway, because "by construction" is a claim about code
    and code is edited."""

    def _edge(self):
        return Scaffold(chart="lean", src_slot="a", dst_slot="b", kind=FORKED_FROM,
                        provenance="manifest:ctx-1")

    def test_a_lineage_edge_is_never_K_eligible(self):
        self.assertFalse(k_eligible(self._edge()))

    def test_a_lineage_edge_is_holonomy_excluded(self):
        self.assertTrue(holonomy_excluded(self._edge()))

    def test_it_has_no_loop_eligible_attribute_to_set_WRONGLY(self):
        self.assertFalse(hasattr(self._edge(), "loop_eligible"))

    def test_it_cannot_be_stored_as_a_correspondence_kind(self):
        from engine.correspondence import KINDS

        self.assertNotIn(FORKED_FROM, KINDS,
                         "lineage became expressible as an equivalence")

    def test_scaffolds_never_enter_the_snapshots_ARROWS(self):
        """The containment rests on one fact: the loop builder and K read `arrows`, and
        scaffolds live in their own field. A merge anywhere would undo all of it silently."""
        snap, ids = _snap("a", "b")
        snap.scaffolds.append(self._edge())
        self.assertEqual(list(snap.arrows), [])
        self.assertEqual(snap.header()["arrows"], 0)


class C4LineageIsInformationNeverAuthority(unittest.TestCase):
    def test_no_lineage_edge_confers_authority(self):
        e = Scaffold(chart="lean", src_slot="a", dst_slot="b", kind=FORKED_FROM,
                     provenance="manifest:ctx-1")
        self.assertFalse(confers_authority(e))

    def test_admitting_descendants_MUTATES_NOTHING(self):
        """PLANTED: a fork demoting its parent. There is no path — `admit` returns edges and a
        ledger and touches neither the snapshot nor any value."""
        snap, ids = _snap("the parent claim", "the child claim")
        before = {sid: (r.value, r.tier, r.confidence) for sid, r in snap.slots.items()}
        admit(Manifest(parents={ids[1]: (ids[0],)}), snap, contributed=[ids[1]])
        after = {sid: (r.value, r.tier, r.confidence) for sid, r in snap.slots.items()}
        self.assertEqual(before, after, "admitting a descendant moved the parent")
        self.assertEqual(list(snap.contested), [], "descent contested a claim")
        self.assertEqual(list(snap.scaffolds), [],
                         "admit attached edges itself; deciding and applying must be separate")

    def test_the_module_holds_no_path_to_a_value_a_tier_or_a_contest(self):
        """AST, NOT GREP. The first version searched the source text for "contested" and hit
        the docstring saying nothing IS contested — a control convicting a sentence that
        states the property it enforces, which is the trap class one layer in. What must not
        exist is an ASSIGNMENT to a claim's value, tier or contest, and a CALL to the
        promotion machinery. Both are structure, and structure is what an AST reads.
        """
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        written = {t.attr for n in ast.walk(tree)
                   if isinstance(n, (ast.Assign, ast.AugAssign))
                   for t in ast.walk(n if isinstance(n, ast.AugAssign) else n)
                   if isinstance(t, ast.Attribute) and isinstance(t.ctx, ast.Store)}
        for banned in ("value", "tier", "contested", "confidence"):
            self.assertNotIn(banned, written, f"lineage assigned to {banned}")
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else
                  getattr(n.func, "id", "") for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for banned in ("promote", "demote", "supersede", "Clamp", "clamp", "propose",
                       "contest"):
            self.assertNotIn(banned, called, f"lineage called {banned}")


class TheExportStubMakesDeclarationPossible(unittest.TestCase):
    def test_the_context_id_is_DERIVED_from_the_content_not_minted(self):
        rec = {"typed": "what does X establish",
               "citations": [{"n": "e1", "slot": "s1"}, {"n": "e2", "slot": "s2"}]}
        self.assertEqual(Export.of(rec).context_id, Export.of(rec).context_id)
        other = Export.of({**rec, "typed": "a different question"})
        self.assertNotEqual(Export.of(rec).context_id, other.context_id)

    def test_the_id_does_not_depend_on_the_order_the_citations_arrived_in(self):
        a = Export.of({"typed": "q", "citations": [{"slot": "s1"}, {"slot": "s2"}]})
        b = Export.of({"typed": "q", "citations": [{"slot": "s2"}, {"slot": "s1"}]})
        self.assertEqual(a.context_id, b.context_id)

    def test_the_sheet_carries_the_stub_and_says_the_manifest_is_the_BUILDERS_act(self):
        from engine.export_sheet import sheet

        out = sheet({"typed": "q", "citations": [
            {"n": "e1", "slot": "s1", "kind": "attached", "chart": "english", "nu": "a"}]})
        self.assertIn("context_id:", out)
        self.assertIn(SCHEMA, out)
        self.assertIn("Writing the manifest is YOUR act", out)
        self.assertIn("DECLARED, never inferred", out)

    def test_a_manifest_round_trips_from_JSON(self):
        m = Manifest.parse(json.dumps({"schema": SCHEMA, "context_id": "cg-1",
                                       "parents": {"child": "parent"}}))
        self.assertEqual(m.context_id, "cg-1")
        self.assertEqual(m.parents, {"child": ("parent",)})


class DescendantsComeHomeAsChildren(unittest.TestCase):
    """The positive case, end to end: the family tree that made the whole thing worth doing."""

    def _built(self):
        snap, ids = _snap("the parent claim about the cone",
                          "a second parent about the kernel",
                          "the artifact that was built out of them")
        rec = {"typed": "what do these establish",
               "citations": [{"slot": ids[0]}, {"slot": ids[1]}]}
        return snap, ids, Export.of(rec)

    def test_a_context_manifest_expands_to_one_edge_per_parent(self):
        snap, ids, export = self._built()
        m = Manifest(context_id=export.context_id, era="build-1")
        got = edges_from(m, snap, contributed=[ids[2]], export=export)
        self.assertEqual(got.void, [])
        self.assertEqual({(e.src_slot, e.dst_slot) for e in got.edges},
                         {(ids[2], ids[0]), (ids[2], ids[1])})
        for e in got.edges:
            self.assertEqual(e.kind, FORKED_FROM)
            self.assertEqual(e.tier, "REFERENCE")
            self.assertTrue(e.provenance.startswith(f"{MANIFEST}:"))

    def test_a_per_file_parent_is_stronger_than_the_context_and_coexists_with_it(self):
        snap, ids, export = self._built()
        m = Manifest(context_id=export.context_id, parents={ids[2]: (ids[0],)})
        got = edges_from(m, snap, contributed=[ids[2]], export=export)
        pairs = [(e.src_slot, e.dst_slot) for e in got.edges]
        self.assertEqual(pairs.count((ids[2], ids[0])), 2,
                         "the context expansion and the explicit parent are two declarations")

    def test_a_cross_chart_fork_records_the_parents_chart(self):
        english, eids = _snap("an english claim about the cone")
        lean, lids = _snap("theorem cone_positive", chart="lean")
        merged = CorpusSnapshot(slots={**english.slots, **lean.slots}, arrows=())
        got = edges_from(Manifest(parents={lids[0]: (eids[0],)}), merged,
                         contributed=[lids[0]])
        self.assertEqual(len(got.edges), 1)
        self.assertEqual(got.edges[0].chart, "lean")
        self.assertEqual(got.edges[0].dst_chart, "english")


class DescentCOUPLES(unittest.TestCase):
    """ENERGY-VISIBLE, end to end. The property that made lineage worth declaring at all, and
    the one a suite of constructor checks would have left untested."""

    def _corpus(self, scaffolds=()):
        from engine.constants import decisions
        from engine.corpus_state import build_snapshot
        from engine.energy import dedupe_deltas
        from engine.extract import build_k_extractors
        from engine.pipeline import ingest, ledger_from_deltas
        from engine.types import Document

        texts = ["The cone is positive under composition. The kernel accepts every checked "
                 "statement.", "The composed cone admits a certified positivity witness."]
        docs = [Document(f"d{i}", "english", t, "src") for i, t in enumerate(texts)]
        deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
        return build_snapshot(ledger_from_deltas(deltas), (), scaffolds=scaffolds)

    def _with_lineage(self):
        base = self._corpus()
        parent = sorted(base.slots)[0]
        child = sorted(base.slots)[-1]
        edge = Scaffold(chart="english", src_slot=child, dst_slot=parent, kind=FORKED_FROM,
                        provenance="manifest:cg-test")
        return self._corpus([edge]), parent, child

    def test_a_perturbation_near_the_parent_reaches_the_child_ONLY_with_lineage(self):
        from engine.relax import relax

        lineage, parent, child = self._with_lineage()
        plain = self._corpus()
        bias = "The cone is positive under composition."
        without = {m.slot for m in relax(bias, plain).moved}
        with_it = {m.slot for m in relax(bias, lineage).moved}
        self.assertNotIn(child, without, "the fixture already coupled without lineage")
        self.assertIn(child, with_it, "descent did not couple: lineage is not energy-visible")

    def test_the_hop_reports_the_LINEAGE_KIND_and_its_REAL_tier(self):
        """A hop that printed EXTRACTION for a REFERENCE edge OVERSTATES warrant, which is the
        one direction a warrant report must never be wrong in. Found by the demo, not by a
        test, because `getattr(tier, "name", "EXTRACTION")` silently defaulted a plain string."""
        from engine.relax import relax

        lineage, parent, child = self._with_lineage()
        moved = {m.slot: m for m in relax("The cone is positive under composition.",
                                          lineage).moved}
        self.assertIn(child, moved)
        hops = moved[child].path
        self.assertTrue(hops, "the child moved with no declared path")
        self.assertEqual(hops[-1].kind, FORKED_FROM)
        self.assertEqual(hops[-1].tier, "REFERENCE",
                         "a reference-tier lineage hop was reported at a stronger tier")

    def test_lineage_joins_the_block_and_STILL_closes_no_loop(self):
        lineage, parent, child = self._with_lineage()
        self.assertIn(child, lineage.blocks.get(parent, ()),
                      "the child and parent settled in separate blocks")
        self.assertEqual(lineage.loops, 0)
        self.assertEqual(list(lineage.arrows), [],
                         "a scaffold reached the arrow list, where K and the loop builder read")


if __name__ == "__main__":
    unittest.main()
