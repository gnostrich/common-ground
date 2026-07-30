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
    shadow_probes,
)
from .extract import Extractor
from .hashing import DRNG, quantile
from .lexicon import Registry, infer_frames, select_sense
from .lexicon import tokens as lex_tokens
from .mint_tape import read_tape, residual_stream
from .normalize import address, classify, nu
from .pipeline import build_ledger, run_meter
from .static_checks import check_no_display_on_f_path
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


# --- cell vi ----------------------------------------------------------------------


def cell_vi_hub_coverage(registry: Registry | None) -> NullCell:
    """Every sense has an English face. The rendered count is a quality metric.

    The hub invariant's first half (LEXICON SPEC §0a): no entry may exist only in a
    formal chart. Rendered faces are *allowed* — they are how a bare Mathlib name gets a
    hub position — so the count is reported rather than failed on. Coverage asymmetry in
    the other direction (English-only senses) is expected and is not counted against.
    """
    if registry is None or not registry.senses:
        return NullCell(
            cell="vi.hub-coverage",
            status=NullStatus.BLOCKED,
            detail="no lexicon registry: D8 import pins unresolved and no senses were built.",
            stats={"senses": 0},
        )

    senses = registry.senses
    faceless = [s.core.sense_id for s in senses if not s.display.english_face.strip()]
    rendered = registry.rendered_face_count()
    english_only = sum(1 for s in senses if not s.core.formal_faces)

    return NullCell(
        cell="vi.hub-coverage",
        status=NullStatus.PASS if not faceless else NullStatus.FAIL,
        detail=(
            f"all {len(senses)} senses carry an English face "
            f"({rendered} rendered, {len(senses) - rendered} authored; "
            f"{english_only} English-only, which is expected)"
            if not faceless
            else f"{len(faceless)} sense(s) exist only in a formal chart: {faceless[:5]}"
        ),
        stats={
            "senses": len(senses),
            "faceless": faceless,
            "rendered_faces": rendered,
            "authored_faces": len(senses) - rendered,
            "english_only_senses": english_only,
            "by_source": registry.summary(),
        },
    )


# --- cell vii ---------------------------------------------------------------------


def cell_vii_shadow(registry: Registry | None) -> NullCell:
    """Technical terms resolve technically in math contexts, generally in general ones.

    Frames are **inferred from the probe's prose** by the declared cue table, not read
    off the probe. That makes this a test of the cue table and the selection function
    rather than a restatement of the fixture.

    A general-English sense winning a math-typed context is shadowing, and the addendum's
    consequence is not a warning: seed rejected. The reverse — a technical sense winning a
    plainly general context — is over-reach and is failed too, since a lexicon that reads
    "she wore a silver ring" as ring theory is just as broken.
    """
    if registry is None or not registry.senses:
        return NullCell(
            cell="vii.shadow-check",
            status=NullStatus.BLOCKED,
            detail="no lexicon registry to probe.",
            stats={},
        )

    probes = shadow_probes()
    shadowing: list[dict[str, object]] = []
    overreach: list[dict[str, object]] = []
    undecided: list[dict[str, object]] = []
    frame_misses: list[str] = []
    checked = 0

    by_id = {c.sense_id: c for c in registry.cores()}

    for probe in probes.get("probes", []):
        lemma = probe["lemma"]
        candidates = registry.candidates_for(lemma)
        if not candidates:
            continue
        checked += 1

        inferred = infer_frames(probe["context"])
        if not (set(probe.get("frames", [])) & set(inferred)):
            frame_misses.append(f"{probe['lemma']}/{probe['kind']}: inferred {sorted(inferred)}")

        selection = select_sense(
            lemma=lemma,
            candidates=candidates,
            context_frames=inferred,
            context_tokens=lex_tokens(probe["context"]),
        )

        expected = probe["expect"]
        row = {
            "lemma": lemma, "kind": probe["kind"], "expect": expected,
            "chosen": selection.chosen, "inferred_frames": sorted(inferred),
        }

        if not selection.decided:
            undecided.append({**row, "fiber": list(selection.fiber)})
            continue
        if selection.chosen == expected:
            continue

        chosen_core = by_id.get(selection.chosen)
        chosen_is_general = bool(chosen_core and chosen_core.source == "general")
        if probe["kind"] == "technical" and chosen_is_general:
            shadowing.append(row)
        elif probe["kind"] == "general" and not chosen_is_general:
            overreach.append(row)
        else:
            undecided.append({**row, "note": "wrong sense, same register"})

    failed = bool(shadowing or overreach)
    return NullCell(
        cell="vii.shadow-check",
        status=NullStatus.FAIL if failed else NullStatus.PASS,
        detail=(
            f"{checked} probes: technical contexts resolved technically, general "
            f"contexts resolved generally"
            + (f"; {len(undecided)} abstained or picked a sibling sense" if undecided else "")
            if not failed
            else (
                f"SHADOWING on {len(shadowing)} probe(s): a general-English sense won a "
                "math-typed context. Per the addendum this rejects the seed. "
                if shadowing else ""
            ) + (f"Over-reach on {len(overreach)} probe(s)." if overreach else "")
        ),
        stats={
            "checked": checked,
            "shadowing": shadowing,
            "overreach": overreach,
            "undecided": undecided,
            "frame_inference_misses": frame_misses,
        },
    )


