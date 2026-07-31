# common-ground

Minimal-faithful reconciliation engine, v0. Built to the KICKOFF brief: seven invariants
(addressing, fibers, certified descent, cast/settle split, warrant tiers, paired loop-side
meter, nulls-before-floors), mint tape logged, **mint OFF**.

Prime directive: *no floor is read before its null cells pass; no seed change after
SEED.lock without a logged seed-morphism event and cold re-anneal.*

---

## Current state

**P0 scaffold: complete. P0 seed assembly: blocked. P1–P4: gated.**

`SEED.lock` has not been written, because D3, D5, D6, D4's spend cap and two of D8's three
artifacts are outstanding, and KICKOFF §7.1 says to refuse past P0 with any blank. That
refusal is mechanical: `engine/seed_lock.py:build()` raises rather than emitting a lock.

```
$ python cli.py status
D1 resolved     D2 resolved     D3 unresolved   D4 partial
D5 unresolved   D6 unresolved   D7 resolved*    D8 partial
D2 now: english, lean, tabular (charts are a seed manifest)
                                * re-approved over PREREG-AMENDMENT-1, -2 and -3
```

The null battery runs and reports honestly at the provisional seed hash. Every cell carries
a **positive control** — an input engineered to break the property that cell tests — and a
cell whose control does not fire is reported `ctl:DEAD` and fails the battery outright,
whatever it said about the real input. A test that cannot fail is not evidence:

| Cell | Status (all controls live) |
|---|---|
| i. normalizer idempotence | **PASS** — `nu(nu(x)) == nu(x)`, 1010 fuzzed samples across both charts |
| ii. paraphrase suite | **PASS** — 10 known-same pairs collided, 10 known-distinct separated |
| iii. empty-corpus floor | **BLOCKED** — D5 unresolved, no pre-minted entries to check for self-contest |
| iv. single-doc null | **BLOCKED** — D3 unresolved, no held-out document |
| v. duplicate-source null | **BLOCKED** — D3 unresolved, no corpus to duplicate |
| vi. hub-coverage | **PASS** — all 184 senses carry an English face (0 rendered, 184 authored) |
| vii. shadow check | **PASS** — 38 probes; technical contexts resolve technically, general generally |
| viii. no-clamp grep | **PASS** — no display attribute reachable from 8 F-path modules or 2 F-feeding functions |
| ix. binding sanity | **BLOCKED** — no Mathlib dump has landed, so nothing to round-trip |

`BLOCKED` is not green, so PREREG R1 applies and the run is VOID — but it is recorded as
"never tested", which is a different finding from "tested and failed" and is reported as
such. See `reports/P1-null-battery.md`.

## What is needed to proceed

| Decision | Needed for | Why it cannot be defaulted |
|---|---|---|
| **D3** corpus manifest + EXCLUSIONS | P2, P3, null cells iv & v | Paths to someone else's data, plus a privacy policy. A guessed path silently changes what the run is about; a defaulted exclusion list is a privacy incident. `adapters/claude_export.py` raises on `exclusions=None` rather than treating "unset" as "nothing excluded". |
| **D4** spend cap | P3 live extraction | An unset cap is not an unlimited cap. `AnthropicExtractor` refuses to construct without one. |
| **D5** pre-minted files | `SEED.lock`, null cell iii, PREREG R2 | `BVALUED-AGREED.md`, `STATEMENTS.md`, `REGISTRY.md` are not in this repo. `STATEMENTS.md` carries the "what we do NOT claim" list that R2 turns into the rediscovery test. |
| **D6** Lean + Python versions | `SEED.lock`, every kernel clamp | Gate 3 makes kernel-accept *under the pinned toolchain* the only proof-side grounding warrant. Read the Lean version from `certified-positivity`'s lake-manifest; do not assume it. |
| **D8** lexicon artifacts | `SEED.lock`, null cells vi/vii/ix | **Policy is set**: latest stable Mathlib, current nLab, WordNet 3.1; the convention table is approved (184 senses, 51 lemmas, 22 bridges). What is missing is the artifacts. "Latest stable" names a fetch rule, not an input — it resolves to different bytes next week — so the pin is the **content digest of the dump that landed**, recorded by `cli.py pin <source> --path ...`. A live pull during a run cannot hash cleanly at all (KICKOFF §7.5). |

D1, D2, and D7 are resolved — D1 from the repository as it exists, D2 and D7 from the
defaults the brief itself states. Details and reasoning in `seed/DECISIONS.md`.

---

## The seven gates, and where each is enforced

`seed/GATES.md` holds the constitutional text. Sentences 1–5 are KICKOFF §2 verbatim;
sentences 6 and 7 were added by operator authorization and are marked as such in the file.
Each is enforced structurally, not by convention:

