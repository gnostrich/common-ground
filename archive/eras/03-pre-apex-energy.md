# Era: pre-apex energy

**Span:** 2026-08-06 14:36 (commit `b650d1f`, previous era's end) through 2026-08-06 15:59
(commit `7bac55a`).

## What defined the era

`engine/blocks.py:edges_from_fibers` built the Q-graph's energy edges by **all-pairs expansion**
of each fiber: every within-fiber pair got its own edge at the full declared weight, so an
n-member fiber contributed n(n−1)/2 edges from what the declarations actually asserted as (at
most) a chain of pairwise correspondences. `seed/CONSTITUTION.md` OI-10 (`:163-168`) names this
as one of **five instances of one cause** — "never pairs where a quotient was declared" — under
the heading **"THE GREAT REPAIR"**, alongside the `same_claim` mis-kinding fixed in the previous
era (`02-pre-demotion-substrate.md`). That earlier fix touched the identity layer; this one
touches the energy layer, and — per the caveat at the end of the previous era file — it may be
the reason the same 120-member-fiber symptom was still visible after the identity-layer fix
landed.

## Headline numbers of the era

From commit `7bac55a` ("Apex-star: the coequalizer, with zero degrees of freedom and one
canonical expansion.", 2026-08-06 15:59) and `seed/CONSTITUTION.md` OI-10:

- `edges_from_fibers` previously contributed **7,140 edges from a single 120-member fiber**
  (C(120,2) = 7,140), where OI-10 states the fiber's own declared arrows numbered **434**:
  *"all-pairs fabricated 7,140 edges from 434 declarations"* (`seed/CONSTITUTION.md:165`).
- Measured on the live corpus before this repair: one 120-member fiber carried **73%** of the
  entire corpus's fiber-coupling energy, and the corpus-wide over-coupling factor was **5.6×**
  (commit `7bac55a`).
- OI-10 additionally names two further measurements from the same cause: **"regions were 95%
  one proposition"** and **"K's support was 61/64 one thing"** (`seed/CONSTITUTION.md:166-167`).
  I did not find the underlying measurement artifact for either inside the repository — they
  are stated in the constitution and, for the 61/64 figure, echoed as withdrawn inside the
  *previous* era's ending commit (`b650d1f`). See "could not find," below.
- Under the repaired `edges_from_fibers`, the same 120-member fiber contributes **120 edges**
  — one per face, to a single derived apex — instead of 7,140.
- **A control that went silent was the real catch.** The author's first version of apex-star
  made the loop finder return zero cycles (two faces of a fiber are two hops apart through the
  new apex node, which is not a slot); `mean_floor()` returned exactly 0.0, and the null
  battery's planted-defect cells iii/iv/v stopped firing. *"A false zero reads as 'nothing
  frustrates' — a finding, not an error."* Fixed by `expand_stars`, one canonical face-to-face
  expansion now shared by all **six** consumers of fiber structure (the energy, the meter's
  weight map, the loop finder, three structure-audit functions, the shadow calibration, and
  block adjacency) — five of the six were found only because they went silent; the sixth
  (block adjacency) was found by sweeping for the pattern deliberately.

## What ended it

Commit **`7bac55a`** (2026-08-06 15:59). `edges_from_fibers` now emits one derived apex per
fiber (`apex_id`, a hash of the fiber's own sorted members, prefixed `apex:` so it can never be
mistaken for a slot) and *k* face-edges to it, replacing all-pairs. The apex carries **zero
degrees of freedom its faces do not determine**: consensus `p_bar = (1/k) * sum(p_j)`,
recomputed on every evaluation — no initial state, no entropy term, no update rule of its own.
The gradient reduces to `lambda*w*(k/(k-1))*(p_i - p_bar)` because `sum_j(p_j - p_bar)` vanishes
identically — no apex term appears in either expression. The `k/(k-1)` factor is anchored at
k=2 (a fiber that *is* one declared pair, where the two factorizations must agree exactly): the
commit records that they do, **to the bit: −4.427054 both ways**.

## What was WITHDRAWN when it ended

- The **73% coupling-dominance and 5.6× over-coupling** measurements themselves, superseded by
  the apex-star numbers above (`7bac55a`: "come from that one line").
- An unnamed first implementation, described and withdrawn within the same commit: the apex's
  first version carried three free parameters — a uniform initial state, its own entropy term,
  its own gradient — described as "the class this project deletes," and replaced before landing
  by the zero-degrees-of-freedom derived-consensus form.
- Two `tests/test_engine.py` controls are named in the commit as retired for asserting the old
  shape (a raw edge count) rather than reading through the new expansion — *"asserting the old
  shape is how a real control becomes a fossil of an old implementation."* I did not verify the
  specific control names against the current file; I read the commit message, not its full diff,
  for this line.

## Numbers I looked for and could not find

- **The measurement artifact behind OI-10's "regions were 95% one proposition" and "K's support
  was 61/64 one thing."** Both appear in `seed/CONSTITUTION.md:166-167`; I found no
  `runs/*.json` or test fixture recording either measurement directly, only the constitution's
  citation of them.
- **Any post-apex-star re-run of the substrate-repair retest** (`150a858`, described in
  `02-pre-demotion-substrate.md`). Still absent as of HEAD (`80791f0`).
- **Confirmation, by reading the diff rather than the message, of which two `test_engine.py`
  controls were retired as fossils.**
