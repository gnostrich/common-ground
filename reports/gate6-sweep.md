# Gate 6 conformance sweep

> Every statistical verdict is decided against a null constructed under the no-effect
> hypothesis (permutation / phase-randomization / independent surrogate), never against a
> resample of the observation. — `seed/GATES.md` sentence 6

Sentence 6 was added because two null cells and one PREREG rule turned out to compare an
observation against a resample of itself. Two of the three were found by a positive
control; the third (R4) was found by hand, by wondering whether the pattern recurred. That
is not a method. This sweep is the method.

## The sites

`static_checks.check_gate6_classification` walks every function in `engine/` and finds
11 that build or read a statistical band across 22 files.
Each must be classified below or the check fails. It classifies rather than forbids: a
non-conforming band may exist as a **diagnostic**; what may not exist is an unexamined one.

`role` is what the number does — `decides` means a verdict turns on it, `diagnostic` means
it is reported and nothing more, `produces` means it is computed and handed on.

| Site | Role | Reference distribution | Gate 6 |
|---|---|---|---|
| `engine/meter.py:surrogate_floor_distribution` | diagnostic | bootstrap resample of the observed loop floors | **NON-CONFORMING** |
| `engine/meter.py:within_noise` | unused | caller-supplied surrogate | n/a |
| `engine/pipeline.py:_q95` | diagnostic | bootstrap, via surrogate_floor_distribution | **NON-CONFORMING** |
| `engine/pipeline.py:run_meter` | produces | n/a — computes both surrogates and stores them | n/a |
| `engine/audit.py:floor_verdict` | decides | second_fdt_surrogate_floor | **conforming** |
| `engine/audit.py:ground_truth_rediscovery` | decides | per-loop second-FDT label permutation, pooled leave-one-out | **conforming** |
| `engine/audit.py:prior_insensitivity` | decides | dropout movement on a degree- and weight-marginal-preserving rewire | **conforming** |
| `engine/meter.py:pooled_loop_nulls` | decides | leave-one-out pool of the other loops' permutation draws | **conforming** |
| `engine/meter.py:second_fdt_surrogate_floor` | decides | warm/cold label permutation, loop by loop | **conforming** |
| `engine/nulls.py:cell_iii_empty_corpus` | decides | exact zero | **conforming** |
| `engine/nulls.py:cell_iv_single_doc` | decides | consensus ledger floor (every block forced to its modal b-value) | **conforming** |
| `engine/nulls.py:cell_ix_binding_sanity` | decides | fixed 5% failure rate, pre-registered in the LEXICON SPEC | **conforming** |
| `engine/nulls.py:cell_v_duplicate_source` | decides | DUPLICATE_RESIDUE_TOLERANCE (1e-12), a numerical tolerance | **conforming** |
| `engine/meter.py:loop_permutation_null` | produces | per-slot warm/cold assignment on one loop, holonomy recomputed | **conforming** |
| `engine/meter.py:studentized_loop_thresholds` | rejected | leave-one-out pool of other loops' permutation draws, scaled by each loop's own null MAD | **conforming** |
| `engine/mint_tape.py:read_tape` | diagnostic | 3x second_fdt_surrogate_floor | **conforming** |

## Findings

### The sweep found R2, which no one had noticed — now amended

`ground_truth_rediscovery` counted a gap as *flagged* when its loop's floor exceeded
`result.surrogate["q95"]` — the bootstrap. So "flagged" meant "above average for this run",
not "above what no path dependence would produce".

The miscalibration ran **opposite to R4's**, and the difference matters. R4's band grew
with the floor, so the rule relaxed exactly where dictionary sensitivity mattered most.
R2's band grew with the floor too, but it sat on the *other side* of the comparison: a
larger floor raised the bar, fewer gaps cleared it, and the miss rate went up. R2 got
stricter as the run got noisier.

PREREG-AMENDMENT-3 replaced it with a label-permutation null. Its rationale (c) is recorded
as **calibration-restoring** rather than strictness-increasing — unlike -1 and -2, this
correction runs in both directions and some runs that would have failed R2 will now pass.

**The amendment deviates from its authorized wording, and the deviation was found by the
mandated positive control.** The authorization specified each loop's *own* permutation
null. That is unsatisfiable: a `k`-slot loop has `2**k` warm/cold assignments, the all-cold
assignment *is* the observed floor, and q95 of four or eight points is the maximum — so no
loop can exceed its own null at any floor. Measured on a synthetic contested corpus, 0 of 4
loops could flag, which would have given a 100% miss rate on every run: the same defect, in
the same punitive direction. The shipped rule pools the *other* loops' permuted floors
leave-one-out. **This needs operator confirmation.**

Its limitation is stated rather than buried: pooling assumes loops are exchangeable with
one another, and they are not exactly — one loud loop raises every other loop's threshold.

### The bootstrap survives as a diagnostic, deliberately

`surrogate_floor_distribution` and `pipeline._q95` are non-conforming and still computed.
Both amendments kept the superseded band reported so that a reader can see what the old
rule would have said — R3 prints the disagreement in its detail line, R4 carries it as
`legacy_self_scaled_band`. Neither decides anything. Deleting them would make the
amendments unauditable.

### One site is conforming for a weaker reason than the others

`cell_ix_binding_sanity` compares against a fixed 5% failure rate from the LEXICON SPEC.
That satisfies sentence 6 by not being data-derived — a fixed threshold cannot move with
the observation. But it is not a null either: nothing calibrates 5%, so the cell bounds a
bug rate rather than testing a hypothesis. It is conforming and weak, and those are
different properties.

### One dead helper

`meter.within_noise` has no call site. It takes a caller-supplied surrogate, so its
conformance would depend entirely on what a future caller passed — the ambiguity sentence
6 exists to remove. It is listed so that a caller has to classify itself.

## Why this is a check and not a document

A sweep written down goes stale the first time someone adds a band. `check_gate6_classification`
fails on any unclassified band-building or band-reading function in `engine/`, so the next
one cannot be added silently — it has to be named, its reference distribution written down,
and its role declared. That is the difference between having found R4 and being able to
find the next one.

CI runs it; `tests/test_controls.py` covers it from both directions.
