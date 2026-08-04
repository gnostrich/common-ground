# mixed-repo fixture

A small, synthetic, multi-language repository used to prove `adapters/repo_adapter.py`
and the `python` chart manifest (`seed/CHARTS.json`, `seed/LANGUAGES.json`) without
touching any of the operator's real repositories. See `seed/DECISIONS.md`'s REPO_INTAKE
entry: real-repo ingestion is HELD pending operator approval of the language-audit table.

This file itself is `.md` — reference-tier under `seed/LANGUAGES.json`. Held, not
ingested: `adapters/repo_adapter.py` counts and hashes it but builds no `Document`.
