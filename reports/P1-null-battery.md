# P1 — null battery

Seed hash `4c1f69766b4e5cf1384ebd7689a3c9f7350b34dfab2c57d9cbbd933a2a1b7914` (**provisional**
— `seed/SEED.lock` is not written; D3, D4's spend cap, D5, and D6 are unresolved).

Run log: `runs/P1-4c1f69766b4e-20260730T102716.647Z.jsonl`. Registry entry committed before
the run, per KICKOFF §7.2.

## Matrix

| Cell | Status | Reading |
|---|---|---|
| i. normalizer idempotence | **PASS** | `nu(nu(x)) == nu(x)` on 1010 fuzzed samples across both charts, plus fixed adversarial cases (empty, whitespace-only, bare chart tag, already-normalized) |
| ii. paraphrase suite | **PASS** | 10 pre-registered known-same pairs collided on one slot id; 10 known-distinct pairs separated, including the cross-chart pair and the Lean case-sensitivity pair |
| iii. empty-corpus floor | **BLOCKED** | D5 unresolved: `seed/LEXICON/preminted/` holds no entries, so the seed has no slot inventory to check for self-contest |
| iv. single-doc null | **BLOCKED** | D3 unresolved: no held-out document per source |
| v. duplicate-source null | **BLOCKED** | D3 unresolved: no corpus to duplicate |

**Battery status: BLOCKED.**

## Verdict sentence

`BLOCKED` is not green, so PREREG R1 applies and the run is **VOID**. The battery
distinguishes this from `FAIL`: cells iii–v were never in a position to be tested, which is
a different finding from having been tested and failed, and publishing them as the same
finding would be a false report.

Gate 5 therefore holds. `meter.read_floor()` refuses any floor read at this seed hash, and
will keep refusing until the battery returns `PASS` on the *same* hash.

## One defect found and fixed

Cell (i)'s fuzzer found a genuine idempotence break in the English normalizer, on input
`'*#\nr\t\x00\x01m → $_\n='`:

- Markdown line-prefix stripping ran **before** whitespace collapse.
- The inline pass removed the leading `*`, which promoted `#` to line-initial.
- `#` was therefore stripped on the *second* application of `nu` but not the first, so
  `nu(nu(x)) != nu(x)`.

This is an addressing defect, not a cosmetic one: a non-idempotent `nu` means a slot's
identity depends on how many times it happened to be normalized. Fixed by iterating the
leading-prefix strip to a fixed point *after* the whitespace collapse
(`engine/normalize.py:_nu_english`). Re-verified at 4010 samples.

That this was found before any floor was read is the null battery working as designed.

## What is NOT claimed

Nothing about the ledger. Cells i and ii test the seed against itself — that addressing is
a well-defined function and that the pre-registered pairs address as pre-registered. They
say nothing about any corpus, because no corpus has been read.

Per PREREG, and holding under every outcome:

- capacity conjecture (needs n>=2 / diversity arms)
- growth law (mint off)
- comms utility (single party)
- generality beyond this corpus and seed hash

## Not terminal

R5's terminal vocabulary does not apply here: this is P1 under a provisional seed, not the
one authorized round. P4 is the terminal round, and it must be run from a fresh session on
a clean checkout (KICKOFF §7.3 — that checkout is the cold arm). No additional rounds are
proposed.
