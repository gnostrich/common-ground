"""The three-moves belonging audit — object-singularity as a measured property.

`seed/OBJECT.md` says the whole system is ONE object and may be extended ONLY by one of
three moves:

  - **swap-base**    a new or extended base B (a chart; persons over charts)
  - **add-measure**  a second measure on the SAME D (fast/slow)
  - **add-morphism** a new arrow (K memory kernel; T_ij coupling; a translator; an LM
                     proposer INTO D; a verdict function feeding K)

Any registered extension that reduces to none of these is jack-of-all-trades creep and MUST
fail this audit. That is what makes "it is still THE object, not a new box" an executable
property rather than a convention — the completion of THE DELTA.

This module is the same shape as the gate-6 / faithfulness / chart-plugin audits: a frozen
registry, a classifier that fails on anything unclassified, and (in tests) a planted-defect
control — an injected extension that fits no move must turn it red.
"""

from __future__ import annotations

from dataclasses import dataclass

# The three — and only three — legal moves. Their names are the audit's vocabulary; an
# extension whose `move` is not one of these is, by definition, creep.
SWAP_BASE = "swap-base"
ADD_MEASURE = "add-measure"
ADD_MORPHISM = "add-morphism"
MOVES: frozenset[str] = frozenset({SWAP_BASE, ADD_MEASURE, ADD_MORPHISM})

# Extension lifecycle — orthogonal to the move. An extension is classified whether or not it
# is switched on; "gated-inert" (gate present, actuator off) is the anti-NELL v0 posture for
# K, and "planned" is a future move-1/3 that is already known to reduce to a single move.
BUILT = "built"
GATED_INERT = "gated-inert"
PLANNED = "planned"
_STATUSES: frozenset[str] = frozenset({BUILT, GATED_INERT, PLANNED})


@dataclass(frozen=True, slots=True)
class Extension:
    """One registered way the object has been (or will be) extended."""

    name: str
    move: str        # MUST be in MOVES or the audit fails
    status: str      # BUILT | GATED_INERT | PLANNED
    rationale: str   # why it reduces to exactly this move
    evidence: str    # code site / doc that realizes (or will realize) it


