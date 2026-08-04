# FAITHFULNESS — theory object → code site → control

`seed/GATES.md` says what the engine may not do. This says what the engine **is**: every
object the theory names, the place it lives in code, and a control that fails if that place
stops implementing it.

Same pattern as the gate-6 sweep, for the same reason. A mapping written in prose goes
stale the first time someone edits the engine, so this one is a check:
`engine/faithfulness.py:check_faithfulness` fails on any **unmapped** row (no code site, or
one that no longer resolves), any **uncontrolled** row (no positive control, or one naming a
test that does not exist), and any **unclassified deviation**.

A deviation is not automatically a defect — this is a *minimal*-faithful build and several
simplifications are deliberate. An **unrecorded** deviation is the problem, because it is
indistinguishable from a mistake, and after P3 the difference is unrecoverable.

`make faithfulness` · 13 rows · 4 deliberate simplifications · **0 open gaps**

## The table

| Theory object | Code site | Control asserts | Deviation |
|---|---|---|---|
| **evidence factor** | `engine/energy.py:evidence_from_deltas` | a slot with no evidence settles uniform; adding supporting deltas moves mass onto the supported value, weighted by confidence x warrant | — |
| **intra-chart sheaf (gluing within one chart)** | `engine/blocks.py:edges_from_fibers` | two same-chart slots joined by a DECLARED-correspondence fiber edge (membership is the exact declared relation, never token similarity) settle closer together than with the edge dropped; the edge carries the DECLARED weight, not a graded score | by design |
| **inter-chart correspondence** | `engine/types.py:QEdge` | a cross-chart edge — a DECLARED typed translation, never inferred from similarity — transports; and a 3-cycle of pairwise edges is shown NOT to represent a genuine ternary factor | by design |
| **Q-priors (equivalence prior as energy)** | `engine/energy.py:FreeEnergy` | a prior weight raised far beyond any corpus evidence still leaves mass off the vertex — the prior tilts and never fixes, which is the difference between an energy and a clamp | — |
| **clamps (grounding)** | `engine/types.py:Clamp` | a clamped slot stays at its value through settling, and constructing a Clamp from an EXTRACTION warrant raises GateViolation | — |
| **type-consistency** | `engine/normalize.py:slot_id` | one surface read as `assert` and as `define` produces two distinct slots that never share a block, so a type mismatch cannot become a contest | by design |
| **blocks as connected components of Q** | `engine/blocks.py:build_blocks` | two contests sharing no Q edge land in two blocks, and perturbing one block's evidence moves the other block's settled state by exactly zero — measured, not asserted | — |
| **descent certificate** | `engine/settle.py:settle` | an objective rigged to rise on every step exhausts the halving safeguard and stamps the block `violated` — the certificate is a real check on the implementation, not a label | — |
| **tree-null (all tree contest is path-debt)** | `engine/meter.py:verify_cycle` | a cycle-free corpus settles to cold floor exactly 0.0 and is flagged `no_cycle_support`; a backtrack walk and an open walk both raise `OpenWalkError`; a restatement fiber yields the genuine triangle Eng_1 -> Lean -> Eng_2 -> Eng_1 | — |
| **measured shadow (per-edge closure defect)** | `engine/meter.py:measured_shadow` | every Q edge contributes a calibration row with `eps_measured`, the seed's `declared`, and their drift; `translator_drift()` names only cross-chart edges; and the floor still subtracts the DECLARED shadow, never the measured one | — |
| **extraction determinism (re-ingestion adds no evidence)** | `engine/extract.py:DeterministicExtractor` | identical text under a new `doc_id` AND a new source label yields a bit-identical set of evidential identities; null cell (v) is green on the standard fixture with residue exactly 0.0; and the live extractor's prompt carries a content hash rather than a doc_id | — |
| **generative keys are content-and-seed only (gate 7)** | `engine/static_checks.py:check_generative_keys` | every `DRNG(...)` site in `engine/` is classified in `GENERATIVE_KEY_SITES`, no row is `identity`-keyed, every `design` row cites the ruling that requires it, and an unclassified new stream fails the check | by design |
| **planted-cycle (frustration is real and persistent)** | `engine/meter.py:measure` | a triangle en1 -> lean -> en2 -> en1 with en1 clamped T and en2 clamped F yields holonomy 0.3224, twenty times the 0.0166 of the same topology with compatible ends, and re-anneal reproduces it exactly | — |

## The six factor families

