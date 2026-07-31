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
| **intra-chart sheaf (gluing within one chart)** | `engine/blocks.py:edges_from_fibers` | two same-chart slots joined by a fiber edge settle closer together than the same two slots with the edge dropped | by design |
| **inter-chart correspondence** | `engine/types.py:QEdge` | a cross-chart edge transports; and a 3-cycle of pairwise edges is shown NOT to represent a genuine ternary factor — it cannot encode a joint constraint that no pair of its projections encodes | by design |
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

## Why this is a check and not a document

The gate-6 sweep found R2 the moment it was made executable, and then caught one of its
author's own additions. This is the same instrument pointed at the theory rather than at the
statistics: a new factor family, or a theory object whose code site is deleted, fails
`check_faithfulness` until someone writes down where it lives and what proves it.

Classified gaps do **not** fail the check. A finding suppressed behind a red build is a
finding nobody reads. `gaps_before_p3()` returns them, and that is the list to clear.
