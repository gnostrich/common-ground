# Era: the pre-demotion substrate

**Span:** through 2026-08-06 14:36 (commit `b650d1f`).

## What defined the era

`same_claim` is the corpus's only loop-eligible arrow kind — the only relation that builds
fibers and lets a floor be measured. Across this era it was overwhelmingly a **mis-kinding**:
`engine/adjudicate.py` (introduced by the fix itself) found that 96.7% of `same_claim`
declarations joined a definition to a sentence of **its own docstring** — containment, not
identity — and gate 1 (exact addressing) had no way to tell the two apart, so closure over that
containment relation manufactured equivalence classes nobody had declared. `seed/CONSTITUTION.md`
names this as one of five instances of one cause under OI-10, "**THE GREAT REPAIR**"
(`seed/CONSTITUTION.md:163-168`) — the other instance from this same cause, in the energy layer
rather than the identity layer, is the subject of the next era file (`03-pre-apex-energy.md`).

## Headline numbers, going into the repair

From commit `b650d1f` ("The demotion is landed.", 2026-08-06 14:36) and its pinned pre-repair
retest fixture, commit `150a858` (14:20):

- `same_claim` pairs: **2,082**
- `same_claim` records demoted: **6,150** total — 4,487 same-file containment (a definition and
  a sentence of its own docstring) + 1,663 cross-document docstring bridges
- Fibers: **1,046**; largest fiber: **120 members**; slots living in a multi-member fiber:
  **2,799**
- Pigeonhole check on the declarations alone, before any text was read: **1,155** docstrings
  declared identity with a definition, **368** of them from more than one sentence, worst case
  **7** sentences claiming the same definition — **576 pairs over-declared on the face of the
  declarations alone**
- One pinned retest question — `"talk about the gibbs ebm across projects and general design
  principles"`, pinned verbatim by `150a858` — measured on the pre-repair substrate
  (`tests/test_fixtures.py:22-54`, `RETEST_PRE_REPAIR`): attachment **59 of 59** shown objects
  (100%, the guard's own limit case, `engine/perturb.py` `INDISCRIMINATE`); **0 of 24** moved
  slots reached over *any* declared arrow; region drawn from what the commit calls "the ETS
  writer/deploy cluster — the 120-member fiber's gravity well."

## What ended it

Commit **`b650d1f`** (2026-08-06 14:36), "The demotion is landed. The simulated table is
superseded-by-commit, and it matches exactly." `engine/adjudicate.py` re-kinds a `same_claim`
arrow to `refines` when its two endpoints are (a) in the same file with one a definition and the
other a sentence of that definition's own docstring, or (b) a cross-document docstring bridge.
Nothing is deleted: a demoted arrow keeps its endpoints, evidence, proposer and tier, still
couples the graph as `refines`, and simply stops being loop-eligible.

After the repair (same commit):

- `same_claim` pairs: **69 surviving of 2,082** (a 96.7% reduction — matching the pigeonhole
  estimate)
- Fibers: **2** (from 1,046); largest fiber: **41 members** (from 120); slots in multi-member
  fibers: **43** (from 2,799)
- Arrow kinds corpus-wide after re-kinding: **66,766 refines, 2,870 instance_of, 547
  same_claim**
- **A self-reported finding inside the same commit:** the demotion was first applied where the
  thing being repaired does not exist. `corpus_state.py`'s `build_snapshot_direct` builds the
  on-disk snapshot from raw corpus material carrying **zero arrows** — the identity layer only
  appears once the window's live read view lays the journal's arrows over it in `with_arrows`.
  So the build-time demotion adjudicated an empty list and printed an all-zero census, "which is
  what showed it." The actual correction was applied to the *existing* on-disk snapshot via
  `tools/rebuild_fibers.py`, a standalone re-adjudication tool the same commit adds (loads the
  snapshot, re-kinds, rebuilds fibers/loops, writes back — minutes, not the ~35-minute full
  re-extraction).
- **"THE ZERO DELTA IS ITSELF A FINDING":** re-running the demotion against the committed
  snapshot, after 11,016 Lean slots had landed in between, produced *exactly* the same numbers
  as an earlier simulation — because the 375 arrows touching the new Lean material carried zero
  `same_claim` among them. "Ingested is not declared; a slot count is not a structure count."

## What was WITHDRAWN when it ended

Each named beside its original inside commit `b650d1f`:

- **"8 loops"** → withdrawn to **1**.
- The **second-FDT surrogate floor value 0.12153270**, computed from `LoopMeasurements` over
  those eight loops — withdrawn, "pending re-measure on the survivor." I found no committed
  re-measurement (see below).
- **"4,928 same_claim"** as a header figure — withdrawn. (Note: this exact figure is also the
  one later `seed/INVENTORY.md` rows cite from the *live* window's `/corpus` endpoint, which
  reads the journal's arrows through a code path — see the caveat below.)
- *"The 73% energy dominance and K's 61-of-64 single-fiber support — both real measurements of
  a substrate that has now mostly left."* Both explicitly withdrawn in the commit's own words.
  Both numbers *also* reappear, independently re-measured, as the trigger for the next era's
  repair (apex-star) roughly 90 minutes later — see `03-pre-apex-energy.md`.

## A caveat I could not resolve

The demotion patches `engine/corpus_state.py` only — the window's live read view and
`build_snapshot_direct` (used by `proposerd.py build-snapshot` for future full rebuilds). It does
**not** patch `engine/pipeline.py`'s `Ledger`-building path (`engine/pipeline.py:139,147`), a
separate fiber/edge builder used by the null battery and the structure audit. Apex-star's own
commit message, written about ninety minutes after this one, still describes "one 120-member
fiber" carrying 73% of coupling energy. I could not determine from the repository whether that is
the *same* fiber this commit reduced to 41 members (i.e., `pipeline.py`'s unpatched path
re-deriving the pre-demotion structure) or a fiber built from different declared-correspondence
input that this commit never touched. I am flagging the ambiguity rather than resolving it by
assumption.

## Numbers I looked for and could not find

- **A post-repair re-run of the pinned substrate-repair retest** (`150a858`'s `RETEST_QUESTION`).
  `tests/test_fixtures.py` as of HEAD (`80791f0`) still defines only `RETEST_PRE_REPAIR` — no
  post-repair companion object, no second set of three numbers. The retest was pre-registered
  specifically so this comparison could be made, and as far as I can find it has not been run.
- **A re-measured second-FDT surrogate floor on the surviving single loop.** Not present in any
  `runs/*.json` I found, nor in a later commit message.
- **A current same_claim/fiber count measured on the live deployed corpus** (as opposed to the
  simulated/rebuilt snapshot `b650d1f` reports against).