Two things are worth stating before the detail, because the table's tidy rows could
otherwise imply more than is there.

**F has three terms, not six.** The free energy is

```
F(p) = sum_i <p_i, e_i>                          evidence
     + lambda2 * sum_i <p_i, r_i>                lexicon prior
     + (lambda/2) * sum_uv w_uv ||p_u - p_v||^2  equivalence prior (Q coupling)
     - (1/beta) * sum_i H(p_i)                   entropic regularizer
```

The six families do not map one-to-one onto those terms. *Evidence* and *Q-priors* are
terms. *Intra-chart sheaf* and *inter-chart correspondence* are two **sources** of edges
that enter the same coupling term, distinguished only by `QEdge.crosses_charts` — which
changes the fiber threshold used to build them and whether shadow is subtracted at the
meter, not the energy they contribute. *Clamps* are not an energy term at all but a
separate constraint set. *Type-consistency* is not in F either; it is in the address.

That is the honest shape, and the deviation fields below say so per row rather than
letting six table rows imply six factors.

### Inter-chart correspondence is PAIRWISE-COLLAPSED

Stated explicitly because the question was asked directly. `QEdge` has exactly two
endpoints and there is **no ternary or k-ary factor type anywhere in the engine**. A
three-way correspondence can only be written as a triangle of pairwise edges.

That is strictly weaker, and the control proves it rather than asserting it. Take the joint
condition *exactly one of these three restatements is T*. It has three satisfying
assignments, and under it **every pair is still undetermined** — for any two of the three
slots, more than one combination of values survives. A constraint whose every pairwise
projection is uninformative cannot be represented by any collection of pairwise factors, so
a triangle of Q edges cannot express it.

**Why the collapse is nonetheless faithful here.** PREREG's matrix names exactly two loop
families: `Eng->Lean->Eng` restatement loops over kernel-checked theorems, and intra-English
paraphrase loops over REGISTRY claims. Both are *binary* correspondences traversed as walks.
Nothing this round measures needs a joint 3-way factor.

**What it forbids.** No claim of ternary correspondence may be advanced from this build. If
the theory wants one, it needs a k-ary factor type, and that is a new object rather than a
parameter change.

## tree-null: repaired

> A contest graph with no cycles has a unique path between any two slots, so transport is
> path-independent and the cold floor is exactly zero. All tree contest is path-debt.

The engine now does this. The gap was ruled an **implementation defect** — "loop" always
meant cycle, and the build was measuring walks — so no PREREG text changed and no amendment
was needed.

### (A) Backtracking is shadow, not holonomy

`loops_from_fibers` used to give a two-member fiber the walk `u -> v -> u` and count its
residual as holonomy. On a single-edge tree that returned **0.1496** where theory says zero.
The residual is a property of the transport operator — `T(q) = (1-a)q + a*p_v` is a
contraction toward its target, so `T_{v->u} . T_{u->v} != id` — not of the ledger.

A two-member fiber now yields **no loop at all**. The same round trip is measured instead by
`meter.measured_shadow` as the edge's per-edge closure defect `eps_e`, which is the quantity
it always was. Holonomy is defined only on **verified cycles**: closed, every edge present in
Q, no immediate backtracking, length >= 3, enforced by `meter.verify_cycle`.

### (B) Open walks raise; they are never skipped

`holonomy` used to skip zero-weight edges, so a loop spec whose closing edge was absent from
Q silently measured an **open** walk — reporting **0.4338** against **0.2283** for the
genuine triangle over the same slots. `order_cycle` now returns `None` unless Q actually
closes, so no such spec is emitted, and `holonomy` raises `OpenWalkError` rather than
skipping. The old quantity survives as `path_transport_disagreement`: same number, honest
name, diagnostic only, and nothing reads it as a floor.

### Restatement loops are now genuine triangles

`Eng_1 -> Lean -> Eng_2 -> Eng_1`. PREREG's matrix always named this; the constructor now
instantiates it, preferring cyclic orderings with the most chart alternations and, among
those, the one that opens on the correspondence leg. Both directions are enumerated rather
than filtered to a lexicographic canonical form — they share an edge set but holonomy starts
at `slots[0]`, so the direction decides which leg is traversed first.

### The calibration channel this produced

Backtracking had to go somewhere, and where it went is useful. `MeterResult.shadow_calibration`
now carries, for every Q edge, the measured closure defect beside the defect the seed
declared a priori. `seed/shadow.json` declares zero, so any measured defect is drift — and on
a cross-chart edge that is **translator drift**: the round trip through the correspondence
loses something the seed said it would not. `translator_drift()` and `shadow_summary()` are
standard meter output on every run.

