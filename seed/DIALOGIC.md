# THE DIALOGIC ATTACHMENT PROTOCOL — lane spec, UNBUILT

**Status: SPEC'D, NOT BUILT.** Nothing in `engine/` implements this. It is written down so the
design is on the record before any code exists, and so `SPEC.md` Part IV can name it.

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
