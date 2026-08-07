# THE DIALOGIC ATTACHMENT PROTOCOL — lane spec

**Status: PART ONE BUILT (2026-08-07), PART TWO SPEC'D.** `engine/dialogue.py` implements the
protocol below; `tests/test_dialogue.py` carries its controls under the same numbering. THE
FOURTH DOOR, added below, is spec'd and not yet built — written down first, as the protocol
above it was.

**THE PRINCIPLE THE MECHANICS SERVE (OI-45).** The dialogue settles toward the **minimal
consistent extension** of the corpus — not toward the corpus as it stands, which is
description, and not toward unbounded growth, which is bulk. **Expansion is licensed only by
measured frustration**: residuals the field can point at. Every admitted step must resolve more
frustration than it introduces. The four decidable checks below are this principle's
ENFORCEMENT, never its definition — a future check is DERIVED from the principle against a real
observed instance, never invented against a hypothetical. Stated here so the mechanics cannot
outlive their rationale, which is OI-26 applied in advance instead of after the fact.

**WATCH:** "minimal" has no explicit check. A valid but larger-than-needed completion — two
terms where one covers — is not prevented today; apex-collision, residue and the aging economy
squeeze it in practice. If over-completion is ever seen surviving the checks, that instance is
the derivation seed. Nothing is built until it is.

**CHAT ONLY.** This protocol is for INTERACTIVE perturbations. **The daemon's extraction stays
coordinate-only** — the unattended walk never runs a dialogue, never reads prose for arrows,
and is untouched by anything here. Two paths, and the interactive one is the only one that
gets to be conversational.

---

## THE PROTOCOL

**CITED-PROSE ATTACHMENT.** In an interactive perturbation the medium may answer in prose, and
arrows are extracted from **citation coordinates + kind tokens only** — `[7] -refines-> [12]`
— **never from the words**. The prose is for the operator to read. The coordinates are what
the engine consumes, and a sentence with no coordinates yields no arrow however persuasive it
is. This is OI-16 (grammar over instruction) applied to a conversational channel: the medium
may write freely, and only the grammar crosses the boundary.

**TESTIMONY AT ZERO WARRANT.** What the medium says in dialogue is retained as a declared
journal record kind — `testimony` — carrying **no warrant at all**. Not EXTRACTION: extraction
is what a parsed triple gets. Testimony is the prose itself, kept because the trajectory
matters, and it can never ground, contest, promote or compose. It is corpus-inert in exactly
the way `bears_on` and the medium chart's glosses are. *(Part II-B taxonomy gains this kind.)*

**INTERROGATION TURNS ARE GENERATED MECHANICALLY FROM STRUCTURE.** The next question is chosen
by the graph, never by a fluency judgement:

- **implied-unaddressed pairs** — composition implies a relation the journal has never asked
  about. That pair is the highest-value question in the graph and it is already computed.
- **scaffold-adjacent declines** — a `depends_on` neighbour of something the medium just
  declined. The decline is a measurement; its neighbourhood is where the next measurement is.

**Never "that answer seemed thin, ask again".** A turn selected because a reply read as
unsatisfying is a fluency judgement steering the corpus, which is the medium grading itself.

**TURN-BUDGETED.** A dialogue has a declared maximum. An unbounded interrogation is the
candidate-list loop with better manners — a budget-capped interrogation beside the sampler is
exactly what Q5 deleted once already.

**REVISIONS ARE ERA'D WITHIN THE CONVERSATION; THE TRAJECTORY IS KEPT.** If the medium revises
a claim at turn 6 that it made at turn 2, both survive with their turn recorded. The
records-vs-pairs law at dialogue level: **the unit is the distinct claim, not the utterance**,
so a medium that restates the same thing five times contributes one claim and five records,
and every count says which it is counting.

---

## CONTROLS (all planted, none written)

1. **No arrow from words.** AST sweep on the dialogic extractor: no tokenizer, no similarity,
   no fluency scoring. A planted "extract an arrow from a persuasive sentence with no
   coordinates" = RED.
2. **Testimony never grounds.** A planted testimony record reaching settlement, contest, K's
   candidate set, or a promotion path = RED.
3. **Turns come from structure.** A planted turn generator that selects on reply length,
   confidence words, or anything read off the prose = RED.
4. **The budget binds.** A planted dialogue exceeding its declared turn maximum = RED.
5. **Trajectory kept, counted correctly.** A planted five-restatement dialogue must report one
   claim and five records; a count that reports five claims = RED.
6. **The daemon is untouched.** A planted dialogic call on the unattended walk path = RED.

## WHY IT IS NOT BUILT YET

It is a new lane and the queue ahead of it is: deploy + the six-prompt battery table, the three
mechanizable WEAK entries (OI-19/24/36), the scaffold settlement demo, python/go scaffolds, the
lexicon lane. This file exists so that when it is built, it is built to a design that was
written down first — OI-28: reasoning designs, measurement tripwires.

---

# THE FOURTH DOOR — synthesis nominations and naming-as-settlement

**Status: SPEC'D, NOT BUILT.** Amended before the code, as part one was.

## CLASSIFICATION, first

**No new mechanism.** Three existing ones gain a case:

- a new **TESTIMONY subclass** — `synthesis-candidate` / `term-candidate`. Testimony stays off
  the warrant poset entirely, unpromotable BY TYPE, exactly as landed;
