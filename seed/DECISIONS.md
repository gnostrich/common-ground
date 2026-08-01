# DECISIONS — D1..D8

Owner: Rohan. `SEED.lock` cannot be written while any decision is `UNRESOLVED`
(`engine/seed_lock.py` scans this file and refuses). Phases P1 and later are blocked on a
written lock, per KICKOFF §7.1.

Machine-readable state lives in `seed/DECISIONS.json`. This file is the human record; the
JSON is what the lock builder reads. Keep them in step — CI checks that every decision id
present here appears there with the same status.

---

## D1 — repo name / visibility / license — **RESOLVED (by fact)**

- name: `gnostrich/common-ground`
- visibility: as configured on the remote (not set by this repo)
- license: MIT, `LICENSE`, © 2026 gnostrich

Resolved from the repository as it exists; no decision was required.

## D2 — charts — **RESOLVED** (english, lean, tabular)

`{english, lean}` per the KICKOFF default, plus **tabular** added 2026-07-31 by the item-2
chart plug-in refactor (operator-authorized). The code chart is still deferred to v0.5.

Charts are now a **seed manifest** (`seed/CHARTS.json`), not a compile-time `Literal`. The
plug-in audit (`engine/chart_plugin_audit.py`) had found the two-chart assumption hardcoded
at five sites and failed; the refactor relocated english and lean behind a registry keyed by
a declared `behavior` id, and the audit now PASSes. A fourth chart is a manifest row plus a
normalizer/classifier/segmenter registered under its behavior id — **no dispatch edit**. The
chart tag rides inside every address, so it is declared in the manifest and hashed into
`SEED.lock` (gate 4).

**The morphism was additive, and that shape is the template for v0.5 code-chart admission.**
English and Lean kept their tags (`\x01en\x01`, `\x01lean\x01`) and their normalizers, so
no existing address moved; tabular added a *new* address space (`\x01tab\x01`) that nothing
maps onto. An additive chart admission is therefore a manifest row + three behavior
functions + a purely-additive seed-morphism (new tag, no remap) + a cold re-anneal, with the
`chart_plugin_audit` PASS as the gate. The v0.5 code chart is admitted the same way: give it
a fresh tag, register its behaviors, do not touch the english/lean tags, and the morphism
stays additive rather than a remap. The audit gates the admission — and it has its own
planted-defect control (`tests/test_probes.py:TheChartAuditCanDetectAReintroducedDefect`), so
a reintroduced `if chart == ...` dispatch turns it red before any new chart can slip in
around it.

## D3 — corpus manifest — **PARTIAL**

Required before P3 (full ingestion). Blocks `SEED.lock`.

- `claude_export`: **pinned** (operator 2026-07-31) — `registry/imports/claude_export_pin.json`,
  129 threads / 11,514 turns, `conversations.json` sha256 `ffe6e6ad…7d60b`. Verified to parse
  in the adapter's expected shape. **Bytes stored external to this public repo** (digest-only),
  since the export is the operator's full personal history.
- `lean_corpus`: **pinned** (operator 2026-07-31) — `registry/imports/aristotle_corpus_pin.json`,
  297 Aristotle projects, 2,128 `.lean` (1,120 unique), `artifact_digest` `24485b87…eb648`.
  Fetched out-of-band and pinned — **not** a live pull (dump preferred over live MCP; KICKOFF §7.5
  forbids live pulls during a run). Zero vendored Mathlib. **Bytes stored external to this public
  repo** (digest-only); a large share is proprietary trading/DeFi formalization.
- `repos`: `[certified-positivity, ____]` — **second repo still OPEN**.
- `EXCLUSIONS` (privacy pass, mandatory, precedes ingestion): **policy set, list OPEN** — operator
  delegated judgement ("exclude personal, non-technical content; nothing technical confidential").
  The concrete term-list is authored at ingestion; an explicit `[]` would still be a decision, never
  a default. `adapters/claude_export.py` still raises on `exclusions=None`.

The two data sources are in hand and pinned; the EXCLUSIONS term-list and the second repo remain.
A wrong guess here silently changes what the run is about, and the EXCLUSIONS list is a privacy
control that must be authored deliberately, not inferred — so D3 stays **partial**, and with D5 and
D6 open, `SEED.lock` is still held closed.

## D4 — extractors — **PARTIAL**

