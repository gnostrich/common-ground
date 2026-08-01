"""R-map: formal face -> rendered English face.

Every sense needs an English face (LEXICON SPEC §0a). Imports that arrive without one —
a bare Mathlib name — get one here, marked `warrant="rendered"`: regenerable, disposable,
and counted by null cell (vi) as a quality metric rather than a defect.

Two rules the importer depends on:

- **The formal face is never modified.** The R-map *derives* a new string; it does not
  normalize the source. Mathlib names keep their case and their full namespace path,
  because the namespace is taxonomy signal and is what disambiguation uses.
- **The abbreviation table is declared.** `ker -> kernel` is a rendering decision, not a
  silent normalization, so it lives in `seed/CONSTANTS.json` and is hashed into the lock.
  Editing it moves English faces, hence `english_slot`, hence addresses — plastic under
  gate 4.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from .constants import RMAP_ABBREVIATIONS

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SPLIT = re.compile(r"[^0-9A-Za-z]+")


def segments(formal_name: str) -> list[str]:
    """Namespace path, verbatim. `Mathlib.Order.Cone.IsPositive` -> 4 segments."""
    return [s for s in formal_name.split(".") if s]


def _words(segment: str) -> list[str]:
    spaced = _CAMEL_BOUNDARY.sub(" ", segment)
    out: list[str] = []
    for raw in _SPLIT.split(spaced):
        if not raw:
            continue
        token = raw.casefold()
        out.append(RMAP_ABBREVIATIONS.get(token, token))
    return out


def render(formal_name: str) -> str:
    """Base rendering: the final namespace segment, decamelized and de-abbreviated."""
    segs = segments(formal_name)
    if not segs:
        return ""
    return " ".join(_words(segs[-1])).strip()


def render_disambiguated(formal_name: str, taken: Iterable[str]) -> str:
    """Rendering that does not collide with an already-used face.

    Widens leftward through the namespace one segment at a time — `is positive`, then
    `is positive (cone)`, then `is positive (order.cone)` — because the namespace is the
    taxonomy and is therefore the honest disambiguator. Falls back to the full formal
    name in parentheses, which always terminates since formal names are unique.
    """
    used = set(taken)
    base = render(formal_name)
    if base and base not in used:
        return base

    segs = segments(formal_name)
    for depth in range(1, len(segs)):
        qualifier = ".".join(segs[-(depth + 1) : -1]).casefold()
        candidate = f"{base} ({qualifier})" if base else qualifier
        if candidate not in used:
            return candidate

    return f"{base} ({formal_name})" if base else formal_name


def render_batch(formal_names: Sequence[str]) -> dict[str, str]:
    """Render a whole batch, resolving collisions deterministically.

    Sorted first so the mapping depends only on the *set* of names, never on the order
    the importer happened to walk the dump in — which is what makes the registry
    byte-identical across re-runs (SPEC §3).
    """
    out: dict[str, str] = {}
    used: set[str] = set()
    for name in sorted(set(formal_names)):
        face = render_disambiguated(name, used)
        out[name] = face
        used.add(face)
    return out
