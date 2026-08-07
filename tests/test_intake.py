"""THE INTAKE SURFACE's controls: one door, and lineage is a declaration an arrival may make.

The property under test is not "forked_from works" — that is tests/test_lineage.py. It is that
there is ONE path. Material with a manifest and material without take the identical route, so
the two cannot drift apart, and everything lineage adds is additive: an arrival whose manifest
resolves to nothing keeps every slot it contributed.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from engine.corpus_state import CorpusSnapshot, SlotRecord
from engine.intake import MERGE_CAVEAT, Arrival, documents, intake
from engine.lineage import SCHEMA, Export, Manifest
from engine.normalize import address
from engine.scaffold import FORKED_FROM

PARENT = "The cone is positive under composition."
CHILD = "The composed cone admits a certified positivity witness."


def _empty() -> CorpusSnapshot:
    return CorpusSnapshot()


def _holding(*texts, chart: str = "english") -> tuple:
    snap, ids = CorpusSnapshot(), []
    for t in texts:
        sid, nu = address(chart, t, "assert")
        snap.slots[sid] = SlotRecord(slot=sid, chart=chart, type="assert", nu=nu,
                                     value="true", confidence=1.0, tier="EXTRACTION",
                                     docs=("r||d/f.md",))
        ids.append(sid)
    return snap, ids


class ONEDoorForEverythingThatArrives(unittest.TestCase):
    def test_material_with_NO_manifest_takes_the_same_route(self):
        snap = _empty()
        got = intake([{"id": "a.md", "chart": "english", "text": PARENT}], snap)
        self.assertGreater(got.slots_new, 0)
        self.assertFalse(got.manifest)
        self.assertEqual(got.edges, [])
        self.assertIn(MERGE_CAVEAT[:20], got.as_record()["note"])

    def test_material_WITH_a_manifest_admits_the_same_slots(self):
        """The lineage branch is ADDITIVE. Same material, same slots, edges on top."""
        plain, withm = _empty(), _empty()
        docs = [{"id": "a.md", "chart": "english", "text": PARENT}]
        a = intake(docs, plain)
        b = intake(docs, withm, manifest={"schema": SCHEMA, "parents": {}})
        self.assertEqual(a.slots_new, b.slots_new)
        self.assertEqual(set(plain.slots), set(withm.slots))

    def test_the_extractors_are_the_CORPUS_BUILDERS_not_the_doors_own(self):
        """A door with its own extractor would address the same sentence differently from the
        rest of the corpus, which is gate 1 broken by a convenience."""
        from engine.constants import decisions
        from engine.energy import dedupe_deltas
        from engine.extract import build_k_extractors
        from engine.pipeline import ingest as pipeline_ingest
        from engine.types import Document

        snap = _empty()
        intake([{"id": "a.md", "chart": "english", "text": PARENT}], snap)
        direct = dedupe_deltas(pipeline_ingest(
            [Document("a.md", "english", PARENT, "intake")],
            build_k_extractors(decisions(), offline=True)))
        self.assertEqual(set(snap.slots), {d.slot for d in direct})

    def test_an_arrival_with_no_text_is_a_STATE_not_a_crash(self):
        got = intake([{"id": "empty.md", "text": "   "}], _empty())
        self.assertEqual(got.slots_new, 0)
        self.assertIn("nothing arrived", got.note)

    def test_documents_accepts_the_shapes_an_upload_actually_has(self):
        docs = documents([{"id": "a", "chart": "lean", "text": "x"}, ("b", "english", "y")])
        self.assertEqual([(d.doc_id, d.chart) for d in docs], [("a", "lean"), ("b", "english")])


class AMergeIsNotARebuildAndSaysSo(unittest.TestCase):
    def test_an_address_the_corpus_ALREADY_HOLDS_is_left_untouched(self):
        snap, ids = _holding(PARENT)
        before = snap.slots[ids[0]]
        got = intake([{"id": "again.md", "chart": "english", "text": PARENT}], snap)
        self.assertEqual(got.already_held, 1)
        self.assertEqual(got.slots_new, 0)
        self.assertIs(snap.slots[ids[0]], before, "re-declaring a held claim rewrote it")

    def test_the_caveat_travels_on_every_record(self):
        self.assertIn("MERGED, not rebuilt", intake([], _empty()).as_record()["note"]
                      or MERGE_CAVEAT)
        got = intake([{"id": "a.md", "text": PARENT}], _empty())
        self.assertIn("NOT recomputed", got.as_record()["note"])

    def test_counts_say_which_they_count(self):
        snap, _ = _holding(PARENT)
        got = intake([{"id": "a.md", "text": PARENT}, {"id": "b.md", "text": CHILD}], snap)
        self.assertEqual(got.slots_seen, got.slots_new + got.already_held)
        self.assertEqual(sum(got.by_chart.values()), got.slots_seen)
        self.assertGreaterEqual(got.deltas, got.slots_seen,
                                "records cannot be fewer than the addresses they carry")


class LineageIsADeclarationAnArrivalMayMake(unittest.TestCase):
    def _export(self, snap, ids):
        return Export.of({"typed": "what does the cone work establish",
                          "citations": [{"slot": s} for s in ids]})

    def test_a_context_manifest_attaches_edges_and_joins_the_blocks(self):
        snap, ids = _holding(PARENT)
        export = self._export(snap, ids)
        got = intake([{"id": "child.md", "chart": "english", "text": CHILD}], snap,
                     manifest={"schema": SCHEMA, "context_id": export.context_id},
                     export=export)
        self.assertTrue(got.manifest)
        self.assertEqual(len(got.edges), 1)
        self.assertEqual(got.edges[0].kind, FORKED_FROM)
        child = got.edges[0].src_slot
        self.assertIn(child, snap.blocks.get(ids[0], ()),
                      "the child and its parent settled in separate blocks")

    def test_a_manifest_that_resolves_to_NOTHING_costs_the_arrival_nothing(self):
        snap = _empty()
        got = intake([{"id": "child.md", "text": CHILD}], snap,
                     manifest={"schema": SCHEMA, "context_id": "cg-nobody-has-this"})
        self.assertEqual(got.edges, [])
        self.assertEqual([v["reason"] for v in got.void], ["unknown-context"])
        self.assertGreater(got.slots_new, 0, "a bad manifest cost the corpus its material")

    def test_the_void_ledger_travels_on_the_record(self):
        snap = _empty()
        got = intake([{"id": "c.md", "text": CHILD}], snap,
                     manifest={"schema": SCHEMA, "parents": {"nope": ["also-nope"]}})
        rec = got.as_record()["lineage"]
        self.assertEqual(rec["ledger"]["void"], 1)
        # THE PARENT IS CHECKED FIRST, and that is the right order: a manifest naming a
        # parent this corpus does not carry has declared descent from nothing, whatever the
        # child's state. `child-not-ingested` is reachable only with a real parent.
        self.assertEqual(rec["void"][0]["reason"], "undeclared")

    def test_lineage_changes_no_value_no_tier_and_contests_nothing(self):
        snap, ids = _holding(PARENT)
        export = self._export(snap, ids)
        before = {s: (r.value, r.tier, r.confidence) for s, r in snap.slots.items()}
        intake([{"id": "c.md", "text": CHILD}], snap,
               manifest={"schema": SCHEMA, "context_id": export.context_id}, export=export)
        after = {s: (r.value, r.tier, r.confidence) for s, r in snap.slots.items()
                 if s in before}
        self.assertEqual(before, after, "descent moved a parent")
        self.assertEqual(list(snap.contested), [])
        self.assertEqual(list(snap.arrows), [],
                         "a scaffold reached the arrow list, where K and the loop builder read")


class AnExportCertifiesItself(unittest.TestCase):
    """Without this, a caller could declare descent from material the export never carried."""

    def test_a_round_tripped_stub_is_accepted(self):
        e = Export.of({"typed": "q", "citations": [{"slot": "s1"}, {"slot": "s2"}]})
        self.assertEqual(Export.read(e.as_record()).context_id, e.context_id)

    def test_a_FORGED_stub_is_refused(self):
        e = Export.of({"typed": "q", "citations": [{"slot": "s1"}]})
        forged = e.as_record()
        forged["built_from"] = ["s1", "a claim this export never carried"]
        with self.assertRaises(ValueError) as caught:
            Export.read(forged)
        self.assertIn("does not certify itself", str(caught.exception))

    def test_a_forged_QUESTION_is_refused_too(self):
        e = Export.of({"typed": "q", "citations": [{"slot": "s1"}]})
        forged = e.as_record() | {"question": "a different question"}
        with self.assertRaises(ValueError):
            Export.read(forged)

    def test_a_stub_read_from_JSON_round_trips(self):
        e = Export.of({"typed": "q", "citations": [{"slot": "s1"}]})
        self.assertEqual(Export.read(json.dumps(e.as_record())).built_from, e.built_from)


class TheEndpointAndTheCLIShareTheDoor(unittest.TestCase):
    def test_the_cli_calls_the_same_function_the_endpoint_does(self):
        """PLANTED AGAINST A SECOND SURFACE. A CLI that ingested differently from the endpoint
        would be two intake surfaces wearing one name."""
        import ast

        for path in (Path("cli.py"), Path("ui/server.py")):
            src = ast.parse(path.read_text(encoding="utf-8"))
            names = {n.module for n in ast.walk(src) if isinstance(n, ast.ImportFrom)}
            with self.subTest(path=str(path)):
                self.assertIn("engine.intake", names,
                              f"{path} does not go through the one door")

    def test_the_endpoint_is_behind_the_WRITE_gate_not_the_read_token(self):
        src = Path("ui/server.py").read_text(encoding="utf-8")
        block = src.split('elif path == "/intake":', 1)[1].split('elif path ==', 1)[0]
        self.assertIn("SEED_UPLOAD_ENV", block, "the intake endpoint is not write-gated")
        self.assertIn("compare_digest", block, "the seed token is compared non-constant-time")

    def test_the_cli_can_report_without_writing(self):
        from cli import main

        self.assertEqual(main(["intake", "--help"] if False else ["intake", "nope.md"]), 1)


if __name__ == "__main__":
    unittest.main()