- a new **RESIDUAL class** for the interrogator — *lexical frustration*. The same
  structural-residual machinery, one more decidable source beside implied-unaddressed and
  contested;
- **the operator's signature remains the only content mouth.** Unchanged.

## THE TWO-MOUTH LAW

New objects arise from exactly two mouths: **the operator's**, and **the measure's own
quotients** (plus ruled ingestion, which is the operator's mouth at a distance). **The medium
never mints.** It may NOMINATE, and a nomination reaches the field only through the operator's
signature or it decays with the testimony that carried it.

## 1. SYNTHESIS NOMINATIONS — the fourth legal birth, by nomination and never by mint

Testimony may contain a **candidate synthesis**: a proposition resting on cited claims that
none of them states — *"these jointly imply X [3][7][9]"*. It is FLAGGED as a
`synthesis-candidate`: the recorded testimony plus its citation footprint.

**It enters nothing.** No slot, no arrow, no warrant. **The extractor is unchanged** — an index
the field never showed is still void — and the candidate lives only in the testimony record.

**SURFACING.** Candidates are offered to the operator in the answer's scope view, and are
re-surfaceable by the walk later: *"the dialogue of ⟨date⟩ nominated: 'X' — resting on
[3][7][9]."* The operator **claims** (restates in their own words → their own record, normal
inlet, authorship) or **ignores** (it fades with the testimony).

**THE INFORMED OFFER.** Identity and redundancy checks run on the candidate BEFORE it is
offered — all declared-fact machinery, zero similarity:

- exact/term-landing on the candidate text: if its ν already exists, the offer says so —
  *"this already exists as [12]; claiming adds an event, not a slot."*
- if its footprint matches an existing claim's rest-on set, or fibers with one, the offer says
  which claim.

## 2. VOCABULARY — anchor where covered, mint where measured

Offers are **phrased through existing apexes** wherever the candidate's footprint touches
concepts the operator's vocabulary already names. The check is **footprint-to-fiber membership
— declared structure, never word-matching.** This kills renaming-the-known.

Where the footprint touches structure **no apex names** — a measured gap in the idiolect — the
**term itself** is nominated: *"this recurring structure across [3][7][9][14] has no name;
proposed: 'mode-splitting'."* Multiple candidate words for one gap collapse to **ONE nomination
with alternatives**: the footprint is the identity, and words are candidate surfaces for it.

Terms enter the idiolect **only by operator signature** — claim, rename-in-the-offer, or
ignore-to-fade. A claimed term becomes an apex-name of the operator's.

## 3. NAMING AS SETTLEMENT — the loop anneals language

**LEXICAL FRUSTRATION is a first-class interrogator residual.** Apexless fiber-clusters and
uncovered synthesis-footprints join implied-unaddressed and contested in the residual set. The
interrogator — still parameter-blind to prose — may ask: *"the structure at [3][7][9] has no
name; name it or decompose it through existing apexes."*

A proposed term is a **TRIAL COORDINATE**, stressed across turns by **decidable checks only**:

| check | question | what a failure means |
|---|---|---|
| **coverage** | does its claimed footprint hold when settled? | the name outran the structure |
| **apex-collision** | does it land on an existing fiber? | synonym — decompose, do not mint |
| **split** | do its citations span what the field measures as several clusters? | two structures: two names, or a refinement |
| **residue** | does it leave measured structure uncovered? | the residue IS the next question |

**THE EXIT CONDITION INCLUDES VOCABULARY-CONSISTENCY.** The loop may not close short of budget
while measured structure in the touched region sits unnamed and un-decomposed. **Budget
exhaustion with open lexical residue is a LEGAL, RECORDED ending** — *"named: 2, open: 1"* —
never a silent one.

What reaches the operator's signature is therefore **pre-annealed**: names converged,
alternatives already collapsed by the process, coherent with the field.

## CONTROLS (planted, none written)

- **c1. Mint-attempt.** A candidate introducing an unshown index anywhere in extraction is void
  by the existing condition, AND its testimony is flagged. A code path creating a slot from
  medium-authored text = RED — the two-mouth law's tombstone, extending the one the null
  surface left.
- **c2. Fluency-blindness holds.** The interrogator's lexical questions derive from the four
  decidable checks only. Assert the parameter set as in part one; a question generated from
  reply prose = RED.
- **c3. One nomination per footprint.** Two term-candidates sharing a footprint collapse; a
  planted duplicate yields one record with alternatives.
- **c4. Signature-only entry.** A term or synthesis reaching any slot or apex-name without an
  operator-authored record = RED. Planted: an enthusiastic transcript, with tier and vocabulary
  unchanged after it.
- **c5. Informed-offer identity check.** A planted candidate whose ν exists → the offer names
  the existing address. A planted footprint-match → the offer names the fibering claim.
- **c6. Anchoring is structural.** The footprint-to-apex phrasing uses fiber membership only.
  The standing AST sweep extends to this module: no word-matching, no tokenizer, no similarity.

## WHY THE SEQUENCING SLIPPED, recorded

The order was to land this WITH pieces 2–3, so the exit logic would be touched once. Pieces 2
and 3 landed minutes before the order arrived. The exit condition will therefore be touched
twice. Small, real, and recorded rather than smoothed over.
