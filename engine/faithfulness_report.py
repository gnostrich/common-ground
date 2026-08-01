"""`python -m engine.faithfulness_report` — print the faithfulness audit.

Non-zero exit means a row is unmapped, uncontrolled, or carries an unclassified deviation.
A *classified* gap does not fail: it is a finding, and a finding behind a red build is a
finding nobody reads. Gaps are listed at the end and are the list to clear before P3.
"""

from __future__ import annotations

from .faithfulness import FAITHFULNESS_ROWS, by_design, check_faithfulness, gaps_before_p3

_MARK = {None: "faithful", "minimal-faithful-by-design": "by-design", "gap-before-P3": "GAP"}


def main() -> int:
    result = check_faithfulness()
    for row in FAITHFULNESS_ROWS:
        kind = _MARK[row.deviation.kind if row.deviation else None]
        print(f"{row.object:<48} {row.family:<10} {kind:<9} {row.site}")

    print(f"\n{result.checked_rows} rows · {len(by_design())} by design · "
          f"{len(gaps_before_p3())} open gap(s)")

    for p in result.problems:
        print(f"UNRESOLVED: {p}")

    gaps = gaps_before_p3()
    if gaps:
        print("\nGaps to close before P3 (these do not fail this check):")
        for g in gaps:
            print(f"  - {g.object} @ {g.site}")
            print(f"    {g.deviation.note.splitlines()[0]}")
    if not result.ok:
        print("\nAdd the row to engine/faithfulness.py with a site, a control, and — if it "
              "deviates — a classification.")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
