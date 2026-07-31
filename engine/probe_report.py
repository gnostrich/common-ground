"""`python -m engine.probe_report` — the probe battery and the chart plug-in verdict.

Non-zero exit means a probe is unstatused or a live probe's control does not resolve. A
stubbed or inferred probe is a flagged finding, not a failure.
"""

from __future__ import annotations

from .chart_plugin_audit import verdict as chart_verdict
from .probes import PROBES, check_probe_battery

_MARK = {"implemented": "live", "mapped": "mapped", "stubbed": "STUB", "inferred": "INFER?"}


def main() -> int:
    result = check_probe_battery()
    for p in PROBES:
        flag = "  <-- flagged" if p.is_flagged else ""
        print(f"{p.id}  {_MARK[p.status]:<7}{p.commitment.splitlines()[0][:72]}{flag}")
    print(f"\n{result.checked} probes · {len(result.flagged)} flagged "
          f"({', '.join(result.flagged)})")
    for m in result.missing_control + result.unstatused:
        print(f"UNRESOLVED: {m}")

    cv = chart_verdict()
    print(f"\nchart plug-in audit: "
          f"{'PASS' if cv['manifest_only_possible'] else 'FAILED'} — "
          f"{len(cv['blocking_sites'])} blocking site(s) {cv['by_severity']}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
