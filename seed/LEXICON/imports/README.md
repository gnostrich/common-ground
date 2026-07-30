# seed/LEXICON/imports — commodity lexicons

Commodity, replaceable, and hashed into `SEED.lock` like everything else in `seed/`.
These are inputs to the normalizer's final step, so **any edit here moves addresses** and is
plastic under gate 4: logged seed-morphism event plus cold re-anneal.

Nothing in this directory can clamp (gate 2). A lexicon entry enters `F` as a term in
`lexicon_energy` and as an edge in the equivalence-prior graph `Q`, and that is all it can
ever do.

## Expected contents

| File | Chart | Shape |
|---|---|---|
| `english_synsets.json` | `english` | wordnet-grade synsets: `{"members": [...], "key": "..."}` |
| `lean_namespaces.json` | `lean` | Mathlib namespace dump: `{"alias": "...", "canonical": "..."}` |

Both are optional at v0. When absent, the normalizer's map step is the identity and the
prior graph carries only edges derived from pre-minted entries and fiber hypotheses. The
engine reads whatever is present and hashes it; it does not fetch, and per KICKOFF §7.5 it
must not pull live during a run.

## Format

`english_synsets.json`

```json
{
  "schema": "common-ground/synsets/v0",
  "entries": [
    { "key": "positive-cone", "members": ["positive cone", "positivity cone"], "weight": 1.0 }
  ]
}
```

`members` are matched against the *normalized* surface, longest first, and rewritten to
`key`. `weight` scales the equivalence-prior edge introduced between slots that differ only
by a substitution from this entry. Omitted weight defaults to `1.0`.

`lean_namespaces.json`

```json
{
  "schema": "common-ground/namespaces/v0",
  "entries": [
    { "canonical": "Mathlib.Order.Cone.IsPositive", "aliases": ["Cone.IsPositive"], "weight": 1.0 }
  ]
}
```

## What must not go here

Anything asserting that two claims are *the same claim*. A lexicon says two surfaces are
interchangeable; it does not say two claims agree. Co-reference across charts is a fiber
hypothesis (`seed/TYPES.md`), it is capped at `m = 5`, and it is settled — never asserted by
a dictionary entry. If a lexicon edit would make a contested block stop being contested,
that is the signature of a dictionary artifact, which is exactly what PREREG R4 tests for.
