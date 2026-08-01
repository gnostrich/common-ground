# seed/LEXICON/preminted — D5 pre-minted entries

Files listed in D5 are ingested here as `PREMINTED`-tier entries. Currently **empty** —
D5 is unresolved, and this directory holding no files is what makes null cell (iii) report
`BLOCKED` rather than `PASS`.

## Warrant

`PREMINTED` is high-warrant and **not clamp-eligible**. Gate 3 admits exactly two grounding
warrants — Lean kernel-accept under the pinned toolchain, and CI-green test receipts — and a
pre-minted lexicon entry is neither. A pre-minted entry gets a large weight in
`lexicon_energy`; it never fixes a slot's value.

This is the load-bearing distinction in the seed. Pre-minted material is the ledger's own
prior record of what it takes itself to have agreed. Letting it clamp would make the run
measure the seed's self-agreement rather than the ledger's consistency, and every floor read
afterwards would be circular.

## Expected files (D5)

- `BVALUED-AGREED.md`
- `STATEMENTS.md`
- `REGISTRY.md`
- (fourth file, unspecified — `____` in KICKOFF §0)

Drop them in this directory and list them under `D5.preminted_present` in
`seed/DECISIONS.json`. `engine/seed_lock.py` hashes each one individually into the lock, so
a later edit to any of them is caught by the CI tripwire.

## Ingestion

`adapters/repo_docs.py` reads each file, extracts claim-bearing spans with the same
deterministic path used everywhere else, and stamps `WarrantTier.PREMINTED` with
`detail="preminted:<filename>"`. The extraction path is identical to the corpus path — the
only difference is the warrant tier, and that difference is applied by the adapter, not by
the extractor.

`STATEMENTS.md` carries the "what we do NOT claim" list that PREREG R2 turns into the
ground-truth rediscovery test. Its spans are ingested with value `F` or `N` per the
extraction prompts' concession rule, and the meter is required to flag every one of them.
A miss rate above zero on that list is a `CLOSED-inconclusive` verdict for the whole run.
