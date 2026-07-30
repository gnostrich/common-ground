"""PREREG R1-R5, evaluated mechanically.

Each rule is a function returning a verdict. No rule is decided by a person reading a
number: R3's "~0" is `floor <= second_fdt_surrogate_floor`, R4's "moves < surrogate noise"
is a comparison against a prior-dropout null, and R5 is enforced by the verdict vocabulary
having no `pending` member.

Amendments to the pre-registration live in `AMENDMENTS` below and in `registry/PREREG.md`.
R1-R5's original text is never rewritten; an amendment is appended and cited from the code
it changes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping, Sequence

from . import GateViolation
from .blocks import drop_edges, rewire_q_graph
from .constants import (
    BVALUE_INDEX,
    BVALUES,
    NBV,
    PRIOR_DROPOUT_RATE,
    PRIOR_DROPOUT_TRIALS,
    REGISTRY_DIR,
    SURROGATE_QUANTILE,
)
from .extract import Extractor
from .hashing import DRNG, quantile
from .meter import MeterResult, pooled_loop_nulls, studentized_loop_thresholds
from .normalize import address, classify
from .pipeline import Ledger, build_ledger, run_meter
from .types import Clamp, Document, NullBatteryReport, NullStatus

#: Authorized, logged amendments to the pre-registration. Append-only.
AMENDMENTS: tuple[dict[str, object], ...] = (
    {
        "id": "PREREG-AMENDMENT-1",
        "date": "2026-07-30",
        "rule": "R3",
        "change": (
            "near_zero is decided by `floor <= second_fdt_surrogate_floor` "
            "(warm/cold label permutation) instead of "
            "`floor <= quantile(surrogate_floor_distribution, 0.95)` (bootstrap of the "
            "observed floors). The bootstrap band is retained as a legacy diagnostic and "
            "decides nothing."
        ),
        "rationale": (
            "(a) transcription defect: the specification always named the second-FDT "
            "surrogate — it is the reference the mint threshold is quoted against in the "
            "seed/GATES.md constants table — and the bootstrap was a drafting degradation, "
            "not a design decision. "
            "(b) no data has passed through R3: P3 and P4 have not run, so no verdict is "
            "being revised after seeing a result. "
            "(c) the amendment is strictness-increasing: the label-permutation threshold "
            "is not centred on the observation, so the `~0` branch — the branch that "
            "advances no protocol claim but does declare the pipeline self-consistent — "
            "becomes harder to obtain, never easier."
        ),
        "authorized_by": "operator",
        "expires": "the moment P3 ingestion begins",
        "class": "transcription-restoration",
        "class_note": (
            "Restores a procedure the specification already named. Admissible on all three "
            "rationales, (a) included."
        ),
        "rationales": ["a", "b", "c"],
        "also": (
            "seed/GATES.md sentence 6 added; D7 re-approved over the amended PREREG; "
            "cold re-anneal under gate 4."
        ),
    },
    {
        "id": "PREREG-AMENDMENT-2",
        "date": "2026-07-30",
        "rule": "R4",
        "class": "pre-data-design",
        "class_note": (
            "NOT a transcription restoration. The specification never named this "
            "procedure; the null-rewire reference and the two-sided arm are both new "
            "design. The class field exists to keep this distinct from "
            "PREREG-AMENDMENT-1, which only restored what was already specified — a "
            "design amendment carries more weight of judgement and its admissibility "
            "rests entirely on the pre-data timing."
        ),
        "rationales": ["b", "c"],
        "rationale_a_applies": False,
        "rationale_a_note": (
            "(a) transcription defect does NOT apply. Nothing in the specification named "
            "a null-rewire reference or a sensitivity arm, so there is nothing to restore. "
            "Claiming (a) here would misrepresent a design choice as a correction."
        ),
        "change": (
            "R4 becomes two-sided. Insensitivity arm (as registered): cold-floor movement "
            "under real 10% Q-edge dropout, 5 trials, PASS iff <= q95 of the movement "
            "under the same dropout applied to a degree- and weight-marginal-preserving "
            "randomization of the Q graph (endpoint permutation within weight strata), "
            "same trial count. Sensitivity arm (added): clamp-tier perturbation must move "
            "the floor ABOVE that same null. Both are reported; both are gate-6 "
            "conforming. The superseded self-scaled bootstrap band is retained as "
            "`legacy_self_scaled_band` and decides nothing."
        ),
        "rationale": (
            "(b) no data has passed through R4: P3 and P4 have not run, so no verdict is "
            "being revised in sight of a result. "
            "(c) the amendment is strictness-increasing on both arms: the insensitivity "
            "arm no longer buys tolerance by having a large floor — the superseded band "
            "scaled with the observed floor and so relaxed exactly where dictionary "
            "sensitivity mattered most — and a second arm must now also pass, so no "
            "outcome that passed before can fail to pass a strictly larger set of checks."
        ),
        "authorized_by": "operator",
        "expires": "the moment P3 ingestion begins",
        "also": (
            "GATES.md gate-6 enforcement row updated; D7 re-approved over the "
            "twice-amended PREREG; cold re-anneal under gate 4; codebase-wide gate-6 "
            "conformance sweep in reports/gate6-sweep.md."
        ),
    },
    {
        "id": "PREREG-AMENDMENT-3",
        "date": "2026-07-30",
        "rule": "R2",
        "class": "pre-data-design",
        "class_note": (
            "Checked against the drafting history before classifying, as authorized. The "
            "history shows no original intent to restore, so transcription-restoration "
            "does not apply and this is design."
        ),
        "drafting_history": (
            "KICKOFF section 5 R2 reads in full: 'the meter must flag the known "
            "claim-vs-proof gaps enumerated in STATEMENTS.md \"what we do NOT claim\". Miss "
            "rate > 0 on that list => meter insensitive at this scale => "
            "CLOSED-inconclusive.' It specifies no flagging criterion whatsoever — no "
            "threshold, no surrogate, no comparison. The brief's only mention of the "
            "second-FDT surrogate is the mint threshold in the constants table, which is "
            "unrelated to R2. Git shows `band = result.surrogate.get(\"q95\", 0.0)` present "
            "in the first commit (P0 scaffold) and unchanged since. The criterion was "
            "therefore originated during P0 drafting, not degraded from a specified one, "
            "and rationale (a) does not apply."
        ),
        "rationales": ["b", "c"],
        "rationale_a_applies": False,
        "change": (
            "A gap counts as flagged iff its loop's cold floor exceeds q95 of a "
            "second-FDT label-permutation null — each slot on the loop independently "
            "supplying its state from the warm or cold arm, holonomy recomputed. Miss rate "
            "is computed over the pre-registered STATEMENTS.md list exactly as before. The "
            "legacy bootstrap flagging is retained as `legacy_bootstrap_flagged` and "
            "decides nothing."
        ),
        "deviation_from_authorization": (
            "The authorization specified q95 of *that loop's own* null. Implemented "
            "literally that criterion is unsatisfiable: a k-slot loop has 2**k assignments, "
            "the all-cold assignment IS the observed floor, and q95 of four or eight points "
            "is the maximum — so no loop can exceed its own null at any floor. Measured on "
            "a synthetic contested corpus: 0 of 4 loops could flag, giving a 100% miss rate "
            "on every run, which reproduces the defect being replaced and fails rationale "
            "(c) on its own terms. The mandated positive control is what caught this. The "
            "shipped rule pools the OTHER loops' permuted floors leave-one-out, which is "
            "the smallest change that keeps the null a permutation of observations while "
            "giving it usable support. This deviation needs operator confirmation."
        ),
        "known_limitation": (
            "Pooling assumes loops are exchangeable with one another, and they are not "
            "exactly — they differ in slot count and edge weight. One loud loop raises "
            "every other loop's threshold. Leave-one-out removes self-contamination but "
            "not heterogeneity."
        ),
        "rationale": (
            "(b) no data has passed through R2: P3 and P4 have not run, and R2 is BLOCKED "
            "on D5 besides, so no verdict is being revised in sight of a result. "
            "(c) calibration-restoring, NOT strictness-increasing. The bootstrap band rose "
            "with the observed floor, so it was punitive on noisy runs — flagging only "
            "above-average loops and missing genuine gaps whose floors were real but below "
            "the mean. The permutation null corrects in BOTH directions: some runs that "
            "failed R2 will now pass. That is the correction, not a loosening, and it is "
            "recorded as such rather than claimed as extra strictness."
        ),
        "positive_control": (
            "Mandated and implemented in tests/test_controls.py:R2AfterTheAmendment. "
            "Direction one: clean synthetic run plus one planted gap -> miss rate 0. "
            "Planted-defect direction: an insensitive meter (every loop the same floor and "
            "the same null) -> the planted gap goes unflagged, miss rate 1.0, "
            "CLOSED-inconclusive. Fewer than two loops -> inconclusive rather than a "
            "degenerate self-comparison."
        ),
        "specification_defect_acknowledged": (
            "The per-loop-only wording in the authorization is the source of the defect, "
            "not an implementation misreading. `q95 of that loop's own null` is "
            "unsatisfiable for any loop at any floor, and the deviation exists solely to "
            "make the rule capable of firing. The operator has acknowledged this and "
            "accepted the leave-one-out repair."
        ),
        "repair_attempt": {
            "id": "PREREG-AMENDMENT-3.repair-1",
            "proposal": "studentize the pooled null — each loop's permuted floors scaled "
                        "by its own null MAD, observed floors in the same units, per-loop "
                        "fallback to raw LOO where the scale is degenerate",
            "intent": "mitigate the exchangeability limitation: loops differ in slot count "
                      "and edge weight, so one loud loop raises every other loop's "
                      "threshold in absolute units",
            "outcome": "REJECTED on its controls, single attempt as authorized",
            "evidence": "On the mandated direction-one control (clean synthetic run plus "
                        "one planted gap), the planted gap's loop — floor 0.218 — "
                        "studentized to -0.089 and did NOT flag, while a numerically "
                        "negligible loop at floor 5.5e-08 studentized to +4.573 and DID. "
                        "Miss rate 1.0 where raw leave-one-out gives 0.0. The repair did "
                        "not merely fail; it inverted the result.",
            "why": "A loop's floor and its permutation null's scale are the same quantity — "
                   "both are produced by warm/cold disagreement on that loop. A loop with a "
                   "real gap has a large floor AND a large null MAD, so the ratio is not "
                   "distinctive, and what survives studentization is loops whose null is "
                   "nearly degenerate. Studentizing is right when scale is a nuisance "
                   "parameter; here it is the estimand.",
            "loud_loop_control": "Ran as specified against raw LOO as shipped: adding a "
                                 "loop with a far larger floor changed no shared loop's "
                                 "flag status and left the miss rate stable. That is one "
                                 "instance, not a proof of insensitivity.",
            "disposition": "raw leave-one-out stands as shipped; the exchangeability "
                           "limitation stays OPEN, not mitigated. The rejected code is "
                           "retained, wired to nothing, classified `rejected` in "
                           "GATE6_SITES, and pinned by "
                           "tests/test_controls.py:StudentizationWasTriedAndRejected.",
        },
        "authorized_by": "operator",
        "expires": "the moment P3 ingestion begins",
        "also": (
            "D7 re-approved over the thrice-amended PREREG; cold re-anneal under gate 4; "
            "gate-6 sweep re-run — every deciding site conforms."
        ),
    },
)


def p3_has_begun(registry_path: Path | None = None) -> bool:
    """True once any P3 phase-run has been registered.

    The amendment authorization is scoped: it expires when P3 ingestion begins. After that
    point no rule may be amended, because the moment data starts flowing through the rules
    an amendment stops being a correction and starts being a choice made in sight of a
    result — which is the thing pre-registration exists to prevent.
    """
    path = registry_path or (REGISTRY_DIR / "REGISTRY.jsonl")
    if not path.exists():
        return False
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("entry") == "phase-run" and str(entry.get("phase", "")).upper().startswith("P3"):
            return True
    return False


def check_amendment_window(registry_path: Path | None = None) -> None:
    """Refuse a further PREREG amendment once P3 has begun. Mechanical, not remembered."""
    if p3_has_begun(registry_path):
        raise GateViolation(
            4,
            "the PREREG amendment window closed when P3 ingestion began: "
            f"{len(AMENDMENTS)} amendment(s) stand as logged and no further amendment is "
            "authorized. A rule changed after data has flowed through it is a choice made "
            "in sight of a result.",
        )


class Verdict(str, Enum):
    """R5: terminal vocabulary. There is deliberately no `pending`."""

    VOID = "VOID"
    CLOSED_INCONCLUSIVE = "CLOSED-inconclusive"
    CLOSED_REJECTED = "CLOSED-rejected"
    FLOOR_NEAR_ZERO = "floor ~0"
    FLOOR_STRUCTURED = "floor structured"


@dataclass(slots=True)
class RuleResult:
    rule: str
    verdict: Verdict | None
    passed: bool
    detail: str
    stats: dict[str, object] = field(default_factory=dict)


# --- R1 ---------------------------------------------------------------------------


def harness(nulls: NullBatteryReport) -> RuleResult:
    """R1: cells 4.i-v green, else the entire run is VOID (published as such)."""
    ok = nulls.status is NullStatus.PASS
    blocked = [c.cell for c in nulls.cells if c.status is NullStatus.BLOCKED]
    failed = [c.cell for c in nulls.cells if c.status is NullStatus.FAIL]

    if ok:
        detail = "all five null cells green"
    elif failed:
        detail = f"null cells FAILED: {failed}" + (f"; also BLOCKED: {blocked}" if blocked else "")
    else:
        detail = (
            f"null cells BLOCKED (inputs unresolved, never tested): {blocked}. "
            "Not green, so R1 applies and the run is VOID — but this is 'never tested', "
            "not 'tested and failed'."
        )

    return RuleResult(
        rule="R1",
        verdict=None if ok else Verdict.VOID,
        passed=ok,
        detail=detail,
        stats={"status": nulls.status.value, "blocked": blocked, "failed": failed},
    )


# --- R2 ---------------------------------------------------------------------------


def ground_truth_rediscovery(
    statements_doc: Document | None,
    result: MeterResult,
    ledger: Ledger,
    not_claimed_spans: Sequence[str] | None = None,
) -> RuleResult:
    """R2: the meter must flag every claim-vs-proof gap in STATEMENTS.md "what we do NOT claim".

    A gap is *flagged* iff the slot addressing its span appears on a loop whose cold floor
    exceeds that loop's label-permutation null. Miss rate above zero means the meter is
    insensitive at this scale.

    **PREREG-AMENDMENT-3 (2026-07-30), class `pre-data-design`.** The flagging criterion
    was `m.floor > result.surrogate["q95"]` — the bootstrap of the observed floors — so
    "flagged" meant "above average for this run" rather than "above what no path dependence
    would produce". It is now a label-permutation null: each slot on a loop independently
    supplies its state from the warm or the cold arm, the holonomy is recomputed, and the
    resulting floors are the reference.

    **Drafting history, checked.** KICKOFF §5's R2 says only "the meter must flag the known
    claim-vs-proof gaps ... Miss rate > 0 => CLOSED-inconclusive". It specifies no flagging
    criterion at all, and the brief's only mention of the second-FDT surrogate is the mint
    threshold in the constants table. The bootstrap was present in the first commit and
    never changed. So there is **no original intent to restore**: the criterion was
    originated at P0, not degraded from a specified one, and rationale (a) does not apply.

    **Rationale (c) is calibration-restoring, not strictness-increasing.** The bootstrap
    band rose with the observed floor, so it was punitive on noisy runs — on a
    uniformly-zero run nothing cleared it and the miss rate was 100%, reporting the meter as
    insensitive when nothing was wrong. The permutation null corrects in *both* directions:
    it can flag on a quiet run and it can decline to flag on a loud one. Some runs that
    failed R2 will now pass, and that is the correction rather than a loosening.

    **Why the null is pooled leave-one-out.** A single loop's permutation null has only
    `2**k` distinct values, and the all-cold assignment — the observed floor — sits at or
    below the maximum, which is what q95 of four points returns. Measured on a synthetic
    contested corpus: 0 of 4 loops could flag at any floor, so the literal per-loop rule
    would give a 100% miss rate on every run, reproducing the very defect it replaces. Each
    loop's threshold is therefore the q95 of every *other* loop's permuted floors. The null
    is still nothing but relabelled observations, and a loop can no longer inflate its own
    bar. This is a deviation from the authorized wording, recorded here and in the
    amendment; the positive control below is what caught it.

    **Fewer than two loops is inconclusive.** A permutation null needs more than one
    exchangeable unit. Rather than fall back to the degenerate self-comparison, R2 reports
    `CLOSED-inconclusive`.

    The legacy bootstrap flagging is retained as `legacy_bootstrap_flagged` and decides
    nothing. The docstring previously also promised flagging on settled mass at `B`; the
    code never implemented it, and the amendment's "iff" removes the claim rather than
    leaving a promise the code does not keep.
    """
    if statements_doc is None and not not_claimed_spans:
        return RuleResult(
            rule="R2",
            verdict=Verdict.CLOSED_INCONCLUSIVE,
            passed=False,
            detail=(
                "D5 is unresolved: STATEMENTS.md is absent, so there is no enumerated "
                "'what we do NOT claim' list to rediscover. R2 cannot be satisfied by a "
                "test that was never run."
            ),
            stats={"targets": 0},
        )

    spans = list(not_claimed_spans or _extract_not_claimed(statements_doc))
    if not spans:
        return RuleResult(
            rule="R2",
            verdict=Verdict.CLOSED_INCONCLUSIVE,
            passed=False,
            detail="STATEMENTS.md contains no parseable 'what we do NOT claim' entries",
            stats={"targets": 0},
        )

    thresholds = pooled_loop_nulls(result.loop_nulls)
    if len(result.loop_nulls) < 2:
        return RuleResult(
            rule="R2",
            verdict=Verdict.CLOSED_INCONCLUSIVE,
            passed=False,
            detail=(
                f"{len(result.loop_nulls)} loop(s) measured: a label-permutation null needs "
                "more than one exchangeable unit, so no loop has a threshold to clear. "
                "R2 cannot be satisfied by a test that could not run."
            ),
            stats={"targets": len(spans), "loops": len(result.loop_nulls),
                   "decided_by": "loop_permutation_null_pooled_loo",
                   "gate6_conforming": True},
        )

    flagged_slots = {
        s for m in result.measurements
        if m.floor > thresholds.get(m.loop_id, float("inf"))
        for s in m.slots
    }

    legacy_band = result.surrogate.get("q95", 0.0)
    legacy_flagged = {
        s for m in result.measurements if m.floor > legacy_band for s in m.slots
    }

    misses: list[str] = []
    for span in spans:
        slot, _ = address("english", span, classify("english", span))
        if slot not in flagged_slots:
            misses.append(span[:80])

    miss_rate = len(misses) / len(spans)
    ok = miss_rate == 0.0
    return RuleResult(
        rule="R2",
        verdict=None if ok else Verdict.CLOSED_INCONCLUSIVE,
        passed=ok,
        detail=(
            f"meter flagged all {len(spans)} enumerated gaps"
            if ok
            else f"miss rate {miss_rate:.2%} ({len(misses)}/{len(spans)}); "
            "meter insensitive at this scale"
        ),
        stats={
            "targets": len(spans), "misses": misses, "miss_rate": miss_rate,
            "loops": len(result.loop_nulls),
            "flagged_slots": len(flagged_slots),
            "loop_thresholds": thresholds,
            "decided_by": "loop_permutation_null_pooled_loo",
            "studentization": "attempted and rejected; see AMENDMENTS[2].repair_attempt",
            "gate6_conforming": True,
            "legacy_bootstrap_band": legacy_band,          # decides nothing
            "legacy_bootstrap_flagged": len(legacy_flagged),
        },
    )


def _extract_not_claimed(doc: Document | None) -> list[str]:
    """Pull the bullet lines out of a 'what we do NOT claim' section."""
    if doc is None:
        return []
    out: list[str] = []
    capturing = False
    for line in doc.text.splitlines():
        stripped = line.strip()
        low = stripped.casefold()
        if stripped.startswith("#"):
            capturing = "do not claim" in low or "not claimed" in low
            continue
        if capturing and stripped.startswith(("-", "*", "+")):
            out.append(stripped.lstrip("-*+ ").strip())
    return [s for s in out if s]


# --- R3 ---------------------------------------------------------------------------


def floor_verdict(result: MeterResult, beta: float | None = None) -> RuleResult:
    """R3: cold floor after shadow subtraction is either ~0 or structured.

    "~0" is `floor <= second_fdt_surrogate_floor` — never an eyeball reading. The two
    branches are different findings, not degrees of one: `~0` validates the pipeline and
    advances no protocol claim; `structured` yields modes reported verbatim with no
    interpretation beyond listing them.

    **PREREG-AMENDMENT-1 (2026-07-30).** The decisive surrogate is the second-kind
    fluctuation-dissipation floor: warm/cold labels permuted loop by loop, which is a null
    constructed under the no-effect hypothesis that the two arms are exchangeable. Under
    that null the distribution matches the observed floor; under real path dependence the
    observed floor exceeds it.

    It previously read `floor <= quantile(surrogate_floor_distribution, 0.95)`, a bootstrap
    of the observed loop floors. That band is centred on the data and moves with whatever
    floor it is handed, so a mean floor of 0.45 carried entirely by the cold arm was called
    `~0` — the same vacuity that retired null cells (iv) and (v). The specification always
    named the second-FDT surrogate (it is the reference the mint threshold is quoted
    against, `seed/GATES.md` constants table); the bootstrap was a drafting degradation, not
    a design decision.

    The bootstrap band is still computed and reported as `surrogate_q95`, a **legacy
    diagnostic**. It decides nothing. Both numbers appear in `stats` on every verdict, and
    a disagreement between them is called out in the detail line.

    See `registry/PREREG.md` for the amendment record and `seed/GATES.md` sentence 6 for
    the constitutional rule this now instantiates.
    """
    floor = result.mean_floor(beta)
    band = result.surrogate.get("q95", 0.0)
    fdt = result.surrogate.get("second_fdt_floor", 0.0)
    near_zero = floor <= fdt
    legacy_branch = floor <= band
    caveat = "" if legacy_branch == near_zero else (
        f" NOTE: the legacy bootstrap band disagrees (q{int(SURROGATE_QUANTILE * 100)} "
        f"{band:.6g} would have said "
        f"{'near_zero' if legacy_branch else 'structured'}). It is centred on the observed "
        "floors and decides nothing; PREREG-AMENDMENT-1 refers."
    )

    modes = [] if near_zero else [
        {
            "loop_id": m.loop_id,
            "kind": m.kind,
            "beta": m.beta,
            "cold": m.cold,
            "warm": m.warm,
            "shadow": m.shadow,
            "floor": m.floor,
            "path_debt": m.path_debt,
            "warm_source": m.warm_source,
            "slots": list(m.slots),
        }
        for m in result.modes(beta)
        # Filtered by the decisive threshold, not the legacy one: a mode is a loop whose
        # floor stands above its own label permutation.
        if m.floor > fdt
    ]

    return RuleResult(
        rule="R3",
        verdict=Verdict.FLOOR_NEAR_ZERO if near_zero else Verdict.FLOOR_STRUCTURED,
        passed=True,  # R3 does not fail; it reports which branch obtains.
        detail=(
            f"cold floor {floor:.6g} <= second-FDT surrogate floor {fdt:.6g}: all contest "
            "is path-debt; the ledger is self-consistent. v0 validation of the pipeline; "
            "protocol claims NOT advanced."
            if near_zero
            else f"cold floor {floor:.6g} > second-FDT surrogate floor {fdt:.6g}: "
            f"structured. {len(modes)} mode(s) reported verbatim; "
            "no interpretation beyond listing."
        ) + caveat,
        stats={
            "floor": floor,
            "second_fdt_floor": fdt,          # decisive (PREREG-AMENDMENT-1)
            "surrogate_q95": band,            # legacy diagnostic; decides nothing
            "legacy_bootstrap_branch": "near_zero" if legacy_branch else "structured",
            "surrogates_agree": legacy_branch == near_zero,
            "decided_by": "second_fdt_surrogate_floor",
            "modes": modes,
        },
    )


# --- R4 ---------------------------------------------------------------------------


def _floor_movements(
    documents,
    extractors,
    beta: float,
    seed_hash: str,
    shadow_cfg,
    trials: int,
    rate: float,
    label: str,
    rewire: bool,
    clamps=(),
) -> tuple[list[float], float]:
    """Movement of the cold floor under `trials` dropout trials, and the arm's own base.

    `rewire=True` randomizes the Q graph first (degree- and weight-marginal preserving),
    which is the R4 null: the arm measures how much dropout moves the floor when the edge
    set carries no dictionary content. Each arm is measured against *its own* undropped
    baseline, because a rewired graph settles somewhere else and the quantity being
    compared is a movement, not a level.
    """
    base_ledger = build_ledger(
        documents,
        extractors,
        clamps=clamps,
        edge_filter=(lambda edges: rewire_q_graph(edges, DRNG("R4-rewire", seed_hash, label)))
        if rewire
        else None,
    )
    base_result, _, _ = run_meter(base_ledger, beta, seed_hash, shadow_cfg)
    base_floor = base_result.mean_floor()

    movements: list[float] = []
    for trial in range(trials):
        rng = DRNG("R4", seed_hash, label, str(trial))

        def _filter(edges, _rng=rng, _trial=trial):
            if rewire:
                edges = rewire_q_graph(edges, DRNG("R4-rewire", seed_hash, label, str(_trial)))
            return drop_edges(edges, rate, _rng)

        ledger = build_ledger(documents, extractors, clamps=clamps, edge_filter=_filter)
        result, _, _ = run_meter(ledger, beta, seed_hash, shadow_cfg)
        movements.append(abs(result.mean_floor() - base_floor))

    return movements, base_floor


def _perturb_clamps(clamps: Sequence[Clamp]) -> list[Clamp]:
    """Rotate every clamp to a different b-value.

    The two-sided arm needs an intervention that *should* move the verdict. A clamp is the
    only thing in the engine that can fix a slot's value outright (gate 3), so moving one
    is the largest legitimate perturbation available. If the floor does not respond to it,
    the meter is not sensitive to anything and R4's insensitivity arm passing means
    nothing.

    The rotation preserves the clamp's warrant, so every rotated clamp is still
    clamp-eligible and `Clamp.__post_init__` still holds. This is a measurement of the
    meter, not a smuggling route around gate 3.
    """
    import dataclasses

    # BValue is a Literal, not an Enum: the canonical ordering is BVALUES in CONSTANTS.json,
    # which is what BVALUE_INDEX and every energy vector are indexed by.
    return [
        dataclasses.replace(
            c, value=BVALUES[(BVALUE_INDEX[c.value] + 1) % NBV]
        )
        for c in clamps
    ]


def prior_insensitivity(
    documents: Sequence[Document],
    extractors: Sequence[Extractor],
    beta: float,
    seed_hash: str,
    shadow_cfg: Mapping[str, object],
    baseline: MeterResult,
    trials: int = PRIOR_DROPOUT_TRIALS,
    rate: float = PRIOR_DROPOUT_RATE,
    clamps: Sequence[Clamp] = (),
) -> RuleResult:
    """R4: the cold floor must be insensitive to the dictionary and sensitive to grounding.

    **PREREG-AMENDMENT-2 (2026-07-30).** Two arms, both decided against the same null:

    - **insensitivity (as registered).** Drop 10% of Q edges at random, 5 trials. PASS iff
      the real-dropout movement is `<= q95` of the *null-rewire* movement.
    - **sensitivity (added).** Perturb the clamp tier. PASS iff that movement is `>` the
      same null. A rule that only ever asks "did nothing move?" is satisfied by a meter
      that cannot move at all; this arm is the positive control that makes the first arm's
      pass mean something.

    The null is dropout applied to a **degree- and weight-marginal-preserving
    randomization** of the Q graph (`blocks.rewire_q_graph`): same nodes, same degree per
    node, same weight multiset per stratum, randomized pairings. It is constructed under
    the hypothesis the rule is testing — *the dictionary does not matter* — which is what
    GATES.md sentence 6 requires and what the superseded version did not do.

    The superseded version compared movement against `baseline.surrogate["q95"]`, the
    bootstrap of the observed floors. That was not vacuous the way R3's was; it was
    miscalibrated in the permissive direction, because the band scales with the observed
    floor and so relaxed exactly where dictionary sensitivity would have mattered most. It
    is retained and reported as `legacy_self_scaled_band`, and decides nothing.

    Unlike PREREG-AMENDMENT-1 this is **not** a transcription restoration — the
    specification never named this procedure. It is a pre-data design amendment, admissible
    on rationale (b) (no data has passed through R4) and (c) (strictness-increasing: the
    insensitivity arm no longer buys tolerance by having a large floor, and a second arm
    must now also pass). See `AMENDMENTS`.
    """
    real, base_floor = _floor_movements(
        documents, extractors, beta, seed_hash, shadow_cfg, trials, rate,
        label="real", rewire=False, clamps=clamps,
    )
    null, null_base = _floor_movements(
        documents, extractors, beta, seed_hash, shadow_cfg, trials, rate,
        label="null", rewire=True, clamps=clamps,
    )

    worst = max(real) if real else 0.0
    null_band = quantile(null, SURROGATE_QUANTILE)
    legacy_band = baseline.surrogate.get("q95", 0.0)
    insensitive = worst <= null_band

    # --- the two-sided arm ---------------------------------------------------------
    if clamps:
        perturbed = build_ledger(documents, extractors, clamps=_perturb_clamps(clamps))
        perturbed_result, _, _ = run_meter(perturbed, beta, seed_hash, shadow_cfg)
        clamp_movement = abs(perturbed_result.mean_floor() - base_floor)
        sensitive = clamp_movement > null_band
        sensitivity_detail = (
            f"clamp-tier perturbation moved the floor by {clamp_movement:.6g} "
            f"{'>' if sensitive else '<='} null {null_band:.6g}"
        )
    else:
        clamp_movement = None
        sensitive = None
        sensitivity_detail = (
            "clamp-tier perturbation NOT RUN: the ledger carries no clamps (D6 unresolved, "
            "so no kernel-accept or CI receipt has grounded anything). The sensitivity arm "
            "is untested, which is not the same as passed."
        )

    if sensitive is None:
        verdict, ok = Verdict.CLOSED_INCONCLUSIVE, False
        headline = (
            "R4 cannot be evaluated: the sensitivity arm has nothing to perturb. "
            "Reporting the insensitivity arm alone would claim a two-sided test that "
            "was never run."
        )
    elif insensitive and sensitive:
        verdict, ok = None, True
        headline = (
            f"worst real-dropout movement {worst:.6g} <= null-rewire q"
            f"{int(SURROGATE_QUANTILE * 100)} {null_band:.6g}, and grounding does move the "
            "floor: the verdicts track the ledger, not the dictionary."
        )
    elif not insensitive:
        verdict, ok = Verdict.CLOSED_REJECTED, False
        headline = (
            f"floor moved by {worst:.6g} > null-rewire q{int(SURROGATE_QUANTILE * 100)} "
            f"{null_band:.6g} under {int(rate * 100)}% Q-edge dropout: verdicts are "
            "dictionary artifacts. Seed design rejected, CLOSED."
        )
    else:
        verdict, ok = Verdict.CLOSED_REJECTED, False
        headline = (
            "the floor is insensitive to the dictionary AND insensitive to grounding: "
            "the meter does not respond to the one intervention that should move it, so "
            "the insensitivity arm carries no information. Seed design rejected, CLOSED."
        )

    return RuleResult(
        rule="R4",
        verdict=verdict,
        passed=ok,
        detail=f"{headline} {sensitivity_detail}.",
        stats={
            "baseline_floor": base_floor,
            "movements": real,
            "worst": worst,
            "null_movements": null,
            "null_band": null_band,
            "null_rewire_baseline_floor": null_base,
            "clamp_movement": clamp_movement,
            "insensitivity_arm": insensitive,
            "sensitivity_arm": sensitive,
            "legacy_self_scaled_band": legacy_band,   # decides nothing
            "legacy_branch": "pass" if worst < legacy_band else "reject",
            "decided_by": "null_rewire_q95",
            "gate6_conforming": True,
            "rate": rate,
            "trials": trials,
        },
    )


# --- assembly ---------------------------------------------------------------------


@dataclass(slots=True)
class AuditReport:
    seed_hash: str
    rules: list[RuleResult] = field(default_factory=list)

    @property
    def terminal_verdict(self) -> Verdict:
        """R5: always terminal, never pending.

        Precedence follows severity of what went wrong: a void harness makes every later
        rule unreadable, a rejected seed design makes the verdicts unattributable, and an
        insensitive meter makes a null floor uninformative. Only when none of those
        obtain does R3's branch stand as the verdict.
        """
        by_rule = {r.rule: r for r in self.rules}
        for rule in ("R1", "R4", "R2"):
            r = by_rule.get(rule)
            if r is not None and not r.passed and r.verdict is not None:
                return r.verdict
        r3 = by_rule.get("R3")
        return r3.verdict if r3 and r3.verdict else Verdict.CLOSED_INCONCLUSIVE

    def as_record(self) -> dict[str, object]:
        return {
            "seed_hash": self.seed_hash,
            "verdict": self.terminal_verdict.value,
            "rules": [
                {
                    "rule": r.rule,
                    "passed": r.passed,
                    "verdict": r.verdict.value if r.verdict else None,
                    "detail": r.detail,
                    "stats": r.stats,
                }
                for r in self.rules
            ],
        }


#: KICKOFF section 5, verbatim. Reproduced in every report so that no outcome can be
#: read as advancing one of them.
NOT_CLAIMED: tuple[str, ...] = (
    "capacity conjecture (needs n>=2 / diversity arms)",
    "growth law (mint off)",
    "comms utility (single party)",
    "generality beyond this corpus and seed hash",
)
