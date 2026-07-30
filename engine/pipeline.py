"""Ingestion -> addressing -> priors -> blocks -> settlement -> meter.

One place where the pieces are wired, so that the null battery, the phases, and the audit
all exercise the same path. A cell that passed against a bespoke wiring would prove
nothing about the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .blocks import (
    build_blocks,
    build_fibers,
    edges_from_fibers,
    is_contested,
    loops_from_fibers,
)
from .energy import dedupe_deltas, evidence_from_deltas, lexicon_prior
from .extract import Extractor, slots_from_deltas
from .linalg import Vector
from .meter import MeterResult, measure, second_fdt_surrogate_floor, surrogate_floor_distribution
from .types import (
    Block,
    BValue,
    Chart,
    Clamp,
    Delta,
    Document,
    Fiber,
    LoopSpec,
    QEdge,
    SettledBlock,
    Slot,
)


@dataclass(slots=True)
class Ledger:
    deltas: list[Delta]
    slots: list[Slot]
    fibers: list[Fiber]
    edges: list[QEdge]
    blocks: list[Block]
    evidence: dict[str, Vector]
    priors: dict[str, Vector]
    chart_of: dict[str, Chart]
    loops: list[LoopSpec]
    clamps: list[Clamp] = field(default_factory=list)

    @property
    def contested_blocks(self) -> list[Block]:
        return [b for b in self.blocks if is_contested(b, self.deltas)]

    def summary(self) -> dict[str, int]:
        return {
            "documents": len({d.provenance.doc_id for d in self.deltas}),
            "deltas": len(self.deltas),
            "slots": len(self.slots),
            "fibers": len(self.fibers),
            "edges": len(self.edges),
            "blocks": len(self.blocks),
            "contested_blocks": len(self.contested_blocks),
            "loops": len(self.loops),
            "clamps": len(self.clamps),
        }


def ingest(
    documents: Sequence[Document],
    extractors: Sequence[Extractor],
) -> list[Delta]:
    """Run every extractor over every document. k-coverage is total by construction."""
    out: list[Delta] = []
    for doc in documents:
        for extractor in extractors:
            out.extend(extractor.extract(doc))
    return out


def build_ledger(
    documents: Sequence[Document],
    extractors: Sequence[Extractor],
    clamps: Sequence[Clamp] = (),
    prior_leaning: Mapping[str, BValue] | None = None,
    edge_filter=None,
) -> Ledger:
    """Full ingestion path. `edge_filter` is the hook PREREG R4 uses to drop Q edges."""
    deltas = dedupe_deltas(ingest(documents, extractors))
    slots = slots_from_deltas(deltas)
    fibers = build_fibers(slots)
    edges = edges_from_fibers(fibers, slots)
    if edge_filter is not None:
        edges = list(edge_filter(edges))
    blocks = build_blocks(slots, edges, deltas)
    chart_of = {s.id: s.chart for s in slots}
    active = {s.id for s in slots}
    loops = loops_from_fibers(fibers, chart_of, restrict_to=active)

    return Ledger(
        deltas=deltas,
        slots=slots,
        fibers=fibers,
        edges=edges,
        blocks=blocks,
        evidence=evidence_from_deltas(deltas),
        priors=lexicon_prior([s.id for s in slots], prior_leaning),
        chart_of=chart_of,
        loops=loops,
        clamps=list(clamps),
    )


def run_meter(
    ledger: Ledger,
    beta: float,
    seed_hash: str,
    shadow_cfg: Mapping[str, object],
    retained: Mapping[str, Mapping[str, Vector]] | None = None,
) -> tuple[MeterResult, dict[str, SettledBlock], dict[str, SettledBlock]]:
    """Measure every loop, on both arms, at one beta.

    `retained` is the warm arm's carried state, keyed by block id — in P4 it comes from
    P3's settlement. Absent it, the warm arm resumes from the cold arm's own result,
    which is the weakest honest warm arm available in-process and is reported as such.
    """
    result = MeterResult(seed_hash=seed_hash)
    warm_states: dict[str, SettledBlock] = {}
    cold_states: dict[str, SettledBlock] = {}

    for block in ledger.blocks:
        loops = [l for l in ledger.loops if set(l.slots) <= set(block.slots)]
        if not loops:
            continue
        rows, warm, cold = measure(
            block=block,
            loops=loops,
            evidence=ledger.evidence,
            priors=ledger.priors,
            chart_of=ledger.chart_of,
            shadow_cfg=shadow_cfg,
            beta=beta,
            seed_hash=seed_hash,
            clamps=ledger.clamps,
            retained=(retained or {}).get(block.id),
        )
        result.measurements.extend(rows)
        warm_states[block.id] = warm
        cold_states[block.id] = cold

    band = surrogate_floor_distribution(result.measurements, seed_hash)
    result.surrogate = {
        "n": float(len(band)),
        "q95": _q95(band),
        "second_fdt_floor": second_fdt_surrogate_floor(result.measurements, seed_hash),
    }
    return result, warm_states, cold_states


def _q95(band: Sequence[float]) -> float:
    from .constants import SURROGATE_QUANTILE
    from .hashing import quantile

    return quantile(band, SURROGATE_QUANTILE)
