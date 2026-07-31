"""The nine faithfulness probes: commitment -> probe -> status.

The faithfulness audit (`engine/faithfulness.py`) maps each theory *object* to its code
site. This is the other axis: each faithfulness *commitment* the engine makes to a reader
of its verdicts, and the probe that would catch a breach. A probe is a commitment made
falsifiable.

Nine probes, numbered as the pre-P3 instructions number them. Each carries a `status`:

- ``implemented`` — a live control exists and is cited.
- ``mapped``      — the commitment is already covered by an existing control, which is
                    cited rather than duplicated.
- ``stubbed``     — the commitment cannot be tested yet because a prerequisite chart does
                    not exist (P1 needs the tabular chart; P7 needs the Lean chart to
                    elaborate). The probe is declared so the gap is visible.
- ``inferred``    — the brief named the probe but not its exact commitment, so the mapping
                    to an existing control is this build's best reading and is FLAGGED for
                    confirmation. `check_probe_battery` treats an inferred row as a
                    no-probe row: reported, never silently counted as covered.

`check_probe_battery` fails on a probe whose cited control does not exist, and on a probe
left with no status. It does not fail on `stubbed` or `inferred` — those are findings, and a
finding behind a red build is a finding nobody reads (the same rule the gate-6 sweep and the
faithfulness audit follow).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from .constants import REPO_ROOT

IMPLEMENTED = "implemented"
MAPPED = "mapped"
STUBBED = "stubbed"
INFERRED = "inferred"
_STATUSES = frozenset({IMPLEMENTED, MAPPED, STUBBED, INFERRED})


@dataclass(frozen=True, slots=True)
class Probe:
    id: str
    commitment: str
    probe: str
    status: str
    control: str = ""      # "tests/x.py:Class.test" or "" for a stub
    note: str = ""

    @property
    def is_flagged(self) -> bool:
        """A no-probe row: nothing is actually verifying this commitment yet."""
        return self.status in (STUBBED, INFERRED)


PROBES: tuple[Probe, ...] = (
    Probe(
        id="P1",
        commitment="Chart-invariance of meaning: the same claims stated as prose and as a "
                   "well-formed table settle to identical verdicts.",
        probe="Ingest a claim set twice — once as English prose, once as a markdown table — "
              "and assert the two runs produce the same floors and the same b-values.",
        status=STUBBED,
        note="Blocked on the tabular chart, which the plug-in audit "
             "(engine/chart_plugin_audit.py) shows cannot be added by manifest alone. Until "
             "there is a tabular chart there is nothing to compare prose against. Declared "
             "so the gap is on the board.",
    ),
    Probe(
        id="P2",
        commitment="Gauge invariance: verdicts depend on content, never on document labels "
                   "or arrival order.",
        probe="Relabel every document (new doc_id, new source) and reverse ingestion order; "
              "assert the ledger's floors, b-values, and shadow calibration are "
              "bit-identical.",
        status=IMPLEMENTED,
        control="tests/test_probes.py:P2RelabelAndReorderInvariance.test_relabel_and_reorder_is_bit_identical",
        note="The gate-7 repair (extraction seeded on content, not doc_id) is what makes "
             "this hold. This probe tests the whole ledger, not just extraction.",
    ),
    Probe(
        id="P3",
        commitment="Idempotent re-ingestion: a duplicated corpus adds no structure — no "
                   "new slots, blocks, fibers, loops, or tape rank.",
        probe="Build the ledger from a corpus and from that corpus concatenated with a "
              "relabelled copy of itself; assert every structural count is equal and the "
              "cold floor is bit-identical.",
        status=IMPLEMENTED,
        control="tests/test_probes.py:P3DuplicationGrowsNoStructure.test_a_relabelled_duplicate_adds_no_structure",
        note="Strictly stronger than null cell (v), which checks the floor residue alone; "
             "this checks the whole structure.",
    ),
    Probe(
        id="P4",
        commitment="Clamp screening: a value is grounded only by a clamp-eligible warrant "
                   "(kernel-accept or CI receipt); nothing else can fix a slot.",
        probe="Attempt to construct a Clamp from every warrant tier; assert only KERNEL and "
              "CI_RECEIPT succeed, and that a settled slot holds a clamped value against "
              "contrary evidence while a heavy prior never fixes one.",
        status=IMPLEMENTED,
        control="tests/test_probes.py:P4ClampScreening.test_only_eligible_warrants_ground",
    ),
    Probe(
        id="P5",
        commitment="INFERRED — the brief said 'into existing controls' without naming the "
                   "commitment. This build reads P5 as: settling is sound — F never ascends "
                   "and a non-monotone step voids the block.",
        probe="Existing control: DescentCertificate. An objective rigged to rise exhausts "
              "the halving safeguard and stamps `violated`.",
        status=INFERRED,
        control="tests/test_faithfulness.py:DescentCertificate.test_an_injected_non_monotone_step_voids_the_block",
        note="FLAGGED: mapping inferred, not specified. Confirm P5 is the descent "
             "certificate, or supply its intended commitment.",
    ),
    Probe(
        id="P6",
        commitment="INFERRED — as P5. This build reads P6 as: block independence — disjoint "
                   "contests settle without influencing each other.",
        probe="Existing control: BlocksAreConnectedComponents. Perturbing one component "
              "moves another by exactly zero.",
        status=INFERRED,
        control="tests/test_faithfulness.py:BlocksAreConnectedComponents.test_two_disjoint_contests_settle_independently",
        note="FLAGGED: mapping inferred, not specified. Confirm P6 is block independence.",
    ),
    Probe(
        id="P7",
        commitment="Lean round-trip: an elaborating Lean statement and its English "
                   "restatement close a restatement loop with a floor that reflects genuine "
                   "translation defect, not machinery noise.",
        probe="Ingest an Eng/Lean/Eng triangle over a kernel-checked theorem; assert the "
              "restatement loop is a verified cycle and its floor tracks agreement.",
        status=STUBBED,
        note="Stubbed pending the Lean chart's elaboration path (routing item 3: elaborating "
             ".lean -> Lean chart, non-elaborating -> shelf). The chart tag exists; the "
             "elaboration gate that decides what reaches it does not yet.",
    ),
    Probe(
        id="P8",
        commitment="Provenance completeness: every delta is traceable to its source, and "
                   "every generative key is content-and-seed only — identity labels "
                   "evidence, never generates it.",
        probe="Walk every delta in a ledger; assert each carries a complete Provenance "
              "(source, doc_id, extractor_id, content_hash), that the content hash matches "
              "the document's, and that no DRNG site in engine/ is identity-keyed.",
        status=IMPLEMENTED,
        control="tests/test_probes.py:P8ProvenanceWalker.test_every_delta_is_fully_provenanced_and_no_key_is_identity_keyed",
    ),
    Probe(
        id="P9",
        commitment="INFERRED — as P5. This build reads P9 as: statistical verdicts are "
                   "decided against a null, never a resample of the observation (gate 6).",
        probe="Existing sweep: check_gate6_classification. Every deciding band site is "
              "conforming.",
        status=INFERRED,
        control="tests/test_controls.py:EveryDecidingSiteConforms.test_no_deciding_site_is_non_conforming",
        note="FLAGGED: mapping inferred, not specified. Confirm P9 is gate 6.",
    ),
)


@dataclass(slots=True)
class ProbeBatteryResult:
    missing_control: list[str]
    unstatused: list[str]
    flagged: list[str]           # stubbed or inferred — reported, not failed
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not (self.missing_control or self.unstatused)


def _test_exists(root: Path, ref: str) -> bool:
    if ":" not in ref:
        return False
    rel, dotted = ref.split(":", 1)
    path = root / rel
    if not path.exists():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    parts = dotted.split(".")
    if len(parts) == 1:
        return any(
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and n.name == parts[0]
            for n in ast.walk(tree)
        )
    cls, meth = parts
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == cls:
            return any(
                isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == meth
                for m in node.body
            )
    return False


def check_probe_battery(root: Path | None = None) -> ProbeBatteryResult:
    """Every probe statused; every non-stub probe's control resolves."""
    base = root or REPO_ROOT
    result = ProbeBatteryResult(missing_control=[], unstatused=[], flagged=[])
    for probe in PROBES:
        result.checked += 1
        if probe.status not in _STATUSES:
            result.unstatused.append(f"{probe.id}: status {probe.status!r} not recognised")
            continue
        if probe.is_flagged:
            result.flagged.append(probe.id)
            # An inferred probe still cites a control; verify it if so.
            if probe.control and not _test_exists(base, probe.control):
                result.missing_control.append(
                    f"{probe.id}: mapped control {probe.control!r} does not exist"
                )
            continue
        if not probe.control or not _test_exists(base, probe.control):
            result.missing_control.append(
                f"{probe.id}: control {probe.control!r} names no existing test"
            )
    return result


def flagged_probes() -> list[Probe]:
    """No-probe rows: stubbed (blocked on a chart) or inferred (commitment unconfirmed)."""
    return [p for p in PROBES if p.is_flagged]
