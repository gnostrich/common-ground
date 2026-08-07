"""FORKED_FROM: descendants of the corpus come home as children, and lineage is DECLARED.

THE GAP THIS CLOSES. The loop `corpus -> export -> somebody builds something -> artifact
returns` exists at both ends and drops the lineage at the door. A re-ingested artifact enters
as stranger-statements, and the daemon later pays LM calls to rediscover kinship the build
process knew for free. Nothing here replaces anything: forks come home as children BESIDE
their parents, family tree intact, and the corpus grows by descent.

DECLARED, NEVER INFERRED, and that is a property of the type rather than a rule this module
follows. `Scaffold.__post_init__` refuses a `forked_from` edge whose provenance is not a
manifest or commit ancestry, so a future parser that decided two artifacts LOOKED related
could not express the result. There is no tokenizer here, no distance, no content comparison,
and no name matching: a manifest names a parent ADDRESS, and an address either exists in the
snapshot or it does not.

RESOLVE-OR-VOID, and the artifact still lands. An undeclared or unresolvable parent produces
NO EDGE — and the artifact ingests as ordinary material anyway. Lineage is a bonus fact about
material that was going to enter regardless, so a bad manifest must never cost the corpus the
claims it accompanied. Voids are ledgered with their reason, because an unresolvable parent is
a measurement about what this corpus contains.

LINEAGE IS INFORMATION, NEVER AUTHORITY. There is no code path from an edge here to a value, a
tier, or a contest. A fork does not demote its parent by descending from it; obsolescence is
already handled by the physics, where a parent nothing confirms decays and one still
load-bearing does not. See `scaffold.confers_authority`, which is that claim in a form a test
can plant against.

Spec: seed/SCAFFOLD.md, written before this file existed. Controls c1-c4 in
tests/test_lineage.py.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .scaffold import (COMMIT_ANCESTRY, FORKED_FROM, MANIFEST, Scaffold, ScaffoldParse,
                       LINEAGE_SOURCES)

#: The manifest's declared schema. A document that does not say what it is is not a manifest.
SCHEMA = "common-ground/lineage/v0"


@dataclass(frozen=True, slots=True)
class Export:
    """THE LINEAGE STUB an export carries: its own ID, and what it was built from.

    This is the half that makes declaration possible. A builder can only name a parent it was
    told about, so the exported context states its identity and its sources, and a manifest
    that cites the ID expands to edges against those addresses.

    THE ID IS DERIVED FROM THE CONTENT, never minted: the same context exported twice has the
    same ID, and an ID cannot be claimed by a context that was not that context. It is a hash
    of the question and the addresses, in sorted order, so it is reproducible from the export
    itself by anybody holding it.
    """

    context_id: str
    question: str
    built_from: tuple = ()

    @staticmethod
    def of(record: dict) -> "Export":
        slots = sorted({str(c.get("slot")) for c in (record.get("citations") or ())
                        if c.get("slot")})
        question = str(record.get("typed") or "")
        digest = hashlib.sha256(
            ("\x01".join([question] + slots)).encode("utf-8")).hexdigest()[:16]
        return Export(context_id=f"cg-{digest}", question=question, built_from=tuple(slots))

    @staticmethod
    def read(raw: object) -> "Export":
        """An export handed back by a builder, VERIFIED rather than trusted.

        The ID is a hash of the question and the addresses, so an export can certify itself:
        recompute it from the fields presented and refuse a mismatch. Without this, a caller
        could hand back any `context_id` beside any address list and declare descent from
        material the export never contained — which would make lineage forgeable and turn a
        declaration into an assertion.
        """
        if isinstance(raw, (str, bytes)):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            raise ValueError("an export stub must be an object")
        got = Export(context_id=str(raw.get("context_id") or ""),
                     question=str(raw.get("question") or ""),
                     built_from=tuple(str(x) for x in (raw.get("built_from") or ())))
        rebuilt = Export.of({"typed": got.question,
                             "citations": [{"slot": s} for s in got.built_from]})
        if rebuilt.context_id != got.context_id:
            raise ValueError(
                f"this export does not certify itself: {got.context_id!r} is not the id of "
                f"the question and addresses presented ({rebuilt.context_id!r}). An id that "
                f"does not follow from its own content would make lineage forgeable.")
        return got

    def as_record(self) -> dict:
        return {"schema": SCHEMA, "context_id": self.context_id,
                "question": self.question, "built_from": list(self.built_from),
                "note": ("Cite `context_id` in a lineage manifest to declare that what you "
                         "built descends from these addresses. Writing the manifest is YOUR "
                         "act — the engine never infers lineage from what an artifact looks "
                         "like, and an artifact with no manifest still ingests normally.")}


@dataclass
class Manifest:
    """What a builder DECLARES about where an artifact came from.

    Two ways to name a parent, and both are declarations:

      * `context_id` — the export that seeded the work. Every address that export was built
        from becomes a parent of every slot the artifact contributed.
      * `parents` — per-slot explicit addresses, for a builder who knows precisely which claim
        a given file descends from.

    A manifest may carry either, both, or neither. Neither is legal and means "no lineage
    declared", which is the ordinary case for material that is not a fork.
    """

    source: str = MANIFEST                      # MANIFEST | COMMIT_ANCESTRY
    context_id: str = ""
    parents: dict = field(default_factory=dict)  # child slot -> tuple of parent slots
    era: str = ""

    @staticmethod
    def parse(raw: object) -> "Manifest":
        """Read a manifest document. STRICT: a wrong schema is not a manifest at all.

        Accepts a dict or a JSON string, because a manifest arrives as a file. It never
        accepts a guess: absent fields are absent, not defaulted to something plausible.
        """
        if isinstance(raw, (str, bytes)):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            raise ValueError("a lineage manifest must be an object")
        if str(raw.get("schema") or "") != SCHEMA:
            raise ValueError(f"not a lineage manifest: schema {raw.get('schema')!r} "
                             f"is not {SCHEMA!r}")
        source = str(raw.get("source") or MANIFEST)
        if source not in LINEAGE_SOURCES:
            raise ValueError(f"unknown lineage source {source!r}; "
                             f"declared sources are {sorted(LINEAGE_SOURCES)}")
        parents = {}
        for child, ps in (raw.get("parents") or {}).items():
            if isinstance(ps, str):
                ps = [ps]
            parents[str(child)] = tuple(str(x) for x in (ps or ()))
        return Manifest(source=source, context_id=str(raw.get("context_id") or ""),
                        parents=parents, era=str(raw.get("era") or ""))


def edges_from(manifest: Manifest, snapshot, contributed: list,
               export: Export | None = None) -> ScaffoldParse:
    """The declared lineage, resolved against the corpus. Resolve-or-void; the artifact stands.

    `contributed` is the list of slot ids the returning artifact produced — what came home.
    `export` is the context the manifest cites, when the caller holds it; without it a
    `context_id` resolves to nothing and is voided by name, which is the honest outcome for a
    manifest citing an export nobody can produce.

    VOIDS ARE MEASUREMENTS. A parent address this corpus does not carry names material the
    artifact was built from and the corpus has never ingested — the same reading `depends_on`
    gives its voids, and the same reason they are counted rather than dropped.
    """
    out = ScaffoldParse()
    slots = getattr(snapshot, "slots", {}) or {}
    provenance = f"{manifest.source}:{manifest.context_id or 'per-file'}"

    def claim(child: str, parent: str) -> None:
        out.symbols += 1
        if child == parent:
            out.void.append((child, parent, "self-descent"))
            return
        if parent not in slots:
            out.void.append((child, parent, "undeclared"))
            return
        if child not in slots:
            out.void.append((child, parent, "child-not-ingested"))
            return
        out.edges.append(Scaffold(
            chart=slots[child].chart, src_slot=child, dst_slot=parent, kind=FORKED_FROM,
            dst_chart=slots[parent].chart, symbol=parent[:16], era=manifest.era,
            provenance=provenance))

    # THE CONTEXT EXPANSION. Every address the cited export was built from is a parent of every
    # slot the artifact contributed. That is what "I built this out of that context" means, and
    # it is the builder's declaration rather than the engine's inference — the engine only
    # knows which addresses the export carried because it wrote them into the export.
    if manifest.context_id:
        if export is None or export.context_id != manifest.context_id:
            out.symbols += 1
            out.void.append(("", manifest.context_id, "unknown-context"))
        else:
            for child in contributed:
                for parent in export.built_from:
                    claim(str(child), str(parent))

    # PER-FILE PARENTS. A builder who knows exactly which claim a file descends from says so,
    # and that is stronger than the context expansion rather than redundant with it.
    for child, ps in manifest.parents.items():
        for parent in ps:
            claim(str(child), str(parent))
    return out


def admit(manifest: Manifest, snapshot, contributed: list,
          export: Export | None = None) -> dict:
    """Admit the descendants. Returns the edges and the ledger; MUTATES NOTHING.

    The caller attaches the edges to the snapshot. Keeping that out of here is the same
    discipline `perturb` follows with retention: a function that both decides and applies is a
    function whose decision cannot be inspected before it takes effect.
    """
    parse = edges_from(manifest, snapshot, contributed, export)
    return {
        "edges": [e.as_record() for e in parse.edges],
        "scaffolds": parse.edges,
        "ledger": parse.as_record(),
        "void": [{"child": c[:16], "parent": p[:16], "reason": why} for c, p, why in parse.void],
        "note": ("Lineage is DECLARED and is information, never authority: these edges couple "
                 "children to parents in the energy and do nothing else. No value moved, no "
                 "tier changed, nothing was contested, and the artifact ingests as ordinary "
                 "material whether or not any of this resolved."),
    }
