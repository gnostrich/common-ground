# PREREG — frozen on commit (D7: re-approved over PREREG-AMENDMENT-1 and -2)

R1–R5 and the not-claimed list are reproduced from KICKOFF §5 verbatim and have never been
rewritten. **Two amendments are in force**, both dated 2026-07-30, both recorded in full
under **Amendments** at the end of this file, appended rather than merged, and cited from
the code they change:

| Amendment | Rule | Class | Rationales |
|---|---|---|---|
| PREREG-AMENDMENT-1 | R3 | transcription-restoration | (a), (b), (c) |
| PREREG-AMENDMENT-2 | R4 | **pre-data-design** | (b), (c) — **(a) does not apply** |

The class distinction is load-bearing. AMENDMENT-1 restored a procedure the specification
had already named; AMENDMENT-2 is new design, admissible only because no data had passed
through R4. D7 was re-approved over the twice-amended text.

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

**On R4 and "surrogate noise".** Superseded by PREREG-AMENDMENT-2: the reference is now
dropout movement on a degree- and weight-marginal-preserving rewire of the Q graph, and a
second arm requires clamp-tier perturbation to move the floor above the same null. The
paragraph naming the original comparison stands unrewritten in R4 above.

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

### PREREG-AMENDMENT-2 — R4's null, and a second arm

**Date:** 2026-07-30 · **Authorized by:** operator · **Status:** in force
**Class:** `pre-data-design` — **not** a transcription restoration
**Touches:** `engine/audit.py:prior_insensitivity`, `engine/blocks.py:rewire_q_graph`, D7

**Change.** R4 becomes two-sided, and both arms are decided against the same null.

*Insensitivity arm (as registered).* Cold-floor movement under real 10% Q-edge dropout, 5
trials. PASS iff that movement is `<= q95` of the movement produced by the same dropout
applied to a **degree- and weight-marginal-preserving randomization** of the Q graph
(endpoint permutation within weight strata), same trial count.

*Sensitivity arm (added).* Clamp-tier perturbation must move the floor **above** that same
null. A rule that only ever asks "did nothing move?" is satisfied by a meter that cannot
move at all; this arm is what makes the first arm's pass mean something. Both arms are
reported. `gate6_conforming: true` on both.

Replacing:

```
ok = worst_movement < quantile(surrogate_floor_distribution(observed_floors), 0.95)
```

The superseded self-scaled band is retained and reported as `legacy_self_scaled_band`. It
decides nothing.

**The null.** `blocks.rewire_q_graph` stratifies edges by `(weight, origin)` and permutes
endpoints within each stratum by double-edge swaps. Every node keeps its degree, every
stratum keeps its edge count and its weight, and swaps that would create a self-loop or a
duplicate pair are refused rather than repaired — so the marginals hold exactly, not
approximately. What the randomization destroys is precisely *which slots the dictionary
chose to link*, which is the hypothesis R4 tests. Stratifying by weight matters: an
unstratified rewire would move a heavy fiber edge onto a pair that never earned one, so a
rejection could not be attributed to the dictionary rather than to edge strength.
Stratifying by `origin` matters for the same reason — a `fiber` edge and a `lexicon` edge
of equal weight are different claims about *why* two slots are alike.

**Rationale — (b) and (c) only. (a) does not apply.**

**(a) Transcription defect — DOES NOT APPLY, recorded explicitly.** Nothing in the
specification named a null-rewire reference or a sensitivity arm. There is nothing here to
restore. PREREG-AMENDMENT-1 could claim (a) because the second-FDT surrogate was already
the reference the mint threshold was quoted against; this amendment cannot, and claiming it
would misrepresent a design choice as a correction. The `class` field on each amendment
record carries this distinction — `transcription-restoration` for AMENDMENT-1,
`pre-data-design` for AMENDMENT-2 — so no later reader has to reconstruct which kind of
change each one was. A design amendment carries more weight of judgement, and its
admissibility rests entirely on the pre-data timing.

**(b) No data has passed through R4.** P3 and P4 have not run. No verdict is being revised
in sight of a result, and no result exists that could have motivated the design.

**(c) Strictness-increasing, on both arms.** The insensitivity arm no longer buys tolerance
by having a large floor — the superseded band scaled with the observed floor, so it relaxed
exactly where dictionary sensitivity mattered most. And a second arm must now also pass. No
run that passed the old R4 faces a smaller set of checks.

**What the old rule did.** It was not vacuous the way R3's was, and the report should not
say it was. It was miscalibrated in the permissive direction: strict on a run whose floor
was near zero, lax on a run whose floor was large.

**No clamps means inconclusive, not passed.** With no clamp-eligible warrant in the ledger
the sensitivity arm cannot run, and R4 returns `CLOSED-inconclusive` rather than reporting
the insensitivity arm alone. Reporting one arm of a two-sided test as if the test had run
would be a false report — the same distinction R1's commentary draws between BLOCKED and
FAIL. This is the expected state until D6 resolves.

**Historical pin.** `tests/test_controls.py:R4IsNotYetConformingToGate6` is **kept**,
rewritten to exercise the superseded self-scaled band directly rather than through
`prior_insensitivity`, on the same terms as AMENDMENT-1's pin.

**Seed consequence.** `seed/GATES.md`'s gate-6 enforcement row and `seed/CONSTANTS.json`
(`rewire_passes`) both move the seed hash. Logged as a `seed-morphism` event with
before/after hashes and an identity slot map; battery re-run cold.

**Sweep.** Sentence 6 binds every statistical verdict, so every band in the engine was
swept against it and the result is `reports/gate6-sweep.md` — and, so that it does not go
stale, `static_checks.check_gate6_classification`, which fails on any unclassified
band-building function in `engine/`. The sweep immediately found a third non-conforming
rule that nobody had noticed: **R2** flags gaps at `floor > bootstrap q95`, miscalibrated
in the *strict* direction (a larger floor raises the bar, so fewer gaps clear it; on a
uniformly-zero run nothing clears it and the miss rate is 100%). R2 is outside this
amendment's scope, so it is flagged, reported in its own stats, and unchanged. It is
BLOCKED on D5 regardless.

**Scope and expiry.** Unchanged from AMENDMENT-1: the authorization expires the moment P3
ingestion begins, enforced by `audit.check_amendment_window()`.
