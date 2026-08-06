# CONSTITUTION.md — common-ground: the airtight record

**NORMATIVE, SUPREME.** This document + `SPEC.md` are the object. Code serves them.

A violation of any OI is a **constitutional defect**: highest severity, preempts all lanes.

Structure: Part 0 = the machine. Part A = the OPERATOR INVARIANT REGISTRY, OI-1..OI-40, each
with its violation history and its enforcement. Part B = the faithfulness proof protocol —
how this document is provably checked, forever, without the operator brute-forcing.

---

## PART 0 — THE MACHINE (normative topology; ETS-generalized)

Components and typed ports. Nothing else exists; **a new port is a constitutional change.**

### 0.1 THE MACHINE DIAGRAM (normative — the auditor checks ports and flows against this)

```
                              OPERATOR
                     raw bytes │      ▲  grammar-gated English
                     (bias —   │      │  (citations, weld rule, [∅];
                      NEVER    │      │   translation free)
                      normal-  │      │
                      ized)    ▼      │
        ┌──────────────────────────────────────────────────────────┐
        │                    THE FIELD (the carrier)               │
        │                                                          │
        │   CHARTS (atlas)          scaffolds within charts        │
        │   ┌─────────┐ ┌────────┐  · apexes (operator-English)    │
        │   │ english │ │  lean  │  · Scaffold deps (lean/py/go)   │
        │   │  python │ │   go   │  · senses+relations (lexicon*)  │
        │   │ tabular │ │ conv.  │  cross-chart Correspondences    │
        │   │ medium° │ │lexicon*│  (same_claim·refines·instance)  │
        │   └─────────┘ └────────┘  °interface tier  *spec'd       │
        │                                                          │
        │   ONE GIBBS MEASURE  p ∝ e^(−βE)  over the whole atlas   │
        │   TWO WEIGHTINGS of it: FAST (tape) · SLOW (corpus)      │
        │   ONE settlement per bias: conditional measure,          │
        │   whole field — the lineup bounds ATTACHMENT ONLY        │
        └───────┬───────────────▲──────────────┬───────────▲───────┘
                │               │              │           │
        settled │        triples│        events│           │ reweight
        state + │        via ONE│              ▼           │ ONLY
        raw     │        INLET  │      ┌──────────────┐    │ (fast→0,
        question│        (extra-│      │   JOURNAL    │    │  slow→1)
                ▼        ction  │      │ (append-only │    │
        ┌──────────────┐ tier)  │      │  tape ledger:│    │
        │      LM      │        │      │  asks·arrows·│    │
        │ (peripheral  │        │      │  verdicts·   │    │
        │  I/O machine │        │      │  admissions, │    │
        │  — 2 ports,  │────────┘      │  era/model/  │    │
        │  pinned,     │ diagram in,   │  region tags)│    │
        │  stamped,    │ triples out   └──────┬───────┘    │
        │  swappable)  │                      │            │
        └──────┬───────┘                      ▼            │
               │                      ┌──────────────┐     │
               │ rendered             │  K (MZ       │─────┘
               ▼ answer               │  kernel):    │
           OPERATOR                   │  boundary    │
               │                      │  sites ·     │
               │ export               │  residual    │
               ▼                      │  streams ·   │
        T_{op→any-agent}              │  Hankel ∧    │
        (settled state as             │  conservative│
         portable preamble)           └──────────────┘

        THE WALK (controller — not on the data path):
        points LM.propose at regions; conditioned on the field
        (arrow neighbourhoods, residual flags, composition-implied)
        + coverage pressure ∝ unwalked-slot mass (self-extinguishing)
```

### 0.2 FLOW SUMMARY (one line per port)

```
OPERATOR  --raw bytes (bias)------------------------------------->  FIELD
OPERATOR  <--grammar-gated rendering (target chart)--------------   LM.render
FIELD (carrier + two measures)  --lineup diagram-->  LM.propose
LM.propose  --triples only-->  ONE INLET  --records-->  JOURNAL (the tape's ledger)
JOURNAL  <--events-->  FAST MEASURE (the tape)  |  SLOW MEASURE (the corpus weight)
K (MZ kernel) reads tape boundary vs settled; reweights ONLY (fast->0, slow->1)
WALK (controller) points LM.propose; conditioned on field + coverage(unwalked mass)
EXPORT = T_{operator->any-agent}: the settled state as portable preamble.
```

**ETS mapping (the generalized tape analogy, canonical):**

