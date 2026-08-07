# Era: pre-null surface

**Span:** 2026-08-06 15:59 (commit `7bac55a`, previous era's end) through 2026-08-07 05:41
(commit `0175806`).

**A note on timing.** This archive entry was commissioned to describe "the era ending right
now" while the null surface was still in flight in another lane, not yet landed — the operator's
own framing for this file was written expecting a placeholder ending, not a commit sha. While
this file was being drafted, the null surface actually landed on this branch (commit `0175806`,
2026-08-07 05:41). I am reporting what actually happened rather than what was expected to still
be in flight, per the instruction to derive era content from the repository itself. The design
record the landing commit itself wrote, `archive/design/2026-08-07-two-coordinate-surface.md`,
names its own supersession point as `SUPERSEDED AT : 80791f0` — the same commit this task was
anchored to — so treating `80791f0` as this era's conceptual reference point and `0175806` as
its actual mechanical close is consistent with how the landing commit describes itself, not a
reinterpretation I invented.

## What defined the era

Everything landed between apex-star and the null surface: the transcript panel (every LM call,
both directions, rendered and cryptographically verified on the page), the clean-state strip
(the render input cut to state + a question, nothing recited), `seed/CONSTITUTION.md` itself
(40 invariants at landing, machine-checked against `seed/OI_REGISTRY.json`), the standing
auditor (read-only, files findings, first run found eight real ones), the Python/Go/Lean chart
scaffolds, and the two-coordinate interaction surface (OI-42/OI-43: objecthood × persistence,
forced and complete) that this era's own ending would go on to delete. See `seed/CHANGELOG.md`
for the full one-line-per-change list across this span.

## Headline numbers, as of HEAD at the point this file was written

- **`seed/OI_REGISTRY.json`** (identical at commit `80791f0` and at current HEAD `0175806` — the
  null surface rewrote OI-41/42/43 in place rather than changing the counts): **43 invariants
  total, 5 WEAK** (OI-2, OI-26, OI-28, OI-38, OI-40), **0 unresolved**. Up from 40
  invariants / 11 WEAK at `seed/CONSTITUTION.md`'s creation (`4a4b238`, 2026-08-06 17:35) — six
  WEAK entries were mechanized in the hours between: OI-19, OI-24, OI-36, OI-30, OI-37, OI-5.
- **`seed/CONSTANT_PROVENANCE.json`**: **26 constants tracked, 22 confessed, 4 derived.** Up
  from 24 tracked / 20 confessed at the sweep's landing (`c1a3dbd`, 2026-08-06 18:55) — the same
  4 derived constants at both readings; every constant added since has landed CONFESSED, not
  derived.
- **Corpus, on disk, read by `tools/restore` on 2026-08-07 (today):** **80,566 slots.**
- **Test suite**, run in isolation at current HEAD (`0175806`) on 2026-08-07: **1,456 tests,
  1 skipped, OK.** (Two earlier runs during this session, both contaminated by concurrent/
  overlapping `unittest discover` invocations — mine and, separately, `tests/test_push_gate.py`
  self-testing the amendment gate by committing and resetting inside this actual repository —
  showed 4 spurious failures in `TheAmendmentGateHasTeeth`, a class that does not exist in
  `tests/test_push_gate.py` at HEAD. A clean, isolated re-run was green. I did not edit
  `tests/`, `engine/`, `ui/`, or `hooks/` at any point.)

## What ended it

Commit **`0175806`** (2026-08-07 05:41), "The null surface: the interface is conversation, and
nothing else." Its own FEATURE-DIFF block:

> **WHAT** — Deleted the entire interaction surface. One box, the answer, the raw LM traffic.
> No mode selector, no retain checkbox, no claim gesture, no ACT speech-reader, no accept, no
> reject.
> **SUPERSEDES** — SPEC §10 + §10a (two-coordinate surface); OI-42 (the 2×2); OI-43 (the
> conservative-direction inversion); OI-41's CLAIMED arrow.

Deleted outright, not made dormant: `engine/mode.py` (97 lines), `engine/claim.py` (103 lines),
`engine/posture.py` (181 lines), the `/claim` endpoint, `_reading_of`, the
`Perturbation.reading` field, and `ACT_GRAMMAR` on the wire. Retired: `tests/test_mode.py`
(209 lines), `tests/test_claim.py` (192 lines), `tests/test_posture.py` (331 lines). Added:
`tests/test_null_surface.py` (170 lines), four new tests including
`TheAUTHORSHIPDoorIsRemovedAndTheAlarmREMAINS` — OI-41's old planted control is kept as a
tombstone so that rebuilding the deleted transfer path would be loud, not silent.

The commit's own argument for why: *"The derivation was sound and the premise was wrong.
Objecthood and persistence ARE independent and binary, and the 2×2 that followed WAS forced —
but neither coordinate needed a SURFACE, because both collapse into the physics."* Every
utterance now enters the tape directly as an authored record; what becomes of it is decided
downstream by aging and by K, from measurement, not pre-declared by a checkbox before any
measurement happens.

## What was WITHDRAWN when it ended

- **SPEC §10 and §10a** (the two-coordinate interaction surface) — superseded. The full prior
  text is kept verbatim, with its own header explaining what replaced it and why, at
  `archive/design/2026-08-07-two-coordinate-surface.md` (that file records `SUPERSEDED AT :
  80791f0`).
- **OI-42**, previously "THE INTERACTION SURFACE IS TWO BINARY COORDINATES PLUS ONE ARROW" —
  rewritten in place (not deleted; the OI number is reused) to state instead "THE INTERFACE IS
  CONVERSATION; SORTING IS THE MEASURE."
- **OI-43**, the conservative-direction inversion for TOLD-vs-read modes — marked in place,
  verbatim in `seed/CONSTITUTION.md`: *"SUPERSEDED BY THE NULL SURFACE (2026-08-07). Kept as
  the record of a correct argument about a mechanism that no longer exists."*
- **OI-41's CLAIMED arrow** — the authorship-transfer path itself is deleted ("gone, not
  locked"); OI-41's statement and its planted control remain, restated as the tombstone that
  would catch anyone rebuilding it.
- Two test controls were *restated* rather than deleted, and the commit names both explicitly
  as OI-26 instances (a caution re-examined once the defect it guarded against was fixed):
  `test_ui_surface.py`'s requirement that `id="retain"` be visible, and
  `test_ui_browser.py`'s render-smoke test, which drove `render` through the retain checkbox
  and now drives it through reset instead.

I found no claim in this commit, or elsewhere in the tree, describing a *quantitative* finding
that triggered the null surface (no measured percentage, no before/after count) — it reads as a
purely conceptual/design correction ("the premise was wrong"), not a measurement-driven repair
like the previous two eras. I am reporting that absence rather than inventing a number to fill
it.

## Numbers I looked for and could not find

- **A dated entry in `seed/CONSTITUTION.md`'s own AMENDMENTS section.** B4 requires this
  document to change "ONLY by operator ruling, recorded as a dated amendment with the
  superseded text retained." OI-41/42/43 were substantively rewritten by this commit, but as of
  the version of `seed/CONSTITUTION.md` I read, the AMENDMENTS section still reads *"(none yet
  — B4 applies: operator ruling only, superseded text retained)."* I am not able to determine
  from the repository whether this is a pending follow-up in the same lane or an oversight; I
  am not the owner of that file and did not touch it.
- **A quantitative before/after measurement motivating the null surface**, of the kind both
  prior eras had (the demotion's pair/fiber counts, apex-star's 73%/5.6×). I could not find one;
  see the note above.