Nothing subtracts the measured defect from a floor. Shadow subtraction still uses the
declared value, and a control asserts it: a measured defect that deflated its own floor would
be exactly the resample-of-the-observation pattern gate 6 forbids.

## extraction determinism: repaired, and generalized into gate 7

`DeterministicExtractor._spans` seeded its RNG on `doc.doc_id`, so the inclusion draw
deciding whether a marginal span was kept depended on what a document was **called**. A
relabelled copy extracted differently and produced evidence the original never did, which
no deduplication can collapse. KICKOFF §4 requires re-ingestion under a second provenance
label to leave zero cold residue; it did not, and null cell (v) failed correctly.

Ruled an implementation defect under gate 1 — nothing registered specified seeding, and the
registered texts jointly entail content-keying. Seeding is now

```
DRNG("extract", extractor_id, prompt_id, doc.content_hash)
```

The per-extractor variance that makes k=3 informative is untouched; what is removed is the
one component that let a label change what was read. A relabelled copy now extracts
**bit-identically**, and cell (v) is green at residue exactly 0.0.

### The sweep found one more, in the live path

`AnthropicExtractor` put `doc_id` in its prompt, so the model could read the label. Same
defect, same repair class, fixed alongside: the prompt now carries a content hash.

### GATES.md sentence 7

> All generative keys are content-and-seed only; artifact identity lives in provenance
> exclusively.

Identity may *label* evidence; it may never *generate* it. Every random stream, address,
cache, and dedup key in ingestion and settlement was swept and classified, and
`check_generative_keys` fails on any unclassified `DRNG(...)` site, any `identity` row, and
any `design` row that cites no ruling. `make gate7`.

| Site | Key material | Keying |
|---|---|---|
| `engine/lexicon.py:sense_id` | `join_hash('sense', lemma, type_sig, source, primary_formal)` | identity-by-design |
| `engine/seed_lock.py:build_manifest` | `hash_obj({relative_path: file_hash, ...})` | identity-by-design |
| `engine/seed_lock.py:importer_script_hash` | `hash_obj({files: [...paths...], hashes: [...]})` | identity-by-design |
| `engine/audit.py:_floor_movements` | `DRNG('R4'|'R4-rewire', seed_hash, arm_label, trial_index)` | seed-keyed |
| `engine/meter.py:second_fdt_surrogate_floor` | `DRNG('fdt2', seed_hash)` | seed-keyed |
| `engine/meter.py:surrogate_floor_distribution` | `DRNG('surrogate', seed_hash)` | seed-keyed |
| `engine/nulls.py:cell_i_idempotence` | `DRNG('null-i', seed_hash)` | seed-keyed |
| `engine/nulls.py:cell_ix_binding_sanity` | `DRNG('null-ix', seed_hash)` | seed-keyed |
| `adapters/lexicon_imports.py:import_convention_table` | `sha256_text(canonical json of the table)` | content-keyed |
| `engine/blocks.py:build_blocks` | `join_hash(*member_slot_ids)` | content-keyed |
| `engine/blocks.py:build_fibers` | `join_hash(*member_slot_ids)` | content-keyed |
| `engine/blocks.py:loops_from_fibers` | `join_hash('loop', *cycle_slot_ids)` | content-keyed |
| `engine/cast.py:cast` | `DRNG('cast', seed_hash, block.id)` | content-keyed |
| `engine/energy.py:evidential_identity` | `(slot, value, extractor_id, content_hash)` | content-keyed |
| `engine/extract.py:AnthropicExtractor._spans` | `prompt carries chart + content hash, never doc_id` | content-keyed |
| `engine/extract.py:DeterministicExtractor._spans` | `DRNG('extract', extractor_id, prompt_id, doc.content_hash)` | content-keyed |
| `engine/lexicon.py:Registry.digest` | `hash_obj(self.as_record())` | content-keyed |
| `engine/meter.py:loop_permutation_null` | `DRNG('loop-perm', seed_hash, loop.id)` | content-keyed |
| `engine/normalize.py:slot_id` | `join_hash(nu, type)` | content-keyed |
| `engine/types.py:Document.content_hash` | `sha256_text(self.text)` | content-keyed |

