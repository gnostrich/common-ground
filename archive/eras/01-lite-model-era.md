# Era: the lite-model era

**Span (as best I can date it):** on or before 2026-08-04 12:47 (commit `20ac348`) through
2026-08-06 09:32 (commit `c2780b8`). See "start date" note at the bottom — I could not find a
commit that marks the *start* of this era as a deliberate decision distinct from the window's
original OpenRouter integration.

## What defined the era

The window's proposer called OpenRouter with `model=openrouter/auto` — model selection left to
the vendor's own routing, chosen deliberately at the time ("operator chose auto model
selection", commit `20ac348`, 2026-08-04 12:47). Nothing in the journal recorded which model had
actually answered a call; every arrow the auto-routed transport produced was indistinguishable
after the fact from an arrow produced by any other model.

## Headline numbers

**The four-transport comparison that ended the era** — one region, one prompt, temperature 0.0
(commit `2e3ec5e`, message):

| transport | lines | distinct pairs | repeats/pair | same_claim |
|---|---|---|---|---|
| `auto` → `gemini-2.5-flash-lite` | 1,789 | 51 | 35.1 | 0 |
| `gemini-2.5-flash` (pinned) | 24 | 24 | 1.0 | 5 |
| `claude-sonnet-4` | 16 | 16 | 1.0 | 2 |
| `gpt-4o-mini` | 15 | 15 | 1.0 | 0 |

- `auto` had served **448 of 465** historical proposer calls to `google/gemini-2.5-flash-lite`
  (commit `2e3ec5e`; restated `engine/quarantine.py` `LEAD_MODELS` docstring; restated
  `seed/CONSTITUTION.md` OI-15).
- Corpus composition attributed to the era: **75% `refines`, 11% `same_claim`**; **359 of 367**
  connected components were trees; only **8 cycles** existed across **16,564 arrows** (commit
  `2e3ec5e`).
- A second defect, diagnosed the same morning in the same transcript (commit `026fe82`,
  2026-08-06 08:45): one region step emitted 1,789 arrow lines that parsed to 962 `ok` / 827
  `void`, and **all 827 void records shared one reason**, `intra-chart` (an arrow between two
  claims in the same chart, which gate 1 refuses). Those same 1,789 lines were only **51
  distinct ordered pairs** — about 35 repeats each. The acceptance guard's ratio had been
  swinging **97% → 2% → 6%** across walk steps because its numerator (`named_pairs`) was
  deduplicated and its denominator (`len(self.void)`) was not — an artifact of the repetition,
  not a measurement of what had actually resolved.

## What ended it

Two commits, nine minutes apart, both 2026-08-06:

- **`2e3ec5e`** (08:58) — "The transport was sick, not the medium." Pinned the served model to
  `google/gemini-2.5-flash`, overridable only by `OPENROUTER_MODEL`, never silently routed.
- **`0b1dd71`** (09:09) — "Per-model tagging, and lite arrows quarantined as leads." Added the
  served model to every journal record (`engine/journal.py:record_ask(model=)`) and a new
  quarantine reason, `lite_pairs()` (`engine/quarantine.py`): any pair whose *only* support came
  from a "lead model" — currently `{google/gemini-2.5-flash-lite}` — is withdrawn from acting
  (excluded from closure, conditioning and the composition path) but retained in full, readable
  and auditable, until a pinned model re-confirms it.

## What was WITHDRAWN — twice, the second correcting the first

1. **The claim that the corpus's sparse, tree-like structure reflected the material.**
   Commit `2e3ec5e`: *"That forest topology is downstream of a ROUTING DEFAULT, not of the
   material."* — withdrawn.

2. **`ce8fc59`** (09:13, five minutes after the pin) reported the *first* correction, at
   n=2,872 pinned arrows: repetition looked fixed (8.83 → 2.12 repeats/pair, "a factor of
   four"), but `same_claim` looked *not* fixed — in fact slightly lower (8.4% lite-era vs.
   7.2% pinned). This commit itself withdraws the implicit hope that pinning would densify the
   graph into cycles: *"What is now false: that a cleaner model would densify the graph into
   cycles."*

3. **`c2780b8`** (09:32, nineteen minutes later), at ten times the sample (n=23,992 pinned
   arrows), **reversed both of `ce8fc59`'s numbers**:
   - Repetition was **not** fixed after all — 8.98 repeats/pair, "indistinguishable from the
     lite era's 8.83." `ce8fc59`'s "fixed, by a factor of four" claim is withdrawn.
   - `same_claim` was **higher**, not lower — 12.07% against the lite era's 8.39%, a 44%
     relative increase. `ce8fc59`'s "not fixed, slightly lower" claim is also withdrawn.
   - `c2780b8`'s own words: *"The withdrawal was as premature as the claim it withdrew."*
   - What did **not** move: total loop count. All arrows (66,329): 1,048 fibers, 357 with ≥3
     members, **8 loops**. Clean stock only (23,992): 6 fibers, 2 with ≥3 members, **1 loop**
     (`c2780b8`).

This double-flip is now load-bearing in the constitution itself. `seed/CONSTITUTION.md:283-285`
(OI-27) names it *"VIOLATED TWICE IN ONE SESSION (n=24 then n=2,872 — both flipped at 10×)"*,
and the fix — `MIN_RATE_N = 10_000` (`engine/battery.py:299`) — is derived directly from where
the flip stopped happening, not chosen.

## What remains true / unresolved as of HEAD (`80791f0`)

Per `seed/INVENTORY.md` rows 345 and 347 (read 2026-08-07):

- **Repetition was never actually repaired, only correctly measured.** Row 347
  (`seed/INVENTORY.md:367`) recomputes it live from `runs/proposer.journal.jsonl`: **7.95
  repeats per pair** over 72,530 ask records / 9,124 distinct pairs — "the same order as
  8.83/8.98" — and states plainly: *"No repair to repetition has been attempted."*
- **A third `same_claim` reading exists and has never been reconciled with the other two.**
  Row 345 (`seed/INVENTORY.md:365`) cites the live `/corpus` figure: 4,928 `same_claim` of
  22,238 asked = **22.16%**, against the 7.2% (n=2,872) and 12.07% (n=23,992) readings already
  on record. The row's status is `UNSTARTED` — nobody has explained the 44%-higher rate yet.

## Numbers I looked for and could not find

- **The era's true start date.** `openrouter/auto` is already the default in the earliest
  window/proposer commit I found that mentions it (`20ac348`, 2026-08-04 12:47: "operator chose
  auto model selection"). I found no earlier commit deciding to use `auto`, so I cannot date the
  start more precisely than "on or before 2026-08-04 12:47."
- **A current count of `lite_pairs()`** as measured on the corpus as it stands today.
  `runs/quarantine.json` on disk (checked 2026-08-07) holds a *different* quarantine
  population — reason "entered from the 2.7%-acceptance unbalanced-region walk run," count
  1,455 — not the lite-model reason, and I found no separate committed artifact reporting the
  current `lite_pairs()` count.