- k=3 composition: **RESOLVED (stated in brief)** —
  `[modelA+promptV1, modelA+promptV2, modelB+promptV1]`.
  Bound to concrete models in `seed/DECISIONS.json` as
  modelA = `claude-opus-5`, modelB = `claude-sonnet-5`.
  These are the current Opus- and Sonnet-tier ids; two tiers give the k=3 design a genuine
  model axis rather than three prompt variants wearing a model's name.
- spend cap: **UNRESOLVED** — `____`

Live extraction is off by default and stays off regardless: `engine/extract.py` refuses to
construct an API-backed extractor unless *both* `COMMON_GROUND_ENABLE_LLM=1` and a numeric
spend cap are set. The offline `DeterministicExtractor` is what the null battery and every
dry run use, so P0–P2 do not need this resolved. P3 does.

## D5 — pre-minted lexicon files — **UNRESOLVED**

`[BVALUED-AGREED.md, STATEMENTS.md, REGISTRY.md, ____]`

The three named files are not present in this repository and no path was given for them.
They are ingested as high-warrant (`PREMINTED`) entries and they populate the seed's slot
inventory, so they are what null cell (iii) — empty-corpus floor — actually runs against.
Until they are present, cell (iii) reports `BLOCKED`, not `PASS`, and gate 5 therefore
holds the floor closed. That is the intended behaviour, not a defect.

Place the files under `seed/LEXICON/preminted/` and list them in `seed/DECISIONS.json`.

## D6 — pinned toolchain — **UNRESOLVED**

- Lean: `____` (from the `certified-positivity` lake-manifest)
- Python: `____`

The Lean version must be read out of that repo's lake-manifest, not assumed — gate 3 makes
kernel-accept *under the pinned toolchain* the only proof-side grounding warrant, so an
unpinned or mis-pinned toolchain makes every kernel clamp meaningless. The Python version
pins the interpreter the engine's own hashes were produced under.

Observed in this container (a candidate, not a decision): Python 3.11.15. The engine is
pure-stdlib by design — no numpy, no scipy — so that hashes and singular values are
reproducible across platforms rather than dependent on a linked LAPACK build.

## D7 — PREREG approved as-is / amended — **RESOLVED (re-approved over AMENDMENT-1, -2 and -3)**

Originally approved as-is: `registry/PREREG.md` reproduced KICKOFF §5 without amendment,
R1–R5 and the not-claimed list verbatim, frozen on commit.

**Re-approved 2026-07-30 over three amendments.** R1–R5's text is still verbatim and
unrewritten in every case; each amendment is appended, not merged.

| Amendment | Rule | Class | Rationales |
|---|---|---|---|
| PREREG-AMENDMENT-1 | R3 | transcription-restoration | (a), (b), (c) |
| PREREG-AMENDMENT-2 | R4 | **pre-data-design** | (b), (c) — **(a) does not apply** |
| PREREG-AMENDMENT-3 | R2 | **pre-data-design** | (b), (c) — (a) checked and does not apply |

**AMENDMENT-1** makes `second_fdt_surrogate_floor` (warm/cold label permutation) decide R3's
branch in place of the bootstrap band. Admissible on all three grounds: the specification
always named the second-FDT surrogate — the mint threshold in the GATES.md constants table
is quoted against it — so the bootstrap was a transcription defect rather than a design
choice; no data had passed through R3; and the change is strictness-increasing.

**AMENDMENT-2** makes R4 two-sided and decides both arms against dropout movement on a
degree- and weight-marginal-preserving rewire of the Q graph. Admissible on **(b) and (c)
only**. Rationale (a) explicitly does not apply: nothing in the specification named a
null-rewire reference or a sensitivity arm, so there is nothing to restore, and claiming (a)
would misrepresent new design as a correction. That is what the `class` field records — a
design amendment carries more weight of judgement than a restoration, and its admissibility
rests entirely on the pre-data timing.

**AMENDMENT-3** makes R2 flag a gap iff its loop's cold floor exceeds q95 of a
leave-one-out pooled label-permutation null. Class determined by checking the drafting
history as authorized: KICKOFF §5's R2 specifies *no* flagging criterion at all, and the
bootstrap was present in the P0 scaffold commit and never changed — so there is nothing to
restore and (a) does not apply. Its rationale (c) is **calibration-restoring**, not
strictness-increasing: the bootstrap was punitive on noisy runs, and the correction runs in
both directions.

AMENDMENT-3 deviates from its authorized wording, which specified each loop's *own* null.
That is unsatisfiable — a k-slot loop has 2**k assignments and the all-cold one is the
observed floor, so no loop can exceed its own null; measured, 0 of 4 loops could ever flag.
The mandated positive control caught it, the deviation is **confirmed**, and the
per-loop-only specification is recorded in the amendment as the defect's source.

