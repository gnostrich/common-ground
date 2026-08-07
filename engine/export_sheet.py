"""EXPORT THE COMPILED SHEET: the settled state, adapted into another agent's frame.

T_{me -> any-agent}. The compile step already produces the one artifact worth carrying between
models — the corpus's own claims, selected BY SETTLEMENT rather than by resemblance, with the
arrows they were reached over and the absences the field actually reports. Until now it existed
only inside one request. This renders it as a paste-ready preamble, so a perturbation is run
once and every downstream prompt to any model carries the relevant weight of the corpus without
the operator re-typing their world.

THIS IS A VIEW AND TAKES NO THREE-MOVES ENTRY. It computes nothing, proposes nothing, and
settles nothing. Every field it prints is read off `CompiledInput.as_record()`, which the
answer path already produced; running the export twice on the same record produces the same
bytes, and running it changes no state anywhere. Gate 10 applies to that sentence and there is
no machinery in this file that could make it false.

WHAT THE SHEET CONTAINS, and the order is the order that makes it checkable:
  the question, verbatim
  what it attached to, by kind
  every moved claim VERBATIM with its index, tier, shift, hop count and declared path
  the structural layer, when the question was about shape
  THE STATED ABSENCES — what the field reports it does not have
  the citation grammar, so the receiving model can be held to the same rule

WHAT IT DOES NOT CONTAIN, deliberately: no scores the receiving model cannot check, no
summary, no answer. A preamble that argues is a preamble that has to be trusted; this one can
be verified line by line against the window that produced it.
"""

from __future__ import annotations

from .lineage import Export
from .grounded import WARRANTS, warrants_held

#: Longest claim printed in the sheet. DISPLAY ONLY and applied ONLY here, on the way to a
#: string a human pastes. The compiled prompt still carries full nu-strings — trimming that
#: was a real defect and gate 8 names it.
SHEET_WIDTH = 2000


def _trim(nu: str) -> str:
    nu = (nu or "").replace("\n", " ").strip()
    return nu if len(nu) <= SHEET_WIDTH else nu[:SHEET_WIDTH - 1].rstrip() + "…"