| ETS | here |
|---|---|
| bias | the operator's raw input — an external field term, never normalized, never an object |
| sampler | `LM.propose` — a peripheral I/O machine; pinned; identity-stamped per call |
| settlement | the field relaxing — ONE settlement, whole field, conditional measure |
| casting gate | K — Hankel ∧ conservative; three honest refusals to date |
| tape | journal + fast measure — auditioned material; born aging |
| speaker | `LM.render` — grammar-gated; translation free; lies inexpressible |

**THE GENERALIZATION:** ETS's tape is ephemeral; here the tape drains through K into a
durable corpus. ETS + memory = Mori–Zwanzig. The LM is one more I/O machine between corpus
and tape — two ports, swappable, never part of physics.

---

## PART A — THE OPERATOR INVARIANT REGISTRY (OI-1 .. OI-40)

Format: STATEMENT · VIOLATION HISTORY (what it cost when broken) · ENFORCEMENT
[E: site / C: control / P: process].

These are the operator's iterated demands. They are not guidelines. **Each was earned.**

### I. THE OBJECT IS DERIVED, NEVER COBBLED

**OI-1** Every mechanism derives from the category or the Gibbs measure; anything not
derivable is creep and is rejected. `[C: three-moves audit, planted creep=RED]`

**OI-2** The diagnostic protocol precedes debugging: object-or-morphism? has morphisms?
subgraph shape? which move? second mechanism? (Q1–Q5). *VIOLATED:* the picker, the retrieval
layer — built instead of asked. `[P + ledger]`

**OI-3** No second mechanism for a job that has one (Q5). *VIOLATED:* candidate-list loop
beside the sampler; two-tier lexical checker beside citations. Both deleted.
`[C: one-code-path AST controls]`

**OI-4** Constants are derived, swept, or confessed — never picked. Precedents:
aging-halving (scale-free), k/(k−1) (anchor-forced), coverage-by-unwalked-mass
(self-extinguishing). **OPEN:** β (confessed, audit ordered). `[C: constants sweep]`

**OI-5** Conditional language in rulings is a tell — "as long as X" either references a gate
(redundant) or nothing (hope). Constraints are controls, not clauses.
`[P: ruling review; auditor flags conditionals in normative text]`

### II. NOTHING LEXICAL, NOTHING SIMILAR, EVER

**OI-6** No similarity mechanism anywhere: no embeddings, no distance, no token overlap, no
fuzzy matching — in extraction, grouping, bridging, nomination, grading, or referees.
*VIOLATED 3× IN REFEREES:* acceptance guard measured verbosity; faithfulness checker was
bag-of-words; conversation verdicts by keyword intersection.
`[C: referee_sweep over ALL grading+compile+bridge modules; exemptions carry arguments, never names]`

**OI-7** No vocabulary judgments by modules: no stopword lists, no curated word sets.
Specificity is derived (character length of literal containment). *VIOLATED:* nominator v1
(bag) — refused by sweep AND independently wrong. `[C]`

**OI-8** Words are keys; senses are claims. Word-nodes would hard-code indiscriminate
equivalence. Lexical strata = senses + DECLARED relations only. `[SPEC I§9, C4]`

**OI-9** Metric invariance: model-fed metrics invariant to verbosity/repetition (dedupe to
distinct things named); solver-fed metrics invariant to schedule (measured across
settlements, never within a trace). *VIOLATED:* acceptance 97/2/6 swings tracked repetition;
Hankel read the solver's decay.
`[C: per-metric invariance assertions; a metric ships with its invariance or is not a guard]`

### III. CONSUME EXACTLY WHAT WAS DECLARED

**OI-10** Never pairs where a quotient was declared; never closure where a chain was
declared; never records where pairs are the unit. **THE GREAT REPAIR:** 96.7% of same_claim
was containment mis-kinded as identity; all-pairs fabricated 7,140 edges from 434
declarations; one fiber held 73% of coupling energy; regions were 95% one proposition; K's
support was 61/64 one thing. FIVE instances, one cause.
`[E: adjudicate.py, apex-star; C: pigeonhole, counting rule, k-independence, standing consumer sweep]`

**OI-11** Mis-kinding is made INEXPRESSIBLE where possible, not forbidden: `Scaffold` is a
separate class (cannot be stored as same_claim — no such field); `APEX_CHART` equals nothing.
**Impossibility-by-construction > prohibition-by-control.** `[E]`