Three rows are identity-derived **on purpose** and each cites its ruling. `sense_id`
includes the source tier because the collision policy forbids auto-merging — the same lemma
from Mathlib and from WordNet must occupy two addresses, so identity here stops two readings
silently becoming one rather than changing what either says. The two seed-manifest hashes
key on repo-relative paths as well as content, because gate 4 wants a rename visible rather
than absorbed. **No row is `identity`-keyed.**

### Translator drift, re-measured

The measured-vs-declared shadow channel was a gauge-variant reading before this repair: it
depended on document labels, so its number meant nothing. After the fix it is
**gauge-invariant** — the full per-edge calibration is bit-identical when every document is
relabelled, which is the property that makes it a measurement at all.

| | max translator drift |
|---|---|
| before the repair (gauge-variant) | 0.160 |
| after (gauge-invariant) | **0.1068** |

**The declared shadow was not changed**, for two reasons. The 0.160 band did not persist —
it fell by a third — so the stated trigger was not met. And independently: this reading comes
from a two-document synthetic corpus, and the declared shadow is subtracted from *every*
floor. Declaring it would deflate real-corpus floors by a number derived from toy data, and
`seed/shadow.json`'s zero is the conservative setting precisely because it cannot deflate
anything. A shadow declaration worth making would be measured on the corpus it will be
applied to, which needs D3.

## Contest under exact addressing — the object's definition of disagreement

**FINDING (first-class).** Once addressing is exact (`GATES.md` sentence 1: slot =
`hash(nu(surface), type)`) and fiber MEMBERSHIP is the DECLARED correspondence relation
(never token similarity), contest is producible **only** by:

1. **A clamp conflicting with extraction on the SAME slot** — a clamp-eligible warrant
   (kernel receipt / CI receipt) asserting one b-value on a slot whose extracted reading
   asserts a different one. Single slot, multiple values: a contested block with no loop.
2. **A declared correspondence over genuinely-same-claim slots with conflicting grounding** —
   a clamp on one member contradicting the extraction its co-referent paraphrases share.
   This closes a **holonomy loop**: the cycle is frustrated and the cold floor is nonzero.

Nothing else produces contest. Distinct addresses are distinct claims and never meet;
genuine paraphrases *declared* into one fiber **agree** (they read the same b-value) and
floor at zero — the declaration alone is not a disagreement. Grounding is what disagrees.

This is why the old null-battery "contest" fixtures were an artifact. They fibered
`"The cone is positive" / "…is not positive" / "…may be positive"` — three GENUINELY
DIFFERENT claims (P, ¬P, ◇P) — on token overlap and read the resulting holonomy as a
contest. Under exact addressing that grouping is not producible without *declaring* those
unequal claims equal, which is false. Every control that rested on the P/¬P triple was
testing a similarity artifact; each was deleted and rebuilt on mechanism (1)/(2) with a real
`Clamp` carrying a KERNEL-tier `Warrant`. (This composed with a second finding — the
value/address span mismatch, now GATES.md sentence 8: a slot's b-value is read off its
address span `nu(chart, surface)`, so no out-of-span proof body or comment can flip it. The
rebuilt controls carry their deciding token in the **clamp**, which is a separate constraint
set derived from no surface at all, so they are span-clean by construction.)

The consequence is a **design input, not just a cleanup**: the object's definition of
disagreement is exactly these two mechanisms, so the correspondence FORMAT (still an
undesigned HOLE — see `engine/correspondence.py`) must be designed to express *declared
co-reference over genuinely-same-claim slots*, because that plus grounding is the only thing
that can put a nonzero floor on H¹. A format that admitted similarity-grouped members would
re-manufacture the artifact.

## What holds

**planted-cycle.** A triangle `en1 -> ln1 -> en2 -> en1` through a cross-chart correspondence
edge, with `en1` clamped `T` and `en2` clamped `F`, yields holonomy **0.3224** — against
**0.0166** for the identical topology with compatible ends, a factor of twenty. It survives
re-anneal bit-identically, and the block still certifies `monotone`: frustration is a
property of the ledger, not a settling failure. Dropping the correspondence edge changes the
floor, so the frustration genuinely runs through it.

**blocks as connected components.** Two contests sharing no Q edge produce two blocks, and
perturbing one block's evidence moves the other's settled state by **exactly 0.0** —
measured, not asserted.

**descent certificate.** An objective rigged to rise on every evaluation exhausts the
halving safeguard and stamps the block `violated`, with the backtrack count non-zero. The
certificate is a real check on the implementation rather than a label.


