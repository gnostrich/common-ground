"""PREREG R1-R5, evaluated mechanically.

Each rule is a function returning a verdict. No rule is decided by a person reading a
number: R3's "~0" is `floor <= surrogate q95`, R4's "moves < surrogate noise" is the same
comparison on the movement, and R5 is enforced by the verdict vocabulary having no
`pending` member.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Mapping, Sequence

from .blocks import drop_edges
from .constants import PRIOR_DROPOUT_RATE, PRIOR_DROPOUT_TRIALS, SURROGATE_QUANTILE
from .extract import Extractor
from .hashing import DRNG, quantile
from .meter import MeterResult
from .normalize import address, classify
from .pipeline import Ledger, build_ledger, run_meter
from .types import Document, NullBatteryReport, NullStatus


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

    A gap is *flagged* if the slot addressing its span appears on a loop whose floor is
    above the surrogate band, or carries settled mass on `B`. Miss rate above zero means
    the meter is insensitive at this scale.
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

    band = result.surrogate.get("q95", 0.0)
    flagged_slots = {
        s for m in result.measurements if m.floor > band for s in m.slots
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
        stats={"targets": len(spans), "misses": misses, "miss_rate": miss_rate},
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

    "~0" is `floor <= surrogate q95` — never an eyeball reading. The two branches are
    different findings, not degrees of one: `~0` validates the pipeline and advances no
    protocol claim; `structured` yields modes reported verbatim with no interpretation
    beyond listing them.
    """
    floor = result.mean_floor(beta)
    band = result.surrogate.get("q95", 0.0)
    near_zero = floor <= band

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
        if m.floor > band
    ]

    return RuleResult(
        rule="R3",
        verdict=Verdict.FLOOR_NEAR_ZERO if near_zero else Verdict.FLOOR_STRUCTURED,
        passed=True,  # R3 does not fail; it reports which branch obtains.
        detail=(
            f"cold floor {floor:.6g} <= surrogate q{int(SURROGATE_QUANTILE * 100)} "
            f"{band:.6g}: all contest is path-debt; the ledger is self-consistent. "
            "v0 validation of the pipeline; protocol claims NOT advanced."
            if near_zero
            else f"cold floor {floor:.6g} > surrogate q{int(SURROGATE_QUANTILE * 100)} "
            f"{band:.6g}: structured. {len(modes)} mode(s) reported verbatim; "
            "no interpretation beyond listing."
        ),
        stats={"floor": floor, "surrogate_q95": band, "modes": modes},
    )


# --- R4 ---------------------------------------------------------------------------


def prior_insensitivity(
    documents: Sequence[Document],
    extractors: Sequence[Extractor],
    beta: float,
    seed_hash: str,
    shadow_cfg: Mapping[str, object],
    baseline: MeterResult,
    trials: int = PRIOR_DROPOUT_TRIALS,
    rate: float = PRIOR_DROPOUT_RATE,
) -> RuleResult:
    """R4: drop 10% of Q edges at random, 5 trials; cold floor moves < surrogate noise.

    Larger movement means the verdicts are artifacts of the fiber-construction dictionary
    rather than of the ledger, and the rule's consequence is not a warning: the seed
    design is rejected and the run is CLOSED.
    """
    base_floor = baseline.mean_floor()
    band = baseline.surrogate.get("q95", 0.0)
    movements: list[float] = []

    for trial in range(trials):
        rng = DRNG("R4", seed_hash, str(trial))
        ledger = build_ledger(
            documents,
            extractors,
            edge_filter=lambda edges, _rng=rng: drop_edges(edges, rate, _rng),
        )
        result, _, _ = run_meter(ledger, beta, seed_hash, shadow_cfg)
        movements.append(abs(result.mean_floor() - base_floor))

    worst = max(movements) if movements else 0.0
    ok = worst < band or (worst == 0.0 and base_floor == 0.0)

    return RuleResult(
        rule="R4",
        verdict=None if ok else Verdict.CLOSED_REJECTED,
        passed=ok,
        detail=(
            f"worst floor movement {worst:.6g} over {trials} dropout trials, "
            f"below surrogate noise {band:.6g}"
            if ok
            else f"floor moved by {worst:.6g} > surrogate noise {band:.6g} under "
            f"{int(rate * 100)}% Q-edge dropout: verdicts are dictionary artifacts. "
            "Seed design rejected, CLOSED."
        ),
        stats={
            "baseline_floor": base_floor,
            "movements": movements,
            "worst": worst,
            "band": band,
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