One repair was attempted inside the window and **rejected**: studentizing the pooled null
by each loop's own MAD inverted the planted-gap control — the real gap (floor 0.218) went
unflagged at −0.089 while a 5.5e-08 loop flagged at +4.573. A loop's floor and its null's
scale are the same quantity, so dividing one by the other divides out the signal. Raw
leave-one-out stands and the exchangeability limitation stays **open**.

All three amendments retain their superseded band as a reported diagnostic that decides
nothing, and all three keep a historical pinning test. Full records in
`registry/PREREG.md`; codebase-wide conformance in `reports/gate6-sweep.md`, where every
deciding site now conforms.

The authorization to amend expires when P3 ingestion begins, enforced by
`audit.check_amendment_window()` rather than remembered.

## D8 — lexicon import pins — **PARTIAL** (policy decided, two artifacts outstanding)

Required by LEXICON SPEC §3. Blocks `SEED.lock`, null cells vi/vii/ix at full coverage,
and null cell ix entirely.

| source | policy | artifact | digest |
|---|---|---|---|
| Mathlib | latest stable at fetch | `____` | `____` |
| nLab | current at fetch | `____` | `____` |
| WordNet | **3.1** | `____` | `____` |
| convention table | — | `seed/LEXICON/convention_table.json` | hashed under `seed/` |

- convention table: **APPROVED with additions** — 184 senses across 51 lemmas, 22 declared
  bridges of which 7 are `declared-none`
- importer script hash: computed, not decided (`engine/seed_lock.py:importer_script_hash`)

### Why "latest stable" is a policy and not a pin

Two of the three answers name a *fetch rule*: latest stable Mathlib, current nLab. Both
are perfectly good rules, and both are recorded as `mathlib_policy` and `nlab_policy` —
but neither is a pin, because each resolves to a different artifact next week. Rerunning
against "latest stable" a month from now reproduces a *procedure*, not a run. WordNet 3.1
is different: it is a fixed version, so it is taken as stated.

What actually pins an import is the **content digest of the dump that landed**, recorded
in `*_sha256`. The commit hash and scrape date sit beside it as provenance — they say
where the bytes came from; the digest says which bytes. `SEED.lock` carries all three, and
`cli.py verify` fails on drift in any of them.

So the decision is split rather than deferred. The policy is settled now; the digests get
recorded when the artifacts land:

```
python cli.py pin mathlib  --path <dump> --commit <sha>
python cli.py pin nlab     --path <scrape.json> --date <YYYY-MM-DD>
python cli.py pin wordnet  --path <dump.json> [--version 3.1]
```

Each records the path, the provenance label, and the digest, and refuses to overwrite an
existing pin once `SEED.lock` is written — changing a pin after the lock moves addresses,
which is plastic under gate 4 and needs a logged seed-morphism and a cold re-anneal, not a
CLI flag. D8 reaches `resolved` when all three digests are present; the policy fields alone
do not resolve it, and `cli.py status` will keep saying so.

Inventing a plausible commit hash to clear the blank would have been worse than leaving it
blank: the lock would look pinned and reproduce nothing.

### The convention table

The table is the one I could draft rather than ask for, and it is now approved with the
requested additions: `positive` split into `definite`/`semidefinite` as their own entries,
and `option`, `settlement`, `margin` added as double-sense entries whose bridges are
`declared-none` — recording that two senses share a name and nothing else, so that nobody
later infers a relation. Worth re-reading on any future edit: `compact` (the Bourbaki
bridge is written as a checkable Lean statement) and the three terms this project itself
overloads — `chart`, `fiber`, `kernel`.


---

## Summary

| Decision | Status | Blocks |
|---|---|---|
| D1 | RESOLVED (by fact) | — |
| D2 | RESOLVED (stated default) | — |
| D3 | **UNRESOLVED** | `SEED.lock`, P3 |
| D4 | PARTIAL (spend cap unresolved) | `SEED.lock`, P3 |
| D5 | **UNRESOLVED** | `SEED.lock`, P1 null cell (iii) |
| D6 | **UNRESOLVED** | `SEED.lock`, every kernel clamp |
| D7 | RESOLVED (re-approved over PREREG-AMENDMENT-1) | — |
| D8 | PARTIAL (policy set, 2 artifacts + 3 digests outstanding) | `SEED.lock`, null cells vi/vii/ix |