# Every extension the object carries or has logged. First job (per the ruling): classify the
# existing/logged ones — charts=move-1, fast/slow=move-2, K=move-3, conversation=move-1,
# LM-proposer=move-3 — plus the schematic's named future extensions, so the registry is
# complete over seed/OBJECT.md.
EXTENSIONS: tuple[Extension, ...] = (
    Extension(
        name="charts (english, lean, tabular)",
        move=SWAP_BASE,
        status=BUILT,
        rationale="a chart is an object of the base B; adding one extends B. Proven by the "
                  "chart plug-in audit: a new chart is a seed-manifest row + behavior "
                  "registration, no engine dispatch edit.",
        evidence="seed/CHARTS.json + engine/charts.py",
    ),
    Extension(
        name="conversation chart",
        move=SWAP_BASE,
        status=BUILT,
        rationale="conversation segmentation is a chart — another object of B, not a new "
                  "kind of thing. Reduces to swap-base exactly like tabular did: a manifest "
                  "row (tag `cv`) + behavior functions, no dispatch edit.",
        evidence="seed/CHARTS.json + engine/conversation.py (speaker claims + "
                 "proposal->verdict ledger = fast-tape content)",
    ),
    Extension(
        name="fast / slow (Mori–Zwanzig timescale split)",
        move=ADD_MEASURE,
        status=BUILT,
        rationale="a second Gibbs measure on the SAME D (p_fast tape vs p_slow corpus). No "
                  "new base, no new bundle — just another measure.",
        evidence="engine/mint_tape.py (fast tape) + the settled corpus (p_slow)",
    ),
    Extension(
        name="K (memory kernel / gated mint) — LIVE valve",
        move=ADD_MORPHISM,
        status=BUILT,
        rationale="the one arrow fast→slow, now actuating (operator-authorized). Promotes a "
                  "residual IFF Hankel>second-FDT ∧ conservative-extension — the only place "
                  "warrant rises, the only write to the corpus. Logged and reversible; a "
                  "planted-noise control asserts noise below the floor never promotes.",
        evidence="engine/mint_tape.py:MintController (act_on_mint acts; mint_enabled=true) + "
                 "engine/linalg.py (Hankel SVD) + engine/meter.py:second_fdt_surrogate_floor",
    ),
    Extension(
        name="single proposer inlet (propose)",
        move=ADD_MORPHISM,
        status=BUILT,
        rationale="THE one write-path into the fast tape at proposal tier. Me, the LM, and "
                  "another instance (translator in front) are all SOURCES through this one "
                  "morphism — not three morphisms. source_tag is provenance only; it never "
                  "affects warrant. A clamp-eligible warrant is refused at the inlet.",
        evidence="engine/inlet.py:FastTape.propose (one append, AST-asserted); "
                 "sources: ui/lm.py:LMProposer (LM), DeterministicExtractor (me), "
                 "engine/inlet.py:stub_translator (instance)",
    ),
    Extension(
        name="verdict-function-as-content",
        move=ADD_MORPHISM,
        status=BUILT,
        rationale="the conversation proposal→verdict ledger IS fast-tape content feeding the "
                  "now-live K — an arrow into the gate, not a new base or measure.",
        evidence="engine/conversation.py:proposal_verdict_ledger → engine/mint_tape "
                 "MintController.consider",
    ),
    Extension(
        name="persons base (single → social)",
        move=SWAP_BASE,
        status=PLANNED,
        rationale="Base' = persons, one level up; single-person is the K=1 special case. "
                  "Swap the base, same three parts.",
        evidence="future move-1 (seed/OBJECT.md · MULTIPLE PERSONS)",
    ),
    Extension(
        name="T_ij inter-person coupling",
        move=ADD_MORPHISM,
        status=PLANNED,
        rationale="a translation profunctor States_i ⇸ States_j entering joint E as energy. "
                  "The full profunctor + joint settlement + H² residue is NOT built — that "
                  "would be a second pipe. For now a stub translator re-stamps an instance's "
                  "claims to proposal tier so they enter through the ONE inlet like any "
                  "source; the real joint energy is future.",
        evidence="stub: engine/inlet.py:stub_translator → the single inlet; "
                 "full profunctor: future (seed/OBJECT.md · MULTIPLE PERSONS)",
    ),
)


@dataclass(frozen=True, slots=True)
class BelongingResult:
    unclassified: tuple[Extension, ...]   # move not in MOVES — creep
    bad_status: tuple[Extension, ...]     # status not recognized
    checked: int
    by_move: dict[str, int]

    @property
    def ok(self) -> bool:
        return not self.unclassified and not self.bad_status


def classify(extensions: tuple[Extension, ...] = EXTENSIONS) -> BelongingResult:
    """Classify every extension against the three moves. Fails on any that fits none.

    The audit is deliberately blunt: an extension belongs iff its `move` is one of the
    three. Anything else — a blank move, a fourth category, a "misc" — is creep, and lands
    in `unclassified`, which drives `ok` to False.
    """
    unclassified = tuple(e for e in extensions if e.move not in MOVES)
    bad_status = tuple(e for e in extensions if e.status not in _STATUSES)
    by_move: dict[str, int] = {m: 0 for m in sorted(MOVES)}
    for e in extensions:
        if e.move in by_move:
            by_move[e.move] += 1
    return BelongingResult(
        unclassified=unclassified,
        bad_status=bad_status,
        checked=len(extensions),
        by_move=by_move,
    )


def check_belonging() -> BelongingResult:
    """The standing check: every registered extension reduces to exactly one move."""
    return classify(EXTENSIONS)
