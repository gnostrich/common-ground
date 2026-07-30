# PREREG — frozen on commit (D7: re-approved over PREREG-AMENDMENT-1)

R1–R5 and the not-claimed list are reproduced from KICKOFF §5 verbatim and have never been
rewritten. **One amendment is in force**: PREREG-AMENDMENT-1 (2026-07-30) changes which
surrogate decides R3's branch. It is recorded in full under **Amendments** at the end of
this file, appended rather than merged, and cited from the code it changes. D7 was
re-approved over the amended text.

Frozen on commit and hashed nowhere else — this file lives outside `seed/` deliberately,
because it constrains *interpretation*, not addressing, so amending it is not by itself a
seed-morphism. PREREG-AMENDMENT-1 also added a sentence to `seed/GATES.md`, and *that* part
is a seed-morphism: logged, and cold re-annealed.

The authorization to amend expires when P3 ingestion begins, enforced by
`audit.check_amendment_window()`.

---

One round. No follow-up rounds authorized. Interpretation mechanical.

Matrix: {certified-positivity + papers + Claude-export threads} x {loops: Eng->Lean->Eng restatement loops over kernel-checked theorems; intra-English paraphrase loops over REGISTRY claims} x {warm, cold} x {beta 1x, 4x}.

Fixed interpretation rules:

