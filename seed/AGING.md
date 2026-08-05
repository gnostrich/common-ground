# Aging the fast tape — PROPOSAL, awaiting the operator's ruling

`seed/OBJECT.md` says unpromoted residue ages out. **Nothing ages.** Extraction-tier arrows
accumulate on the fast tape and are never removed, never demoted, and never excluded from
anything. Without a policy the tape becomes a second corpus by accretion — which is NELL at
one remove, and the memory kernel `K` was the whole answer to NELL.

This is a **proposal**. The shape is argued below; the number is not chosen here, because
choosing it silently is the failure class the attachment law names.

## What ages, and what does not

Only **EXTRACTION-tier correspondence claims on the fast tape**. Nothing at CI_RECEIPT or
above ages: those are grounded, and a receipt does not become less true by not being looked
at again. Corpus claims do not age; the slow side is `K`'s business.

## The proposed states

| state | meaning | effects |
|---|---|---|
| **live** | proposed, and either fresh or re-confirmed within the window | enters implied-closure; conditions the window; visible in the atlas |
| **dormant** | unconfirmed and un-re-confirmed for **N walk-visits of its region** | **excluded from implied-closure and from conditioning**; retained in the journal in full; still readable, still countable, still auditable |

Dormancy is **not deletion**. The journal is append-only and nothing leaves it. What dormancy
removes is *load-bearing-ness*: a dormant arrow stops implying composites, stops steering the
walk, and stops shaping what the window says. It can be revived by a single later
confirmation, and a revival is itself a recorded event.

## The clock is visits, not time

Wall-clock aging would punish arrows in regions the walk simply has not reached, which is a
fact about the walk. The clock is **how many times the walk has visited a region containing
that arrow** — so an arrow is only demoted after the medium has had N genuine opportunities
to re-name it and did not. That makes dormancy a statement about the arrow rather than about
the schedule.

## The number, which is the operator's

`N` is not chosen here. What is worth knowing before choosing it:

- The walk already records a related count: `Walk.declines`, how many *different* regions
  declined to name an implied arrow, with `DRIFT_AFTER = 2` marking composition drift. N for
  dormancy should be **strictly larger** than that, since drift is a finding about two hops
  and dormancy is a judgement about one arrow.
- N too small demotes real arrows the medium happened not to mention — and unmentioned is
  explicitly **not** a denial in the region reading discipline, so a small N would quietly
  convert silence into a negative, which the whole format was built to prevent.
- N too large is the current state: no aging, and accretion.
- A first honest measurement: run the walk with aging **recorded but not enforced**, and
  report how many arrows *would* have gone dormant at N = 3, 5, 10. Then N is chosen against
  a distribution rather than against an intuition.

## What must be true before this is enforced

1. The walk logs would-be dormancy for at least one full run without acting on it.
2. A control asserts a dormant arrow is excluded from implied-closure **and** still present
   in the journal — the two halves that make it demotion rather than deletion.
3. A control asserts nothing above EXTRACTION can be aged at all.
4. Revival on confirmation is recorded as an event, so a flapping arrow is visible rather
   than silently oscillating.