**OI-12** Under-report over invent: unresolved references VOID, never guessed; a missing edge
is a gap, an invented edge is fabrication. Ambiguity is not resolved by proximity (that's
similarity in parser's clothes).
`[E: resolve-or-void everywhere; C: planted unresolved-but-kept = RED]`

**OI-13** Absence is data: declines recorded; unmeasured ≠ no; unmentioned never dies by
arithmetic; `[∅]` forms are citable and checked.
`[E: aging halving, absence grammar; C: absence-claim verification]`

### IV. THE LM IS A PERIPHERAL, NEVER A MECHANISM

**OI-14** The medium is queried, never trusted: extraction tier, resolve-or-void, gated,
aging, disposable, swappable. `[E: inlet; warrant tiers]`

**OI-15** Model identity stamped on every call and every arrow; never route blind.
*VIOLATED:* `openrouter/auto` served lite 448/465 calls — repetition 35×, the forest-topology
false conclusion, 10-minute latencies.
`[E: pin + usage stamping + header; C: env-override announces itself]`

**OI-16** Output grammar is the trusted kernel: triples-only in extraction; citations +
weld-rule + absence-forms in rendering; everything else silently unparsed. No self-reported
confidence. **Grammar over instruction** — every prose rule that mattered was ignored by every
model until compiled into the format.
`[E: parsers; C: prose+one-triple yields one arrow; AST two-regex assertion]`

**OI-17** Region granularity = the medium's measured co-relaxation range (acceptance guard
band), not a knob; the lineup bounds ATTACHMENT ONLY, never the answer's universe.
`[C: battery; clean-state item 4]`

**OI-18** Prompts contain wire format + grammar + state + NOTHING. No personas, no style, no
editorial instructions. *VIOLATED:* the accreted style codex (voice preference, scope
phrasing, "I read your question as") — stripped.
`[C: enumerable-prompt control, planted style instruction = RED]`

### V. THE BIAS IS RAW; ONLY THE FIELD IS FORMAL

**OI-19** Operator input is an external field term: never normalized, never addressed as a
stage, never objectified into the category. ν/hash consulted ONLY to detect incidental
declared coincidences (whole-input, contiguous-term) that strengthen coupling. *WAS VIOLATED,
NOW MECHANIZED:* the bias object went out as its ν — case folded, whitespace collapsed,
terminal punctuation stripped, wearing the `english` chart tag — so the medium answered the
addresser's paraphrase of the question. `Member.surface` now carries the typed bytes and
`Member.wire` is the one accessor the renderer reads; ν remains the address and nothing else.
`[C: tests/test_bias_bytes.py — the typed bytes are extracted from the recorded wire and
compared; four planted normalizations (lowercase, whitespace, terminal punctuation, the full ν
pipeline) each = RED]`

**OI-20** Identity ≠ attachment; they never share a rule. Identity exact (gate 1); attachment
proposed. *VIOLATED:* exact-landing-required made novel input an isolated object — THE
amendment. `[E: perturb path; C: battery no-silent-zero]`

**OI-42** **THE INTERACTION SURFACE IS TWO BINARY COORDINATES PLUS ONE ARROW, and it is
CLOSED.** Objecthood (AUTHORSHIP or nothing — assert/brainstorm) and persistence (discard or
keep — retain) are independent and binary, so the 2×2 is the product of two two-element sets:
forced and complete, no fifth state constructible. The one constructible arrow is the
authorship pullback (claim), which is a VERB and not a state, always retains, and invokes the
EXISTING perturb-retain write-point rather than adding one. *VIOLATED BY OMISSION:* the mode
shipped in code, tests and UI with zero mentions in either normative document — built
machinery, unwritten law, which is B5's definition of unconstitutional.
`[E: engine/mode.py, engine/claim.py, SPEC.md Part I §10; C: tests/test_claim.py:TheTwoByTwoIsForcedAndComplete, tests/test_mode.py:AllFourCellsAreMeaningful]`

**OI-43** **WHEN THE MACHINE READS RATHER THAN IS TOLD, THE CONSERVATIVE DIRECTION INVERTS.**
An unknown TOLD mode defaults to ASSERT, because defaulting the other way would strip warrant
from something the operator meant to stand behind. An unread or ambiguous ACT defaults to
EXPLORE/KEEP-NOTHING, because a misread that invents a claim confers authorship nobody
asserted. **When unsure whether you claimed, assume you didn't.** The two defaults point
opposite ways on purpose, and each is the safe direction for its own failure mode. Every
reading is DISPLAYED and correctable; a correction re-stamps with an era trail rather than
overwriting, so a misread can be seen after the fact.
`[E: engine/posture.py; C: tests/test_posture.py:TheConservativeDirectionINVERTS, tests/test_posture.py:ACorrectionRestampsWithAnERATRAIL]`

