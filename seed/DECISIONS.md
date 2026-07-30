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

## D2 — charts — **RESOLVED (stated default)**

`{english, lean}`. The code chart is deferred to v0.5, per the default stated in KICKOFF
§0 D2 ("code chart deferred to v0.5 unless overridden"). No override was given.

## D3 — corpus manifest — **UNRESOLVED**

Required before P3 (full ingestion). Blocks `SEED.lock`.

- `claude_export`: path `____`
- `lean_corpus`: directory dump of Aristotle-held Lean sources, path `____`
  (dump preferred over live MCP; pinned files hash cleanly — KICKOFF §7.5 forbids live
  pulls during a run)
- `repos`: `[certified-positivity, ____]`
- `EXCLUSIONS` (privacy pass, mandatory, precedes ingestion): `____`

These are paths and a privacy policy on someone else's data. They cannot be defaulted or
guessed; a wrong guess here silently changes what the run is about, and the EXCLUSIONS
list is a privacy control that must be authored deliberately, not inferred.

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

## D7 — PREREG approved as-is / amended — **RESOLVED (as-is)**

Approved as-is. `registry/PREREG.md` reproduces KICKOFF §5 without amendment; R1–R5 and the
not-claimed list are verbatim. It is frozen on commit.

## D8 — lexicon import pins — **UNRESOLVED**

Required by LEXICON SPEC §3. Blocks `SEED.lock`, null cells vi/vii/ix at full coverage,
and null cell ix entirely.

- Mathlib dump path + **commit hash**: `____`
- nLab alias/redirect scrape path + **scrape date**: `____`
- WordNet-grade dump path + **version**: `____`
- convention table: **DRAFTED, pending approval** — `seed/LEXICON/convention_table.json`,
  176 senses across 46 lemmas, 17 declared bridges
- importer script hash: computed, not decided (`engine/seed_lock.py:importer_script_hash`)

Each of the first three is a *pinned artifact*, not a live source. KICKOFF §7.5 forbids a
live pull during a run, and the reason is mechanical rather than procedural: an unpinned
source cannot hash cleanly, so a registry built from one is not reproducible and the seed
hash keying every verdict would be meaningless.

The convention table is the one I could draft rather than ask for. It needs your approval,
not just your paths — it makes ~176 substantive claims about which senses of which words
are distinct, and three of its bridges are `declared-none`, recording that two senses share
a name and nothing else so that nobody later infers a relation. Review at least: `compact`
(the Bourbaki bridge is written as a checkable Lean statement), `positive` (strict vs
non-strict, which the certified-positivity corpus will lean on hardest), and the three
terms this project itself overloads — `chart`, `fiber`, `kernel`.


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
| D7 | RESOLVED (as-is) | — |
| D8 | **UNRESOLVED** (convention table drafted) | `SEED.lock`, null cells vi/vii/ix |
