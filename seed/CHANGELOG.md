# CHANGELOG — landed design changes, newest first

Feature-level rollup, one line per landed design change, each linking its commit. This is a
curated subset of `git log`: pure bug fixes, ledger/record-only commits, checkpoint commits, and
routine infra (container-reclaim recovery, deploy plumbing) are left out on purpose — see
`git log --oneline` for the complete, unfiltered history. Numbers quoted here are the commit's
own; see `/archive/eras/` for the four major eras with fuller sourcing and their withdrawals.

Repo: [gnostrich/common-ground](https://github.com/gnostrich/common-ground). Link format:
`[sha](https://github.com/gnostrich/common-ground/commit/<full-sha>)`.

---

- **2026-08-07** — **The null surface** — IN FLIGHT when this changelog was first drafted;
  landed mid-task as [`0175806`](https://github.com/gnostrich/common-ground/commit/01758065fb3029664052b747e71bdfe048244ce1).
  Deletes the entire two-coordinate interaction surface (mode selector, retain checkbox, claim
  gesture, ACT reader) — every operator utterance now enters the tape directly as an authored
  record, and what becomes of it is sorted downstream by aging and by K. Supersedes SPEC §10/§10a
  and OI-42/OI-43/OI-41's CLAIMED arrow; superseded designs kept verbatim in `archive/design/`.
  See `archive/eras/04-pre-null-surface.md`.
- **2026-08-06** — Python and Go chart scaffolds: `depends_on` parsed from source (AST for
  Python, a documented scanner for Go), zero LM calls; 640 python / 3,039 go edges measured on
  the live corpus snapshot. [`025727b`](https://github.com/gnostrich/common-ground/commit/025727b)
- **2026-08-06** — OI-5 mechanized: `engine/conditionals.py` scans normative prose for
  conditional-language tells, forgiving a clause only when it cites something that refuses.
  [`b597a51`](https://github.com/gnostrich/common-ground/commit/b597a51)
- **2026-08-06** — OI-30 mechanized: `engine/decompose.py` — a remainder has three places to
  go and two are lies, so decomposition always carries an honest `unattributed`. Found a real
  violation in `Journal.totals()`. [`13d911a`](https://github.com/gnostrich/common-ground/commit/13d911a)
- **2026-08-06** — OI-37 mechanized: two-armed key-exposure scan (pattern SHAPE + literal
  env-value LITERAL) over the tree and full reachable git history; found a real gap
  (`*.env` was not gitignored) on its first run. [`497161c`](https://github.com/gnostrich/common-ground/commit/497161c)
- **2026-08-06** — The transcript panel: every LM call, both directions, rendered on the page
  and verified — a `raw LM traffic` section with a client-side re-hash of what's on screen
  against the server's own digest, so "what you are shown is what was sent" is checkable.
  Fixed two defects: the transcript sink was never reset per-request, and `/propose`/`/claim`
  returned no transcript at all. [`83cc6e3`](https://github.com/gnostrich/common-ground/commit/83cc6e3)
  (precursor: raw LM logging + the warrant selector, [`ef7f172`](https://github.com/gnostrich/common-ground/commit/ef7f172);
  follow-up: render call names its model, [`13b0e38`](https://github.com/gnostrich/common-ground/commit/13b0e38))
- **2026-08-06** — OI-24 and OI-36 mechanized: `engine/nonempty` (success-on-the-empty-set is a
  defect class) and the reflexivity sweep made standing (own material stays out of the corpus,
  0 matches across 80,566 slots). [`d0b03c4`](https://github.com/gnostrich/common-ground/commit/d0b03c4)
- **2026-08-06** — OI-19 mechanized: `Member.surface` (typed bytes) vs. `Member.wire` (the one
  accessor the renderer reads) — the operator's raw input now reaches the medium byte-identical
  to what was typed, not its normalized ν. [`65a9601`](https://github.com/gnostrich/common-ground/commit/65a9601)
- **2026-08-06** — OI-43 (posture): an unknown TOLD mode defaults to ASSERT, an unread ACT
  defaults to EXPLORE/KEEP-NOTHING — the conservative direction inverts depending on whether the
  machine is told or reads. Superseded 2026-08-07 by the null surface, above.
  [`e78fbfb`](https://github.com/gnostrich/common-ground/commit/e78fbfb)
- **2026-08-06** — OI-4 mechanized: the constants sweep. 20 of 24 constants confessed at landing
  (now 22 of 26 — see `archive/eras/04-pre-null-surface.md`); the sweep asserts the *transition*
  confessed→derived is the controlled event, not the ratio. [`c1a3dbd`](https://github.com/gnostrich/common-ground/commit/c1a3dbd)
- **2026-08-06** — OI-42 (interaction surface, first version): two independent binary
  coordinates plus one constructible arrow — objecthood (assert/brainstorm) and persistence
  (retain) — forced and complete, no fifth state. Superseded 2026-08-07 by the null surface,
  above. [`f985d36`](https://github.com/gnostrich/common-ground/commit/f985d36)
- **2026-08-06** — **The clean-state strip**: the render input is cut to state + a question,
  nothing else. Removed 6 recited grammar rules (1,193 → 495 chars) and an editorial mechanism
  preamble (18,474 → 7,535 chars) the model was reciting back instead of answering from;
  restored the missing task verb. Also records a false-repair finding (a stale disclaimer, not
  a code defect) and a mutually-concealing pair of bugs. [`78d6659`](https://github.com/gnostrich/common-ground/commit/78d6659)
  (precursor: "the prompt is wire, grammar and state," [`2598c25`](https://github.com/gnostrich/common-ground/commit/2598c25))
- **2026-08-06** — `seed/CONSTITUTION.md` lands: 40 invariants (OI-1..OI-40), machine-readable
  via `seed/OI_REGISTRY.json`, every enforcement site AST-resolved, 0 unresolvable, 11 WEAK
  named outright. [`4a4b238`](https://github.com/gnostrich/common-ground/commit/4a4b238)
- **2026-08-06** — The standing auditor: read-only, fixes nothing, files findings with artifact
  evidence. First run found eight real findings, including a sweep that could not execute at
  all and a battery prompt whose response arrived incomplete. [`65cc424`](https://github.com/gnostrich/common-ground/commit/65cc424)
- **2026-08-06** — The Lean chart scaffold: 5,964 dependency edges parsed from material that
  had gone in flat. [`3f5bca1`](https://github.com/gnostrich/common-ground/commit/3f5bca1)
- **2026-08-06** — Nomination: a question about arrow-poor material can now assemble a region
  about it; exploration pressure derived from measured imbalance and self-extinguishing.
  [`6a42bbb`](https://github.com/gnostrich/common-ground/commit/6a42bbb) /
  [`53a8096`](https://github.com/gnostrich/common-ground/commit/53a8096)
- **2026-08-06** — **Apex-star**: `edges_from_fibers` emits one derived apex per fiber and *k*
  face-edges to it, replacing all-pairs. Zero degrees of freedom the faces don't determine; a
  120-member fiber goes from 7,140 fabricated edges to 120. See `archive/eras/03-pre-apex-energy.md`.
  [`7bac55a`](https://github.com/gnostrich/common-ground/commit/7bac55a)
- **2026-08-06** — **The great repair** (demotion): `engine/adjudicate.py` re-kinds
  code-to-own-docstring containment from `same_claim` to `refines` — 2,082 same_claim pairs to
  69 surviving, 1,046 fibers to 2. Nothing deleted; a demoted arrow keeps its evidence and stops
  being loop-eligible. See `archive/eras/02-pre-demotion-substrate.md`. [`b650d1f`](https://github.com/gnostrich/common-ground/commit/b650d1f)
- **2026-08-06** — The data channel: the corpus reaches the deploy on a Railway volume without
  ever touching a git tree. [`adb5135`](https://github.com/gnostrich/common-ground/commit/adb5135)
- **2026-08-06** — The build now names its MATERIAL (corpus snapshot digest and age), not only
  its code commit. [`f126f8d`](https://github.com/gnostrich/common-ground/commit/f126f8d)
- **2026-08-06** — The medium chart: the last silent cross-format translation made declared and
  gated. [`bc12f92`](https://github.com/gnostrich/common-ground/commit/bc12f92)
- **2026-08-06** — The structure layer and the export sheet: `T_{op→any-agent}` as a settled
  state exported as a portable preamble, with fixtures pinning its exact content.
  [`609a27a`](https://github.com/gnostrich/common-ground/commit/609a27a)
- **2026-08-06** — OI-6 enforced by referee sweep: three separate similarity mechanisms found
  and removed from referees (the acceptance guard measured verbosity; the faithfulness checker
  was bag-of-words; conversation verdicts used keyword intersection). [`c358298`](https://github.com/gnostrich/common-ground/commit/c358298)
- **2026-08-06** — Answer-first: the "least trusted" caution, which had outlived the
  faithfulness gate that made it necessary, is removed (OI-26). [`78f8e73`](https://github.com/gnostrich/common-ground/commit/78f8e73)
- **2026-08-06** — The page is code and now gets a compiler: cross-chart rules move from prose
  instruction into the output grammar itself. [`27bb07a`](https://github.com/gnostrich/common-ground/commit/27bb07a) /
  [`bfb927b`](https://github.com/gnostrich/common-ground/commit/bfb927b)
- **2026-08-06** — Streaming reverted to buffered responses with an honest elapsed counter,
  after chunked streaming was found to hang the browser behind a keep-alive proxy.
  [`4b5f3ad`](https://github.com/gnostrich/common-ground/commit/4b5f3ad)
- **2026-08-06** — The deploy build-stamp mechanism: served commit is written at deploy time,
  never committed, and the served model reports itself. [`cd6ad14`](https://github.com/gnostrich/common-ground/commit/cd6ad14)
- **2026-08-06** — **Lite-model era ends**: `openrouter/auto` (448/465 historical calls routed
  to a lite model, 35x repetition) is replaced by a pin to `google/gemini-2.5-flash`; per-model
  tagging and a lead-model quarantine land alongside it. See `archive/eras/01-lite-model-era.md`.
  [`2e3ec5e`](https://github.com/gnostrich/common-ground/commit/2e3ec5e) /
  [`0b1dd71`](https://github.com/gnostrich/common-ground/commit/0b1dd71)
- **2026-08-06** — void=962 diagnosed: the acceptance guard's numerator was deduplicated and its
  denominator was not, so the reported ratio tracked model repetition rather than what had
  resolved. Both sides deduped. [`026fe82`](https://github.com/gnostrich/common-ground/commit/026fe82)
- **2026-08-05** — Ask and propose become one act with a persistence (`retain`) flag; the
  bare-propose path is deleted the same day once D14's aging exists to receive it.
  [`5224d4f`](https://github.com/gnostrich/common-ground/commit/5224d4f) /
  [`9d20dff`](https://github.com/gnostrich/common-ground/commit/9d20dff)
- **2026-08-05** — The candidate-list loop (a second mechanism beside the sampler) is deleted;
  one mechanism reaches the field (OI-3). [`e2cab6a`](https://github.com/gnostrich/common-ground/commit/e2cab6a)
- **2026-08-05** — Re-confirmation requires an independent region — closing a loophole where a
  quarantined arrow could re-enter without genuinely new support. [`34c3bf1`](https://github.com/gnostrich/common-ground/commit/34c3bf1)
- **2026-08-05** — The quarantine mechanism and the `bears_on` relation land together; drift
  triples that were being computed but never persisted are fixed. [`4bc8df3`](https://github.com/gnostrich/common-ground/commit/4bc8df3)
- **2026-08-05** — The wire carries the diagram directly; the composition table moves to
  `seed/COMPOSITION.json`. [`e54b9b2`](https://github.com/gnostrich/common-ground/commit/e54b9b2)
- **2026-08-05** — Region relaxation lands: the core mechanism, its void gate, and a first run
  that failed (informatively). [`ec1ee3c`](https://github.com/gnostrich/common-ground/commit/ec1ee3c)
- **2026-08-05** — **The amendment**: attachment is proposed, not inherited — landed as
  canonical and the daemon moves onto the deploy. [`9a2ee31`](https://github.com/gnostrich/common-ground/commit/9a2ee31)
  (implementation: [`643b5ec`](https://github.com/gnostrich/common-ground/commit/643b5ec))
- **2026-08-05** — Inbound becomes bias-and-relax: settlement runs on the real corpus, no
  fixture fallback. [`717acdb`](https://github.com/gnostrich/common-ground/commit/717acdb)
- **2026-08-05** — **Retrieval is navigation, not addressing** — a foundational reframing of
  how the window answers a question, and the window works again as a result.
  [`affc0e1`](https://github.com/gnostrich/common-ground/commit/affc0e1)
- **2026-08-05** — The corpus becomes a pointer file, not three environment variables.
  [`975c375`](https://github.com/gnostrich/common-ground/commit/975c375)
- **2026-08-05** — The Anthropic extractor is deleted outright — one provider path, not two
  half-maintained ones. [`486f67c`](https://github.com/gnostrich/common-ground/commit/486f67c)
- **2026-08-05** — Candidate census per chart pair: declaration granularity is bound as the
  whole candidate surface (70,241 slots measured over 11 repositories).
  [`48e3f99`](https://github.com/gnostrich/common-ground/commit/48e3f99)
- **2026-08-05** — Hole enumeration generalized to any chart pair, not only lean→english.
  [`9eb0a47`](https://github.com/gnostrich/common-ground/commit/9eb0a47)
- **2026-08-05** — Every normative rule is labelled with whose it is (operator vs. inferred);
  an invented constraint is removed (OI-1). [`0aae3be`](https://github.com/gnostrich/common-ground/commit/0aae3be)
- **2026-08-05** — The journal is split so the record survives a container reclaim without ever
  publishing corpus content. [`e941f44`](https://github.com/gnostrich/common-ground/commit/e941f44)
- **2026-08-04** — Python and Go charts land: the router seam held on the second and third
  chart added after English/Lean. [`4ec72c6`](https://github.com/gnostrich/common-ground/commit/4ec72c6)
- **2026-08-04** — The router seam closes: which chart an extension enters is seed data, not
  code. [`179231d`](https://github.com/gnostrich/common-ground/commit/179231d)
- **2026-08-04** — Verbatim is declared a property of a span, not of a document — a precision
  rule that later work depends on. [`230f779`](https://github.com/gnostrich/common-ground/commit/230f779)
- **2026-08-04** — **The window sees the real corpus** — the live daemon's corpus, not a
  fixture, reaches the served window for the first time. [`08c45fb`](https://github.com/gnostrich/common-ground/commit/08c45fb)
- **2026-08-04** — The proposer's ledger is kept out of the repository (data sovereignty, OI-35
  precursor). [`111a927`](https://github.com/gnostrich/common-ground/commit/111a927)
- **2026-08-04** — The window shows the daemon's ledger, with the operator's hand visibly on
  it. [`c505674`](https://github.com/gnostrich/common-ground/commit/c505674)
- **2026-08-04** — Continuous and global: the proposer becomes a background daemon over one
  shared corpus rather than a per-request process. [`4796be2`](https://github.com/gnostrich/common-ground/commit/4796be2)
- **2026-08-04** — OpenRouter only: the Anthropic call path is deleted from the window (OI-14
  precursor — see `92f5b12`; distinct from the extractor deletion, `486f67c`, above).
  [`92f5b12`](https://github.com/gnostrich/common-ground/commit/92f5b12)
- **2026-08-04** — Type filter turned OFF cross-chart (a Lean `conditional` and its English
  restatement `assert` are the same claim in different surface forms); corpus state persisted;
  the INBOUND direction added. [`0e0d19d`](https://github.com/gnostrich/common-ground/commit/0e0d19d)
- **2026-08-04** — Subtree bounding: a prose document's position asserts its scope over what
  lives below it — no ranking, no lexical matching. [`8e5878e`](https://github.com/gnostrich/common-ground/commit/8e5878e) /
  [`1c272bf`](https://github.com/gnostrich/common-ground/commit/1c272bf)
- **2026-08-04** — Docstrings become English claims in the corpus (a significant expansion of
  what counts as material). [`53d8a6d`](https://github.com/gnostrich/common-ground/commit/53d8a6d)
- **2026-08-04** — Face admission by measurement, not curation: the stop-list is retired
  (OI-7). [`0c00bd3`](https://github.com/gnostrich/common-ground/commit/0c00bd3)
- **2026-08-04** — **Gate 10**: docstrings are not warrants — a claimed mechanism property needs
  a named control or it is flagged. [`ea4c288`](https://github.com/gnostrich/common-ground/commit/ea4c288)
- **2026-08-04** — Corpus-derived formal faces: the term-level anchor layer for the lexicon
  (operator option 2). [`2e95093`](https://github.com/gnostrich/common-ground/commit/2e95093)
- **2026-08-04** — **Correspondence becomes a base-category morphism** (GATES sentence 9): a
  directed, typed morphism between two slot addresses, entering through the one inlet.
  [`db02302`](https://github.com/gnostrich/common-ground/commit/db02302)
- **2026-08-04** — Null-battery P/¬P similarity artifact stripped; the contest rebuilt on the
  object's two real mechanisms (a clamp conflicting with extraction, or a declared
  correspondence with conflicting grounding). [`7735b53`](https://github.com/gnostrich/common-ground/commit/7735b53)
  (origin: [`de86716`](https://github.com/gnostrich/common-ground/commit/de86716))
- **2026-08-04** — GATES sentence 8: a slot-attributed property is computed over that slot's
  own address span; nothing outside the span may influence it. [`9eb7498`](https://github.com/gnostrich/common-ground/commit/9eb7498)
- **2026-08-04** — One current, one valve, one window: the single inlet, K live, and the LM in
  the loop unified into one architecture. [`4d21983`](https://github.com/gnostrich/common-ground/commit/4d21983)
- **2026-08-04** — Window LM source wired via OpenRouter (`auto` model) — the key lives
  server-side, no UX prompt. This is where the lite-model era's routing choice begins; see
  `archive/eras/01-lite-model-era.md`. [`20ac348`](https://github.com/gnostrich/common-ground/commit/20ac348)
- **2026-08-04** — The conversation chart (move-1): speaker-attributed claims plus a
  proposal→verdict ledger, entering as a fresh address space. [`f29ca44`](https://github.com/gnostrich/common-ground/commit/f29ca44)
- **2026-08-04** — Object north-star (`seed/OBJECT.md`) plus the three-moves belonging audit —
  completes THE DELTA. [`392370b`](https://github.com/gnostrich/common-ground/commit/392370b)
- **2026-07-31** — Charts become a seed manifest: chart plug-in refactor, the belonging audit
  flips to PASS. [`24c3720`](https://github.com/gnostrich/common-ground/commit/24c3720)
- **2026-07-31** — The spellcheck ν stage is built, then dropped on its own controls — a
  design decision recorded with its reasoning, not silently reverted. [`b264506`](https://github.com/gnostrich/common-ground/commit/b264506)
- **2026-07-31** — The ingestion router lands: one artifact, one destination, a logged count.
  [`084dfb1`](https://github.com/gnostrich/common-ground/commit/084dfb1)
- **2026-07-31** — Probe battery (9 commitments) established as the first-run acceptance
  contract for new mechanisms. [`71c62fc`](https://github.com/gnostrich/common-ground/commit/71c62fc)
- **2026-07-31** — DRNG content-keying repair plus GATES sentence 7: generative keys are
  content-and-seed only; artifact identity lives in provenance exclusively. [`dd5c759`](https://github.com/gnostrich/common-ground/commit/dd5c759)
- **2026-07-31** — Tree-null repair: holonomy defined only on verified cycles (closed, all
  edges in Q, no immediate backtracking, length ≥ 3); backtracking becomes a measured shadow
  instead of a false loop. [`036b752`](https://github.com/gnostrich/common-ground/commit/036b752)
- **2026-07-31** — `FAITHFULNESS.md` and `check_faithfulness` land: theory object → code site →
  control, as a checked chain rather than an assertion. [`e45db26`](https://github.com/gnostrich/common-ground/commit/e45db26)
- **2026-07-30** — PREREG-AMENDMENT-1/2/3: R3 decided by a null rather than a resample, R4
  against a two-sided rewire null with an executable gate-6 sweep, R2 against a permutation
  null. [`52933e4`](https://github.com/gnostrich/common-ground/commit/52933e4) /
  [`b817af4`](https://github.com/gnostrich/common-ground/commit/b817af4) /
  [`e47dc3f`](https://github.com/gnostrich/common-ground/commit/e47dc3f)
- **2026-07-30** — Lexicon layer lands: a hub of faces, not a hub of truth (null cells vi-ix).
  [`b1901fe`](https://github.com/gnostrich/common-ground/commit/b1901fe)
- **2026-07-30** — **P0**: the scaffold, the seed layer and the reconciliation engine — project
  origin. [`a108a0b`](https://github.com/gnostrich/common-ground/commit/a108a0b)

---

*Compiled 2026-08-07 by reading `git log --oneline` (170 commits on this branch at the start
of this task, through `80791f0`) against `seed/INVENTORY.md`, `seed/CONSTITUTION.md`, and each
cited commit's own message. The null surface (`0175806`) landed mid-task, and this file was
updated to cover it; further commits landed on this branch after that from a concurrent lane
(a running amendment-gate and auditor effort) are not yet reflected here — check `git log
--oneline` past `0175806` for anything newer. Omissions are otherwise a curation choice, not
an oversight — see the note at the top.*