**OI-21** The ETS feel is the acceptance bar: no silence without a consulted-and-declined
trace; response graded with bias sharpness; stateful; no phrasing cliffs.
`[C: the battery — no_silent_zero/graded/no_cliff/stateful/one_path]`

### VI. WIRE-TRUTH OVER CODE-TRUTH

**OI-22** Nothing is landed until verified on the SERVED artifact. *VIOLATED 7 DISTINCT WAYS:*
stale HTML skin; missing commit stamp; env var beating the code pin; curl-tolerant stream
hanging browsers; gitignore blocking the seed path (correct code never executed); snapshot
drift behind local; sim-reported-as-landed.
`[E: header self-identifies commit+model+corpus provenance+material age+βs; C: deploy self-audit runs battery before LANDED]`

**OI-23** Controls execute the runtime, never inspect source as proxy. *"A control simpler
than the thing it stands for"* — 3 instances (substring checks over `getsource` passed while
`SNAPSHOT_PATH` was never imported). `[C: control-liveness sweep]`

**OI-24** "Success on the empty set" is a defect class: operations assert non-empty inputs; an
all-zero census from an empty adjudication = RED. *WAS VIOLATED, NOW MECHANIZED:* demotion
applied at snapshot-build (zero arrows) reported clean success. `engine/nonempty` is the shared
vocabulary — `require()` where an empty population is a caller bug, `census()` where it is a
real state, and `clean()`, the only sanctioned way to ask a census whether it found nothing,
which REFUSES to answer for a census over nothing. Every census carries its own population.
At the finest grain a `Verdict` now separates read-and-kept from could-not-be-read, so an
unreadable pair is never counted as a surviving identity.
`[C: tests/test_nonempty.py — the incident's literal census is rebuilt by hand and shown
indistinguishable from a clean one; every adjudication site refuses an empty population and
answers a real one]`

**OI-25** Silence never means unknown: long-running processes announce phases; a progress
channel that can hang its subject is worse than none.
`[E: phase announcements; elapsed counters]`

**OI-26** A caution must be re-examined when the defect it guarded against is fixed, or the
caution becomes its own defect. *VIOLATED:* "least trusted" label outlived the faithfulness
gate; answer-first regressed. `[P + ledger law]`

### VII. MEASUREMENT DISCIPLINE

**OI-27** Minimum-n: no rate stated as a finding below declared n (stability to ~10n).
*VIOLATED TWICE IN ONE SESSION* (n=24 then n=2,872 — both flipped at 10×); the withdrawal was
as premature as the claim. `[C: minimum-n rule; readings labeled readings]`

**OI-28** Reasoning designs; measurement tripwires. No test-after-test iteration: one
properly-powered A/B per design generation; planted-nonsense and known-good controls prove the
harness can fail and pass. `[P; validation harness shape]`

**OI-29** Pre-register before running: fixture outcomes written down BOTH WAYS before the
re-run so numbers can't be read to suit. `[E: RETEST fixtures; P]`

**OI-30** A known cause must not absorb an unknown one: deltas decomposed by cause.
`[P: the lean-delta separation precedent]`

**OI-31** Every empirical claim carries provenance (era, model, region, prompt hash);
quarantine over deletion — SIX applications (lite arrows, keyword verdicts, containment leads,
closure-only pairs, per-medium glosses, bad-run arrows); withdrawn findings ledgered BESIDE
their originals. `[E: tags; C: era rules]`

### VIII. THE TAPE IS NOT A SECOND CORPUS

**OI-32** One inlet; all proposers equal; warrant conferred only at the gate; priors are
energy, never oracles. `[E: inlet; C: planted second pipe = RED]`

**OI-33** Retention is born aging; promotion is reweighting through K only; the closed
write-point set (retain, walk-arrow, aging-decay, promote) admits nothing else.
`[E: mz.py, aging.py; C: any other write-point raises]`

**OI-34** K refuses rubber stamps: no default floors, no solver signatures, no mode
measurements — three honest refusals are its record and its character. Armed-and-silent is an
acceptable terminal state.
`[E: zero-floor refusal pinned; C: settled-refuses/contested-passes/solver-FAILS]`

### IX. DATA SOVEREIGNTY

**OI-35** The operator's corpus never enters any git tree, any image, any public object. Data
moves by data channels that appear and disappear (token-gated, 404-not-403, fixed writable
names, digest-verified). *VIOLATED-AND-CAUGHT:* the 25MB backup pickle swept by `git add -A` —
the pre-push gate refused it.
`[E: pre-push gate; C: no tracked file >4KB begins with a pickle header]`

