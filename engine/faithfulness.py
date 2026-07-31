"""Theory object -> code site -> executable control. The faithfulness audit.

`GATES.md` says what the engine may not do. This says what the engine *is*: every object
the theory names, the place it lives in code, and a control that fails if that place stops
implementing it. Same shape as the gate-6 sweep, and for the same reason — a mapping
written in prose goes stale the first time someone edits the engine, so this one is a
check.

Three things fail `check_faithfulness`:

- an **unmapped** row: a theory object with no code site, or a site that no longer resolves
- an **uncontrolled** row: no positive control, or one that names a test that does not exist
- an **unclassified deviation**: the build differs from the theory and nobody said whether
  that was a decision or an oversight

The third is the one that matters. A deviation is not automatically a defect — this is a
*minimal*-faithful build and several simplifications are deliberate — but an unrecorded
deviation is indistinguishable from a mistake, and by P3 the difference is unrecoverable.
So every deviation carries a `kind`:

- ``minimal-faithful-by-design`` — a deliberate simplification, with the ruling that forces
  or permits it cited. Cheap to check: if the ruling does not actually imply the
  simplification, the row is mislabelled.
- ``gap-before-P3`` — the build does not do what the theory says and nobody decided that.
  These are what `gaps_before_p3()` returns, and they are the list to clear before ingestion.

Deviations of the second kind do not fail the check. They are findings, and hiding them
behind a red build would defeat the point of writing them down.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from .constants import REPO_ROOT

MINIMAL_FAITHFUL = "minimal-faithful-by-design"
GAP = "gap-before-P3"
_KINDS = frozenset({MINIMAL_FAITHFUL, GAP})


@dataclass(frozen=True, slots=True)
class Deviation:
    kind: str
    note: str
    ruling: str = ""


@dataclass(frozen=True, slots=True)
class Row:
    """One theory object, where it lives, and what proves it is still there."""

    object: str
    family: str
    site: str          # "engine/module.py:symbol"
    role: str
    control: str       # "tests/test_faithfulness.py:ClassName.test_name"
    control_claim: str
    deviation: Deviation | None = None

    @property
    def module(self) -> str:
        return self.site.split(":", 1)[0]

    @property
    def symbol(self) -> str:
        return self.site.split(":", 1)[1] if ":" in self.site else ""


#: The audit. Ordered by factor family, then by structure, then by the two theory-level
#: controls that test the hypergraph claim itself rather than any one component.
FAITHFULNESS_ROWS: tuple[Row, ...] = (
    # --- the six factor families ---------------------------------------------------
    Row(
        object="evidence factor",
        family="factor",
        site="engine/energy.py:evidence_from_deltas",
        role="linear term in F: sum_i <p_i, e_i>",
        control="tests/test_faithfulness.py:EvidenceFactor.test_evidence_moves_the_settled_state_and_absence_leaves_it_uniform",
        control_claim="a slot with no evidence settles uniform; adding supporting deltas "
                      "moves mass onto the supported value, weighted by confidence x warrant",
    ),
    Row(
        object="intra-chart sheaf (gluing within one chart)",
        family="factor",
        site="engine/blocks.py:edges_from_fibers",
        role="Q edges between same-chart slots; quadratic coupling in F",
        control="tests/test_faithfulness.py:IntraChartSheaf.test_same_chart_coupling_pulls_and_dropping_it_releases",
        control_claim="two same-chart slots joined by a fiber edge settle closer together "
                      "than the same two slots with the edge dropped",
        deviation=Deviation(
            kind=MINIMAL_FAITHFUL,
            note="There is no sheaf object: no restriction maps, no cocycle condition, no "
                 "check that sections agree on overlaps. Gluing is a soft quadratic penalty "
                 "`(lambda/2) w ||p_u - p_v||^2` that two slots can pay and stay apart. A "
                 "sheaf condition is a *constraint*; this is an *energy*.",
            ruling="GATES.md sentence 2 — 'Lexicon and equivalence priors enter F only as "
                   "energy terms. They can never clamp.' A hard gluing condition would be a "
                   "prior that constrains, which sentence 2 forbids outright. The soft form "
                   "is not an approximation chosen for convenience; it is the only form gate "
                   "2 permits.",
        ),
    ),
    Row(
        object="inter-chart correspondence",
        family="factor",
        site="engine/types.py:QEdge",
        role="Q edges whose endpoints lie in different charts; same coupling term, plus "
             "shadow subtraction at the meter",
        control="tests/test_faithfulness.py:InterChartCorrespondence.test_correspondence_is_pairwise_and_a_three_cycle_is_not_a_ternary_factor",
        control_claim="a cross-chart edge transports; and a 3-cycle of pairwise edges is "
                      "shown NOT to represent a genuine ternary factor — it cannot encode a "
                      "joint constraint that no pair of its projections encodes",
        deviation=Deviation(
            kind=MINIMAL_FAITHFUL,
            note="**PAIRWISE-COLLAPSED, explicitly.** `QEdge` has exactly two endpoints and "
                 "there is no ternary (or k-ary) factor type anywhere in the engine. A "
                 "three-way correspondence is representable only as a triangle of pairwise "
                 "edges, and that is a strictly weaker object: a triangle encodes three "
                 "pairwise compatibilities, whereas a ternary factor can encode a joint "
                 "condition with no pairwise shadow (the control constructs one). So the "
                 "engine cannot express 'these three restatements are jointly compatible "
                 "but no two of them determine the third'.",
            ruling="PREREG's matrix names exactly two loop families — 'Eng->Lean->Eng "
                   "restatement loops over kernel-checked theorems' and 'intra-English "
                   "paraphrase loops over REGISTRY claims'. Both are binary "
                   "correspondences traversed as walks; neither needs a joint 3-way factor. "
                   "The collapse is faithful to what this round measures. It is NOT faithful "
                   "to a theory that claims ternary correspondence in general, and no such "
                   "claim may be advanced from this build without a k-ary factor type.",
        ),
    ),
    Row(
        object="Q-priors (equivalence prior as energy)",
        family="factor",
        site="engine/energy.py:FreeEnergy",
        role="(lambda/2) sum_uv w_uv ||p_u - p_v||^2, plus the per-slot lexicon prior "
             "lambda2 <p_i, r_i>",
        control="tests/test_faithfulness.py:QPriors.test_an_arbitrarily_heavy_prior_still_cannot_fix_a_value",
        control_claim="a prior weight raised far beyond any corpus evidence still leaves "
                      "mass off the vertex — the prior tilts and never fixes, which is the "
                      "difference between an energy and a clamp",
    ),
    Row(
        object="clamps (grounding)",
        family="factor",
        site="engine/types.py:Clamp",
        role="hard assignment, constructible only from a clamp-eligible warrant; a separate "
             "argument to `settle`, never reachable from a prior",
        control="tests/test_faithfulness.py:Clamps.test_a_clamp_holds_and_a_non_eligible_warrant_cannot_make_one",
        control_claim="a clamped slot stays at its value through settling, and constructing "
                      "a Clamp from an EXTRACTION warrant raises GateViolation",
    ),
    Row(
        object="type-consistency",
        family="factor",
        site="engine/normalize.py:slot_id",
        role="claim-form is a component of the address: id = hash(nu(surface), type)",
        control="tests/test_faithfulness.py:TypeConsistency.test_same_surface_different_type_cannot_collide_or_contest",
        control_claim="one surface read as `assert` and as `define` produces two distinct "
                      "slots that never share a block, so a type mismatch cannot become a "
                      "contest",
        deviation=Deviation(
            kind=MINIMAL_FAITHFUL,
            note="Type-consistency is not a factor in F. There is no energy term penalising "
                 "a type mismatch, because a mismatch is not representable: differing types "
                 "are different addresses and never meet. The build is *stronger* than a "
                 "soft type factor here, not weaker — but it is a different object, and a "
                 "theory that wants graded type compatibility would not find it implemented.",
            ruling="GATES.md sentence 1 — 'Slot identity = hash(nu(surface), type).' Type "
                   "is constitutive of the address, so a soft type factor would contradict "
                   "gate 1 rather than extend it.",
        ),
    ),
    # --- structure -----------------------------------------------------------------
    Row(
        object="blocks as connected components of Q",
        family="structure",
        site="engine/blocks.py:build_blocks",
        role="each contested block is one connected component, restricted to slots carrying "
             "at least one delta",
        control="tests/test_faithfulness.py:BlocksAreConnectedComponents.test_two_disjoint_contests_settle_independently",
        control_claim="two contests sharing no Q edge land in two blocks, and perturbing "
                      "one block's evidence moves the other block's settled state by exactly "
                      "zero — measured, not asserted",
    ),
    Row(
        object="descent certificate",
        family="structure",
        site="engine/settle.py:settle",
        role="F is non-increasing along the iterate sequence; the block is stamped "
             "`monotone`, or `violated` if no descending step can be found",
        control="tests/test_faithfulness.py:DescentCertificate.test_an_injected_non_monotone_step_voids_the_block",
        control_claim="an objective rigged to rise on every step exhausts the halving "
                      "safeguard and stamps the block `violated` — the certificate is a real "
                      "check on the implementation, not a label",
    ),
    # --- theory-level: the hypergraph claim itself ---------------------------------
    Row(
        object="tree-null (all tree contest is path-debt)",
        family="theory",
        site="engine/meter.py:holonomy",
        role="a contest graph with no cycles must produce cold floor exactly zero: with a "
             "unique path between any two slots, transport is path-independent",
        control="tests/test_faithfulness.py:TreeNull.test_a_tree_contest_graph_does_not_yield_zero_floor",
        control_claim="FAILS AS THEORY PREDICTS IT SHOULD NOT. A single-edge tree yields "
                      "holonomy 0.1496, and a 3-slot walk over a path yields 0.4338 — larger "
                      "than the genuine triangle it should be dominated by. The control pins "
                      "both, so the gap cannot be closed by accident.",
        deviation=Deviation(
            kind=GAP,
            note="Two distinct defects, both measured.\n\n"
                 "**(A) Backtracking walks are not cycles.** `loops_from_fibers` gives a "
                 "two-member fiber the walk `u -> v -> u`. On a tree that is a closed walk "
                 "with no cycle, so theory says zero holonomy. The engine returns 0.1496, "
                 "because transport `T(q) = (1-a)q + a p_v` is a contraction toward the "
                 "target rather than a reversible parallel transport: `T_{v->u} . T_{u->v} "
                 "!= id` whenever `p_u != p_v`. The residual is a property of the operator, "
                 "not of the ledger. This is not a corner case — a two-member fiber is the "
                 "commonest fiber the engine builds.\n\n"
                 "**(B) Loops are specified without checking their closing edge exists.** "
                 "`loops_from_fibers` builds the cycle from fiber *membership*, and "
                 "`holonomy` skips any edge whose weight is zero (`if w <= 0.0: continue`). "
                 "A three-member fiber whose Q graph is the path u-v-x therefore yields the "
                 "loop spec (u,v,x) whose closing edge (x,u) does not exist; holonomy then "
                 "silently measures the OPEN walk u->v->x and reports `TV(p_u, transported)` "
                 "— comparing the start state against a state transported somewhere else "
                 "entirely. Measured 0.4338, against 0.2283 for the same slots with the "
                 "closing edge actually present. The meter's central quantity is being "
                 "computed over walks that are not cycles in the contest graph.",
            ruling="No ruling covers this. KICKOFF's paired loop-side meter presumes loops "
                   "are cycles; nothing in GATES.md, PREREG, or any amendment licenses "
                   "measuring holonomy over a backtracking or open walk. Closing it needs a "
                   "decision on both halves: whether a two-member fiber yields a loop at all, "
                   "and whether `loops_from_fibers` must verify closure against the Q graph "
                   "before emitting a spec.",
        ),
    ),
    Row(
        object="planted-cycle (frustration is real and persistent)",
        family="theory",
        site="engine/meter.py:measure",
        role="a frustrated cycle through a correspondence edge with incompatible clamped "
             "ends must yield a nonzero cold floor that survives re-anneal",
        control="tests/test_faithfulness.py:PlantedCycle.test_a_frustrated_cycle_yields_a_persistent_nonzero_floor",
        control_claim="a triangle en1 -> lean -> en2 -> en1 with en1 clamped T and en2 "
                      "clamped F yields holonomy 0.3224, twenty times the 0.0166 of the same "
                      "topology with compatible ends, and re-anneal reproduces it exactly",
    ),
)


@dataclass(slots=True)
class FaithfulnessResult:
    unmapped: list[str] = field(default_factory=list)
    uncontrolled: list[str] = field(default_factory=list)
    unclassified: list[str] = field(default_factory=list)
    checked_rows: int = 0

    @property
    def ok(self) -> bool:
        return not (self.unmapped or self.uncontrolled or self.unclassified)

    @property
    def problems(self) -> list[str]:
        return [*self.unmapped, *self.uncontrolled, *self.unclassified]


def _defines(path: Path, symbol: str) -> bool:
    """True if `symbol` is defined at any level in the module. AST, not import.

    Reading the source means a row still reports usefully when importing the module is
    what broke — which is exactly when an audit is worth having.
    """
    if not path.exists():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == symbol:
                return True
    return False


def _test_exists(root: Path, ref: str) -> bool:
    """`tests/x.py:Class.test_name` -> does that test method exist?"""
    if ":" not in ref:
        return False
    rel, dotted = ref.split(":", 1)
    path = root / rel
    if not path.exists():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    parts = dotted.split(".")
    if len(parts) != 2:
        return _defines(path, dotted)
    cls_name, meth = parts
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            return any(
                isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == meth
                for m in node.body
            )
    return False


def check_faithfulness(root: Path | None = None) -> FaithfulnessResult:
    """Every theory object mapped, controlled, and — where it deviates — classified."""
    base = root or REPO_ROOT
    result = FaithfulnessResult()

    for row in FAITHFULNESS_ROWS:
        result.checked_rows += 1

        if not row.site or not _defines(base / row.module, row.symbol):
            result.unmapped.append(f"{row.object}: site {row.site!r} does not resolve")

        if not row.control or not _test_exists(base, row.control):
            result.uncontrolled.append(
                f"{row.object}: control {row.control!r} names no existing test"
            )
        elif not row.control_claim.strip():
            result.uncontrolled.append(f"{row.object}: control states no claim")

        dev = row.deviation
        if dev is not None:
            if dev.kind not in _KINDS:
                result.unclassified.append(
                    f"{row.object}: deviation kind {dev.kind!r} not in {sorted(_KINDS)}"
                )
            if not dev.note.strip():
                result.unclassified.append(f"{row.object}: deviation states no note")
            if dev.kind == MINIMAL_FAITHFUL and not dev.ruling.strip():
                result.unclassified.append(
                    f"{row.object}: '{MINIMAL_FAITHFUL}' must cite the ruling that permits it"
                )

    return result


def gaps_before_p3() -> list[Row]:
    """Rows where the build does not do what the theory says, and nobody decided that.

    These do not fail `check_faithfulness` — a finding suppressed by a red build is a
    finding nobody reads. They are the list to clear before ingestion.
    """
    return [r for r in FAITHFULNESS_ROWS if r.deviation and r.deviation.kind == GAP]


def by_design() -> list[Row]:
    """Deliberate simplifications, each with the ruling that permits it."""
    return [r for r in FAITHFULNESS_ROWS if r.deviation and r.deviation.kind == MINIMAL_FAITHFUL]
