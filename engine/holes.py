"""Candidate generation is STRUCTURAL, not scanning: the engine enumerates HOLES.

A hole is a place where the base category is *missing a morphism*: a cross-chart pair of
type-compatible slots between which no correspondence has been proposed. The engine finds
these by construction and hands them to a proposer; it never scans all pairs, and it never
proposes a correspondence itself.

Three constraints, each load-bearing:

- **Cross-chart only.** Exact addressing (gate 1) already owns intra-chart identity: two
  intra-chart slots are either the same address (one claim) or different claims. An
  intra-chart "correspondence" would be similarity by the back door.
- **Type-compatible only.** A `define` and an `assert` are different claim-forms; a
  correspondence between them would cross the type discipline the address encodes.
- **Never all-pairs.** Candidates are grouped by (chart_a, chart_b, type) and ranked by
  RESTATEMENT COUNT — slots restated across many documents first, because a bridge at a
  well-restated claim closes more loops per confirmation than a bridge at a hapax. The caller
  takes the top-k; the enumeration is bounded before it is materialized.

The cost of finding holes is O(N) grouping plus the cost of the k the caller asks for; the
full cross-product is never built.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from .correspondence import Correspondence
from .types import Slot


@dataclass(frozen=True, slots=True)
class Hole:
    """A missing morphism: two type-compatible slots in different charts, unconnected."""

    src_chart: str
    src_slot: str
    src_nu: str
    dst_chart: str
    dst_slot: str
    dst_nu: str
    type: str
    restatement: int          # combined document support — the prioritization key

    def as_record(self) -> dict[str, object]:
        return {
            "src_chart": self.src_chart, "src_slot": self.src_slot, "src_nu": self.src_nu,
            "dst_chart": self.dst_chart, "dst_slot": self.dst_slot, "dst_nu": self.dst_nu,
            "type": self.type, "restatement": self.restatement,
        }


def enumerate_holes(
    slots: Sequence[Slot],
    doc_support: dict[str, int],
    existing: Sequence[Correspondence] = (),
    limit: int = 200,
    chart_pairs: Sequence[tuple[str, str]] | None = None,
    per_slot_cap: int = 3,
) -> list[Hole]:
    """The top `limit` holes by restatement count. The cross-product is never materialized.

    `doc_support[slot_id]` is how many distinct documents restate that slot — the priority
    signal. `existing` arrows are excluded in either direction: a pair already carrying a
    proposal is not a hole, whatever the proposal's tier or verdict.

    `per_slot_cap` bounds how many candidate partners a single slot may claim, so one
    heavily-restated slot cannot crowd out every other bridge in the batch.
    """
    taken: set[tuple[str, str]] = set()
    for a in existing:
        taken.add(a.pair)

    # Group by (chart, type); only type-compatible cross-chart pairs are candidates.
    by_key: dict[tuple[str, str], list[Slot]] = defaultdict(list)
    for s in slots:
        by_key[(s.chart, s.type)].append(s)

    charts = sorted({s.chart for s in slots})
    pairs = list(chart_pairs) if chart_pairs is not None else [
        (a, b) for i, a in enumerate(charts) for b in charts[i + 1:]
    ]

    out: list[Hole] = []
    used: dict[str, int] = defaultdict(int)
    for chart_a, chart_b in pairs:
        if chart_a == chart_b:
            continue                     # cross-chart only
        types = {t for (c, t) in by_key if c == chart_a} & {t for (c, t) in by_key if c == chart_b}
        for claim_type in sorted(types):
            # Rank each side by restatement first, so the highest-value bridges are formed
            # from the front of both lists and the tail is never visited.
            left = sorted(by_key[(chart_a, claim_type)],
                          key=lambda s: (-doc_support.get(s.id, 1), s.id))
            right = sorted(by_key[(chart_b, claim_type)],
                           key=lambda s: (-doc_support.get(s.id, 1), s.id))
            for s in left[: limit]:
                if used[s.id] >= per_slot_cap:
                    continue
                for t in right[: limit]:
                    if s.id == t.id or used[t.id] >= per_slot_cap:
                        continue
                    pair = (s.id, t.id) if s.id < t.id else (t.id, s.id)
                    if pair in taken:
                        continue
                    taken.add(pair)
                    used[s.id] += 1
                    used[t.id] += 1
                    out.append(Hole(
                        src_chart=chart_a, src_slot=s.id, src_nu=s.nu,
                        dst_chart=chart_b, dst_slot=t.id, dst_nu=t.nu,
                        type=claim_type,
                        restatement=doc_support.get(s.id, 1) + doc_support.get(t.id, 1),
                    ))
                    if used[s.id] >= per_slot_cap:
                        break

    out.sort(key=lambda h: (-h.restatement, h.src_slot, h.dst_slot))
    return out[:limit]


def document_support(deltas) -> dict[str, int]:
    """slot -> number of distinct documents that restate it. The prioritization signal."""
    docs: dict[str, set[str]] = defaultdict(set)
    for d in deltas:
        docs[d.slot].add(d.provenance.doc_id)
    return {slot: len(ds) for slot, ds in docs.items()}


# --- provenance-bounded candidate generation (the structural bound) --------------------

def provenance_unit(doc_id: str, level: str = "dir") -> str:
    """The provenance unit a document belongs to. Pure structure, no inference.

    A doc_id is `<repo>||<relative/path>`. `dir` bounds by the directory the file sits in,
    `project` by the top-level subtree, `repo` by the repository. Nothing here reads content.
    """
    import posixpath

    repo, _, rel = doc_id.partition("||")
    if level == "repo" or not rel:
        return repo
    if level == "project":
        head = rel.split("/", 1)[0] if "/" in rel else ""
        return f"{repo}/{head}"
    return f"{repo}/{posixpath.dirname(rel)}"


def slot_units(deltas, level: str = "dir") -> dict[str, set[str]]:
    """slot id -> the provenance units it appears in. A slot restated in two directories
    belongs to both; that is a fact about the corpus, not a merge."""
    out: dict[str, set[str]] = defaultdict(set)
    for d in deltas:
        out[d.slot].add(provenance_unit(d.provenance.doc_id, level))
    return out


def holes_by_provenance(
    slots: Sequence[Slot],
    deltas,
    level: str = "dir",
    src_chart: str = "lean",
    dst_chart: str = "english",
) -> dict[str, list[Hole]]:
    """Candidates bounded by PROVENANCE: per source-chart slot, the destination-chart slots
    CO-LOCATED with it.

    This is the whole rule, and it is not a rule about meaning: two claims are candidates
    because they were written in the same place. There is no ranking, no anchor, no
    threshold, no list — nothing to tune and nothing to accumulate. Returns a mapping from
    source slot id to its co-located candidate holes, which is also the natural batch unit:
    one proposer call per source declaration.
    """
    units = slot_units(deltas, level)
    by_unit_dst: dict[str, list[Slot]] = defaultdict(list)
    for s in slots:
        if s.chart == dst_chart:
            for u in units.get(s.id, ()):
                by_unit_dst[u].append(s)

    out: dict[str, list[Hole]] = {}
    for s in slots:
        if s.chart != src_chart:
            continue
        seen: set[str] = set()
        holes: list[Hole] = []
        for u in sorted(units.get(s.id, ())):
            for t in by_unit_dst.get(u, ()):
                if t.id in seen or t.type != s.type:
                    continue          # type-compatible, per the existing hole contract
                seen.add(t.id)
                holes.append(Hole(
                    src_chart=s.chart, src_slot=s.id, src_nu=s.nu,
                    dst_chart=t.chart, dst_slot=t.id, dst_nu=t.nu,
                    type=s.type, restatement=0,   # retired as a ranking signal
                ))
        if holes:
            out[s.id] = holes
    return out
