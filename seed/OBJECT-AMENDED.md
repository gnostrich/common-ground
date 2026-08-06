# common-ground — CORE SCHEMATIC, AMENDED (canonical)

**THIS SUPERSEDES `seed/OBJECT.md`.** The attachment law and the diagnostic protocol below
are **binding, not advisory** — they are enforced in code by `engine/static_checks.py`
(`check_move_citation`, `MECHANISM_CLAIMS`) and by `tests/test_amendment.py`, in the same
shape as the rest of the gate suite. Where this document and `OBJECT.md` differ, this one
governs; `OBJECT.md` is kept for its history and carries a superseded banner.

Authoritative. Read this BEFORE debugging anything. Recorded verbatim from the operator;
the commentary at the end is Claude's and is labelled as such.

The whole system is ONE object read at different levels.
Structure = (base) + (thing living over the base) + (a measure on it).

## THE OBJECT (single level)

| | |
|---|---|
| **Base** `B` | small category. OBJECTS = charts. MORPHISMS = typed translations (declared correspondences). |
| **State** `S : B → Set` | well-typed expressions per chart; functorial. |
| **Directions** `π : D → States` | discrete fibration; fibre = admissible edits. |
| **Measure** `p ∝ e^{−βE}` | Gibbs measure on States. |
| **Dynamics** | settling = entropic mirror descent + monotone descent certificate. *(resolvent / spectral-gap framing is STRUCTURAL-RHYME, not built)* |
| **Invariant** `hol : Π₁(B) → Aut(Sem)` | holonomy of round-trip translations = the floor. |

**WARRANT (constitutional):** only top-tier (kernel / test-receipt) may CLAMP. Priors enter
`E` as energy, never clamp.

## THE ATTACHMENT LAW (the amendment — this was missing)

IDENTITY and ATTACHMENT are different questions and MUST NOT share a rule.

```
IDENTITY   — "which object is this?"       = exact. hash(nu, type). Gate 1. Correct.
ATTACHMENT — "what morphisms does it have?" = PROPOSED and GATED. Never inherited
                                              from the identity rule.
```

A typed input (a query, a bias, a fragment) is an OBJECT with NO MORPHISMS until morphisms
are proposed for it. An object with no morphisms:

- has no image under any functor
- lies outside `Π₁(B)`
- cannot propagate, cannot be relaxed toward, cannot appear in any `hol`

This is not a bug. It is what "isolated object" MEANS. Any design where free-form input must
first match an existing address has silently made ATTACHMENT = IDENTITY, and has therefore
guaranteed that novel input is an isolated object forever.

**THE ONLY LEGAL SOURCE OF MORPHISMS** is a proposer (the LM), entering through the one inlet
at EXTRACTION tier, gated. This is true for prose↔code arrows and it is EQUALLY true for
attaching a typed query. Same mechanism, different job. There is no second attachment
mechanism and none may be invented.

## FAST / SLOW (two measures on the SAME D — Mori-Zwanzig)

| | |
|---|---|
| `p_fast` | live tape: proposals + verdicts. |
| `p_slow` | the corpus. |
| `K : fast → slow` | MEMORY KERNEL = the gated mint. Promotes IFF `Hankel(residual) > second-FDT floor` AND conservative-extension. |

This is what stops NELL.

## MULTIPLE PERSONS (same schema, base swapped up a level)

| | |
|---|---|
| `Base'` | persons |
| `T_{ij}` | inter-person translation profunctors |
| Joint `E` | `Σ E_i + Σ λ·d(T_{ij}(S_i), S_j)` |
| Invariant | `α ∈ H²(SocialGraph, Aut(Atlas))` |

Single-person is the `K=1` case. Nothing new is introduced.

## THE THREE MOVES (the only legal extensions)

1. **SWAP THE BASE** (add a chart; persons instead of modalities)
2. **ADD A MEASURE** (fast alongside slow)
3. **ADD A MORPHISM** (`K`; `T_{ij}`; a translator edge; a proposer into `D`)

If a proposal is none of these, it is creep and is REJECTED.

## DIAGNOSTIC PROTOCOL (mandatory — read the diagram before the code)

When something "doesn't work", answer these IN ORDER, BEFORE reading any code:

- **Q1.** Is the thing an OBJECT or a MORPHISM?
- **Q2.** Does it HAVE morphisms? If it is isolated, nothing will propagate — and no amount
  of engineering will change that. Fix = propose morphisms, not tune code.
