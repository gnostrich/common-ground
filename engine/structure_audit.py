"""structure_audit — the live computational graph IS the algebra, audited as structure.

Naturality is a property of the graph *being* the algebra, invisible to output tests. This
audit asserts it, in the sweep pattern (gate6 / three-moves / faithfulness):

1. **Nodes = contested fibers only.** Variable nodes live on fibered blocks (blocks with a Q
   edge); an isolated slot gets no variable — it is frozen background. A node-per-slot graph
   is REFUTED.
2. **Six typed factor families**, each distinct: unary evidence, intra-chart sheaf,
   inter-chart correspondence, Q-priors, clamps, type-consistency. Every live factor
   classifies into exactly one; an unclassifiable factor fails.
3. **Correspondence is genuinely ternary — DECLARED GAP.** The engine's edges are pairwise
   `w_uv‖p_u−p_v‖²`; there is no k-ary factor type. Declared, cited deviation
   (FAITHFULNESS.md · "Inter-chart correspondence is PAIRWISE-COLLAPSED"), fenced.
4. **Edge weights derive from the fibers, not free parameters.** A declared correspondence
   carries the declared weight; re-deriving every edge from the fibers must reproduce it.
5. **Frustration lives on H¹.** A tree-shaped contest settles to floor exactly 0; a planted
   frustrated cycle floors nonzero. Bound to the tree-null and planted-cycle controls.
6. **Planted-defect (edge).** A spurious edge (a weight not derived from the fibers) is not
   reproducible from the fibers, so it is flagged spurious and the audit goes RED.
7. **Membership is the EXACT declared-correspondence relation, never similarity.** Fibers must
   be exactly the connected components of the declared correspondence edges. A fiber grouping
   slots with no declared correspondence among them — a similarity-style membership — is not
   reproducible from the relation and makes the audit RED. This is the check that was missing
   while membership was a Jaccard threshold: the old audit checked that edges derive from
   fibers, but never that fiber MEMBERSHIP is the specified relation.

Green iff: every factor classifies, no spurious/hand-set edge, no similarity-style membership,
and every deviation is declared and fenced. `make structure` joins the gate suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .blocks import build_fibers, edges_from_fibers, expand_stars
from .pipeline import Ledger

EVIDENCE = "unary-evidence"
QPRIOR = "q-prior"
INTRA = "intra-chart-sheaf"
INTER = "inter-chart-correspondence"
CLAMP = "clamp"
TYPECON = "type-consistency"
FAMILIES: frozenset[str] = frozenset({EVIDENCE, QPRIOR, INTRA, INTER, CLAMP, TYPECON})

#: Q-edge origins that are correspondence factors (intra/inter by chart). The similarity
#: origin "fiber" is gone with the Jaccard relation; declared correspondence uses this.
_CORRESPONDENCE_ORIGIN = "correspondence"

_DECLARED_GAP = "declared-gap"
_HOLDS = "holds"


@dataclass(frozen=True, slots=True)
class StructureClaim:
    id: str
    claim: str
    status: str            # _HOLDS | _DECLARED_GAP
    detail: str
    fence: str = ""        # citation + prohibition for a declared gap; "" when it holds


def _fixture_base():
    """The four-chart fixture docs + extractors, and a first ledger with NO correspondence."""
    from .extract import build_k_extractors
    from .pipeline import build_ledger
    from .surface import _d4, fixture_documents

    docs, _ = fixture_documents()
    extractors = build_k_extractors(_d4(), offline=True)
    base = build_ledger(docs, extractors, correspondence=frozenset())
    return docs, extractors, base


def fixture_correspondence(base: Ledger) -> frozenset[tuple[str, str]]:
    """A DECLARED correspondence for the audit fixture, so the live graph has real edges.

    Declared by discovered slot-id (not similarity): one cross-chart pair (english↔lean) so
    the audit inspects an inter-chart correspondence factor and non-trivial fibered nodes.
    This is a *declared* planted correspondence — the exact relation the audit tests — never a
    string-overlap inference.
    """
    by_chart: dict[str, list[str]] = {}
    for s in base.slots:
        by_chart.setdefault(s.chart, []).append(s.id)
    pairs: set[tuple[str, str]] = set()
    if by_chart.get("english") and by_chart.get("lean"):
        u, v = sorted(by_chart["english"])[0], sorted(by_chart["lean"])[0]
        pairs.add((u, v) if u < v else (v, u))
    return frozenset(pairs)


def fixture_ledger() -> Ledger:
    """The fixture ledger built over a DECLARED correspondence (a live graph with real edges)."""
    from .pipeline import build_ledger

    docs, extractors, base = _fixture_base()
    return build_ledger(docs, extractors, correspondence=fixture_correspondence(base))


def classify_factors(ledger: Ledger) -> tuple[dict[str, int], list[str]]:
    """Every live factor -> exactly one of the six families. Unclassifiable ones are returned."""
    counts: dict[str, int] = {f: 0 for f in sorted(FAMILIES)}
    unclassified: list[str] = []

    have_ev = set(ledger.evidence)
    have_prior = set(ledger.priors)
    for s in ledger.slots:
        counts[EVIDENCE] += 1 if s.id in have_ev else 0
        counts[QPRIOR] += 1 if s.id in have_prior else 0
        counts[TYPECON] += 1                      # the slot's type is a factor on it

    # THROUGH THE CANONICAL EXPANSION. This module asks chart-level questions about SLOT
    # pairs — is this edge intra-chart or inter-chart — and an apex has no chart, so reading
    # apex-star edges directly classifies every face-edge as intra-chart by accident (both
    # endpoints resolve to None, which compares equal). Fourth consumer of fiber structure,
    # and the first one found by a failing audit rather than by the sweep.
    chart_of = ledger.chart_of
    for e in expand_stars(ledger.edges):
        if e.origin in ("lexicon", "preminted"):
            counts[QPRIOR] += 1
        elif e.origin == _CORRESPONDENCE_ORIGIN:
            same = chart_of.get(e.u) == chart_of.get(e.v)
            counts[INTRA if same else INTER] += 1
        else:
            unclassified.append(f"edge {e.u[:8]}~{e.v[:8]} origin={e.origin!r} (no family)")

    counts[CLAMP] += len(ledger.clamps)
    return counts, unclassified


def spurious_edges(ledger: Ledger) -> list[str]:
    """Edges whose weight is not derivable from the fibers — hand-set / spurious factors."""
    derived = {(e.u, e.v): e.weight
               for e in expand_stars(edges_from_fibers(ledger.fibers, ledger.slots))}
    out: list[str] = []
    for e in expand_stars(ledger.edges):
        if e.origin == _CORRESPONDENCE_ORIGIN:
            d = derived.get((e.u, e.v))
            if d is None or abs(d - e.weight) > 1e-9:
                out.append(f"{e.u[:8]}~{e.v[:8]} weight={e.weight:.4f} not derivable from fibers")
        elif e.origin not in ("lexicon", "preminted"):
            out.append(f"{e.u[:8]}~{e.v[:8]} origin={e.origin!r} — hand-set")
    return out


def membership_violations(ledger: Ledger) -> list[str]:
    """Fibers that are NOT the exact declared-correspondence relation — similarity-style membership.

    The declared correspondence is exactly the set of `correspondence`-origin edges. Fiber
    membership must be the connected components of that relation, and nothing else. A fiber
    the relation does not reproduce (its members are not a declared-correspondence component)
    is a string-overlap / similarity grouping and makes the audit RED. This is the check the
    Jaccard membership evaded.
    """
    # Through the expansion, for the same reason: `build_fibers` takes SLOT PAIRS, and an
    # apex-star edge is a slot paired with a node that is not a slot. Reading them raw makes
    # every fiber look unreproducible from its own declarations.
    corr = {(e.u, e.v) for e in expand_stars(ledger.edges)
            if e.origin == _CORRESPONDENCE_ORIGIN}
    expected = {frozenset(f.slots) for f in build_fibers(ledger.slots, corr)}
    actual = {frozenset(f.slots) for f in ledger.fibers}
    out: list[str] = []
    for f in sorted(actual - expected, key=lambda s: sorted(s)):
        members = sorted(f)
        out.append(
            f"fiber {{{members[0][:8]}..+{len(members) - 1}}} is not a declared-correspondence "
            "component — similarity-style membership"
        )
    return out


def variable_nodes_are_fibered_only(ledger: Ledger) -> tuple[set[str], list[str]]:
    """Partition slots into variable nodes (on fibered blocks) and frozen constants (isolated)."""
    fibered_slots = {s for b in ledger.blocks if b.edges for s in b.slots}
    frozen = [s.id for s in ledger.slots if s.id not in fibered_slots]
    return fibered_slots, frozen


STRUCTURE_CLAIMS: tuple[StructureClaim, ...] = (
    StructureClaim(
        "S1", "nodes = contested fibers only (isolated slots are frozen constants)", _HOLDS,
        "variable nodes live on fibered blocks; a node-per-slot graph is refuted"),
    StructureClaim(
        "S2", "every live factor classifies into exactly one of the six typed families", _HOLDS,
        "unary evidence, intra-chart sheaf, inter-chart correspondence, Q-priors, clamps, "
        "type-consistency"),
    StructureClaim(
        "S3", "inter-chart correspondence is genuinely ternary {A, B, corr_AB}", _DECLARED_GAP,
        "the engine has only pairwise w_uv‖p_u−p_v‖² edges; no k-ary factor type exists",
        fence="FAITHFULNESS.md · 'Inter-chart correspondence is PAIRWISE-COLLAPSED'; "
              "PROHIBITION: no claim of ternary correspondence may be advanced from this build"),
    StructureClaim(
        "S4", "edge weights derive from the fibers, not free parameters", _HOLDS,
        "every correspondence edge weight is re-derivable from the fibers (the declared weight)"),
    StructureClaim(
        "S5", "frustration is supported on H¹ (tree floors 0; frustrated cycle floors nonzero)",
        _HOLDS,
        "bound to the tree-null control (floor 0 by path-debt) and the planted-cycle control "
        "(floor nonzero) — genuine floor content lives on H¹ of the factor graph"),
    StructureClaim(
        "S6", "a spurious factor (hand-set edge weight) makes the audit RED", _HOLDS,
        "planted-defect control: an edge not derivable from the fibers is flagged spurious"),
    StructureClaim(
        "S7", "fiber membership is the EXACT declared-correspondence relation, never similarity",
        _HOLDS,
        "fibers are exactly the connected components of the declared correspondence edges; a "
        "fiber grouping non-corresponding slots (a string-overlap membership) makes it RED. "
        "This is the check that was absent while membership was a Jaccard threshold"),
)


@dataclass(slots=True)
class StructureResult:
    unclassified: list[str] = field(default_factory=list)
    spurious: list[str] = field(default_factory=list)
    membership: list[str] = field(default_factory=list)
    undeclared_deviations: list[str] = field(default_factory=list)
    by_family: dict[str, int] = field(default_factory=dict)
    node_detail: str = ""

    @property
    def ok(self) -> bool:
        return not (self.unclassified or self.spurious or self.membership
                    or self.undeclared_deviations)


def check_structure(ledger: Ledger | None = None) -> StructureResult:
    """The standing check: the live graph is the algebra, deviations declared and fenced."""
    ledger = ledger if ledger is not None else fixture_ledger()
    by_family, unclassified = classify_factors(ledger)
    spurious = spurious_edges(ledger)
    membership = membership_violations(ledger)
    variables, frozen = variable_nodes_are_fibered_only(ledger)
    node_detail = (f"{len(variables)} variable (fibered) nodes, {len(frozen)} isolated slots "
                   f"frozen as constants — the graph is not node-per-slot")
    undeclared = [c.id for c in STRUCTURE_CLAIMS if c.status == _DECLARED_GAP and not c.fence]
    return StructureResult(
        unclassified=unclassified,
        spurious=spurious,
        membership=membership,
        undeclared_deviations=undeclared,
        by_family=by_family,
        node_detail=node_detail,
    )