1. **Addressing** — `normalize.slot_id(nu, type)` takes exactly two arguments and reads no
   engine state. `nu` is chart-indexed and emits the chart as a control-character tag
   *inside* its own output, so the chart rides along in `nu(surface)` and the hash
   signature stays `hash(nu(surface), type)` verbatim.
2. **Priors are energy** — lexicon and equivalence priors appear only as terms in
   `energy.FreeEnergy`. The clamp set is a separate argument. There is no code path from a
   prior to a clamp.
3. **Only top tiers ground** — `Warrant.clamp_eligible` is a derived property on a frozen
   dataclass, `Clamp.__post_init__` refuses a non-eligible warrant, and `Extractor.extract`
   stamps `EXTRACTION` on everything it emits with no subclass override.
4. **Address moves are plastic** — `seed_lock.verify()` recomputes every seed hash; CI runs
   it on every push and fails on drift.
5. **Nulls before floors** — `meter.read_floor()` requires a `NullBatteryReport` that
   passed *on the same seed hash*, and it is the only function that returns a floor.
6. **Nulls, not resamples** — every statistical verdict is decided against a null built
   under the no-effect hypothesis, never against a resample of the observation. Three
   layers: `audit.floor_verdict` decides R3 by warm/cold label permutation and
   `audit.prior_insensitivity` decides both of R4's arms against a degree- and
   weight-marginal-preserving rewire of the Q graph, and `audit.ground_truth_rediscovery`
   flags R2's gaps against a pooled label-permutation null; `run_battery` fails outright if
   any cell's positive control is dead; and `static_checks.check_gate6_classification` fails
   CI on any band in `engine/` not classified with its reference distribution and role. The
   third layer exists because the first three defects were found by hand — see
   `reports/gate6-sweep.md`, which found a fourth (R2) the moment it was written. **Every
   deciding site now conforms**; the three that do not are diagnostics, kept so the
   amendments stay auditable.
7. **Generative keys are content-and-seed only** — identity may label evidence, never
   generate it. `static_checks.check_generative_keys` classifies every random stream,
   address, and dedup key in `engine/` and fails on any that is unclassified or keyed on an
   artifact's label. Written after extraction was found seeded on `doc_id`, which made the
   same text read differently under a second name.

Try to violate them: `tests/test_gates.py` does, including smuggling a downgraded warrant
past `Clamp`'s constructor via `object.__setattr__` to check `settle()` still catches it.
`tests/test_controls.py` covers gate 6 from both sides — the live controls, and the
superseded R3 computation kept as a historical pin.

## Is the engine the theory?

The gates say what the engine may not do. `FAITHFULNESS.md` says what it **is**: every
theory object, its code site, and a control that fails if that site stops implementing it —
enforced by `make faithfulness`, which fails on any unmapped or uncontrolled row.

Three simplifications are deliberate and cite the ruling that permits them; the largest is
that **inter-chart correspondence is pairwise-collapsed** — `QEdge` has two endpoints and
there is no k-ary factor type, so no ternary-correspondence claim may be advanced from this
build.

The audit opened two gaps and both were ruled implementation defects and repaired.
**Tree-null**: holonomy is now defined only on verified cycles, backtracking became a
per-edge measured-shadow channel, and open walks raise instead of being silently measured —
which produced a free calibration output. **Extraction determinism**: seeding moved from
`doc_id` to the content hash, so a relabelled copy now extracts bit-identically and cell (v)
is green at exactly zero. That second repair became gate 7.

`gaps_before_p3()` is empty. Every remaining deviation is deliberate and cites its ruling.

## The lexicon layer — hub of faces, not hub of truth

`seed/LEXICON/SPEC.md` is frozen alongside the gates. One registry, per-chart faces, with
both halves of the hub invariant enforced separately:

**Every sense has an English face.** No entry may exist only in a formal chart. A bare
Mathlib name gets one from the R-map (`engine/rmap.py`), marked `warrant="rendered"` and
counted by cell (vi) as a quality metric rather than a defect.

**Warrant never flows through it.** This is a type boundary, not a convention.
`SenseCore` — the F-visible projection — carries `english_slot` (the *hash*, which is the
address) and **has no `english_face` field at all**. The strings live on `SenseDisplay`,
which nothing on an F path can reach. Cell (viii) is an AST check enforcing it, and it is
never blocked because it reads the engine's own source.

Sense selection is by typed context — frames and slot neighbourhood — deliberately **not**
by gloss text, which would route authority back through the hub. When context does not
decide, `select_sense` returns an honest fiber including `abstain`; a coin flip there is a
seed bug. Merging is refused at import time: it is plastic and mint-gated, and mint is OFF.

Imports run in the fixed order Mathlib → convention → nLab → pre-minted → WordNet, and
`import_all` refuses any other sequence. An unresolved pin reports BLOCKED rather than
faking a result. The registry serializes canonically, so a re-run at the same pins is
byte-identical — tested, since SPEC §3 says any diff is a bug.

### Three bugs cell (vii) caught

