"""Declared correspondence — the specified fiber-membership relation.

GATES.md sentence 1 makes slot identity exact: `hash(nu(surface), type)`. Two DISTINCT
addresses are distinct claims; two IDENTICAL addresses are already the same slot. So
co-reference across distinct addresses is never *inferred* — it is **DECLARED**, as a typed
translation (OBJECT.md: `hol : Pi_1(B) -> Aut(Sem)` integrates over the base morphisms, the
typed chart-to-chart translations).

This module loads those declarations from `seed/CORRESPONDENCE.json` and resolves each to a
pair of slot addresses through the exact gate-1 addressing function. There is **no
similarity fallback** — a correspondence that is not declared does not exist.

At v0 the declaration set is EMPTY. That is the honest state and the reason the holonomy
cold-floor is reported as a GAP rather than as zero: nothing cross-chart has been declared,
so no cross-chart fiber can form.
"""

from __future__ import annotations

import json
from functools import lru_cache

from . import EngineError
from .constants import SEED_DIR

CORRESPONDENCE_PATH = SEED_DIR / "CORRESPONDENCE.json"


@lru_cache(maxsize=1)
def declared_correspondence() -> frozenset[tuple[str, str]]:
    """Declared correspondence pairs (slot-id, slot-id). EMPTY at v0 — the correspondence GAP.

    The registry is a HOLE, not a mechanism. HOW a correspondence gets declared — hand-authored,
    LM-proposed-and-gated, or derived structurally — is a deliberate design decision made from
    the object outward, in a separate pass. It is NOT designed here, so no declaration FORMAT
    is interpreted: the file's `declared` list must be empty. A non-empty list is refused
    rather than read through a format this build has not been authorized to invent.
    """
    payload = json.loads(CORRESPONDENCE_PATH.read_text(encoding="utf-8"))
    declared = payload.get("declared", [])
    if declared:
        raise EngineError(
            "seed/CORRESPONDENCE.json carries declarations, but the declaration FORMAT is an "
            "undesigned GAP (the operator designs it separately, from the object outward). "
            "Refusing to interpret rows in an un-authorized format. Leave `declared` empty."
        )
    return frozenset()
