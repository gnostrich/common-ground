# P1 — null battery

Provisional seed hash (`seed/SEED.lock` is not written; D3, D4's spend cap, D5, D6 and D8
are unresolved). Registry entry committed before the run, per KICKOFF §7.2.

## Lexicon imports

| Source | Status | Detail |
|---|---|---|
| mathlib | **BLOCKED** | D8: no pinned dump path and commit. A live pull is forbidden during a run (KICKOFF §7.5) and could not hash cleanly anyway. |
| convention | **imported** | 176 senses, 17 bridges; 113 unresolved formal-face candidates dropped rather than invented |
| nlab | **BLOCKED** | D8: no pinned scrape path and date |
| preminted | **BLOCKED** | D5: `seed/LEXICON/preminted/` holds no files |
| wordnet | **BLOCKED** | D8: no pinned dump path and version |

The 113 dropped candidates are correct behaviour, not loss: a convention-table
`formal_faces` entry is a *candidate* Mathlib binding, and with no dump imported none
resolves. The importer drops and counts them rather than inventing a binding no dump backs.

## Matrix

| Cell | Status | Reading |
|---|---|---|
| i. normalizer idempotence | **PASS** | `nu(nu(x)) == nu(x)` on 1010 fuzzed samples across both charts, plus fixed adversarial cases |
| ii. paraphrase suite | **PASS** | 10 pre-registered known-same pairs collided; 10 known-distinct separated, including the cross-chart pair and the Lean case-sensitivity pair |
| iii. empty-corpus floor | **BLOCKED** | D5: no pre-minted entries, so the seed has no slot inventory to check for self-contest |
| iv. single-doc null | **BLOCKED** | D3: no held-out document per source |
| v. duplicate-source null | **BLOCKED** | D3: no corpus to duplicate |
| vi. hub-coverage | **PASS** | all 176 senses carry an English face (0 rendered, 176 authored; 176 English-only, expected) |
| vii. shadow check | **PASS** | 32 probes: technical contexts resolved technically, general contexts resolved generally, zero abstentions |
| viii. no-clamp grep | **PASS** | no display attribute reachable from 8 F-path modules or 2 F-feeding functions |
| ix. binding sanity | **BLOCKED** | D8: no Mathlib-derived senses, so there is no R-map round trip to check |

**Battery status: BLOCKED.**

## Verdict sentence

`BLOCKED` is not green, so PREREG R1 applies and the run is **VOID**. The battery
distinguishes this from `FAIL`: cells iii–v and ix were never in a position to be tested,
which is a different finding from having been tested and failed. Publishing them as the
same finding would be a false report.

Gate 5 therefore holds. `meter.read_floor()` refuses any floor read at this seed hash and
will keep refusing until the battery returns `PASS` on the *same* hash.

## Defects found and fixed

The battery earned its keep twice.

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

That all five were found before any floor was read is the battery working as designed.

## What is NOT claimed

Nothing about the ledger. The passing cells test the seed and the engine's own source
against themselves: that addressing is a well-defined function, that the pre-registered
pairs address as pre-registered, that every sense has a hub position, that technical terms
resolve technically, and that no display string is reachable from F. They say nothing about
any corpus, because no corpus has been read.

Cell (vii) passing is evidence about the **convention table**, which covers 46 lemmas. It is
not evidence that general English cannot shadow a technical sense in general — WordNet has
not been imported, and the shadow probes are 32 hand-written contexts, not a sample.

Per PREREG, and holding under every outcome:

- capacity conjecture (needs n>=2 / diversity arms)
- growth law (mint off)
- comms utility (single party)
- generality beyond this corpus and seed hash

## Not terminal

R5's terminal vocabulary does not apply: this is P1 under a provisional seed, not the one
authorized round. P4 is the terminal round and must run from a fresh session on a clean
checkout (KICKOFF §7.3 — that checkout is the cold arm). No additional rounds are proposed.
