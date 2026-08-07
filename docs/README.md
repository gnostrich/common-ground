# /docs — presentation-grade explainers (NON-NORMATIVE)

This directory holds explanatory writing about common-ground: prose meant to be *read*, for
people who do not want to start from `seed/SPEC.md` and `seed/CONSTITUTION.md` directly.

**seed/ is the law. Everything in this directory is a courtesy copy of it, and may lag.**

`seed/SPEC.md` and `seed/CONSTITUTION.md` are normative — they are the object, checked by the
faithfulness proof protocol (`seed/CONSTITUTION.md` Part B), enforced by the registry
(`seed/OI_REGISTRY.json`) and the control suite. Nothing here is checked that way. A file in
`/docs` can be wrong, can be written against a commit that has since moved, and no control in
this repository will turn red because of it.

**On any conflict between a file in `/docs` and `seed/`, `seed/` wins — always, without
exception.** If you find a disagreement, `seed/` is correct and the `/docs` file is stale;
file it as a defect against `/docs`, not against `seed/`.

## What belongs here

Presentation-grade explanation: the kind of document you would hand to someone who needs the
shape of the thing before they can read the law — an architecture walkthrough, a glossary of
terms, a "how does a question become an answer" narrative. Prose that explains, illustrates,
and simplifies for a reader, at the cost of being allowed to fall behind.

## What does not belong here

Anything a control depends on, anything the auditor checks, anything a number is derived from.
Those live in `seed/`. `/archive` is a separate, different kind of directory — record-keeping
(era summaries, superseded design documents), not explanation; see `/archive/eras/` and
`/archive/design/`.

## Header requirement

**Every file added to `/docs` must carry this notice near the top**, so a reader who lands on
one directly (not through this README) still sees it:

```
NON-NORMATIVE. Presentation-grade explainer; may lag the source. seed/ wins on any conflict.
```

## Current status

This directory exists and carries this README. No explainers have been written yet.