- **Q3.** What is the SHAPE of the relevant subgraph?
  forest / stars → `Π₁` is trivial → holonomy is NECESSARILY zero. More arrows CANNOT help.
  Need a different relation. has cycles → holonomy is measurable.
- **Q4.** Which of the three moves would the proposed fix be? If none: reject.
- **Q5.** Does the fix create a SECOND mechanism for something the object already has one
  for? If yes: reject. (Two attachment rules, two write paths, two proposers — all forbidden.)

## KNOWN STRUCTURAL FACTS (do not re-derive, do not "fix")

- A docstring belongs to exactly ONE declaration ⇒ declaration-granularity correspondence
  produces ONLY stars ⇒ a forest ⇒ zero holonomy, always.
- Cycles require: one English slot corresponding to ≥2 declarations, OR a third chart in the
  loop, OR a clamp (needs no cycle at all).
- An isolated object never propagates. Novel phrasing is isolated until attached.

## FAILURE MODES ALREADY PAID FOR (do not repeat)

- Similarity substituted for a declared relation (Jaccard fibers). **DELETED.**
- Term overlap in the ANSWER path. **DELETED.** (Navigation is not evidence.)
- Docstrings claiming mechanisms the call graph lacks ("index", "settlement runs", "provably
  identical"). Gate 10 — extend to MECHANISM claims.
- A rule inherited where none was specified (attachment ← identity). **THE AMENDMENT.**
- Refining a wrong mechanism instead of asking the diagram whether it can work.
- **A malformed region extracts REPETITIVELY, not merely badly.** The 2.7%-acceptance run
  wrote 1,455 journal records over only 63 distinct pairs — it named the same handful again
  and again. Repetition is the signature; counting records rather than pairs is what hid it,
  and reported the quarantine set as twenty-three times its real size.
- **A tally kept where the finding belonged.** Twice in one day: a drift COUNT logged without
  the drifting triple, and an answer journalled without the region it was named in. Both made
  a real measurement unrecoverable after the process exited. If a number is worth logging, the
  thing it counts is worth logging.
- **A GUARD NUMBER THAT MEASURED THE MACHINERY INSTEAD OF THE CLAIM.** The acceptance guard
  was a function of generation verbosity: `named_pairs` deduped repeats and `len(void)` did
  not, so acceptance compared a deduped numerator against a repetition-inflated denominator.
  It swung 97% -> 2% -> 6% across walk steps according to how much the model had repeated
  itself, not according to what it had resolved. This is the gate-10 class operating at the
  METRIC level — a number claiming to measure the field while measuring the apparatus.

  **Second occurrence of the same shape.** The first was K's Hankel input: the block settling
  trace is a geometric decay whose rate is the solver's schedule, so its top singular value
  was a property of the optimizer and identical across every site in a block. A guard fed by
  model output, and a guard fed by solver output, both reported on their own machinery.

  **STANDING CONTROL SHAPE, from the pattern:** any metric fed by model output must be
  INVARIANT TO VERBOSITY AND REPETITION — computable from the set of distinct things named,
  never from the count of lines emitted. Any metric fed by solver output must be invariant to
  the solver's schedule — measured ACROSS separate settlements, never within one trace. A new
  metric ships with the invariance its input demands, asserted, or it is not a guard.
  Controls: `tests/test_region.py:AcceptanceMustNotMeasureVerbosity`.

  **AND A MINIMUM n, from today's data.** Every per-model rate stated this session flipped
  when the sample grew tenfold — `same_claim` read 21% at n=24, 7.2% at n=2,872 and 12.07% at
  n=23,992; repetition read 2.12 at n=2,872 and 8.98 at n=23,992, back to the lite era's 8.83.
  Twice in one session, in the same direction: a reading was reported as a finding.

  So: **no per-model or per-era rate is reportable below a declared minimum n, and a rate at
  n is a READING until it has held to ~10n.** The flips happened at exactly 10x, so 10x is
  the stability the data itself demands. Below that, report the number with its n and call it
  a reading; above it, call it a finding. `engine/battery.py:MIN_RATE_N` carries the number
  and `Sample` refuses to state a rate under it.

- **`openrouter/auto` silently routed the whole corpus to a LITE model.** 448 of 465 calls
  went to `google/gemini-2.5-flash-lite`, which on one pinned region emitted 1,789 arrow lines
  covering 51 distinct pairs — 35 repeats each — and **zero `same_claim` in any of them**. The
  same region, same prompt, same temperature: `gemini-2.5-flash` gave 24 lines / 24 distinct
  pairs / 5 `same_claim`; `claude-sonnet-4` gave 16/16/2; `gpt-4o-mini` gave 15/15. Every
  pinned model has repeats-per-pair of exactly 1.0.

  `same_claim` is the ONLY loop-eligible relation, so a model that never emits it cannot grow
  a fiber, cannot close a cycle, and cannot produce a floor. **A model selector is a mechanism
  parameter, and `auto` means the mechanism was chosen by a vendor's cost heuristic per call.**

  **WITHDRAWN, on corpus-scale data.** I also claimed the forest topology — 359 of 367
  components trees, only 8 cycles in 16,564 arrows — was downstream of that routing default.
  It is not. The first pinned-model tranche gives `same_claim` at **7.2%** (n=2,872) against
  the lite era's **8.4%** — slightly LOWER, not higher. Repetition was real and is fixed
  (8.83 -> 2.12 records per distinct pair, corpus-wide); the identity scarcity was never the
  transport's doing.

  **The error was generalising from one region.** A single pinned probe showed 5 `same_claim`
  in 24 lines (21%) and I read a corpus-wide cause off it. n=24 against n=2,872. The same
  probe's repetition finding held at scale and its kind-distribution finding did not, which is
  exactly what a sample of one region can and cannot support. If 7.2% holds as clean stock
  grows, eight loops is roughly the truth and the floor story is about those loops DEEPENING,
  not multiplying.

- **A process that cannot say what phase it is in.** The walk burned four minutes in an eager
  global closure before its first print, and "silent" meant "unknown whether loading or
  wedged" for twenty-two minutes. This is the process-level form of a docstring claiming a
  mechanism the call graph does not contain.

## WHAT IS OURS vs OCCUPIED (keep honest)

base+state functor ≈ Spivak ologs *[occupied]*. Gibbs on relations ≈ MLN/PSL *[occupied]*.
H¹/H² ≈ Hansen-Ghrist discourse sheaves *[occupied]*. LM-proposer+kernel gate ≈ LeanDojo loop
*[occupied]*. Modular-forms-from-resolvent *[structural-rhyme, NOT claimed]*.

**THE DELTA (ours):** the null battery + constitutional gates enforced IN CODE. The maths is
occupied; the enforcement is not. That is the only headline.

---

## Where each clause is enforced — CLAUDE'S NOTE, not the operator's

| Clause | Enforced at |
|---|---|
| ATTACHMENT ≠ IDENTITY | `engine/attach.py`; `tests/test_attach.py:ABiasAttachesByProposalNotByAddress` |
| only legal source of morphisms is the proposer | `tests/test_attach.py:TheProposerSeesTheCorpusPrompt` — same `PROPOSE_SYSTEM`, same body |
| attachment at EXTRACTION, gated | `tests/test_attach.py:AttachmentIsAnArrowUnderTheSameRules` |
| no second attachment mechanism (Q5) | `tests/test_relax.py:SilenceIsAResultNotADegradation.test_there_is_no_second_mechanism_to_fall_back_to` |
| no term overlap in the answer path | same control, on the import graph |
| mechanism claims need the machinery | `engine/static_checks.py:MECHANISM_CLAIMS`; `tests/test_relax.py:GateTenCatchesAMechanismClaim` |
| relaxation travels declared arrows only | `tests/test_relax.py:EveryCompiledFactTracesToDeclaredStructure` |
| only top tier may clamp | `engine/settle.py` re-checks gate 3 at every settle |
| a mechanism fix cites its MOVE and its Q | `engine/static_checks.py:check_move_citation`; `tests/test_amendment.py` |

**One open reading, flagged rather than assumed.** The amendment says morphisms enter
"through the one inlet at EXTRACTION tier, gated". Attachment arrows are built by the
proposer at EXTRACTION and are laid over a READ view only — they are never written to the
tape, because `tests/test_inbound.py:InboundIsReadSideOnly` asserts the read path cannot
call `.propose(`. So they are gated in the sense that they cannot ground, clamp or promote,
but they do not physically traverse `FastTape.propose`. Whether an ephemeral read-side arrow
must still pass the inlet is the operator's ruling to make; it has not been made, and this
note exists so the question is not silently answered by the implementation — which is
precisely how attachment inherited the identity rule in the first place.
