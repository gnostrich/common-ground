"""THE DEMO THAT DECIDES `forked_from` IS LANDED — not a green suite.

seed/SCAFFOLD.md names the acceptance: one artifact ingested with a manifest, its
`forked_from` edges on the wire, and a perturbation near the PARENT visibly reaching the
CHILD. A suite can prove the edges are constructed correctly and still leave the property that
made lineage worth declaring — that descent COUPLES — untested end to end.

Zero LM calls. Everything below is declared structure and settlement.

Run:  python3 tools/lineage_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.constants import decisions                        # noqa: E402
from engine.corpus_state import build_snapshot                # noqa: E402
from engine.energy import dedupe_deltas                       # noqa: E402
from engine.export_sheet import sheet                         # noqa: E402
from engine.extract import build_k_extractors                 # noqa: E402
from engine.lineage import Export, Manifest, admit            # noqa: E402
from engine.pipeline import ingest, ledger_from_deltas        # noqa: E402
from engine.relax import relax                                # noqa: E402
from engine.types import Document                             # noqa: E402

PARENTS = ("The cone is positive under composition. "
           "The kernel accepts every checked statement.")
#: THE ARTIFACT. Somebody took the export and built this; it comes home as ordinary material.
CHILD = "The composed cone admits a certified positivity witness."


def _snapshot(texts, scaffolds=()):
    docs = [Document(f"d{i}", "english", t, "src") for i, t in enumerate(texts)]
    deltas = dedupe_deltas(ingest(docs, build_k_extractors(decisions(), offline=True)))
    return build_snapshot(ledger_from_deltas(deltas), (), scaffolds=scaffolds)


def main() -> int:
    print("=" * 78)
    print("1. THE CORPUS, before anything descends from it")
    base = _snapshot([PARENTS])
    parents = sorted(base.slots)
    for sid in parents:
        print(f"   [{sid[:12]}] {base.slots[sid].nu.split(chr(1))[-1][:60]}")

    print("\n2. THE EXPORT carries its own ID and what it was built from")
    record = {"typed": "what does the cone work establish",
              "citations": [{"n": f"e{i+1}", "slot": s, "kind": "attached",
                             "chart": "english", "nu": base.slots[s].nu}
                            for i, s in enumerate(parents)]}
    export = Export.of(record)
    print(f"   context_id: {export.context_id}")
    print(f"   built_from: {[s[:12] for s in export.built_from]}")
    assert "LINEAGE — if you build something out of this" in sheet(record)
    print("   (the sheet carries the stub; writing a manifest is the BUILDER's act)")

    print("\n3. THE ARTIFACT COMES HOME, with a manifest citing that context")
    both = _snapshot([PARENTS, CHILD])
    child = sorted(set(both.slots) - set(parents))
    manifest = Manifest.parse(json.dumps({
        "schema": "common-ground/lineage/v0", "context_id": export.context_id,
        "era": "demo-build-1"}))
    got = admit(manifest, both, contributed=child, export=export)
    print(f"   contributed {len(child)} slot(s); manifest declared context "
          f"{manifest.context_id}")
    for e in got["edges"]:
        print(f"   ON THE WIRE  [{e['src']}] -{e['kind']}-> [{e['dst']}]  "
              f"tier={e['tier']}  provenance={e['provenance']}")
    print(f"   ledger: {got['ledger']}")
    if not got["edges"]:
        print("   NO EDGES — the demo cannot show coupling"); return 1

    print("\n4. THE FAMILY TREE IS IN THE FIELD")
    lineage = _snapshot([PARENTS, CHILD], scaffolds=got["scaffolds"])
    blocks = {len(v) for v in lineage.blocks.values()}
    print(f"   arrows: {len(lineage.arrows)} (lineage is NOT one) | "
          f"scaffolds: {len(lineage.scaffolds)} | largest block: {max(blocks or {0})}")
    print(f"   loops: {lineage.loops}  <- holonomy untouched: a scaffold cannot close a cycle")

    print("\n5. A PERTURBATION NEAR THE PARENT, WITH AND WITHOUT THE LINEAGE")
    bias = "The cone is positive under composition."
    plain = relax(bias, both)
    coupled = relax(bias, lineage)
    reached_plain = {m.slot for m in plain.moved}
    reached = {m.slot for m in coupled.moved}
    kid = set(child)
    print(f"   without lineage: {len(plain.moved)} moved, child reached: "
          f"{bool(reached_plain & kid)}")
    print(f"   with lineage:    {len(coupled.moved)} moved, child reached: "
          f"{bool(reached & kid)}")
    for m in coupled.moved:
        if m.slot in kid:
            hops = " -> ".join(f"{h.kind}({h.tier})" for h in m.path) or "(landed here)"
            print(f"   THE CHILD MOVED  [{m.slot[:12]}] shift={m.shift:.6f} "
                  f"hops={m.hops} via {hops}")

    ok = bool(reached & kid) and not (reached_plain & kid)
    print("\n" + "=" * 78)
    if ok:
        print("LANDED: the artifact came home as a child, its lineage is on the wire, and a "
              "perturbation near the parent reached it over a declared forked_from edge.")
        return 0
    print("NOT LANDED: the child was not reached over the lineage edge "
          f"(with={bool(reached & kid)}, without={bool(reached_plain & kid)}).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
