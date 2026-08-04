# GATES.md — constitutional

These sentences are constitutional. They are frozen under `SEED.lock`. No engine module may
weaken them; each is enforced structurally in code, and each enforcement point is cited
below the sentence it enforces.

**Provenance.** Sentences 1–5 are reproduced verbatim from KICKOFF §2. Sentences 6 and 7
are not from KICKOFF: both were added by operator authorization on 2026-07-30 — sentence 6
as part of PREREG-AMENDMENT-1 (`registry/PREREG.md`), sentence 7 alongside the DRNG
implementation-defect repair — and both are marked as such so that nobody later reads them
as original text. They are constitutional on the same terms as the others: frozen, and
weakenable only by another authorized, logged amendment.

1. Slot identity = hash(nu(surface), type). Addressing is a function of the seed, never of engine state.
2. Lexicon and equivalence priors enter F only as energy terms. They can never clamp.
3. Only top-tier warrants ground (clamp-eligible): Lean kernel-accept under pinned toolchain; CI-green test receipts. Extraction provenance never grounds.
4. Anything that moves addresses (lexicon edit, prompt change, toolchain bump) is plastic: requires seed-morphism log event + cold re-anneal. No silent bumps; toolchain hashes tripwired in CI.
5. No floor is read before the null battery passes on the same seed hash.
6. Every statistical verdict is decided against a null constructed under the no-effect hypothesis (permutation / phase-randomization / independent surrogate), never against a resample of the observation. *(Added 2026-07-30 by PREREG-AMENDMENT-1; not KICKOFF text.)*
7. All generative keys are content-and-seed only; artifact identity lives in provenance exclusively. *(Added 2026-07-30 with the DRNG repair; not KICKOFF text.)*
8. Any property attributed to a slot is computed over that slot's address span; nothing outside the span may influence what the slot asserts. *(Added 2026-08-04 by operator authorization with the span repair; not KICKOFF text.)*
9. A correspondence is a directed, typed morphism between two slot addresses, entering as a claim through the one inlet. Uncertainty about a correspondence is expressed as warrant, never as a fuzzy morphism type. *(Added 2026-08-04 by operator authorization with the correspondence build; not KICKOFF text.)*

### On sentence 9

The base category's morphisms are **claims**, disposed like every other claim. There is no
side registry that writes structure directly: the correspondence set is DERIVED from accepted
correspondence claims, so `propose()` remains the single door and the one-write-path assertion
still covers it.

Three kinds and no fourth. `same_claim` is an isomorphism class and is the **only** kind that
carries holonomy; its reverse is a **separate claim** with a separate address, so an
unreciprocated arrow is reported as open rather than assumed symmetric. `refines` and
`instance_of` are directed and non-invertible: they contribute coupling structure but are
**excluded from loops**, because a round trip through a non-invertible arrow never closes.

**There is no `approximates` kind, and this is constitutional.** Uncertainty about whether two
slots say the same thing is expressed as *low warrant on a `same_claim` proposal* — an LM
proposal enters at `EXTRACTION`, the operator's confirmation at `AUTHORSHIP`, a kernel-verified
translation at `KERNEL`. Fuzziness lives in the warrant ladder, not in the structure. A fuzzy
arrow type would put a similarity score back inside the algebra, which is exactly the defect
this build deleted: a graded morphism is a threshold wearing a type's clothes.

Extraction-tier correspondences may form **provisional** fibers and loops and be reported as
such, but they never clamp and K never promotes them: promotion requires `AUTHORSHIP` or
stronger (`engine/types.py:PROMOTION_FLOOR`).

### On sentence 8

