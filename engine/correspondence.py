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

from .constants import SEED_DIR
from .normalize import address

CORRESPONDENCE_PATH = SEED_DIR / "CORRESPONDENCE.json"


@lru_cache(maxsize=1)
def declared_correspondence() -> frozenset[tuple[str, str]]:
    """Unordered declared slot-id pairs. Empty at v0 (the correspondence gap).

    Each declaration names two claims by `(chart, surface, type)`; both are put through the
    exact addressing function, so the pair is content-derived (gate 1) rather than a free
    edge. A row whose two sides address to the SAME slot is dropped: that is not a
    correspondence, it is one claim.
    """
    payload = json.loads(CORRESPONDENCE_PATH.read_text(encoding="utf-8"))
    pairs: set[tuple[str, str]] = set()
    for row in payload.get("declared", []):
        a, b = row["a"], row["b"]
        sa, _ = address(a["chart"], a["surface"], a["type"])
        sb, _ = address(b["chart"], b["surface"], b["type"])
        if sa != sb:
            pairs.add((sa, sb) if sa < sb else (sb, sa))
    return frozenset(pairs)
