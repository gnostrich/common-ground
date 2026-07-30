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
9 that build or read a statistical band across 21 files.
Each must be classified below or the check fails. It classifies rather than forbids: a
non-conforming band may exist as a **diagnostic**; what may not exist is an unexamined one.

`role` is what the number does — `decides` means a verdict turns on it, `diagnostic` means
it is reported and nothing more, `produces` means it is computed and handed on.

| Site | Role | Reference distribution | Gate 6 |
|---|---|---|---|
| `engine/audit.py:ground_truth_rediscovery` | decides | bootstrap q95 of the observed floors | **NON-CONFORMING** |
| `engine/meter.py:surrogate_floor_distribution` | diagnostic | bootstrap resample of the observed loop floors | **NON-CONFORMING** |
| `engine/meter.py:within_noise` | unused | caller-supplied surrogate | n/a |
| `engine/pipeline.py:_q95` | diagnostic | bootstrap, via surrogate_floor_distribution | **NON-CONFORMING** |
| `engine/pipeline.py:run_meter` | produces | n/a — computes both surrogates and stores them | n/a |
| `engine/audit.py:floor_verdict` | decides | second_fdt_surrogate_floor | **conforming** |
| `engine/audit.py:prior_insensitivity` | decides | dropout movement on a degree- and weight-marginal-preserving rewire | **conforming** |
| `engine/meter.py:second_fdt_surrogate_floor` | decides | warm/cold label permutation, loop by loop | **conforming** |
| `engine/nulls.py:cell_iii_empty_corpus` | decides | exact zero | **conforming** |
| `engine/nulls.py:cell_iv_single_doc` | decides | consensus ledger floor (every block forced to its modal b-value) | **conforming** |
| `engine/nulls.py:cell_ix_binding_sanity` | decides | fixed 5% failure rate, pre-registered in the LEXICON SPEC | **conforming** |
| `engine/nulls.py:cell_v_duplicate_source` | decides | DUPLICATE_RESIDUE_TOLERANCE (1e-12), a numerical tolerance | **conforming** |
| `engine/mint_tape.py:read_tape` | diagnostic | 3x second_fdt_surrogate_floor | **conforming** |

## Findings

### The sweep found R2, which no one had noticed

`ground_truth_rediscovery` counts a gap as *flagged* when its loop's floor exceeds
`result.surrogate["q95"]` — the bootstrap. So "flagged" means "above average for this
run", not "above what no path dependence would produce".

The miscalibration runs **opposite to R4's**, and the difference matters. R4's band grew
with the floor, so the rule relaxed exactly where dictionary sensitivity mattered most.
R2's band grows with the floor too, but it sits on the *other side* of the comparison: a
larger floor raises the bar, fewer gaps clear it, and the miss rate goes up. R2 gets
stricter as the run gets noisier — and on a uniformly-zero run no loop clears the band at
all, so the miss rate is 100% and R2 reports the meter as insensitive when nothing was
wrong with it.

R2 was outside PREREG-AMENDMENT-2's scope (R4 only), so it is **flagged and unchanged**.
It reports `decided_by` and `gate6_conforming: false` in its stats, and it is BLOCKED on
D5 in any case — `STATEMENTS.md` is absent, so no data has passed through it either. The
conforming reference would be the per-loop second-FDT surrogate, the same null R3 uses.
Amending it needs its own authorization, and the window closes at the first P3 phase-run.

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