# --- cell viii --------------------------------------------------------------------


def cell_viii_no_clamp_grep() -> NullCell:
    """No gloss or English-face string is reachable from any F-constraint term.

    Gate 2 at the lexicon layer. Runs on the AST rather than on text, so a mention in a
    comment is not a false positive. Always runnable — it reads the engine's own source,
    not the corpus — so it is green or red, never blocked.
    """
    result = check_no_display_on_f_path()
    return NullCell(
        cell="viii.no-clamp-grep",
        status=NullStatus.PASS if result.ok else NullStatus.FAIL,
        detail=(
            f"no display attribute reachable from {result.checked_files} F-path module(s) "
            f"or {result.checked_functions} F-feeding function(s); SenseCore fields are "
            f"{list(result.core_fields)}"
            if result.ok
            else f"{len(result.violations)} violation(s): " + "; ".join(str(v) for v in result.violations[:5])
        ),
        stats={
            "checked_files": result.checked_files,
            "checked_functions": result.checked_functions,
            "core_fields": list(result.core_fields),
            "violations": [str(v) for v in result.violations],
        },
    )


# --- cell ix ----------------------------------------------------------------------


def cell_ix_binding_sanity(registry: Registry | None, seed_hash: str, sample: int = 50) -> NullCell:
    """english_face -> nu -> slot -> binding returns the originating formal face.

    Sampled over Mathlib-derived senses, since those are the ones the R-map generated a
    face for and therefore the ones where the round trip can actually break. Over 5%
    failures is an importer bug, per the addendum.
    """
    if registry is None:
        return NullCell(
            cell="ix.binding-sanity",
            status=NullStatus.BLOCKED,
            detail="no lexicon registry.",
            stats={},
        )

    pool = [s for s in registry.senses if s.core.source == "mathlib" and s.core.formal_faces]
    if not pool:
        return NullCell(
            cell="ix.binding-sanity",
            status=NullStatus.BLOCKED,
            detail=(
                "D8 unresolved: no Mathlib-derived senses, so there is no R-map round "
                "trip to check."
            ),
            stats={"pool": 0},
        )

    rng = DRNG("null-ix", seed_hash)
    picked = rng.shuffled(pool)[:sample]
    bindings = registry.bindings()

    failures: list[dict[str, str]] = []
    for sense in picked:
        origin = sense.core.formal_faces[0].surface
        slot, _ = address("english", sense.display.english_face, "define")
        bound = {f.surface for f in bindings.get(slot, ())}
        if origin not in bound:
            failures.append({
                "sense_id": sense.core.sense_id,
                "english_face": sense.display.english_face,
                "origin": origin,
                "bound": ", ".join(sorted(bound)[:3]) or "(nothing)",
            })

    rate = len(failures) / len(picked)
    ok = rate <= 0.05
    return NullCell(
        cell="ix.binding-sanity",
        status=NullStatus.PASS if ok else NullStatus.FAIL,
        detail=(
            f"{len(picked)} sampled Mathlib senses round-tripped "
            f"english_face -> nu -> slot -> binding ({rate:.1%} failures)"
            if ok
            else f"{rate:.1%} round-trip failures over {len(picked)} samples, above the 5% "
            "bar: importer bug"
        ),
        stats={"sampled": len(picked), "pool": len(pool), "failures": failures[:10], "rate": rate},
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
    registry: Registry | None = None,
) -> NullBatteryReport:
    """Run all nine cells.

    Cells i, ii and viii are always runnable — they test the seed and the engine's own
    source against themselves. The rest report BLOCKED when D3, D5 or D8 has not supplied
    what they need, and BLOCKED is not PASS, so gate 5 holds.
    """
    return NullBatteryReport(
        seed_hash=seed_hash,
        cells=[
            cell_i_idempotence(seed_hash, samples),
            cell_ii_paraphrase(),
            cell_iii_empty_corpus(seed_hash, preminted, extractors, beta),
            cell_iv_single_doc(seed_hash, held_out, extractors, beta),
            cell_v_duplicate_source(seed_hash, corpus, extractors, beta),
            cell_vi_hub_coverage(registry),
            cell_vii_shadow(registry),
            cell_viii_no_clamp_grep(),
            cell_ix_binding_sanity(registry, seed_hash),
        ],
    )
