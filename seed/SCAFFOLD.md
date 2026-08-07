# THE SCAFFOLD CLASS — declared structure that is not a correspondence

**Status: `depends_on` LANDED. `forked_from` SPEC'D BELOW, then built.** Written before the
code, as OI-28 requires: reasoning designs, measurement tripwires.

---

## WHY THE CLASS EXISTS

`Correspondence.__post_init__` REFUSES an intra-chart arrow, and it is right to — exact
addressing already owns intra-chart identity under gate 1, so an intra-chart correspondence
would re-introduce similarity by the back door. But real declared structure is often
intra-chart: a Lean theorem uses a Lean definition, a module imports a module, an artifact is
forked from the material it was built out of. Making those correspondence kinds would mean
relaxing the guard for everything.

So the Scaffold is a **separate edge type**, and three properties then hold BY CONSTRUCTION
rather than by a flag somebody must remember:

- **HOLONOMY-EXCLUDED** — holonomy is computed over `Correspondence.loop_eligible` pairs. A
  Scaffold is not a Correspondence and has no such attribute to set wrongly.
- **NOT MIS-KINDABLE** — a scaffold relation cannot be stored as `same_claim` / `refines` /
  `instance_of`, because those are values of a field on a different class. The containment
  mistake is *impossible* here rather than forbidden.
- **FIREWALLED FROM K** — K's candidate set and the contest machinery both read
  Correspondences.

Every member of the class is **DECLARED, never inferred**, **reference-tier**, and costs
**zero LM calls**.

---

## MEMBER 1 — `depends_on` (LANDED)

The declared structure inside a chart, parsed from the artifact. See `engine/scaffold.py`,
`engine/scaffold_lean.py`, `engine/scaffold_go.py`. Composition:
`depends_on ∘ depends_on = depends_on`; every cross-composition UNDEFINED.

---

## MEMBER 2 — `forked_from`: ADMITTING DESCENDANTS OF THE CORPUS

### THE GAP

The loop `corpus → export → operator/agent builds something → artifact returns` exists at both
ends and **drops the lineage at the door**. A re-ingested artifact enters as
stranger-statements, and the daemon later pays LM calls to rediscover kinship the build
process knew for free.

Nothing replaces anything. The intent is **admission of descendants**: forks come home as
children beside their parents, family tree intact. The corpus grows by descent.

### THE RELATION

`forked_from` is a Scaffold-class relation, on the `depends_on` template, with these rulings:

1. **DECLARED, NEVER INFERRED.** Parsed from build metadata only — a lineage manifest the
   exporting or building session writes, naming the export-context ID that seeded the work
   and/or a per-file explicit parent address; or commit ancestry where the artifact is a repo
   fork. **No name-matching, no similarity, no content comparison.** The fork declares its
   parent address or the edge does not exist.

2. **RESOLVE-OR-VOID.** An undeclared or unresolvable parent yields **no edge**, and the
   artifact **still ingests as ordinary material**. A void is ledgered, never dropped: an
   unresolvable parent is a measurement about what this corpus contains, exactly as a
   `depends_on` void is.

3. **ENERGY-VISIBLE.** Children couple to parents, so a perturbation near a claim reaches its
   descendants and a perturbation near a descendant reaches its parents. This is the one
   property `depends_on` does not yet exercise, and it is the reason lineage is worth
   declaring at all.

4. **HOLONOMY-EXCLUDED, REFERENCE-TIER, FIREWALLED FROM K** — the `depends_on` containments
   verbatim, inherited by being in the class rather than restated.

5. **COMPOSITION.** `forked_from ∘ forked_from = forked_from` — ancestry chains. **All
   cross-composition with the three correspondence kinds and with `depends_on` is UNDEFINED**
   and therefore implies nothing. Declared in `seed/COMPOSITION.json`, not in code.

6. **NO SUPERSESSION MECHANISM.** A fork never replaces, demotes, or contests its parent by
   lineage alone. Obsolescence is already handled honestly by the existing physics: a parent
   nothing confirms decays, one still load-bearing does not. **Lineage is information, never
   authority.** There is no code path from a `forked_from` edge to a value, a tier, or a
   contest, and c4 asserts it.

### THE EXPORT SIDE — the half that makes declaration possible

A manifest can only name a parent the builder was told about. So the export gains a **lineage
stub**: the compiled context carries **its own ID** and **the addresses it was built from**.
The intake surface accepts an artifact accompanied by a manifest referencing that ID, which
expands to `forked_from` edges to those addresses, plus any per-file explicit parents.

**The manifest is the DECLARED fact, and writing it is the builder's act** — operator or
agent — exactly as authorship is. The engine never writes a manifest on a builder's behalf and
never infers one from what an artifact looks like.

### CONTROLS

- **c1. INFERRED-LINEAGE ATTEMPT.** Any `forked_from` edge whose provenance is not a manifest
  or commit-ancestry record = RED. The standing anti-similarity AST sweep extends to the
  lineage parser: no tokenizer, no content comparison, no distance.
- **c2. UNRESOLVABLE PARENT.** Edge void, artifact ingests normally, void ledgered with its
  reason.
- **c3. CLASS CONTAINMENT.** `forked_from` in K's candidate set or loop-eligible = RED. It
  should hold by construction; it is asserted anyway, because "holds by construction" is a
  claim about code that can be edited.
- **c4. NO SUPERSESSION.** A fork demoting or contesting its parent via lineage: no such path
  exists, and a planted attempt is RED.

### WHAT LANDED MEANS HERE

A demo, not a green suite: **one artifact ingested with a manifest, its `forked_from` edges on
the wire, and a perturbation near the parent visibly reaching the child.**