def sheet(record: dict) -> str:
    """The portable preamble. Pure function of the compiled record."""
    rel = record.get("relaxation") or {}
    att = record.get("attachment") or {}
    cites = record.get("citations") or []
    rows = {r.get("slot"): r for r in (rel.get("rows") or [])}
    held = warrants_held(record)

    by_kind: dict[str, list] = {}
    for c in cites:
        by_kind.setdefault(c.get("kind", "?"), []).append(c)

    out: list[str] = [
        "# CONTEXT FROM A RECONCILIATION ENGINE — selected by settlement, not by search",
        "",
        "The claims below are not search results and were not matched to the question by any",
        "resemblance. The question was applied to a corpus as a soft constraint, the field was",
        "allowed to settle, and every claim listed CHANGED STATE as a result. Each carries the",
        "declared correspondences the perturbation reached it through. Treat them as the",
        "asker's own material, quoted verbatim.",
        "",
        "## THE QUESTION",
        record.get("typed", ""),
        "",
    ]

    corr = [c for c in by_kind.get("attached", [])]
    bears = [c for c in by_kind.get("bears_on", [])]
    out += ["## WHAT IT ATTACHED TO"]
    if corr or bears:
        out.append(f"{len(corr)} correspondence attachment(s), {len(bears)} bears-on "
                   f"(a bears-on says a claim is ABOUT the topic; it asserts no relation).")
        for c in corr + bears:
            out.append(f"[{c['n']}] {c['kind']} — [{c['chart']}] {_trim(c['nu'])}")
    else:
        out.append("Nothing attached: the medium drew no arrow to the question.")
    out.append("")

    moved = by_kind.get("moved", [])
    out += [f"## WHAT MOVED — {len(moved)} claim(s), verbatim"]
    if not moved:
        out.append("Nothing moved.")
    for c in moved:
        r = rows.get(c.get("slot"), {})
        hops = r.get("hops", 0)
        origin = ("the question landed on this claim's own address" if not hops
                  else f"reached over {hops} declared arrow(s), weakest tier "
                       f"{r.get('weakest_tier', '?')}")
        out.append(f"[{c['n']}] [{c['chart']}] warrant={r.get('tier', '?')} "
                   f"shift={r.get('shift', 0)}"
                   f"{' CONTESTED' if r.get('contested') else ''} — {origin}")
        out.append(f"     {_trim(c['nu'])}")
        for step in (r.get("path") or []):
            if isinstance(step, dict):
                out.append(f"     VIA {step.get('kind', '?')} "
                           f"[{step.get('src_chart', '?')}] -> [{step.get('dst_chart', '?')}]")
    out.append("")

    gl = by_kind.get("gloss", [])
    if gl:
        out += ["## GLOSSARY — how to read the asker's terms",
                "Each line is a validated translation between a term this corpus carries and "
                "the canonical sense a language model reads it in. These are about the "
                "INTERFACE, not about the world: use them to read the claims below, never as "
                "claims themselves.",
                ]
        for c in gl:
            out.append(f"[{c['n']}] GLOSS {_trim(c['nu'])}")
        out.append("")

    struct = by_kind.get("fiber", []) + by_kind.get("cluster", []) + by_kind.get("loop", [])
    if struct:
        out += ["## THE CORPUS'S OWN STRUCTURE",
                "The question was about shape rather than about any single claim, so what the "
                "corpus JOINS is included.",
                ]
        for c in struct:
            out.append(f"[{c['n']}] {c['kind'].upper()} [{c['chart']}] {_trim(c['nu'])}")
        out.append("")

    out += ["## WHAT THE FIELD REPORTS IT DOES NOT HAVE",
            "These are measured absences, not omissions. Do not fill them."]
    if held:
        for name in sorted(held):
            out.append(f"[∅{name}] {WARRANTS[name]}")
    else:
        out.append("No structural absence is reported for this perturbation.")
    out.append("")

    out += [
        "## HOW TO USE THIS",
        "Answer from the material above. Every sentence you write should end with the "
        "bracketed number(s) of the line(s) it rests on — [4], or [2][7] for a sentence "
        "resting on two. A sentence about what this material does NOT contain carries [∅] "
        "instead, or one of the [∅name] markers above when the field states the reason.",
        "Do not supply a fact this material does not carry. Where it reports an absence, say "
        "the relation is unmeasured rather than supplying one.",
    ]

    # THE LINEAGE STUB — the half that makes DECLARED descent possible.
    #
    # A builder can only name a parent it was told about. Without this block, anything built
    # out of this context comes home as stranger-statements and the daemon pays LM calls to
    # rediscover kinship the build already knew. With it, the artifact can DECLARE its parents
    # and the edges are free.
    #
    # It is an offer and never an obligation: an artifact with no manifest ingests exactly as
    # it does today. And it is the builder's act — the engine writes the ID and the addresses
    # it actually used, and never writes a manifest on anybody's behalf.
    stub = Export.of(record)
    out += [
        "",
        "## LINEAGE — if you build something out of this",
        f"context_id: {stub.context_id}",
        f"built from {len(stub.built_from)} address(es), listed in the record accompanying "
        f"this sheet.",
        "If what you build comes back to this corpus, ship a lineage manifest beside it:",
        '  {"schema": "common-ground/lineage/v0", "context_id": "' + stub.context_id + '"}',
        "and every slot your artifact contributes is declared a child of those addresses — "
        "`forked_from`, reference tier, holonomy-excluded, information and never authority. "
        "Per-file parents go in a `parents` map when you know precisely which claim a file "
        "descends from. Writing the manifest is YOUR act: lineage is DECLARED, never inferred, "
        "and nothing here is guessed from what your artifact resembles.",
    ]
    return "\n".join(out)
