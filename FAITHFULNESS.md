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

`make faithfulness` · 10 rows · 3 deliberate simplifications · **1 open gap**

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
| **tree-null (all tree contest is path-debt)** | `engine/meter.py:holonomy` | FAILS AS THEORY PREDICTS IT SHOULD NOT. A single-edge tree yields holonomy 0.1496, and a 3-slot walk over a path yields 0.4338 — larger than the genuine triangle it should be dominated by. The control pins both, so the gap cannot be closed by accident. | **GAP — before P3** |
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

## The open gap: tree-null

> A contest graph with no cycles has a unique path between any two slots, so transport is
> path-independent and the cold floor is exactly zero. All tree contest is path-debt.

**The engine does not do this.** Two distinct defects, both measured, both pinned by
`tests/test_faithfulness.py:TreeNull` so they cannot drift or be closed by accident.

### (A) Backtracking walks are not cycles

`loops_from_fibers` gives a two-member fiber the walk `u -> v -> u`. On a tree that is a
closed walk containing no cycle, so theory says zero holonomy. The engine returns
**0.1496**.

The cause is the transport operator. `T(q) = (1-a)q + a*p_v` is a contraction *toward* the
target, not a reversible parallel transport, so `T_{v->u} . T_{u->v} != id` whenever
`p_u != p_v`. The residual is a property of the operator, not of the ledger.

This is not a corner case: a two-member fiber is the commonest fiber the engine builds, and
`Eng->Lean->Eng` with a single English slot is exactly this shape.

### (B) A loop spec may name a closing edge that does not exist

`loops_from_fibers` builds its cycle from fiber **membership**, and `holonomy` skips any
edge whose weight is zero (`if w <= 0.0: continue`). So a three-member fiber whose Q graph
is the path `u-v-x` yields the loop spec `(u,v,x)` whose closing edge `(x,u)` is absent —
and holonomy then silently measures the **open** walk `u -> v -> x`, reporting
`TV(p_u, transported)`: the start state compared against a state transported somewhere else
entirely.

| walk | closing edge in Q? | holonomy |
|---|---|---|
| `u -> v -> x` over the path `u-v-x` | **no** | **0.4338** |
| `u -> v -> x -> u` over the triangle | yes | 0.2283 |

The open walk reports *more* holonomy than the genuine cycle. The meter's central quantity
is being computed over walks that are not cycles in the contest graph.

### No ruling covers this

KICKOFF's paired loop-side meter presumes loops are cycles. Nothing in `GATES.md`, PREREG,
or any of the three amendments licenses measuring holonomy over a backtracking or open walk.
Closing it needs a decision on both halves:

1. whether a two-member fiber yields a loop at all, and if so what its holonomy means; and
2. whether `loops_from_fibers` must verify closure against the Q graph before emitting a
   spec — or `holonomy` must refuse a spec whose closing edge is missing rather than
   skipping it.

Both are engine changes with a seed consequence. Neither is proposed here; this document
reports.

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
