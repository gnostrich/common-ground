# P1 — null battery

Provisional seed hash `d7a069368709` (`seed/SEED.lock` is not written; D3, D4's spend cap,
D5, D6 are unresolved and D8 is partial). Registry entry committed before the run, per
KICKOFF §7.2.

This is a **cold re-anneal**, the fourth. Every PREREG amendment and the one repair attempt
touched `seed/`, so each was plastic under gate 4 and each is logged in
`registry/REGISTRY.jsonl` with before/after hashes and an identity slot map — no lexicon,
prompt, or normalizer surface changed in any of them, so no address moved:

| Morphism | Cause | Seed hash |
|---|---|---|
| — | P1 baseline | `5043231e3f58` |
| AMENDMENT-1 (R3) | `GATES.md` sentence 6 added | `d8f330fa4164` |
| AMENDMENT-2 (R4) | gate-6 enforcement row; `rewire_passes` constant | `0e7cb5568c17` |
| AMENDMENT-3 (R2) | D7 re-approval recorded in `DECISIONS.*` | `53f709ce82bc` |
| -3.repair-1 (rejected) | `studentize_min_scale`; rejection recorded in `DECISIONS.md` | `d7a069368709` |

The battery was re-run from scratch on each new hash rather than carried across. No warm
state was discarded because none existed.

## Lexicon imports

| Source | Status | Detail |
|---|---|---|
| mathlib | **BLOCKED** | D8 policy is "latest stable at fetch"; no dump has landed. A live pull is forbidden during a run (KICKOFF §7.5) and could not hash cleanly anyway. |
| convention | **imported** | 184 senses, 22 bridges; 114 unresolved formal-face candidates dropped rather than invented |
| nlab | **BLOCKED** | D8 policy is "current at fetch"; no scrape has landed |
| preminted | **BLOCKED** | D5: `seed/LEXICON/preminted/` holds no files |
| wordnet | **BLOCKED** | D8 version is fixed at 3.1; no dump has landed |

The 114 dropped candidates are correct behaviour, not loss: a convention-table
`formal_faces` entry is a *candidate* Mathlib binding, and with no dump imported none
resolves. The importer drops and counts them rather than inventing a binding no dump backs.

## Matrix

Each cell carries a **positive control** — an input engineered to break the property the
cell tests. `ctl` is the control's verdict, and it is a separate column on purpose: a cell
reporting PASS with a dead control has not passed anything, because nobody has shown it can
fail.

| Cell | Status | ctl | Reading |
|---|---|---|---|
| i. normalizer idempotence | **PASS** | live | `nu(nu(x)) == nu(x)` on 1010 fuzzed samples across both charts, plus fixed adversarial cases |
| ii. paraphrase suite | **PASS** | live | 10 pre-registered known-same pairs collided; 10 known-distinct separated, including the cross-chart pair and the Lean case-sensitivity pair |
| iii. empty-corpus floor | **BLOCKED** | live | D5: no pre-minted entries, so the seed has no slot inventory to check for self-contest |
| iv. single-doc null | **BLOCKED** | live | D3: no held-out document per source |
| v. duplicate-source null | **BLOCKED** | live | D3: no corpus to duplicate |
| vi. hub-coverage | **PASS** | live | all 184 senses carry an English face (0 rendered, 184 authored; 184 English-only, expected) |
| vii. shadow check | **PASS** | live | 38 probes: technical contexts resolved technically, general contexts resolved generally, zero abstentions |
| viii. no-clamp grep | **PASS** | live | no display attribute reachable from 8 F-path modules or 2 F-feeding functions |
| ix. binding sanity | **BLOCKED** | live | D8: no Mathlib dump has landed, so there is no R-map round trip to check |

**Battery status: BLOCKED. Dead controls: none.**

## Verdict sentence

`BLOCKED` is not green, so PREREG R1 applies and the run is **VOID**. The battery
distinguishes this from `FAIL`: cells iii–v and ix were never in a position to be tested,
which is a different finding from having been tested and failed. Publishing them as the
same finding would be a false report.

Gate 5 therefore holds. `meter.read_floor()` refuses any floor read at this seed hash and
will keep refusing until the battery returns `PASS` on the *same* hash.