Sentence 1 makes the slot the identity of a claim. Sentence 8 is its consequence: if a
property is *attributed to* that slot — its b-value, its confidence, its claim-form — it must
be a function of the claim's identity, and therefore computed over `nu(chart, surface)` and
nothing wider. `classify` already carried this discipline explicitly ("so that classification
and addressing cannot disagree"); the sentence generalizes it to every slot-attributed
property, because two defects of exactly this shape were found in one pass:

- **#2, the b-value.** `_value_for` ran on the raw segment. The Lean segmenter spans one
  declaration head to the next, so proof bodies and trailing docstrings — often prose about a
  *neighbouring* declaration — reached the value. A stray `no `/`does not`/`might` in a comment
  flipped a theorem to F/N and manufactured contest against the identical statement elsewhere.
  On the real corpus, **52 of 59** single-slot "contests" had their deciding token outside the
  address span; all 59 were voided.
- **#3, the confidence.** The draw was seeded on `doc.content_hash` and consumed in document
  order, so editing a comment moved a slot's confidence and inserting a declaration shifted
  every later slot's. Gate-7 clean (content-keyed, no identity) and still wrong: variance
  driven by document *composition* is not extractor noise.

Both took the same form — **a property whose seed or input is wider than the slot's address**
— so the check is shaped to that form rather than to either instance. `surface` is exempt by
construction: it is the provenance target, a fact about where the claim was found, not a
property of what the claim asserts.

Rejected alternatives, recorded: addressing the *full* span would put proof bodies into claim
identity and destroy proof-irrelevance; re-bounding the segmenter only relocates the mismatch.

### On sentence 7

Identity may *label* evidence; it may never *generate* it. A document's id, its source
label, its path, and the order it arrived in are all facts about the artifact rather than
about its content, and none of them may reach a random stream, an address, a cache, or a
dedup key. They belong in `Provenance` and nowhere else.

The sentence was written because two defects of exactly this shape were found in one
afternoon: the offline extractor seeded its inclusion draw on `doc.doc_id`, and the live
extractor put `doc_id` in its prompt. Both made the same text read differently under a
second label, and both defeated KICKOFF §4's requirement that re-ingestion leave zero cold
residue.

`design` keying — identity-derived on purpose — is permitted where a ruling requires it, and
there are three: sense ids include their source tier because the collision policy forbids
auto-merging, and the two seed-manifest hashes include file paths because gate 4 wants a
rename to be visible. Each cites its ruling in `GENERATIVE_KEY_SITES`.

### Why sentence 6 is numbered 6

The authorization asked for "sentence 7". This file held exactly five sentences, so the
next number is 6 and that is what was used; leaving a phantom clause 6 in a constitutional
document would be worse than the renumbering. If the intended numbering was the seven
KICKOFF invariants rather than this file's clause list, renumbering is a one-line seed
edit — and, being a seed edit, a plastic one under gate 4.

---

## Enforcement points

| Gate | Enforced in | Mechanism |
|---|---|---|
| 1 | `engine/normalize.py:slot_id` | `slot_id` takes only `(nu, type)`. It is a module-level pure function with no access to engine state. `nu` is chart-indexed and emits a control-character chart tag, so the chart is carried inside `nu(surface)` and the hash signature stays exactly `hash(nu(surface), type)`. |
| 2 | `engine/energy.py:FreeEnergy` | Lexicon priors (`r`) and equivalence priors (`Q`) enter only as the `lexicon_energy` and `coupling_energy` terms. The clamp set is a separate argument sourced solely from `Warrant.clamp_eligible`; there is no code path from a prior to a clamp. `settle()` raises `GateViolation` if a clamp is presented whose warrant is not clamp-eligible. |
| 3 | `engine/types.py:WarrantTier` | `clamp_eligible` is a read-only property derived from the tier, not a settable field. Only `KERNEL` and `CI_RECEIPT` return `True`. Every `Delta` produced by `engine/extract.py` is stamped `EXTRACTION` by the extractor base class, which the concrete extractors cannot override. |
| 4 | `engine/seed_lock.py:verify` | `verify()` recomputes the hash of every seed file, prompt, and pinned toolchain version and compares against `SEED.lock`. CI runs it on every push (`.github/workflows/ci.yml`). Drift fails the build. Legitimate changes must be accompanied by a `phase: seed-morphism` record in `registry/REGISTRY.jsonl` carrying `cold_anneal_ref`. |
| 5 | `engine/meter.py:read_floor` | `read_floor()` requires a `NullBatteryReport` argument whose `seed_hash` equals the current seed hash and whose status is `PASS`. Any other value raises `GateViolation`. There is no floor-reading path that bypasses it. |
| 6 | `engine/static_checks.py:check_gate6_classification` (+ `audit.floor_verdict`, `audit.prior_insensitivity`, `nulls.run_battery`) | Three enforcement layers. **Per rule:** R3's branch is decided by `floor <= second_fdt_surrogate_floor`, a loop-by-loop permutation of the warm/cold labels; R4's two arms are decided against dropout movement on a degree- and weight-marginal-preserving rewire of the Q graph. Both are nulls built under the no-effect hypothesis the rule tests. Superseded bootstrap bands are still computed and reported as legacy diagnostics but decide nothing. **Per cell:** every null cell carries a positive control and `NullBatteryReport.status` returns `FAIL` if any control is dead, so no cell can report a verdict it was incapable of failing. **Codebase-wide:** `check_gate6_classification` AST-walks `engine/` and fails on any band-building or band-reading function not classified in `GATE6_SITES` with its reference distribution and role, so a new band cannot be added unexamined. Current conformance: `reports/gate6-sweep.md`. `tests/test_controls.py` covers all three. |
| 7 | `engine/static_checks.py:check_generative_keys` | AST-walks `engine/` for every `DRNG(...)` call site and fails on any not classified in `GENERATIVE_KEY_SITES`, on any row keyed `identity`, and on any `design` row that cites no ruling. The per-site table records what each stream is keyed on. `make gate7`. |

## Constants (SEED.lock scope)

Authoritative values live in `seed/CONSTANTS.json` and are hashed into `SEED.lock`.
Reproduced here for readability; `seed/CONSTANTS.json` wins on any discrepancy.

| Constant | Value |
|---|---|
| `lambda` (equivalence-prior coupling) | 1.0 |
| `lambda2` (lexicon-prior weight) | 1.0 |
| `eta` (mirror-descent nominal step) | 0.1 |
| settle termination | `grad < 1e-6` or 500 iters |
| fiber cap `m` | 5 |
| T2 anneal | 1.0 → 0.1, ×0.9 per sweep |
| Hankel window | 64 |
| mint threshold | 3× second-FDT surrogate floor (LOGGED, not acted on) |
| mint | **OFF** |

### Note on `eta` and the monotone certificate

`eta = 0.1` is the *nominal* mirror-descent step. The certificate in gate-adjacent
logging asserts monotone descent of F. To make that assertion total rather than
probabilistic, `settle()` applies a logged halving safeguard: if a step at the current
size would raise F, the step is halved (up to `SETTLE_MAX_BACKTRACKS` times) and the
halving is recorded in the run log as `backtracks`. F is convex under the entropic
mirror map used here, so the safeguard is expected to fire rarely; when it does fire it
is visible in the log rather than silent. A step that cannot be made descending after
the maximum number of halvings terminates settling and stamps the certificate
`violated` — it never silently ascends.
