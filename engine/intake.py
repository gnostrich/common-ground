"""THE INTAKE SURFACE — one door for material arriving from outside, lineage optional.

ONE DOOR, WHICH IS THE WHOLE POINT. This is not a `forked_from` feature with an ingestion step
bolted on; it is the intake path, and lineage is a thing an arrival may DECLARE about itself.
Material with no manifest travels the identical route and is treated identically — the manifest
branch adds edges and subtracts nothing, so "with lineage" and "without lineage" are not two
code paths that can drift apart.

WHAT ARRIVES. Documents, exactly as the corpus builder produces them: an id, a chart, and text.
They are routed and extracted by THE ORDINARY MACHINERY — `engine.router`, the K extractors,
`engine.pipeline.ingest` — because an intake path with its own extractor would be a second
mechanism for the one job the inlet exists to be.

WHAT A MERGE IS, STATED, BECAUSE IT IS NOT A REBUILD. The snapshot is a read view and does not
carry the deltas it was derived from, so arriving material cannot re-derive the whole corpus:
it is MERGED. New addresses are added; an address the corpus already holds is left exactly as
it was and counted as `already_held`, because re-declaring a claim the corpus carries is not
new information about it and this door confers no warrant. Contest status, fibers and the floor
are properties of the whole corpus and are NOT recomputed here — a full rebuild
(`proposerd.py build-snapshot`) is what recomputes them, and this says so rather than letting a
merged snapshot be mistaken for a rebuilt one.

WHAT LINEAGE ADDS, AND ALL IT ADDS. When a manifest accompanies the material, `engine.lineage`
resolves it against the merged corpus and the surviving edges are attached. Voids travel with
the result. No value moves, no tier changes, nothing is contested: lineage is information,
never authority, and a manifest that resolves to nothing costs the arrival nothing.

Spec: seed/SCAFFOLD.md. Controls in tests/test_intake.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: What this door does NOT do, said once here and repeated on every record it returns. A merge
#: that let itself be read as a rebuild would report a corpus-wide number nobody computed.
MERGE_CAVEAT = (
    "MERGED, not rebuilt. New addresses were added and existing ones left untouched. Contest "
    "status, fibers and the floor are properties of the whole corpus and were NOT recomputed "
    "— run a full snapshot build for those."
)


@dataclass
class Arrival:
    """One intake, and everything it did. Counts that each say what they count."""

    documents: int = 0
    #: RECORDS AND ADDRESSES, BOTH NAMED. The extractors produce several deltas per claim —
    #: K's voters each see the same sentence — so "how much arrived" and "how many addresses
    #: arrived" are different numbers. The first version called the delta count `slots_seen`,
    #: which reported three for one claim. Every count here says which it counts.
    deltas: int = 0
    slots_seen: int = 0
    slots_new: int = 0
    already_held: int = 0
    by_chart: dict = field(default_factory=dict)
    edges: list = field(default_factory=list)
    void: list = field(default_factory=list)
    ledger: dict = field(default_factory=dict)
    manifest: bool = False
    note: str = ""

    def as_record(self) -> dict:
        return {
            "documents": self.documents, "deltas": self.deltas,
            "slots_seen": self.slots_seen,
            "slots_new": self.slots_new, "already_held": self.already_held,
            "by_chart": dict(self.by_chart),
            "lineage": {
                "declared": self.manifest,
                "edges": [e.as_record() for e in self.edges],
                "void": list(self.void),
                "ledger": dict(self.ledger),
            },
            # THE CAVEAT IS ON EVERY RECORD, not only the ordinary one. A record whose own
            # note replaced it would be the one place a merge could be read as a rebuild.
            "note": f"{self.note} {MERGE_CAVEAT}".strip() if self.note else MERGE_CAVEAT,
        }


def documents(items) -> list:
    """Arriving material as Documents. Accepts the shapes an upload actually has.

    A dict per file (`{"id", "chart", "text"}`) or a `(id, chart, text)` triple. The chart is
    the arrival's DECLARATION about its own material, resolved by the ordinary router when it
    is a path and taken as given when it is named — this door does not classify text.
    """
    from .types import Document

    out = []
    for i, item in enumerate(items or ()):
        if isinstance(item, dict):
            doc_id = str(item.get("id") or f"intake-{i}")
            chart = str(item.get("chart") or "english")
            text = str(item.get("text") or "")
        else:
            doc_id, chart, text = (list(item) + ["", "", ""])[:3]
            doc_id, chart, text = str(doc_id), str(chart or "english"), str(text)
        if text.strip():
            out.append(Document(doc_id, chart, text, "intake"))
    return out


def intake(items, snapshot, manifest=None, export=None) -> Arrival:
    """THE DOOR. Material in, merged; lineage attached when it is declared.

    `manifest` is an `engine.lineage.Manifest`, a manifest document, or None. None is the
    ordinary case and takes the identical route — that is what makes this the intake surface
    rather than a lineage feature.

    MUTATES THE SNAPSHOT, which is the one thing this function is for. It is separated from
    `lineage.admit`, which decides and mutates nothing, so a caller can inspect what lineage
    WOULD attach before anything is attached.
    """
    from .constants import decisions
    from .corpus_state import SlotRecord, _join_blocks_over
    from .energy import dedupe_deltas
    from .extract import build_k_extractors
    from .lineage import Manifest, admit
    from .pipeline import ingest

    docs = documents(items)
    out = Arrival(documents=len(docs))
    if not docs:
        out.note = "nothing arrived: no document carried text"
        return out

    # THE ORDINARY MACHINERY. Same extractors, same dedupe, same addressing the corpus builder
    # uses — a door with its own extractor would address the same sentence differently from the
    # rest of the corpus, which is gate 1 broken by a convenience.
    deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
    # DISTINCT ADDRESSES, in arrival order. `contributed` feeds the lineage expansion, and a
    # list carrying one address three times declared the same descent three times — three
    # records of one claim, which is the records-versus-pairs law broken at the door.
    contributed: list[str] = []
    seen: set[str] = set()
    for d in deltas:
        out.deltas += 1
        if d.slot in seen:
            continue
        seen.add(d.slot)
        out.slots_seen += 1
        out.by_chart[d.chart] = out.by_chart.get(d.chart, 0) + 1
        contributed.append(d.slot)
        if d.slot in snapshot.slots:
            out.already_held += 1
            continue
        snapshot.slots[d.slot] = SlotRecord(
            slot=d.slot, chart=d.chart, type=d.type, nu=d.nu, value=d.value,
            confidence=float(d.confidence), tier=d.warrant.tier.name,
            docs=(d.provenance.doc_id,))
        out.slots_new += 1

    if manifest is None:
        return out

    # LINEAGE, DECLARED. Everything below is additive: no branch here can change a value, a
    # tier or a contest, and an arrival whose manifest resolves to nothing keeps every slot it
    # just contributed.
    out.manifest = True
    m = manifest if isinstance(manifest, Manifest) else Manifest.parse(manifest)
    got = admit(m, snapshot, contributed=contributed, export=export)
    out.edges = list(got["scaffolds"])
    out.void = list(got["void"])
    out.ledger = dict(got["ledger"])
    if out.edges:
        snapshot.scaffolds = list(snapshot.scaffolds) + out.edges
        # THE FAMILY TREE ENTERS THE PHYSICS HERE and nowhere else: joining the blocks a
        # lineage edge spans is what makes a perturbation near a parent able to reach a child.
        _join_blocks_over(snapshot)
    return out
