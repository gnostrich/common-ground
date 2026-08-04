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

**As of the DRNG repair there are none.** Two gaps were opened by this audit and both were
ruled implementation defects rather than theory changes: holonomy computed over backtracking
and open walks, and extraction seeded on document identity rather than content. Both are
repaired and their rows now record the repaired behaviour. Every remaining deviation is
`minimal-faithful-by-design` and cites its ruling.
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
        role="Q edges between same-chart slots of a DECLARED-correspondence fiber (membership "
             "is the exact declared relation, never a token-similarity threshold); quadratic "
             "coupling in F",
        control="tests/test_faithfulness.py:IntraChartSheaf.test_same_chart_coupling_pulls_and_dropping_it_releases",
        control_claim="two same-chart slots joined by a declared-correspondence fiber edge "
                      "settle closer together than the same two slots with the edge dropped; "
                      "the edge carries the DECLARED weight, not a graded similarity score",
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
        role="Q edges whose endpoints lie in different charts — a DECLARED typed translation "
             "(OBJECT.md hol over the base morphisms), never inferred from token similarity; "
             "same coupling term, plus shadow subtraction at the meter",
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
        site="engine/meter.py:verify_cycle",
        role="a contest graph with no cycles yields cold floor exactly zero: holonomy is "
             "defined only on verified cycles — closed, every edge in Q, no immediate "
             "backtracking, length >= 3",
        control="tests/test_faithfulness.py:TreeNull.test_tree_null_passes_with_floor_zero",
        control_claim="a cycle-free corpus settles to cold floor exactly 0.0 and is flagged "
                      "`no_cycle_support`; a backtrack walk and an open walk both raise "
                      "`OpenWalkError`; a restatement fiber yields the genuine triangle "
                      "Eng_1 -> Lean -> Eng_2 -> Eng_1",
    ),
    Row(
        object="measured shadow (per-edge closure defect)",
        family="theory",
        site="engine/meter.py:measured_shadow",
        role="the residual of the backtrack walk `u -> v -> u`, reported per edge beside "
             "the seed's declared shadow; cross-chart excess is translator drift",
        control="tests/test_faithfulness.py:MeasuredShadowChannel.test_measured_defect_is_reported_beside_the_seed_declaration",
        control_claim="every Q edge contributes a calibration row with `eps_measured`, the "
                      "seed's `declared`, and their drift; `translator_drift()` names only "
                      "cross-chart edges; and the floor still subtracts the DECLARED shadow, "
                      "never the measured one",
    ),
    Row(
        object="extraction determinism (re-ingestion adds no evidence)",
        family="theory",
        site="engine/extract.py:DeterministicExtractor",
        role="KICKOFF section 4: re-ingesting one corpus under a second provenance label "
             "leaves zero cold residue and no rank growth. Extraction is seeded on the "
             "document's content hash, never on its id.",
        control="tests/test_faithfulness.py:GenerativeKeysAreContentAndSeedOnly.test_a_relabelled_copy_extracts_bit_identically",
        control_claim="identical text under a new `doc_id` AND a new source label yields a "
                      "bit-identical set of evidential identities; null cell (v) is green "
                      "on the standard fixture with residue exactly 0.0; and the live "
                      "extractor's prompt carries a content hash rather than a doc_id",
    ),
    Row(
        object="generative keys are content-and-seed only (gate 7)",
        family="structure",
        site="engine/static_checks.py:check_generative_keys",
        role="every random stream, address, cache and dedup key in ingestion and settlement "
             "is keyed on content or on the seed; artifact identity lives in provenance",
        control="tests/test_faithfulness.py:GenerativeKeysAreContentAndSeedOnly.test_every_generative_key_is_classified_and_none_is_identity_keyed",
        control_claim="every `DRNG(...)` site in `engine/` is classified in "
                      "`GENERATIVE_KEY_SITES`, no row is `identity`-keyed, every `design` "
                      "row cites the ruling that requires it, and an unclassified new "
                      "stream fails the check",
        deviation=Deviation(
            kind=MINIMAL_FAITHFUL,
            note="Three sites are identity-derived on purpose. `lexicon.sense_id` includes "
                 "the source tier, so the same lemma from Mathlib and from WordNet occupies "
                 "two addresses rather than one. `seed_lock.build_manifest` and "
                 "`importer_script_hash` key on repo-relative paths as well as content, so "
                 "renaming a seed file moves the seed hash even when its bytes do not. "
                 "Neither lets identity change *what* is read; the first stops two readings "
                 "silently becoming one, the second stops a rename passing unseen.",
            ruling="LEXICON SPEC section 2 ('Never auto-merge. Senses keyed by (lemma, "
                   "type_sig, source)') for the first; GATES.md sentence 4 ('Anything that "
                   "moves addresses is plastic ... No silent bumps') for the other two.",
        ),
    ),
    Row(
        object="chart plug-in seam (charts are a seed manifest, not a literal)",
        family="structure",
        site="engine/charts.py:chart_spec",
        role="charts declared in seed/CHARTS.json; nu/classify/segment dispatch by behavior "
             "id with no `if chart == ...` anywhere; a new chart is a manifest row plus "
             "registered behaviors, and admission is gated by chart_plugin_audit",
        control="tests/test_probes.py:TheChartAuditCanDetectAReintroducedDefect.test_the_audit_goes_red_end_to_end_when_a_dispatch_is_planted",
        control_claim="the shipped tree audits clean (0 blocking sites, manifest-only "
                      "possible), AND a planted `if chart == ...` dispatch turns the audit "
                      "red both at the detector and end-to-end — so the gate can fail",
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
