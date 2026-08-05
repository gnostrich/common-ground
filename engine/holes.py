"""Candidate generation is STRUCTURAL, not scanning: the engine enumerates HOLES.

A hole is a place where the base category is *missing a morphism*: a cross-chart pair of
type-compatible slots between which no correspondence has been proposed. The engine finds
these by construction and hands them to a proposer; it never scans all pairs, and it never
proposes a correspondence itself.

Three constraints, each load-bearing:

- **Cross-chart only.** Exact addressing (gate 1) already owns intra-chart identity: two
  intra-chart slots are either the same address (one claim) or different claims. An
  intra-chart "correspondence" would be similarity by the back door.
- **NO cross-chart type filter.** Claim-form is a property of the SURFACE FORM, and a
  correspondence is precisely a translation between surface forms: a Lean theorem that binds
  hypotheses classifies `conditional` while its English restatement is phrased `assert`, so
  requiring equal claim-form rejects exactly the true pairs. Type-match remains correct
  INTRA-chart, where it keeps two readings of one surface in separate blocks.
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
        # Cross-chart: pair every claim-form against every other. See the note in
        # holes_by_subtree — type-equality is anti-correlated across charts.
        types_a = sorted({t for (c, t) in by_key if c == chart_a})
        types_b = sorted({t for (c, t) in by_key if c == chart_b})
        for claim_type, type_b in [(a, b) for a in types_a for b in types_b]:
            # Rank each side by restatement first, so the highest-value bridges are formed
            # from the front of both lists and the tail is never visited.
            left = sorted(by_key[(chart_a, claim_type)],
                          key=lambda s: (-doc_support.get(s.id, 1), s.id))
            right = sorted(by_key[(chart_b, type_b)],
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


def declaration_key(delta) -> tuple[str, str] | None:
    """`(file, declaration)` for one delta, or None if it names no declaration.

    Read from provenance in ONE way for every chart, which is what makes enumeration
    chart-agnostic:

    - a doc-derived English slot carries it in its doc_id: `<file>#doc:<declaration>`;
    - a code slot carries it in the locator its own segmenter wrote — `theorem:foo`,
      `def:positive`, `func:Book.Match`.

    Nothing is inferred from content. Both halves are the author's own structure: the doc
    comment sits on the declaration, and the segmenter split on the declaration head.
    """
    doc_id = delta.provenance.doc_id
    if "#doc:" in doc_id:
        source_file, _, decl = doc_id.partition("#doc:")
        return (source_file, decl) if decl else None
    locator = delta.provenance.locator or ""
    if ":" not in locator:
        return None
    head, _, name = locator.partition(":")
    if not name or name.isdigit():
        return None                     # a positional locator names no declaration
    return (doc_id, name)


def holes_by_declaration(slots: Sequence[Slot], deltas,
                         chart_pairs: Sequence[tuple[str, str]] | None = None
                         ) -> dict[str, list[Hole]]:
    """The TIGHTEST bound, for ANY pair of charts: one declaration, two charts.

    Two slots are candidates when they carry the same `(file, declaration)` key and sit in
    different charts. That covers every pairing the corpus can actually express:

    - `english x lean` — a `/-- -/` docstring and the theorem it documents;
    - `english x python` — a PEP 257 docstring and its `def`/`class`;
    - `english x go` — a `//` doc block and the declaration below it.

    It does NOT cover `lean x python` or `lean x go`, and that is a fact about the bound
    rather than a gap in the code: two different files never share a declaration key, and a
    Lean spec and its Go implementation are always two files. Cross-language pairs are
    reachable only by `holes_by_subtree`. Pairing them on a shared NAME would be a different
    rule that nobody has ruled on, so it is not done here.

    `chart_pairs` restricts the output; `None` means every cross-chart pair present.
    """
    by_key: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for d in deltas:
        key = declaration_key(d)
        if key is not None:
            by_key[key][d.chart].add(d.slot)

    wanted = ({tuple(sorted(p)) for p in chart_pairs} if chart_pairs is not None else None)
    nu_of = {s.id: s.nu for s in slots}
    type_of = {s.id: s.type for s in slots}
    out: dict[str, list[Hole]] = defaultdict(list)
    for charts in by_key.values():
        present = sorted(charts)
        for i, src_chart in enumerate(present):
            for dst_chart in present[i + 1:]:
                if wanted is not None and (src_chart, dst_chart) not in wanted:
                    continue
                for src in charts[src_chart]:
                    for dst in charts[dst_chart]:
                        if src not in nu_of or dst not in nu_of:
                            continue
                        out[src].append(Hole(
                            src_chart=src_chart, src_slot=src, src_nu=nu_of[src],
                            dst_chart=dst_chart, dst_slot=dst, dst_nu=nu_of[dst],
                            type=type_of[src], restatement=0))
    return dict(out)


def _depth_below(prose_dir: str, src_dir: str) -> int | None:
    """How many directory levels `src_dir` sits below `prose_dir`; None if not below it."""
    if prose_dir == src_dir:
        return 0
    if prose_dir and not src_dir.startswith(prose_dir + "/"):
        return None
    tail = src_dir[len(prose_dir) + 1:] if prose_dir else src_dir
    return len(tail.split("/")) if tail else 0


def chart_pairs_present(slots: Sequence[Slot]) -> list[tuple[str, str]]:
    """Every unordered cross-chart pair the corpus actually contains, `correspondence`
    excluded — that chart holds the arrows themselves, not material to bridge."""
    charts = sorted({s.chart for s in slots} - {"correspondence"})
    return [(a, b) for i, a in enumerate(charts) for b in charts[i + 1:]]


def holes_by_subtree_all(slots: Sequence[Slot], deltas, max_depth: int = 1,
                         chart_pairs: Sequence[tuple[str, str]] | None = None
                         ) -> dict[tuple[str, str], dict[str, list[Hole]]]:
    """`holes_by_subtree` over EVERY chart pair, keyed by the pair.

    The subtree relation is symmetric in what it means — two files near each other in the
    tree — but `holes_by_subtree` treats one side as the document whose POSITION asserts
    scope. Both directions are enumerated so a pair is not missed because the prose happened
    to sit below the code rather than above it.
    """
    pairs = list(chart_pairs) if chart_pairs is not None else chart_pairs_present(slots)
    out: dict[tuple[str, str], dict[str, list[Hole]]] = {}
    for a, b in pairs:
        merged: dict[str, list[Hole]] = defaultdict(list)
        for src, dst in ((a, b), (b, a)):
            for slot, holes in holes_by_subtree(slots, deltas, src_chart=src, dst_chart=dst,
                                                max_depth=max_depth).items():
                merged[slot].extend(holes)
        if merged:
            out[(a, b)] = dict(merged)
    return out


def holes_by_subtree(slots: Sequence[Slot], deltas,
                     src_chart: str = "lean", dst_chart: str = "english",
                     max_depth: int = 1) -> dict[str, list[Hole]]:
    """The second structural relation: a prose document describes the subtree BELOW it.

    `certified-positivity/STATEMENTS.md` — "the exact formal claims, verbatim from the named
    source file" — sits at the repo root while the 75 `.lean` files it restates sit in
    `lean/`. Docs at top, code below. Declaration-granularity cannot see that pairing (a
    STATEMENTS.md entry is not a docstring), and directory-granularity cannot either (one
    level apart).

    The justification is the same as for docstrings, one level up: a document's *position*
    asserts its scope. A prose file at `d/` is about what lives at `d/` and below. No ranking,
    no threshold, no lexical matching — the pairing is where the author put the file.

    This is also the many-to-one shape a CYCLE needs. Declaration-granularity can only make
    stars (a docstring belongs to exactly one declaration), so the correspondence graph is a
    forest and holonomy is always zero by path-debt. One prose document restating many
    theorems is the first structure in which an English slot can correspond to two Lean
    declarations — the precondition for a closed cycle.
    """
    import posixpath

    def parts(doc_id: str) -> tuple[str, str]:
        repo, _, rel = doc_id.partition("||")
        return repo, posixpath.dirname(rel.split("#", 1)[0])

    src_docs: dict[str, set[str]] = defaultdict(set)   # slot -> doc_ids
    dst_docs: dict[str, set[str]] = defaultdict(set)
    for d in deltas:
        if d.chart == src_chart:
            src_docs[d.slot].add(d.provenance.doc_id)
        elif d.chart == dst_chart and "#doc:" not in d.provenance.doc_id:
            # A doc-derived slot is already paired at declaration granularity, which is
            # strictly tighter, so admitting it here would only duplicate that pairing.
            dst_docs[d.slot].add(d.provenance.doc_id)

    nu_of = {s.id: s.nu for s in slots}
    type_of = {s.id: s.type for s in slots}
    src_at: dict[tuple[str, str], set[str]] = defaultdict(set)
    for slot, docs in src_docs.items():
        for doc in docs:
            src_at[parts(doc)].add(slot)

    out: dict[str, list[Hole]] = defaultdict(list)
    for dst_slot, docs in dst_docs.items():
        for doc in docs:
            repo, prose_dir = parts(doc)
            for (r, src_dir), src_slots in src_at.items():
                if r != repo:
                    continue
                # "below it", read CONSERVATIVELY: the source file sits in the prose
                # document's own directory or at most `max_depth` levels beneath it. A
                # document's position asserts its scope, but a root README does not thereby
                # claim every .lean file in the repository — read maximally, one english slot
                # reached 903 Lean declarations, which is a scope error rather than a
                # selection problem. Depth-1 gives STATEMENTS.md exactly the lean/ files it
                # describes and stops a root doc from claiming the whole tree.
                depth = _depth_below(prose_dir, src_dir)
                if depth is None or depth > max_depth:
                    continue
                for src_slot in src_slots:
                    # NO type filter cross-chart. Claim-form is a property of the SURFACE
                    # FORM, and a correspondence is a translation BETWEEN surface forms: a
                    # Lean theorem binding hypotheses is `conditional` while its English
                    # restatement is `assert`, so type-equality rejects exactly the true
                    # pairs. Type-match stays correct INTRA-chart (it keeps `assert` and
                    # `define` readings of one surface in separate blocks) and is wrong here.
                    out[src_slot].append(Hole(
                        src_chart=src_chart, src_slot=src_slot, src_nu=nu_of[src_slot],
                        dst_chart=dst_chart, dst_slot=dst_slot, dst_nu=nu_of[dst_slot],
                        type=type_of[src_slot], restatement=0))
    return dict(out)