## The probe battery (commitment → probe → status)

The table above maps theory *objects* to code. This maps the *commitments* the engine
makes to a reader of its verdicts — each one made falsifiable by a probe. Enforced by
`engine/probes.py:check_probe_battery` and `make probes`.

| Probe | Commitment | Status | Control |
|---|---|---|---|
| P1 | Chart-invariance of meaning: the same claims stated as prose and as a  | ✅ live | `P1ProseVsTable.test_the_same_claims_settle_the_same_whether_prose_or_table` |
| P2 | Gauge invariance: verdicts depend on content, never on document labels | ✅ live | `P2RelabelAndReorderInvariance.test_relabel_and_reorder_is_bit_identical` |
| P3 | Idempotent re-ingestion: a duplicated corpus adds no structure — no ne | ✅ live | `P3DuplicationGrowsNoStructure.test_a_relabelled_duplicate_adds_no_structure` |
| P4 | Clamp screening: a value is grounded only by a clamp-eligible warrant  | ✅ live | `P4ClampScreening.test_only_eligible_warrants_ground` |
| P5 | Settling is sound: F never ascends, and a non-monotone step voids the  | ✅ mapped | `DescentCertificate.test_an_injected_non_monotone_step_voids_the_block` |
| P6 | Abstain stability: a block whose evidence is symmetric between competi | ✅ live | `P6AbstainStability.test_symmetric_evidence_coexists_stably_across_seeds_and_schedules` |
| P7 | Lean round-trip: an elaborating Lean statement and its English restate | ⏸ **stub** | — |
| P8 | Provenance completeness: every delta is traceable to its source, and e | ✅ live | `P8ProvenanceWalker.test_every_delta_is_fully_provenanced_and_no_key_is_identity_keyed` |
| P9 | Statistical verdicts are decided against a null, never a resample of t | ✅ mapped | `EveryDecidingSiteConforms.test_no_deciding_site_is_non_conforming` |

**Flagged rows** (no committed probe yet, reported rather than silently counted as
covered):

- **P1** and **P7** are `stub`bed on a missing chart. P1 (prose-vs-table verdict equality)
  needs the tabular chart, which the plug-in audit below shows cannot be added by manifest
  alone. P7 (Lean round-trip) needs the Lean chart's elaboration gate, which routing item 3
  has not yet built.
- **P5**, **P6**, **P9** are `infer?` — the brief said 'into existing controls' without
  naming the commitment, so each is mapped to the nearest existing control and flagged for
  confirmation. This build reads them as descent-certificate, block-independence, and gate-6
  respectively. Confirm or correct.

## Chart plug-in audit — PASSED (item 2 landed)

The tabular chart was to be stood up "via the declarative manifest path", with the ruling
that if that was impossible the plug-in audit had failed and must be reported before
proceeding. It was impossible, it was reported, the registry refactor was authorized, and
**the audit now PASSes** — the audit that caught the gap proving the fix, which was the
stated completion criterion.

Charts are now a **seed manifest** (`seed/CHARTS.json`):

```json
{"name": "tabular", "tag": "tab", "behavior": "tabular"}
```

`nu`, `classify`, and the extractor's segmenter dispatch through the manifest's `behavior`
id — there is **no `if chart == ...` anywhere in the engine**, which is the property
`engine/chart_plugin_audit.py` verifies. Adding a chart is a manifest row plus (if the
behavior is new) a normalizer, a classifier, and a segmenter registered under the behavior
id. The tag rides inside every address, so it is declared in the manifest and hashed into
`SEED.lock` (gate 4); english and lean keep their old tags, so no existing address moved and
the morphism is purely additive.

The five sites the audit had flagged — `Chart` (was a `Literal`), the tag table, `nu`,
`classify`, and the extractor segmenter, plus `content_tokens` — all now dispatch through
the registry or strip the tag generically. `chart_plugin_audit.verdict()` returns
`manifest_only_possible: true`, zero blocking sites.

## Why this is a check and not a document

The gate-6 sweep found R2 the moment it was made executable, and then caught one of its
author's own additions. This is the same instrument pointed at the theory rather than at the
statistics: a new factor family, or a theory object whose code site is deleted, fails
`check_faithfulness` until someone writes down where it lives and what proves it.

Classified gaps do **not** fail the check. A finding suppressed behind a red build is a
finding nobody reads. `gaps_before_p3()` returns them, and that is the list to clear.
