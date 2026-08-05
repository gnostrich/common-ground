# common-ground — CORE SCHEMATIC (canonical)

**AMENDMENT: attachment law + diagnostic protocol.**
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

**One open reading, flagged rather than assumed.** The amendment says morphisms enter
"through the one inlet at EXTRACTION tier, gated". Attachment arrows are built by the
proposer at EXTRACTION and are laid over a READ view only — they are never written to the
tape, because `tests/test_inbound.py:InboundIsReadSideOnly` asserts the read path cannot
call `.propose(`. So they are gated in the sense that they cannot ground, clamp or promote,
but they do not physically traverse `FastTape.propose`. Whether an ephemeral read-side arrow
must still pass the inlet is the operator's ruling to make; it has not been made, and this
note exists so the question is not silently answered by the implementation — which is
precisely how attachment inherited the identity rule in the first place.
