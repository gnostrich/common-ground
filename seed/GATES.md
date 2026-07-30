# GATES.md — constitutional

These five sentences are constitutional. They are reproduced verbatim from KICKOFF §2 and
are frozen under `SEED.lock`. No engine module may weaken them; each is enforced
structurally in code, and each enforcement point is cited below the sentence it enforces.

1. Slot identity = hash(nu(surface), type). Addressing is a function of the seed, never of engine state.
2. Lexicon and equivalence priors enter F only as energy terms. They can never clamp.
3. Only top-tier warrants ground (clamp-eligible): Lean kernel-accept under pinned toolchain; CI-green test receipts. Extraction provenance never grounds.
4. Anything that moves addresses (lexicon edit, prompt change, toolchain bump) is plastic: requires seed-morphism log event + cold re-anneal. No silent bumps; toolchain hashes tripwired in CI.
5. No floor is read before the null battery passes on the same seed hash.

---

## Enforcement points

| Gate | Enforced in | Mechanism |
|---|---|---|
| 1 | `engine/normalize.py:slot_id` | `slot_id` takes only `(nu, type)`. It is a module-level pure function with no access to engine state. `nu` is chart-indexed and emits a control-character chart tag, so the chart is carried inside `nu(surface)` and the hash signature stays exactly `hash(nu(surface), type)`. |
| 2 | `engine/energy.py:FreeEnergy` | Lexicon priors (`r`) and equivalence priors (`Q`) enter only as the `lexicon_energy` and `coupling_energy` terms. The clamp set is a separate argument sourced solely from `Warrant.clamp_eligible`; there is no code path from a prior to a clamp. `settle()` raises `GateViolation` if a clamp is presented whose warrant is not clamp-eligible. |
| 3 | `engine/types.py:WarrantTier` | `clamp_eligible` is a read-only property derived from the tier, not a settable field. Only `KERNEL` and `CI_RECEIPT` return `True`. Every `Delta` produced by `engine/extract.py` is stamped `EXTRACTION` by the extractor base class, which the concrete extractors cannot override. |
| 4 | `engine/seed_lock.py:verify` | `verify()` recomputes the hash of every seed file, prompt, and pinned toolchain version and compares against `SEED.lock`. CI runs it on every push (`.github/workflows/ci.yml`). Drift fails the build. Legitimate changes must be accompanied by a `phase: seed-morphism` record in `registry/REGISTRY.jsonl` carrying `cold_anneal_ref`. |
| 5 | `engine/meter.py:read_floor` | `read_floor()` requires a `NullBatteryReport` argument whose `seed_hash` equals the current seed hash and whose status is `PASS`. Any other value raises `GateViolation`. There is no floor-reading path that bypasses it. |

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
