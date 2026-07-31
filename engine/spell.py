"""Deterministic non-word normalization for the prose chart (item 4) — BUILT, then DROPPED.

**Shipping status: DROPPED, stage OFF.** The three gating controls are not all green: the
mechanism works (dirty-input folds a typo onto its word) and the allow-list protects domain
terms, but the *clean-corpus-bit-identical* control fails with any dictionary that is not
comprehensive — a small dictionary treats every word it lacks as a non-word and edit-1
correction then mangles common words (`and -> add`, `it -> is`, `we -> be`). A comprehensive
hunspell-class dictionary is a pinned artifact not available this round (D8-shaped), so per
the ruling — "ship only on green controls; else drop and record" — the stage does not ship.
It is retained, correct and inert (`SPELLCHECK_ENABLED` defaults false, and with no
production dictionary the pass is a no-op regardless), so that if a real pinned dictionary
lands, enabling it is one seed-morphism away and control 2 is the gate. `tests/test_spell.py`
pins control 2's failure so it cannot be flipped on with an inadequate dictionary.

The design (all of which held; only the dictionary let it down): a typo fragments the
address space, so this stage folds a *non-word* onto its nearest dictionary word so the two
share an address — hedged on every side, because it edits `nu`, and `nu` decides addresses:

- **Optional, off by default.** `SPELLCHECK_ENABLED` is a seed constant defaulting `false`.
  With it off, `nu` is byte-for-byte what it was, so no address moves. Turning it on is a
  seed edit: plastic under gate 4 — logged seed-morphism, cold re-anneal.
- **Non-word only.** A token already in the dictionary or the allow-list is never touched.
  Real words do not move, so a correctly spelled corpus is unaffected.
- **Allow-list first.** The seed's own lexicon lemmas and the chart symbols are allow-listed
  before anything else, so a domain term absent from the general dictionary is still never
  "corrected" into something wrong.
- **Deterministic.** Correction is to the lexicographically-smallest dictionary word within
  edit distance 1; a non-word with no distance-1 word is left alone rather than guessed.
  No randomness, so addressing stays a pure function of the seed (gate 1).
- **Prose only.** Lean is case-sensitive code and tabular is structured; only the `prose`
  behavior runs this. The pinned dictionary and allow-list come from the seed.
- **Raw bytes stay evidence.** This changes only the normalized form used for addressing;
  `Document.text`, the stored surface, and the provenance content hash are the raw bytes,
  so the correction is a lens for fibering, never a rewrite of what was said.

Idempotent: a correction target is itself a dictionary word, so re-running skips it. That is
what lets `nu` stay idempotent (null cell i) with the stage on.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache

from .constants import SEED_DIR

SPELL_DIR = SEED_DIR / "SPELL"
DICTIONARY_PATH = SPELL_DIR / "dictionary.txt"

_TOKEN_RE = re.compile(r"[a-z]+")
_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


@dataclass(frozen=True, slots=True)
class Correction:
    span: str        # the original token
    to: str          # what it became
    locator: int     # character offset in the input


@lru_cache(maxsize=1)
def _dictionary() -> frozenset[str]:
    if not DICTIONARY_PATH.exists():
        return frozenset()
    words = (
        line.strip().casefold()
        for line in DICTIONARY_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )
    return frozenset(words)


def _edits1(word: str) -> set[str]:
    """Every string one edit (delete/transpose/replace/insert) from `word`."""
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
    replaces = [a + c + b[1:] for a, b in splits if b for c in _ALPHABET]
    inserts = [a + c + b for a, b in splits for c in _ALPHABET]
    return set(deletes + transposes + replaces + inserts)


def correct_token(token: str, dictionary: frozenset[str], allow: frozenset[str]) -> str:
    """Fold a non-word onto its nearest dictionary word, or leave it untouched.

    A token in the dictionary or the allow-list is a word and is returned unchanged. A
    non-word is replaced by the lexicographically-smallest dictionary word at edit distance
    1; if none exists it is returned unchanged — the stage corrects, it does not guess.
    """
    if token in allow or token in dictionary:
        return token
    candidates = sorted(_edits1(token) & dictionary)
    return candidates[0] if candidates else token


def spellcheck_prose(
    text: str,
    dictionary: frozenset[str] | None = None,
    allow: frozenset[str] = frozenset(),
) -> tuple[str, list[Correction]]:
    """Correct non-word alphabetic tokens in `text`. Returns (corrected, corrections).

    Only `[a-z]+` runs are considered tokens; punctuation, digits, and spacing pass through
    untouched, so the correction is span-local and the surrounding structure is preserved.
    """
    dic = _dictionary() if dictionary is None else dictionary
    if not dic:
        return text, []

    out: list[str] = []
    corrections: list[Correction] = []
    last = 0
    for m in _TOKEN_RE.finditer(text):
        out.append(text[last:m.start()])
        token = m.group()
        fixed = correct_token(token, dic, allow)
        out.append(fixed)
        if fixed != token:
            corrections.append(Correction(span=token, to=fixed, locator=m.start()))
        last = m.end()
    out.append(text[last:])
    return "".join(out), corrections


def allow_list_from_seed() -> frozenset[str]:
    """Seed lexicon lemmas + chart symbols: the terms that must never be 'corrected'.

    Built from the convention table's lemmas and every declared chart tag id, so a domain
    word the general dictionary lacks is still protected. Loaded lazily and cached.
    """
    return _allow_list()


@lru_cache(maxsize=1)
def _allow_list() -> frozenset[str]:
    from .charts import chart_names, chart_spec

    terms: set[str] = set()
    # Chart symbols: the tag ids and chart names themselves.
    for name in chart_names():
        terms.add(name)
        terms.add(chart_spec(name).tag_id)

    # Seed lexicon lemmas from the convention table.
    table_path = SEED_DIR / "LEXICON" / "convention_table.json"
    if table_path.exists():
        data = json.loads(table_path.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            lemma = str(entry.get("lemma", "")).casefold()
            for tok in _TOKEN_RE.findall(lemma):
                terms.add(tok)
    return frozenset(terms)


def summarize_corrections(corrections: list[Correction]) -> dict[str, object]:
    """Span-level diff log with counts (item 4). Deterministic, ordered by span.

    Every correction is a (span -> to) pair with its character offset; this rolls them into
    the counts a run log records: total corrections, distinct tokens touched, and the
    per-(span->to) tally. When the stage is enabled, ingestion attaches this to the run log
    so every byte the addresser changed is auditable against the raw document.
    """
    from collections import Counter

    pairs = Counter((c.span, c.to) for c in corrections)
    return {
        "total": len(corrections),
        "distinct_spans": len({c.span for c in corrections}),
        "diffs": [
            {"span": span, "to": to, "count": n}
            for (span, to), n in sorted(pairs.items())
        ],
    }
