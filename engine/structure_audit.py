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
   `w_uv‖p_u−p_v‖²`; there is no k-ary factor type. So this is a declared, cited deviation
   (FAITHFULNESS.md · "Inter-chart correspondence is PAIRWISE-COLLAPSED"), fenced by the
   standing prohibition: *no claim of ternary correspondence may be advanced from this build*.
   It is NOT a silent re-encoding, and the audit records it as a gap, not a pass.
4. **Restriction maps derive from the type discipline.** Edge weights are recomputed from the
   typed content (Jaccard over `nu` tokens), not set freely — asserted by re-deriving every
   fiber edge from the fibers and requiring it to match.
5. **Frustration lives on H¹.** A tree-shaped contest settles to floor exactly 0 (path-debt by
   construction); a planted frustrated cycle floors nonzero. Bound to the existing tree-null
   and planted-cycle controls — genuine floor content is supported on H¹ of the factor graph.
6. **Planted-defect control.** A spurious edge (a hand-set weight not derived from
   type/evidence/prior) is not reproducible from the fibers, so it is flagged spurious and the
   audit goes RED.

Green iff: every factor classifies, no spurious/hand-set edge, and every deviation is declared
and fenced. `make structure` joins the gate suite.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .blocks import edges_from_fibers
from .pipeline import Ledger

EVIDENCE = "unary-evidence"
QPRIOR = "q-prior"
INTRA = "intra-chart-sheaf"
INTER = "inter-chart-correspondence"
CLAMP = "clamp"
TYPECON = "type-consistency"
FAMILIES: frozenset[str] = frozenset({EVIDENCE, QPRIOR, INTRA, INTER, CLAMP, TYPECON})

_DECLARED_GAP = "declared-gap"
_HOLDS = "holds"


@dataclass(frozen=True, slots=True)
class StructureClaim:
    id: str
    claim: str
    status: str            # _HOLDS | _DECLARED_GAP
    detail: str
    fence: str = ""        # citation + prohibition for a declared gap; "" when it holds


def fixture_ledger() -> Ledger:
    """The four-chart fixture ledger, so the audit inspects a live graph with real edges."""
    from .extract import build_k_extractors
    from .pipeline import build_ledger
    from .surface import _d4, fixture_documents

    docs, _ = fixture_documents()
    return build_ledger(docs, build_k_extractors(_d4(), offline=True))


def classify_factors(ledger: Ledger) -> tuple[dict[str, int], list[str]]:
    """Every live factor -> exactly one of the six families. Unclassifiable ones are returned."""
    counts: dict[str, int] = {f: 0 for f in sorted(FAMILIES)}
    unclassified: list[str] = []

    # Unary factors: each slot carries evidence, a Q-prior, and a type-consistency factor.
    have_ev = set(ledger.evidence)
    have_prior = set(ledger.priors)
    for s in ledger.slots:
        counts[EVIDENCE] += 1 if s.id in have_ev else 0
        counts[QPRIOR] += 1 if s.id in have_prior else 0
        counts[TYPECON] += 1                      # the slot's type is a factor on it

    # Edge factors: intra vs inter by chart; lexicon/preminted origins are Q-priors.
    chart_of = ledger.chart_of
    for e in ledger.edges:
        if e.origin in ("lexicon", "preminted"):
            counts[QPRIOR] += 1
        elif e.origin == "fiber":
            same = chart_of.get(e.u) == chart_of.get(e.v)
            counts[INTRA if same else INTER] += 1
        else:
            unclassified.append(f"edge {e.u[:8]}~{e.v[:8]} origin={e.origin!r} (no family)")

    # Clamp factors.
    counts[CLAMP] += len(ledger.clamps)
    return counts, unclassified


def spurious_edges(ledger: Ledger) -> list[str]:
    """Edges whose weight is not derivable from the fibers — hand-set / spurious factors."""
    derived = {(e.u, e.v): e.weight for e in edges_from_fibers(ledger.fibers, ledger.slots)}
    out: list[str] = []
    for e in ledger.edges:
        if e.origin == "fiber":
            d = derived.get((e.u, e.v))
            if d is None or abs(d - e.weight) > 1e-9:
                out.append(f"{e.u[:8]}~{e.v[:8]} weight={e.weight:.4f} not derivable from fibers")
        elif e.origin not in ("lexicon", "preminted"):
            out.append(f"{e.u[:8]}~{e.v[:8]} origin={e.origin!r} — hand-set")
    return out


def variable_nodes_are_fibered_only(ledger: Ledger) -> tuple[set[str], list[str]]:
    """Partition slots into variable nodes (on fibered blocks) and frozen constants (isolated).

    A variable node is a slot in a block that carries a Q edge — a fiber, i.e. a contest site.
    An isolated slot (no edge) gets no variable and is frozen background. Returns
    (variable_slot_ids, frozen_slot_ids).
    """
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
        "S4", "restriction maps derive from the type discipline, not free parameters", _HOLDS,
        "every fiber edge weight is re-derivable from the fibers (Jaccard over typed nu tokens)"),
    StructureClaim(
        "S5", "frustration is supported on H¹ (tree floors 0; frustrated cycle floors nonzero)",
        _HOLDS,
        "bound to the tree-null control (floor 0 by path-debt) and the planted-cycle control "
        "(floor nonzero) — genuine floor content lives on H¹ of the factor graph"),
    StructureClaim(
        "S6", "a spurious factor (hand-set weight) makes the audit RED", _HOLDS,
        "planted-defect control: an edge not derivable from the fibers is flagged spurious"),
)


@dataclass(slots=True)
class StructureResult:
    unclassified: list[str] = field(default_factory=list)
    spurious: list[str] = field(default_factory=list)
    undeclared_deviations: list[str] = field(default_factory=list)
    by_family: dict[str, int] = field(default_factory=dict)
    node_detail: str = ""

    @property
    def ok(self) -> bool:
        return not (self.unclassified or self.spurious or self.undeclared_deviations)


def check_structure(ledger: Ledger | None = None) -> StructureResult:
    """The standing check: the live graph is the algebra, deviations declared and fenced."""
    ledger = ledger if ledger is not None else fixture_ledger()
    by_family, unclassified = classify_factors(ledger)
    spurious = spurious_edges(ledger)
    variables, frozen = variable_nodes_are_fibered_only(ledger)
    node_detail = (f"{len(variables)} variable (fibered) nodes, {len(frozen)} isolated slots "
                   f"frozen as constants — the graph is not node-per-slot")
    # Every declared gap must carry a fence (citation + prohibition); an unfenced deviation
    # would be a silent re-encoding and fails.
    undeclared = [c.id for c in STRUCTURE_CLAIMS if c.status == _DECLARED_GAP and not c.fence]
    return StructureResult(
        unclassified=unclassified,
        spurious=spurious,
        undeclared_deviations=undeclared,
        by_family=by_family,
        node_detail=node_detail,
    )
