# TYPES.md — claim-forms and thin type ontology

Frozen under `SEED.lock`. Changing this file moves addresses (a slot id is
`hash(nu(surface), type)`) and is therefore **plastic** under gate 4: it requires a
logged seed-morphism event and a cold re-anneal.

## Claim-forms

Exactly four. A slot's `type` is one of these strings, verbatim.

| Form | Admits | Test | Example (English) | Example (Lean) |
|---|---|---|---|---|
| `assert` | A proposition put forward as holding. | Can be true or false; is not stipulating a meaning. | "Positivity is preserved under composition." | `theorem comp_pos : ...` |
| `define` | A stipulation fixing the meaning of a term. | Introduces a term; cannot be false, only ill-formed or unused. | "A cone is positive when ..." | `def Cone.IsPositive ...` |
| `conditional` | A claim whose content is a dependency. | Has a discernible antecedent and consequent. | "If the kernel accepts, the statement is certified." | `theorem foo (h : P) : Q` |
| `normative` | A claim about what ought to be done or held. | Contains a deontic operator; not settled by any proof. | "No floor is read before its null cells pass." | (none — Lean chart admits no normative slots) |

### Assignment rule (deterministic, frozen)

Assignment is performed by `engine/normalize.py:classify` and is a total function of the
normalized surface. The rule is ordered; the first matching clause wins.

1. If the chart is `lean` and the declaration head is `def`, `abbrev`, `structure`,
   `class`, `instance`, `inductive`, or `notation` → `define`.
2. If the chart is `lean` and the declaration head is `theorem`, `lemma`, `example`, or
   `axiom`: `conditional` if the statement has at least one explicit binder before the
   final colon, otherwise `assert`.
3. If the surface contains a deontic marker from the frozen marker set → `normative`.
4. If the surface contains a conditional marker from the frozen marker set → `conditional`.
5. If the surface contains a definitional marker from the frozen marker set → `define`.
6. Otherwise → `assert`.

The three marker sets are frozen in `seed/CONSTANTS.json` under `markers`. They are part
of the addressing function; editing them is plastic under gate 4.

## Thin type ontology

The ontology is deliberately thin: it carries only what addressing needs. It is not a
domain ontology and makes no commitments about the subject matter of any claim.

- **Chart** — `english` | `lean`. A chart is a normalization regime plus a marker set.
  The code chart is deferred to v0.5 (D2). Charts do not nest and are not ordered.
- **Slot** — `sha256(nu(surface) || 0x00 || type)`. The atom of address. Two surfaces
  occupy the same slot iff their normalizations and types are identical. Slots are
  chart-separated in practice because `nu` prefixes a chart tag.
- **Fiber** — an unordered set of at most `m = 5` slots held to be potentially
  co-referring. A fiber is a *hypothesis about co-reference*, never an identification:
  slots in a fiber keep distinct addresses and distinct b-values. Fibers may cross charts;
  that is what makes a Lean↔English loop possible.
- **b-value** — the value a slot carries, drawn from the Belnap four: `N` (neither),
  `F` (false), `T` (true), `B` (both). `B` is the load-bearing one: it is how a slot
  records that it is *genuinely* contested rather than merely undetermined. A settled
  state assigns each slot a distribution over these four.
- **Block** — a maximal connected component of the equivalence-prior graph `Q` restricted
  to slots carrying at least one delta. Settlement runs per block.
- **Warrant** — a tier plus a detail string. Tiers are ordered; only the top two are
  clamp-eligible (gate 3).

## What this file does not fix

- It does not fix the *content* of any lexicon. Lexicons live in `seed/LEXICON/`.
- It does not fix loop structure. Loops are declared in `registry/PREREG.md`.
- It does not assign truth. Assignment is the settlement's job, and at v0 casting is
  withheld except where a block's fiber contains a kernel clamp (KICKOFF §3, P3).
