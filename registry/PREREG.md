# PREREG — frozen on commit (D7: approved as-is)

Reproduced from KICKOFF §5 without amendment. D7 was approved as-is; there are no
amendments. Frozen on commit and hashed nowhere else — this file lives outside `seed/`
deliberately, because it constrains *interpretation*, not addressing, and amending it
would not be a seed-morphism.

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
