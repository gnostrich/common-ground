# normalizer prompt (nu) — specification

Content-hashed into `SEED.lock`. This file **specifies** the normalizer; the normalizer
itself is deterministic code in `engine/normalize.py`, not a model call. The prompt text is
carried here because a model-assisted normalizer is a v0.5 option and, if it is ever
enabled, its prompt must already be inside the addressing hash — a normalizer that changes
moves every address (gate 4).

At v0 the model path is **off**. `engine/normalize.py` implements the specification below
directly and no API call is made during normalization.

## Contract

`nu(chart, surface) -> str` must satisfy:

1. **Idempotence.** `nu(chart, nu(chart, s)) == nu(chart, s)` for all `s`. Tested by null
   cell (i) at n=500 fuzzed samples per chart.
2. **Totality.** Defined on every string, including empty and control-character-only input.
3. **Chart tagging.** The result begins with the chart's tag, `\x01<chart>\x01`. Because
   step 2 of the core normalization deletes all C0 control characters from the input, a raw
   surface can never contain a tag, so tag-stripping on re-entry is unambiguous and
   idempotence is exact rather than approximate.
4. **Purity.** No dependence on engine state, corpus, clock, or run. Gate 1.

## English chart

Applied in order:

1. Strip a leading chart tag if present.
2. Delete C0 and C1 control characters.
3. Unicode NFKC.
4. Fold typographic characters to ASCII: curly quotes → `'` / `"`, en/em dash and minus →
   `-`, ellipsis → `...`.
5. Remove markdown presentation markers: `*`, `_`, `` ` ``, `~` when used as emphasis or
   code spans; heading `#` runs; list bullets at line start; block quote `>` at line start.
6. Remove inline LaTeX delimiters `$`, `\(`, `\)`, `\[`, `\]` while keeping their contents.
7. Casefold.
8. Collapse all whitespace runs to a single space; strip leading and trailing space.
9. Strip trailing terminal punctuation `. ? ! ; , :` (repeatedly).
10. Apply the frozen synset map from `seed/LEXICON/imports/` if a map is present, longest
    surface form first. Absent a map this step is the identity.

## Lean chart

Applied in order:

1. Strip a leading chart tag if present.
2. Delete C0 and C1 control characters (tabs and newlines are handled by step 6).
3. Unicode NFKC.
4. Remove comments: `--` to end of line, and balanced `/- ... -/` blocks (nesting aware).
5. For claim heads (`theorem`, `lemma`, `example`, `axiom`) only, cut the declaration at the
   first top-level `:=` — the proof term is not part of the statement's address
   (proof irrelevance). For definition heads (`def`, `abbrev`, `structure`, `class`,
   `instance`, `inductive`, `notation`) the body **is** the content and is retained.
6. Collapse all whitespace runs to a single space; strip.
7. **Do not casefold.** Lean is case-sensitive; `Cone` and `cone` are different terms and
   must keep different addresses. Null cell (ii) pins this with `lean-distinct-case`.
8. Apply the frozen Mathlib namespace map from `seed/LEXICON/imports/` if present. Absent a
   map this step is the identity.

## If the model path is ever enabled (v0.5)

The model would be asked, verbatim:

> Normalize the following {chart} surface to its canonical addressing form. Remove
> presentation, preserve content. Do not paraphrase, do not summarize, do not correct, do
> not translate between charts. If the surface is already canonical, return it unchanged.
> Return only the normalized string.

Enabling it is plastic under gate 4 and requires a cold re-anneal, because a model-assisted
normalizer is not idempotent by construction and cell (i) would have to be re-established
empirically at the new seed hash.
