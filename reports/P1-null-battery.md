# P1 — null battery

Provisional seed hash (`seed/SEED.lock` is not written; D3, D4's spend cap, D5, D6 are
unresolved and D8 is partial). Registry entry committed before the run, per KICKOFF §7.2.

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

**PREREG R3 carries the same defect — reported, not fixed.** Once the pattern was named it
was worth checking whether anything else compares an observation against a resample of
itself. R3 does, and R3 is the rule that decides the headline result of the whole run:
`floor <= quantile(surrogate_floor_distribution, 0.95)`, the same bootstrap over the same
observed floors. A mean floor of 0.45 carried entirely by the cold arm is called `~0` by
that test — pinned in `tests/test_controls.py:R3CarriesTheSameDefect`.

R3 has **not** been amended. PREREG is frozen under D7, and rewriting a pre-registered
rule's decision procedure after the fact is precisely what pre-registration exists to
prevent; it is the operator's call. Nothing has been decided through R3 yet — P3 and P4
have not run — so this is caught before it mattered, which is the only good time. What was
done instead: the defect is pinned by a test, and `audit.floor_verdict` now reports
`second_fdt_floor` in its stats and appends an explicit caveat to the detail line whenever
the two surrogates disagree, so no reader of an R3 verdict is unaware of it.

The non-vacuous alternative already exists and is already computed and logged on every run.
`second_fdt_surrogate_floor` permutes the warm/cold *labels* loop by loop: under the null
that the arms are exchangeable it matches the observed floor, and under real path
dependence the observed floor exceeds it. It is a null rather than a resample of the
answer. Adopting it is a one-line amendment (`near_zero = floor <=
result.surrogate["second_fdt_floor"]`) and needs authorization, a logged amendment, and a
cold re-anneal.

That all of this was found before any floor was read is the battery working as designed.
That three of the finds were *the project's own tests* — two battery cells and a PREREG
rule — is why the control column exists.

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
