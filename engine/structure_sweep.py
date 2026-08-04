"""`python -m engine.structure_sweep` — print the structural-naturality table.

The live factor graph as the algebra: the six typed families with their live counts, the
node partition (variable vs frozen), and each structural claim with its status. A declared
gap (correspondence pairwise-collapse) prints its fence. A non-zero exit means a factor did
not classify, or a spurious hand-set edge was found, or a deviation is undeclared.
"""

from __future__ import annotations

from .structure_audit import STRUCTURE_CLAIMS, check_structure


def main() -> int:
    r = check_structure()
    print("factor families (live counts):")
    for fam, n in sorted(r.by_family.items()):
        print(f"  {fam:<28} {n}")
    print(f"\nnodes: {r.node_detail}\n")
    for c in STRUCTURE_CLAIMS:
        mark = "HOLDS" if c.status == "holds" else "DECLARED-GAP"
        print(f"  {c.id}  {mark:<12} {c.claim}")
        if c.fence:
            print(f"       fence: {c.fence}")
    for u in r.unclassified:
        print(f"UNCLASSIFIED FACTOR: {u}")
    for s in r.spurious:
        print(f"SPURIOUS EDGE: {s}")
    for d in r.undeclared_deviations:
        print(f"UNDECLARED DEVIATION: {d}")
    print(f"\nstructure_audit: {'OK' if r.ok else 'RED'}")
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
