"""The null battery (KICKOFF section 4). Gate 5 turns on this passing.

Five cells:

  i.   normalizer idempotence, fuzzed, n=500 per chart
  ii.  the pre-registered paraphrase suite: known-same collide, known-distinct separate
  iii. empty-corpus floor == 0: the seed alone generates no contest
  iv.  single-doc null: one document, k=3, cold floor ~ 0 within surrogate noise
  v.   duplicate-source null: one corpus ingested twice under distinct provenance gives
       zero cold residue and zero rank growth on the tape

Cells i and ii are always runnable — they test the seed against itself. Cells iii-v need
inputs that D5 and D3 have not yet supplied, and they report **BLOCKED** rather than PASS
when those are missing. A blocked battery is not a passing battery, so gate 5 keeps the
floor closed. That is the intended behaviour: a run that has not been in a position to
fail its own nulls has not passed them.

Cell (iv) failing is not a bug report. KICKOFF section 4 is explicit: extraction too noisy
at this scale, run void, and **VOID IS A PUBLISHABLE VERDICT**.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .constants import (
    CHARTS,
    NULL_FUZZ_SAMPLES,
    SURROGATE_QUANTILE,
    paraphrase_suite,
    shadow as load_shadow,
)
from .extract import Extractor
from .hashing import DRNG, quantile
from .mint_tape import read_tape, residual_stream
from .normalize import address, classify, nu
from .pipeline import build_ledger, run_meter
from .types import (
    Chart,
    Clamp,
    Document,
    NullBatteryReport,
    NullCell,
    NullStatus,
)

# Fuzz alphabet: deliberately nasty. Control characters, the tag sentinel, markdown,
# LaTeX, unicode punctuation, Lean syntax, and whitespace of several kinds — every class
# of input the normalizer claims to be total and idempotent on.
_FUZZ_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    " \t\n\r"
    "\x00\x01\x02\x07\x0b\x1f\x7f\x85\x9f"
    "*_`~#>-+."
    "$\\()[]{}"
    "'\"‘’“”–—…  "
    ":=∘→∀∃≤≥"
    "/-"
    "theorem lemma def axiom instance structure "
    "if then whenever must ought defined as means that "
)


def _fuzz(rng: DRNG, max_len: int = 120) -> str:
    n = rng.randrange(max_len) + 1
    return "".join(_FUZZ_ALPHABET[rng.randrange(len(_FUZZ_ALPHABET))] for _ in range(n))


# --- cell i -----------------------------------------------------------------------


def cell_i_idempotence(seed_hash: str, samples: int = NULL_FUZZ_SAMPLES) -> NullCell:
    rng = DRNG("null-i", seed_hash)
    failures: list[dict[str, str]] = []
    checked = 0

    for chart in CHARTS:
        for _ in range(samples):
            s = _fuzz(rng)
            once = nu(chart, s)  # type: ignore[arg-type]
            twice = nu(chart, once)  # type: ignore[arg-type]
            checked += 1
            if once != twice:
                if len(failures) < 5:
                    failures.append({"chart": chart, "input": repr(s), "once": repr(once), "twice": repr(twice)})

    # Fixed adversarial cases alongside the fuzz: a bare tag, empty input, and a surface
    # that already looks normalized.
    for chart in CHARTS:
        for s in ("", " ", "\x01en\x01", "\x01lean\x01", "\x01en\x01already normalized"):
            once = nu(chart, s)  # type: ignore[arg-type]
            checked += 1
            if once != nu(chart, once):  # type: ignore[arg-type]
                failures.append({"chart": chart, "input": repr(s), "once": repr(once), "twice": repr(nu(chart, once))})  # type: ignore[arg-type]

    return NullCell(
        cell="i.normalizer-idempotence",
        status=NullStatus.PASS if not failures else NullStatus.FAIL,
        detail=(
            f"nu(nu(x)) == nu(x) on {checked} samples across {len(CHARTS)} charts"
            if not failures
            else f"{len(failures)} idempotence failure(s); first: {failures[0]}"
        ),
        stats={"checked": checked, "failures": len(failures), "examples": failures},
    )


# --- cell ii ----------------------------------------------------------------------


def cell_ii_paraphrase() -> NullCell:
    suite = paraphrase_suite()
    same_fail: list[str] = []
    distinct_fail: list[str] = []

    for pair in suite["known_same"]:
        chart: Chart = pair["chart"]
        a, _ = address(chart, pair["a"], classify(chart, pair["a"]))
        b, _ = address(chart, pair["b"], classify(chart, pair["b"]))
        if a != b:
            same_fail.append(pair["id"])

    for pair in suite["known_distinct"]:
        if pair["chart"] == "cross":
            ca, cb = pair["a_chart"], pair["b_chart"]
        else:
            ca = cb = pair["chart"]
        a, _ = address(ca, pair["a"], classify(ca, pair["a"]))
        b, _ = address(cb, pair["b"], classify(cb, pair["b"]))
        if a == b:
            distinct_fail.append(pair["id"])

    ok = not same_fail and not distinct_fail
    return NullCell(
        cell="ii.paraphrase-suite",
        status=NullStatus.PASS if ok else NullStatus.FAIL,
        detail=(
            f"{len(suite['known_same'])} known-same pairs collided, "
            f"{len(suite['known_distinct'])} known-distinct pairs separated"
            if ok
            else f"known_same failures={same_fail}; known_distinct failures={distinct_fail}"
        ),
        stats={
            "known_same": len(suite["known_same"]),
            "known_distinct": len(suite["known_distinct"]),
            "same_failures": same_fail,
            "distinct_failures": distinct_fail,
        },
    )


# --- cell iii ---------------------------------------------------------------------


def cell_iii_empty_corpus(
    seed_hash: str,
    preminted: Sequence[Document],
    extractors: Sequence[Extractor],
    beta: float,
) -> NullCell:
    """Seed alone must generate zero contest.

    Runs on the pre-minted entries only, with no corpus. If the priors were fighting each
    other, the floor would be non-zero before a single document was read, and every later
    floor reading would be measuring the seed rather than the ledger.
    """
    if not preminted:
        return NullCell(
            cell="iii.empty-corpus-floor",
            status=NullStatus.BLOCKED,
            detail=(
                "D5 is unresolved: seed/LEXICON/preminted/ holds no pre-minted entries, "
                "so the seed has no slot inventory to check for self-contest."
            ),
            stats={"preminted_documents": 0},
        )

    ledger = build_ledger(preminted, extractors)
    result, _, _ = run_meter(ledger, beta, seed_hash, load_shadow())
    floor = result.mean_floor()
    ok = floor == 0.0

    return NullCell(
        cell="iii.empty-corpus-floor",
        status=NullStatus.PASS if ok else NullStatus.FAIL,
        detail=(
            "seed alone generates zero contest"
            if ok
            else f"seed alone generates a floor of {floor:.6g}; the priors are fighting each other"
        ),
        stats={"floor": floor, **ledger.summary()},
    )


# --- cell iv ----------------------------------------------------------------------


def cell_iv_single_doc(
    seed_hash: str,
    document: Document | None,
    extractors: Sequence[Extractor],
    beta: float,
) -> NullCell:
    """One document, k=3 extraction, cold floor ~ 0 within surrogate noise.

    A single document cannot disagree with anything but itself, so any floor it produces
    is extraction variance. Failing means extraction is too noisy at this scale — and per
    KICKOFF section 4 that voids the run, which is a publishable verdict, not a defect.
    """
    if document is None:
        return NullCell(
            cell="iv.single-doc",
            status=NullStatus.BLOCKED,
            detail="D3 is unresolved: no held-out document available per source.",
            stats={},
        )

    ledger = build_ledger([document], extractors)
    if not ledger.loops:
        return NullCell(
            cell="iv.single-doc",
            status=NullStatus.PASS,
            detail="single document produced no loops; there is no path for a floor to arise",
            stats=ledger.summary(),
        )

    result, _, _ = run_meter(ledger, beta, seed_hash, load_shadow())
    floor = result.mean_floor()
    band = result.surrogate.get("q95", 0.0)
    ok = floor <= band or floor == 0.0

    return NullCell(
        cell="iv.single-doc",
        status=NullStatus.PASS if ok else NullStatus.FAIL,
        detail=(
            f"cold floor {floor:.6g} within surrogate noise (q{int(SURROGATE_QUANTILE * 100)}={band:.6g})"
            if ok
            else (
                f"cold floor {floor:.6g} exceeds surrogate noise (q{int(SURROGATE_QUANTILE * 100)}={band:.6g}): "
                "extraction is too noisy at this scale. RUN VOID — a publishable verdict."
            )
        ),
        stats={"floor": floor, "surrogate_q95": band, **ledger.summary()},
    )


# --- cell v -----------------------------------------------------------------------


def cell_v_duplicate_source(
    seed_hash: str,
    corpus: Sequence[Document],
    extractors: Sequence[Extractor],
    beta: float,
) -> NullCell:
    """One corpus ingested twice under distinct provenance: zero residue, zero rank growth.

    The duplicate carries different doc ids and a different source label but identical
    text. `energy.evidential_identity` keys on the content hash rather than the label, so
    the second ingestion contributes no evidence. If the floor moved or the tape gained
    rank, the ledger would be treating a relabelled copy as corroboration.
    """
    if not corpus:
        return NullCell(
            cell="v.duplicate-source",
            status=NullStatus.BLOCKED,
            detail="D3 is unresolved: no corpus to duplicate.",
            stats={},
        )

    doubled = list(corpus) + [
        Document(
            doc_id=f"dup::{d.doc_id}",
            chart=d.chart,
            text=d.text,
            source=f"{d.source}::duplicate",
            meta=dict(d.meta),
        )
        for d in corpus
    ]

    shadow_cfg = load_shadow()
    once = build_ledger(list(corpus), extractors)
    twice = build_ledger(doubled, extractors)

    r1, _, cold1 = run_meter(once, beta, seed_hash, shadow_cfg)
    r2, _, cold2 = run_meter(twice, beta, seed_hash, shadow_cfg)

    residue = abs(r2.mean_floor() - r1.mean_floor())
    band = max(r1.surrogate.get("q95", 0.0), r2.surrogate.get("q95", 0.0))

    growth = 0
    for block_id, settled in cold1.items():
        other = cold2.get(block_id)
        if other is None:
            growth += 1
            continue
        fdt = r1.surrogate.get("second_fdt_floor", 0.0)
        before = read_tape(residual_stream(settled), fdt)
        after = read_tape(residual_stream(other), fdt)
        growth += max(0, after.effective_rank - before.effective_rank)

    ok = residue <= band and growth == 0
    return NullCell(
        cell="v.duplicate-source",
        status=NullStatus.PASS if ok else NullStatus.FAIL,
        detail=(
            f"duplicate ingestion left the floor unmoved (residue {residue:.3g}) "
            "and added no rank to the tape"
            if ok
            else f"duplicate ingestion moved the floor by {residue:.6g} (band {band:.6g}) "
            f"and added {growth} to the tape rank"
        ),
        stats={
            "residue": residue,
            "band": band,
            "rank_growth": growth,
            "blocks_once": len(cold1),
            "blocks_twice": len(cold2),
        },
    )


# --- battery ----------------------------------------------------------------------


def run_battery(
    seed_hash: str,
    extractors: Sequence[Extractor],
    beta: float,
    preminted: Sequence[Document] = (),
    held_out: Document | None = None,
    corpus: Sequence[Document] = (),
    samples: int = NULL_FUZZ_SAMPLES,
) -> NullBatteryReport:
    """Run all five cells. Cells iii-v report BLOCKED when their inputs are unresolved."""
    return NullBatteryReport(
        seed_hash=seed_hash,
        cells=[
            cell_i_idempotence(seed_hash, samples),
            cell_ii_paraphrase(),
            cell_iii_empty_corpus(seed_hash, preminted, extractors, beta),
            cell_iv_single_doc(seed_hash, held_out, extractors, beta),
            cell_v_duplicate_source(seed_hash, corpus, extractors, beta),
        ],
    )
