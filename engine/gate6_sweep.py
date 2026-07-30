"""`python -m engine.gate6_sweep` — print the gate-6 conformance table.

The same classification `reports/gate6-sweep.md` documents and CI enforces, printed so it
can be read without opening either. A non-zero exit means some band in `engine/` is not
classified in `GATE6_SITES`; add it there with its reference distribution and its role.
"""

from __future__ import annotations

from .static_checks import check_gate6_classification, gate6_report

_MARK = {True: "conforming", False: "NON-CONFORMING", None: "n/a"}


def main() -> int:
    result = check_gate6_classification()
    for site in gate6_report():
        print(f"{site['site']:<50} {site['role']:<11} {_MARK[site['conforming']]}")
    print(f"\n{result.checked_functions} band site(s) across {result.checked_files} files")
    for v in result.violations:
        print(f"UNCLASSIFIED: {v}")
    if not result.ok:
        print("Add it to static_checks.GATE6_SITES with its reference distribution and role.")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