- **R1 (harness):** cells 4.i-v green, else entire run VOID (published as such).
- **R2 (ground-truth rediscovery):** the meter must flag the known claim-vs-proof gaps enumerated in STATEMENTS.md "what we do NOT claim". Miss rate > 0 on that list => meter insensitive at this scale => CLOSED-inconclusive.
- **R3 (floor verdict):** cold floor after shadow subtraction is either ~0 (all contest is path-debt; the ledger is self-consistent; result stands as v0 validation of the pipeline, protocol claims NOT advanced) or structured (report the modes verbatim; these are the ledger's genuine H1 candidates; no interpretation beyond listing).
- **R4 (prior-insensitivity):** drop 10% of Q edges at random, 5 trials; cold floor moves < surrogate noise, else verdicts are dictionary artifacts => seed design rejected, CLOSED.
- **R5:** "inconclusive at this scale with this method" is terminal, recorded CLOSED, never pending.

Not claimed under any outcome: capacity conjecture (needs n>=2 / diversity arms), growth law (mint off), comms utility (single party), generality beyond this corpus and seed hash.

---

## Mechanical reading of each rule

Interpretation is mechanical, so each rule below names the function that decides it. No
rule is decided by a person reading a number and forming a view.

| Rule | Decided by | Verdict values |
|---|---|---|
| R1 | `engine/nulls.run_battery` → `NullBatteryReport.status` | `PASS` proceeds; anything else is `VOID` |
| R2 | `engine/audit.ground_truth_rediscovery` | miss rate `0` proceeds; `> 0` is `CLOSED-inconclusive` |
| R3 | `engine/audit.floor_verdict` | `~0` (within surrogate noise) or `structured` |
| R4 | `engine/audit.prior_insensitivity` | movement `< surrogate noise` proceeds; else `CLOSED-rejected` |
| R5 | any of the above | `CLOSED`, never `pending` |

**On R1 and BLOCKED.** The battery has a third status the rule does not name: a cell can
be `BLOCKED` when an input it needs is unresolved. `BLOCKED` is not green, so R1 applies
and the run is VOID — but the report distinguishes it from `FAIL`, because "the harness
was never in a position to be tested" and "the harness was tested and failed" are
different findings, and publishing them as the same one would be a false report.

**On R3 and "~0".** "~0" is read against the surrogate band, never by eye:
`floor <= quantile(surrogate_floor_distribution, 0.95)`. The band is computed by
bootstrap over loops from the same run. Without that, "approximately zero" would be a
judgement call, and R3 says interpretation is mechanical.

> **Superseded by PREREG-AMENDMENT-1.** The paragraph above is the original text and is
> kept unrewritten. The surrogate it names is no longer decisive; see the amendment below.

**On R3's two branches.** They are not degrees of the same finding. `~0` advances nothing
about the protocol — it validates the pipeline and stops. `structured` produces a list of
modes reported verbatim, and the rule forbids interpreting them further in this round.

**On R2's dependency.** R2 cannot be evaluated until D5 supplies `STATEMENTS.md`. Absent
it there is no enumerated list to miss, and a run that reports R2 as satisfied without one
would be claiming a rediscovery test it never ran.

**On the warm arm.** The matrix names `{warm, cold}`. KICKOFF §7.3 makes the cold arm a
fresh session from a clean checkout, so the warm arm is only genuinely warm when P4 runs
against state retained from P3. Every measurement records `warm_source`; a report whose
measurements say `in-process-partial-anneal` must say so rather than presenting an
in-process fallback as a cross-session warm arm.

## Deliverable

One page in `reports/`: matrix, verdict sentence, what is NOT claimed. Worktree closed.
Terminal either way. Per KICKOFF §7.6, no additional rounds are proposed on completion.

---

## Amendments

Amendments are appended, never merged into the rules above. R1–R5's original text and the
original commentary stand unrewritten; each amendment states what it changes, why, and
under what authorization, and is cited from the code it changes.

### PREREG-AMENDMENT-1 — R3's decisive surrogate

**Date:** 2026-07-30 · **Authorized by:** operator · **Status:** in force
**Touches:** `engine/audit.py:floor_verdict`, `seed/GATES.md` sentence 6, D7

**Change.** R3's branch is decided by

```
near_zero = floor <= second_fdt_surrogate_floor      # label permutation
```

replacing

```
near_zero = floor <= quantile(surrogate_floor_distribution, 0.95)   # bootstrap
```

The bootstrap band is **retained and still reported** on every verdict as
`stats["surrogate_q95"]`, a legacy diagnostic. It decides nothing. When the two surrogates
would disagree, `floor_verdict` says so explicitly in its detail line. The mode list is
filtered by the decisive threshold.

**Rationale.**

**(a) Transcription defect.** The specification always named the second-FDT surrogate — it
is the reference the mint threshold is quoted against in the `seed/GATES.md` constants
table ("3× second-FDT surrogate floor"). The bootstrap in R3 was a drafting degradation
during transcription, not a design decision. This amendment restores the specified
procedure rather than choosing a new one.

**(b) No data has passed through R3.** P3 and P4 have not run. No verdict is being revised
after seeing a result, and no result exists that could have motivated the change. The
defect was found by applying the positive-control rule to a rule rather than to a cell.

**(c) Strictness-increasing.** The label-permutation threshold is not centred on the
observation, so it does not rise to meet whatever floor it is handed. The `~0` branch —
which advances no protocol claim but does declare the pipeline self-consistent — becomes
harder to obtain, never easier. An amendment that could only make a favourable branch
easier would not be admissible on rationale (b) alone.

**What the old rule did.** A mean floor of 0.45 carried entirely by the cold arm was called
`~0`, because the bootstrap band was a resample of those same floors. This is the same
vacuity that retired null cells (iv) and (v) at P1.

**Historical pin.** `tests/test_controls.py:R3CarriesTheSameDefect` is **kept**. It tests
the superseded computation directly rather than through `floor_verdict`, so it records what
the defect was and stays green under the amended rule. Deleting it would erase the reason
the amendment exists.

**Constitutional consequence.** `seed/GATES.md` sentence 6, added under this amendment:

> Every statistical verdict is decided against a null constructed under the no-effect
> hypothesis (permutation / phase-randomization / independent surrogate), never against a
> resample of the observation.

That sentence generalizes the fix beyond R3. It is marked in GATES.md as operator-added
rather than KICKOFF text.

**Seed consequence.** Editing `seed/GATES.md` moves the seed hash. That is plastic under
gate 4: a `seed-morphism` event is logged in `REGISTRY.jsonl` with the before/after hashes,
and the null battery is re-run cold on the new hash. No warm state was carried across —
there was none to carry, the lock being provisional and no phase beyond P1 having run.

**Scope and expiry.** The authorization expires the moment P3 ingestion begins. This is
enforced mechanically, not remembered: `audit.check_amendment_window()` raises once any
`P3` phase-run appears in `registry/REGISTRY.jsonl`. After that point a rule changed is a
choice made in sight of a result.