Writing the shadow check found three real defects in the layer it was checking:

1. The importer hardcoded `source="convention"`, ignoring each sense's declared tier — so
   no sense was ever classified as general English and shadowing detection could not fire.
2. `candidates_for` scored a sense that merely *mentions* a lemma ("degree of a field
   extension") equally against one whose lemma *is* the query ("field").
3. Cue matching was substring-based: `"norm"` fired the `analysis` frame inside the word
   *"normal"*, and bare `"field"`/`"ring"`/`"measure"` were cues for their own technical
   frames — the ambiguous word voting for its own disambiguation.

A fourth surfaced while fixing the third: word boundaries strict enough to keep `"norm"`
out of `"normal"` also kept `"closed set"` out of `"closed sets"`, so the matcher now
allows exactly one trailing `s`. And `"identity element"` had to come out of the `unital`
cue list — it appears in the rng probe too ("*not required to have* a multiplicative
identity element"), and a phrase-cue table cannot see negation.

## Design decisions worth knowing

**Pure stdlib, no numpy.** A verdict keyed to a seed hash is not reproducible if that hash
depends on a linked LAPACK build. The engine ships its own one-sided Jacobi SVD, a
counter-based SHA-256 RNG, and simplex arithmetic. CI asserts no third-party import
reaches `engine/` or `adapters/`.

**F is convex, and the certificate is a real check.** Linear evidence and prior terms, a
PSD quadratic coupling, and convex negative entropy. Mirror descent under the entropic map
converges, so the monotone F-trace certificate tests the implementation rather than
expressing a hope about the objective. `eta = 0.1` is the nominal step; a logged halving
safeguard keeps descent monotone and counts every halving into the run log. A step that
cannot be made descending stamps `violated` — it never silently ascends.

**Holonomy vanishes on agreement.** Transport along a Q edge is a relaxation toward the far
end's settled state. Compose around a loop and compare to the start: identically zero when
every state on the loop agrees, positive and path-ordered when they do not. Verified in
both directions in `tests/test_engine.py`.

**The warm arm reports what it actually was.** With state retained from P3 it is the real
cross-phase arm; without it, it resumes from the anneal's first rung — a genuinely
different trajectory. What it must never do is resume from the cold arm's own answer, which
would report `path_debt = 0` as a tautology. Every measurement carries `warm_source`.

**Re-ingestion is idempotent by construction.** Evidence is keyed on the document's
*content* hash, not its id or source label, so re-ingesting one corpus under a second
provenance adds nothing (null cell v) while two genuinely distinct documents asserting the
same claim still corroborate. See `energy.evidential_identity`.

**Shadow is declared zero.** `seed/shadow.json` declares no closure defect between charts.
Declaring one larger than the truth would deflate the floor and could manufacture a null
result, so zero is the conservative setting and raising it is plastic under gate 4,
requiring a justification string.

**Casting is withheld.** `cast.cast()` raises unless the caller passes `allow=True`, which
`cast.may_cast()` grants only for blocks whose fiber contains a kernel clamp — KICKOFF §3,
P3. The withholding is a property of the code, not of the operator remembering.

## Layout

```
seed/          GATES.md, TYPES.md, DECISIONS.{md,json}, CONSTANTS.json,
               paraphrase_suite.json, shadow.json, PROMPTS/,
               LEXICON/{SPEC.md, convention_table.json, shadow_probes.json}  → SEED.lock
engine/        normalize · extract · energy · settle · cast · meter · nulls · mint_tape
               blocks · pipeline · audit · seed_lock · logio · linalg · hashing
               lexicon · rmap · static_checks
adapters/      claude_export · lean_corpus · repo_docs · lexicon_imports
registry/      PREREG.md (frozen, D7 as-is) · REGISTRY.jsonl (append-only)
runs/          JSONL logs; every record carries seed_hash
reports/       one-pagers
```

## Usage

```bash
make status          # decisions, lock state, phase readiness
make test            # 280 tests, stdlib only
make demo            # synthetic end-to-end run; reads no corpus, writes no log
make nulls           # P1 null battery + positive controls at the current seed hash
make lock            # refuses while any decision is blank
make verify          # gate-4 tripwire
make gate6           # statistical-band conformance sweep (GATES.md sentence 6)
make gate7           # generative-key sweep (GATES.md sentence 7)
make faithfulness    # theory object -> code site -> control audit
make probes          # commitment -> probe -> status battery + chart audit

python cli.py register P2 --note "..."           # BEFORE running a phase (KICKOFF §7.2)
python cli.py pin mathlib --path <dump> \
                          --commit <sha>         # record a landed D8 artifact's digest
```

## Session order

Per KICKOFF §7.3, P0–P2 belong to one session and P3–P4 to a fresh session from a clean
checkout — *that checkout is the cold arm*. This repository is the P0–P2 session's output.
P3 and P4 must not be run from it.