**OI-36** Reflexivity firewall: common-ground's own material stays out of the corpus.
`engine/reflexivity` audits on two DECLARED arms and never on resemblance — provenance (this
repo's bucket, or a path this repo tracks) and exact ν (byte-identical to a line of this repo's
seed documents, which is gate 1's identity rule, not a similarity). The blind spot travels on
the record: material re-labelled, re-pathed AND paraphrased is undetectable here, because the
only mechanism that would catch it is the one this engine refuses everywhere else and refuses
here most of all. Standing: 0 matches across 80,566 slots, re-checked every run.
`[C: tests/test_reflexivity.py — planted contamination on each arm is caught unconditionally;
the real corpus is audited when present and SKIPPED LOUDLY when absent, never passed]`

**OI-37** Keys: exposure is tracked as BLOCKED-on-operator, never forgotten, never committed.
The first two clauses are ledger discipline; the third is a fact about bytes, and is checked.
Two arms: SHAPE (generic key patterns — has false negatives by construction, and says so) and
LITERAL (the actual values in the operator's env files — no pattern guessing, so it cannot
false-positive). Both the tree AND the whole reachable history are searched, because a key
committed and then deleted is still published — "not in HEAD" is not the property, and the
remedy for a hit is ROTATION, which is a BLOCKED-on-operator row.
`[C: tests/test_key_exposure.py — the scan runs on planted blobs so a real key in a TEST file
is still caught; the literal arm SKIPS LOUDLY where no key material exists rather than passing
on an empty search]`

### X. THE OPERATOR'S POSITION

**OI-38** The operator's "fucked" preempts everything until wire-verified fixed. All lanes
concurrent; his findings jump every queue. `[P: concurrency order]`

**OI-39** Anything the operator re-explains twice becomes a named fixture the same day; the
goal metric is operator-caught regressions/week → ZERO via the auditor. **His nose built this
registry; the registry retires his nose.** `[P+C]`

**OI-41** **NO WARRANT LIFT EXCEPT K-MEASUREMENT OR OPERATOR-AUTHORSHIP.** The tier poset has
exactly two lift mechanisms: K promotes by measurement, authorship enters by assertion. An
"accept" or "approve" control would be a THIRD arrow up the poset — warrant increasing by
approval without authorship — and it does not exist in the diagram. **Its absence is
constitutional, not an omission.** Any UI or API surface implying a third lift = RED. The
three fates of anything on the tape are each an existing arrow and nothing new: IGNORED (the
aging endomorphism contracts it toward zero), EARNING (K measures its residual and reweights
iff it qualifies), CLAIMED (the authorship pullback — a new object, same surface, operator
warrant, `claimed_from` provenance).
`[E: engine/claim.py, engine/mz.py; C: tests/test_claim.py:ThereIsNoThirdLift]`

**OI-40** Honest-thin beats fluent-fake, always: smaller true numbers over impressive
fabrications; *"the corpus grows only by what survives the physics."* The whole project in one
line. `[everything above]`

---

## PART B — THE FAITHFULNESS PROOF PROTOCOL

**B1. REGISTRY→CONTROL TABLE.** Machine-readable `seed/OI_REGISTRY.json`: every OI-n maps to
its enforcement sites and control names. An OI with enforcement `[P]` only is flagged **WEAK**
and listed for mechanization. **The auditor FAILS its run if any OI-n lacks a resolvable
entry.**

**B2. CONTROL LIVENESS.** Every `[C:]` control must FIRE on its planted defect in the liveness
sweep (a control that must fire and doesn't = RED). Silence never reads as pass (OI-23/24
applied to the registry itself).

**B3. THE AUDITOR RUNS THE REGISTRY.** Per-deploy + daily, read-only, Sonnet-tier, against the
SERVED wire: OI table resolution, control liveness, the six-prompt battery with pre-registered
shapes, SPEC/CONSTITUTION conformance diff (every `[E:]` site exists at its symbol; drift =
defect in code or doc — **never silently reconciled**), prompt-content enumeration, header
self-identification. Findings filed with artifact evidence. Main session disposes.

**B4. AMENDMENT RULE.** This document changes ONLY by operator ruling, recorded as a dated
amendment with the superseded text retained (the withdrawal discipline applied to the
constitution itself). **CC may propose; never merge.**

**B5. DRIFT DEFINITION.** Any behavior, prompt sentence, constant, edge type, or port not
traceable to `SPEC.md` or an OI-n is **UNCONSTITUTIONAL BY DEFAULT** — the burden of proof is
on the code, never on the operator's memory.

---

## AMENDMENTS

*(none yet — B4 applies: operator ruling only, superseded text retained)*