## Defects found and fixed

The battery earned its keep three times: the fuzzer, the shadow probes, and — after the
positive-control rule was adopted — the controls themselves.

**Cell (i) — addressing.** The fuzzer found a genuine idempotence break in the English
normalizer on `'*#\nr\t\x00\x01m → $_\n='`: markdown line-prefix stripping ran *before*
whitespace collapse, the inline pass removed the leading `*`, and that promoted `#` to
line-initial — so it was stripped on the second application of `nu` but not the first.
A non-idempotent `nu` means a slot's identity depends on how many times it happened to be
normalized. Fixed by iterating the leading-prefix strip to a fixed point after the collapse;
re-verified at 4010 samples.

**Cell (vii) — the lexicon layer.** Three defects, each in the mechanism the cell exists to
check:

1. The importer hardcoded `source="convention"`, ignoring each sense's declared tier, so no
   sense was ever classified as general English and shadowing detection could not fire at all.
2. `candidates_for` scored a sense that merely *mentions* the lemma ("degree of a field
   extension") equally against one whose lemma *is* the query ("field").
3. Cue matching was substring-based: `"norm"` fired the `analysis` frame inside the word
   *"normal"*, and bare `"field"` / `"ring"` / `"measure"` were cues for their own technical
   frames — the ambiguous word voting for its own disambiguation.

Two more surfaced during the fix. Word boundaries strict enough to keep `"norm"` out of
`"normal"` also kept `"closed set"` out of `"closed sets"`, so the matcher now allows one
trailing `s`. And `"identity element"` had to leave the `unital` cue list: it appears in the
rng probe too — "*not required to have* a multiplicative identity element" — and a
phrase-cue table cannot see negation.

**Cells (iv) and (v) — two vacuous tests, found only by their own controls.** Both had been
reporting PASS since they were written, and neither could have reported anything else.

- **(iv)** compared the observed floor against a bootstrap of the observed floors. That band
  is centred on the data, so `floor <= q95` held at 0.4 exactly as readily as at 0.0 — the
  cell was reporting on the resampler, not on the document. It now settles a **consensus
  ledger** (every block forced to its modal b-value, so it *cannot* disagree with itself)
  and reads the real floor against that, within `single_doc_tolerance`. The bootstrap's
  indifference to its input is pinned as a regression test.
- **(v)** used the same kind of band — a residue of 0.013 "passed" a band of 0.25 — and its
  control was inert besides: `dedupe=False` stopped at `build_ledger` and never reached
  `evidence_from_deltas`, which deduplicated unconditionally. The control could not disable
  the thing the cell was testing. The switch now reaches the accumulator, and since the
  engine is deterministic the tolerance is `duplicate_residue_tolerance` (1e-12): re-ingesting
  one corpus under a second provenance label moves the floor by *exactly* zero, or the cell
  fails.

**Cell (ix)'s control was dead.** It borrowed the real registry, which is empty while D8 is
unpinned — so the control could not fire precisely when you would most want to know the cell
works. It now builds synthetic Mathlib senses and is independent of D8.

**PREREG R3 carried the same defect — now amended.** Once the pattern was named it was
worth checking whether anything else compares an observation against a resample of itself.
R3 did, and R3 is the rule that decides the headline result of the whole run: it read
`floor <= quantile(surrogate_floor_distribution, 0.95)`, the same bootstrap over the same
observed floors. A mean floor of 0.45 carried entirely by the cold arm was called `~0`.

**PREREG-AMENDMENT-1** (authorized 2026-07-30, recorded in full in `registry/PREREG.md`)
replaces the decisive surrogate:

```
near_zero = floor <= second_fdt_surrogate_floor      # warm/cold label permutation
```

`second_fdt_surrogate_floor` permutes the warm/cold *labels* loop by loop: under the null
that the arms are exchangeable it matches the observed floor, and under real path dependence
the observed floor exceeds it. It is a null constructed under the no-effect hypothesis
rather than a resample of the answer.

Three grounds made the amendment admissible. **(a)** The specification always named the
second-FDT surrogate — the mint threshold in the GATES.md constants table is quoted against
it — so the bootstrap was a transcription defect, not a design choice; this restores the
specified procedure rather than choosing a new one. **(b)** No data has passed through R3:
P3 and P4 have not run, so no verdict is being revised in sight of a result. **(c)** The
change is strictness-increasing — the label-permutation threshold does not rise to meet the
floor it is handed, so the `~0` branch becomes harder to obtain, never easier.

R1–R5's text is unchanged and unrewritten; the amendment is appended. The bootstrap band is
still computed and reported as `stats["surrogate_q95"]`, a legacy diagnostic that decides
nothing, and `floor_verdict` says so explicitly whenever the two surrogates would disagree.
`tests/test_controls.py:R3CarriesTheSameDefect` is kept as the historical pin — it exercises
the superseded computation directly, so it records what the defect was without asserting
anything about the current rule.

**Constitutional consequence.** `seed/GATES.md` gained sentence 6: *every statistical
verdict is decided against a null constructed under the no-effect hypothesis (permutation /
phase-randomization / independent surrogate), never against a resample of the observation.*
That generalizes the fix past R3. Editing GATES.md moves the seed hash, which is plastic
under gate 4 — logged as a `seed-morphism` event with before/after hashes, and the battery
re-run cold on the new hash. No warm state was discarded because none existed.

The amendment authority expires when P3 ingestion begins, and that expiry is mechanical:
`audit.check_amendment_window()` raises once any P3 phase-run appears in `REGISTRY.jsonl`.

**R4 also carried the defect — now amended as PREREG-AMENDMENT-2.** Sentence 6 binds every
statistical verdict, so R4 was checked against it and failed: it compared the floor's
movement under Q-edge dropout against `baseline.surrogate["q95"]`, the same bootstrap.

Its failure mode was **not** R3's and the record should not conflate them. R4 was never
vacuous; it was **miscalibrated in the permissive direction** — the band scaled with the
observed floor, so the rule was strict on a run whose floor was near zero and lax on a run
with a large structured floor, relaxing exactly where dictionary sensitivity would have
mattered most.

R4 is now two-sided, both arms against the same null:

- **insensitivity (as registered)** — real 10% Q-dropout movement over 5 trials, PASS iff
  `<= q95` of the movement under the same dropout applied to a degree- and
  weight-marginal-preserving rewire of the Q graph.
- **sensitivity (added)** — clamp-tier perturbation must move the floor *above* that null.
  A rule that only asks "did nothing move?" is satisfied by a meter that cannot move at
  all; this arm is what makes the first arm's pass mean something.

`blocks.rewire_q_graph` stratifies edges by `(weight, origin)` and permutes endpoints by
double-edge swaps, refusing any swap that would make a self-loop or a duplicate pair — so
every node keeps its degree and every stratum keeps its weight and count *exactly*. What
the randomization destroys is only which slots the dictionary chose to link, which is the
hypothesis R4 tests. Stratifying matters: an unstratified rewire would move a heavy fiber
edge onto a pair that never earned one, and a rejection could then be attributed to edge
strength rather than to the dictionary.

**AMENDMENT-2 is a different class of amendment, and that is recorded explicitly.**
AMENDMENT-1 restored a procedure the specification had already named, so it could claim
rationale (a). AMENDMENT-2 cannot: nothing in the spec named a null-rewire reference or a
sensitivity arm, so there is nothing to restore. It is admissible on **(b) and (c) only** —
no data has passed through R4, and both arms are strictly harder to pass. Each amendment
record carries a `class` field (`transcription-restoration` vs `pre-data-design`) so no
later reader has to reconstruct which kind of change it was. A design amendment rests
entirely on the pre-data timing, and saying so is the point.

**With no clamps, R4 is inconclusive rather than passed.** D6 is unresolved, so nothing has
grounded and the sensitivity arm has nothing to perturb. R4 returns `CLOSED-inconclusive`
rather than reporting the insensitivity arm alone — the same distinction R1 draws between
BLOCKED and FAIL. This is the expected state until D6 resolves.

**PREREG R2 carried it too — now amended as PREREG-AMENDMENT-3.** The sweep found it (see
below), and the fix is a label-permutation null: a gap counts as flagged iff its loop's cold
floor exceeds q95 of the null, replacing `floor > bootstrap q95`.

Two things about this amendment differ from the first two and are recorded rather than
smoothed over.

*Its rationale (c) is calibration-restoring, not strictness-increasing.* The bootstrap band
rose with the observed floor, so it was punitive on noisy runs — only above-average loops
flagged, and a genuine gap with a real but below-mean floor was missed. The correction runs
in **both** directions, and some runs that would have failed R2 will now pass. Calling that
extra strictness would misdescribe it.

*Its class was determined by checking, not assumed.* The authorization said
`pre-data-design` unless the drafting history showed the per-loop surrogate was original
intent. It does not: KICKOFF §5's R2 specifies **no flagging criterion at all** — no
threshold, no surrogate, no comparison — and the brief's only second-FDT mention is the mint
threshold, unrelated to R2. `git show` on the P0 scaffold commit has the bootstrap present
from the first commit, unchanged since. There is nothing to restore, so rationale (a) does
not apply and the class stands as `pre-data-design`.

**The mandated positive control caught a defect in the authorized rule itself.** Implemented
literally, "q95 of that loop's own null" is *unsatisfiable*: a `k`-slot loop has `2**k`
warm/cold assignments, the all-cold assignment **is** the observed floor, and q95 of four or
eight points is the maximum. Measured on a synthetic contested corpus, **0 of 4 loops could
flag at any floor** — a 100% miss rate on every run, reproducing the very defect being
replaced in the same punitive direction. The shipped rule pools the *other* loops' permuted
floors leave-one-out, which is the smallest change that keeps the reference a permutation of
observations while giving it usable support. **This deviates from the authorized wording and
needs confirmation.** Its limitation is stated rather than buried: loops are not exactly
exchangeable with one another, so one loud loop raises every other loop's threshold.

The control passes in both mandated directions: clean run plus one planted gap → miss rate
0; an insensitive meter → the planted gap unflagged, miss rate 1.0, `CLOSED-inconclusive`.
Fewer than two loops returns inconclusive rather than a degenerate self-comparison.

**A repair was attempted inside the window and rejected.** The exchangeability limitation
above was to be mitigated by studentizing — scaling each loop's permuted floors by its own
null MAD. One attempt, as authorized. It did not merely fail; it **inverted** the
direction-one control:

| loop | floor | null MAD | studentized | flags? | raw LOO flags? |
|---|---|---|---|---|---|
| the planted gap | 0.217756 | 2.54e-06 | **−0.089** | no | **yes** |
| — | 1.36e-07 | 8.60e-09 | −1.000 | no | no |
| — | 5.49e-08 | 4.04e-10 | **+4.573** | **yes** | no |

Miss rate 1.0 where raw leave-one-out gives 0.0. The reason is structural rather than a
tuning problem: a loop's floor and its permutation null's scale are *the same quantity* —
both come from warm/cold disagreement on that loop — so a loop with a real gap has a large
floor **and** a large null MAD, and dividing one by the other divides out the signal. What
survives is loops whose null is nearly degenerate. Studentizing is right when scale is a
nuisance parameter; here it is the estimand.

The third mandated control, the loud-loop case, ran against raw leave-one-out as shipped:
adding a loop with a far larger floor changed no shared loop's flag status and left the miss
rate stable. That is one instance and not a proof of insensitivity, which is why the
limitation is recorded as **open** rather than closed by it.

Per the authorization this was a single attempt and no further iteration was made — the
window is for repairs, not tuning. Raw leave-one-out stands as shipped. The rejected code is
retained, wired to nothing, classified `rejected` in `GATE6_SITES`, and pinned by
`tests/test_controls.py:StudentizationWasTriedAndRejected`.

The per-loop-only specification is recorded in the amendment as the source of the defect the
pooling works around, not as an implementation misreading.

**The sweep, and what it found.** Three of the four sites above were found by hand, by
noticing that a pattern recurred. That is not a method, so gate 6 now has a codebase-wide
enforcement layer: `static_checks.check_gate6_classification` AST-walks `engine/` and fails
on any band-building or band-reading function not classified in `GATE6_SITES` with its
reference distribution and role. It classifies rather than forbids — a non-conforming band
may exist as a *diagnostic*; what may not exist is an unexamined one. Full results in
`reports/gate6-sweep.md`.

It found a fourth site immediately, one nobody had noticed: **R2**, whose miscalibration ran
*opposite* to R4's — a larger floor raised the bar, so fewer gaps cleared it and the miss
rate went up. That finding is what AMENDMENT-3 acts on. The sweep has since caught one more
thing, this time one of my own: `pooled_loop_nulls` was added and immediately failed the
check as an unclassified band until it was written into `GATE6_SITES`. That is the mechanism
working on its author.

That all of this was found before any floor was read is the battery working as designed.
That five of the finds were *the project's own tests* — two battery cells and three PREREG
rules — is why the control column exists, and why the sweep is a check rather than a
document.

## D8 — what is pinned and what is not

D8 now records a fetch **policy** for each external source, and only WordNet's answer is
also a pin:

| source | policy | artifact | digest |
|---|---|---|---|
| Mathlib | latest stable at fetch | not landed | — |
| nLab | current at fetch | not landed | — |
| WordNet | **3.1** | not landed | — |
| convention table | — | `seed/LEXICON/convention_table.json` | hashed under `seed/` |

"Latest stable" and "current" name a rule, not an input: they resolve to different bytes
next week, so a run keyed to them reproduces a procedure rather than a result. What pins an
import is the **content digest of the dump that landed**, recorded by
`cli.py pin <source> --path ...` alongside the commit / date / version as provenance. Both
reach `SEED.lock`; `check_digest` compares the digest at import time and `cli.py verify`
compares it against the lock, so a re-fetch under the same policy that produces different
bytes trips gate 4 instead of passing silently.

D8 is therefore **partial**, not resolved, and `cli.py status` says so. Writing a plausible
commit hash to clear the blank would have produced a lock that looks pinned and reproduces
nothing.

## Gate 6 — closing table

The amendment window is still open (it closes at the first P3 phase-run), and this is its
closing artifact: every site in the engine that builds or reads a statistical band, and
what decides on it. Generated by `make gate6`; enforced by
`static_checks.check_gate6_classification`, which fails CI on any unclassified band.

**Every deciding site conforms.**

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

Three sites remain non-conforming and all three are diagnostics. That is deliberate: each
amendment kept its superseded band reported so a reader can see what the old rule would
have said. Deleting them would make the amendments unauditable. `within_noise` is dead
code, listed so that a future caller has to classify itself.

Two conformances are weaker than the rest, and the table should not flatten them:

- `cell_ix_binding_sanity` compares against a fixed 5% failure rate. That satisfies
  sentence 6 by not being data-derived, but it is not a null either — nothing calibrates
  5%, so the cell bounds a bug rate rather than testing a hypothesis. Conforming and weak
  are different properties.
- `pooled_loop_nulls` pools across loops that are not exactly exchangeable — they differ
  in slot count and edge weight, so one loud loop raises every other loop's threshold.
  Leave-one-out removes self-contamination but not heterogeneity.

Full sweep, including what each amendment changed and why: `reports/gate6-sweep.md`.

## What is NOT claimed

Nothing about the ledger. The passing cells test the seed and the engine's own source
against themselves: that addressing is a well-defined function, that the pre-registered
pairs address as pre-registered, that every sense has a hub position, that technical terms
resolve technically, and that no display string is reachable from F. They say nothing about
any corpus, because no corpus has been read.

Cell (vii) passing is evidence about the **convention table**, which covers 51 lemmas. It is
not evidence that general English cannot shadow a technical sense in general — WordNet has
not been imported, and the shadow probes are 38 hand-written contexts, not a sample.

A live control shows a cell *can* fail on one engineered input. It does not show the cell is
sensitive to every way the property could break, and it is not a power calculation.

Per PREREG, and holding under every outcome:

- capacity conjecture (needs n>=2 / diversity arms)
- growth law (mint off)
- comms utility (single party)
- generality beyond this corpus and seed hash

## Not terminal

R5's terminal vocabulary does not apply: this is P1 under a provisional seed, not the one
authorized round. P4 is the terminal round and must run from a fresh session on a clean
checkout (KICKOFF §7.3 — that checkout is the cold arm). No additional rounds are proposed.
