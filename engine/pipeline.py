"""Ingestion -> addressing -> priors -> blocks -> settlement -> meter.

One place where the pieces are wired, so that the null battery, the phases, and the audit
all exercise the same path. A cell that passed against a bespoke wiring would prove
nothing about the run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

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
    dedupe: bool = True,
    correspondence: Iterable[tuple[str, str]] | None = None,
) -> Ledger:
    """Full ingestion path.

    `edge_filter` is the hook PREREG R4 uses to drop Q edges. `dedupe=False` exists only
    for null cell (v)'s positive control: it disables the content-hash deduplication that
    makes re-ingestion idempotent, so the control can confirm the cell actually detects a
    double-counted source rather than passing because nothing was ever at risk.

    `correspondence` is the DECLARED fiber-membership relation (exact slot-id pairs). It
    defaults to `engine/correspondence.py:declared_correspondence()` — empty at v0. It is a
    parameter so a control can declare a correspondence for a planted case; there is no
    similarity path that would manufacture one.
    """
    deltas = ingest(documents, extractors)
    if dedupe:
        deltas = dedupe_deltas(deltas)
    return ledger_from_deltas(
        deltas, clamps=clamps, prior_leaning=prior_leaning,
        edge_filter=edge_filter, evidence_dedupe=dedupe, correspondence=correspondence,
    )


def ledger_from_deltas(
    deltas: Sequence[Delta],
    clamps: Sequence[Clamp] = (),
    prior_leaning: Mapping[str, BValue] | None = None,
    edge_filter=None,
    evidence_dedupe: bool = True,
    correspondence: Iterable[tuple[str, str]] | None = None,
) -> Ledger:
    """Build the ledger from pre-made deltas — the shared tail of `build_ledger`.

    Exposed so cross-instance coupling can join two instances' deltas and rebuild one ledger
    over both, without re-running extraction. `correspondence` defaults to the seed's declared
    correspondence (empty at v0 — the gap); pass an explicit set to declare one.
    """
    from .correspondence import declared_correspondence

    deltas = list(deltas)
    corr = declared_correspondence() if correspondence is None else correspondence
    slots = slots_from_deltas(deltas)
    fibers = build_fibers(slots, corr)
    edges = edges_from_fibers(fibers, slots)
    if edge_filter is not None:
        edges = list(edge_filter(edges))
    blocks = build_blocks(slots, edges, deltas)
    chart_of = {s.id: s.chart for s in slots}
    active = {s.id for s in slots}
    loops = loops_from_fibers(fibers, chart_of, restrict_to=active, edges=edges)

    return Ledger(
        deltas=deltas,
        slots=slots,
        fibers=fibers,
        edges=edges,
        blocks=blocks,
        evidence=evidence_from_deltas(deltas, dedupe=evidence_dedupe),
        priors=lexicon_prior([s.id for s in slots], prior_leaning),
        chart_of=chart_of,
        loops=loops,
        clamps=list(clamps),
    )


def consensus_ledger(ledger: Ledger) -> Ledger:
    """The same ledger with every block forced to internal agreement.

    Per block, every delta is rewritten to the block's modal b-value, and clamps are
    dropped. The result is a ledger that *cannot* disagree with itself, so its floor is the
    numerical residue of the pipeline and nothing else.

    Dropping clamps is part of forcing agreement, not a convenience. A clamp that pins a
    slot against its block's modal value is itself a disagreement — it is exactly the
    mechanism-(2) grounding conflict a floor is made of — so a "cannot disagree with itself"
    null must neutralise it. Were the clamp retained, a planted grounding conflict would push
    the consensus floor up by its own value, the band would rise to meet the observed floor,
    and cell (iv)'s control could never fire: the same resample-of-the-observation pathology
    that made the bootstrap band vacuous, wearing a clamp.

    This is the null null cell (iv) needs. Bootstrapping the observed floors gives a band
    centred on the observed data, which makes `floor <= band` true at any floor — the test
    passes at 0.4 as readily as at 0.0 and is therefore vacuous. Comparing against a
    consensus floor instead tests what the cell claims to test: whether a single document
    disagrees with itself more than the machinery's own noise.
    """
    import dataclasses
    from collections import Counter

    block_of: dict[str, str] = {}
    for block in ledger.blocks:
        for slot in block.slots:
            block_of[slot] = block.id

    votes: dict[str, Counter] = {}
    for d in ledger.deltas:
        bid = block_of.get(d.slot)
        if bid is not None:
            votes.setdefault(bid, Counter())[d.value] += d.confidence

    modal = {
        bid: sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        for bid, counter in votes.items()
    }

    rewritten = [
        dataclasses.replace(d, value=modal[block_of[d.slot]])
        if block_of.get(d.slot) in modal
        else d
        for d in ledger.deltas
    ]

    return Ledger(
        deltas=rewritten,
        slots=ledger.slots,
        fibers=ledger.fibers,
        edges=ledger.edges,
        blocks=ledger.blocks,
        evidence=evidence_from_deltas(rewritten),
        priors=ledger.priors,
        chart_of=ledger.chart_of,
        loops=ledger.loops,
        clamps=[],  # a forced-agreement null carries no grounding conflict; see the docstring
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
        if not loops and not block.edges:
            continue
        rows, warm, cold, nulls, calib = measure(
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
        result.loop_nulls.update(nulls)
        result.shadow_calibration.extend(calib)
        if not rows:
            # The block has slots and edges but no verified cycle in Q, so no holonomy is
            # defined on it. Reported, never silently treated as a zero floor.
            result.no_cycle_support.append(block.id)
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
