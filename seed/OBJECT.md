# common-ground — CORE SCHEMATIC (SUPERSEDED)

> **SUPERSEDED by `seed/OBJECT-AMENDED.md`.** That document adds the ATTACHMENT LAW — identity
> and attachment are different questions and must not share a rule — and the mandatory
> DIAGNOSTIC PROTOCOL, both of which are binding and enforced in code. This file is kept
> because the structure below is unchanged and its history is worth reading; where the two
> differ, the amended one governs. Nothing here is a licence to skip the protocol.

# common-ground — CORE SCHEMATIC (canonical, singular object)

**North-star. Constitutional.** The whole system is ONE object read at different
levels — not a toolbox. Structure = **(base) + (thing living over the base) + (a measure
on it)**. Everything below is that structure, re-indexed. If a proposed addition is not one
of the THREE MOVES, it does not belong. Belonging is enforced in code by the three-moves
audit (`engine/three_moves.py`); this document is the source of truth it classifies against.

---

## THE OBJECT (single level)

| Part | Definition |
|---|---|
| **Base B** | a small category of modalities/charts (objects = charts; morphisms = typed translations) |
| **State S : B → Set** | current well-typed expressions per chart; functorial (`S(g∘f) = S(g)∘S(f)` — the glue law) |
| **Directions π : D → States** | discrete fibration; fibre = admissible edits (translate \| add \| refine \| merge \| delete) |
| **Measure p ∝ e^{−βE}** | Gibbs measure on States; E scores coherence |
| **Dynamics (settling)** | **entropic mirror descent + a monotone descent certificate.** The resolvent / spectral-gap framing — `L`, `R(z) = (zI−L)⁻¹`, mixing time — is a **[structural-rhyme], NOT built**; the honest mechanism is mirror descent to stationarity, and resolvent notation must not drift back in. |
| **Invariant hol : Π₁(B) → Aut(Sem)** | holonomy of round-trip translations [= H¹, the cold-floor / genuine-contest layer] |

**WARRANT** (not drawn in the maths, but constitutional): every element of D carries a
warrant tier; only top-tier (kernel / test-receipt) may **CLAMP** (Dirichlet boundary).
Priors (lexicon, Q-edges) enter E as energy, never clamp.

---

## FAST / SLOW (two measures on the SAME D — Mori–Zwanzig layer)

| | |
|---|---|
| **p_fast ∝ e^{−β_f E}** | live tape: proposals (excitation) + verdicts (annealing) |
| **p_slow ∝ e^{−β_s E}** | the corpus (durable settled section) |
| **K : fast → slow** | MEMORY KERNEL = the gated mint. Promotes a fast residual into slow corpus **IFF** `Hankel(residual) > second-FDT floor ∧ conservative-extension`. Unpromoted residue ages out. (This is what stops NELL: the tape enters the corpus only through the gate.) |

NOT a new base, NOT a new bundle — a second measure on D + one morphism K. That is why it
is still THE object, not a new box. **K is LIVE (operator-authorized, mint_enabled=true).**
`MintController.consider` promotes fast→slow only through the gate above, every promotion
logged and reversible; a planted-noise control asserts noise below the floor never promotes.
The gate is the whole safety — the NELL hazard is fenced by Hankel ∧ conservative, not by an
off-switch. With `mint_enabled=false` the quarantine returns (`act_on_mint` refuses), so the
posture is one seed-flip away in either direction.

**The law.** Information moves only UP the warrant gradient, and only by SETTLING, never by
copying. Every source — me (typing), the LM (Opus), another instance (a translator in front)
— enters through ONE inlet, `engine/inlet.py:FastTape.propose`, at proposal tier. `source_tag`
is provenance only; it never confers warrant. No source writes past the inlet. **Warrant
rises in exactly one place: the gate (K).** The single inlet is one move-3 proposer morphism —
me/LM/instance are sources through it, not three morphisms (the three-moves audit asserts
one), and its one write-path is AST-asserted in `tests/test_inlet.py`.

---

## MULTIPLE PERSONS (SAME schema, base swapped up one level)

| | |
|---|---|
| **Base' = persons** (B ↓ I); fibre over person *i* = that person's whole object above |
| **Coupling T_{ij} : States_i ⇸ States_j** | inter-person translation profunctors |
| **Joint E** | `Σ_i E_i + Σ_{i~j} λ · d(T_{ij}(S_i), S_j)` |
| **Joint p ∝ e^{−βE_joint}** | → auto-communication = relaxation to joint equilibrium |
| **Invariant α ∈ H²(SocialGraph, Aut(Atlas))** | the 2-cocycle [= Hansen–Ghrist discourse-sheaf class; OCCUPIED] |

Same three parts, indexed one level up. Single-person is the **K=1 special case** (what is
built today). Nothing new is introduced.

---

## THE THREE MOVES (the ONLY legal ways to extend the object)

1. **SWAP THE BASE** — e.g. modalities → persons (single → social); add a chart (English, Lean, tabular, conversation, …)
2. **ADD A MEASURE** — e.g. fast alongside slow (the MZ timescale split)
3. **ADD A MORPHISM** — e.g. K (memory kernel), T_{ij} (coupling), a translator edge, an LM proposer INTO D, a verdict function feeding K

**TEST OF BELONGING:** if a proposed feature cannot be written as swap-base / add-measure /
add-morphism, it is jack-of-all-trades creep and is **REJECTED**. Charts are move 1.
LM-in-the-loop is move 3 (a proposer INTO D, extraction-tier, never clamps). Conversation
segmentation is move 1 (a chart). Fast/slow is move 2. Verdict-function-as-content is move 3
(a morphism feeding K). This test is executable: `engine/three_moves.py` classifies every
registered extension and fails on any that fits no move.

---

## WHAT IS "OURS" vs OCCUPIED (keep honest)

| Piece | Prior art |
|---|---|
| base + state functor | ≈ Spivak ologs / categorical DB [occupied] |
| Gibbs measure on relations | ≈ MLN / PSL [occupied] |
| H¹ holonomy / H² cocycle | ≈ Hansen–Ghrist discourse sheaves [occupied] |
| LM-proposer + kernel gate | ≈ LeanDojo / theorem-prover loop [occupied] |
| modular-forms-from-resolvent | [structural-rhyme — NOT claimed] |

**THE DELTA (ours):** the null-battery + constitutional gates enforced **IN CODE** — warrant
tiers, positive controls, cold-floor measured loop-side, mint = K gated, and object-
singularity itself made a measured property by the three-moves audit. The diagram's maths is
mostly occupied; **the enforcement is not.** That is the only headline.
