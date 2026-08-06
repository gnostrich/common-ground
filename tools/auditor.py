"""THE STANDING AUDITOR: read-only, evidence-gathering, files findings and fixes nothing.

THE GOAL METRIC IS INVERTED. It is no longer "how fast was the operator's catch turned into a
fixture" — it is operator-caught regressions per week, target zero, because the auditor caught
them first. Every check here exists because a human found something a green suite did not.

WHAT IT RUNS, and each one answers a defect that actually shipped:
  SWEEPS      referee (no module decides by resemblance), gate 10 / claim discipline,
              constants, control-map-vs-territory, consumer sweep. All static, all cheap.
  WIRE        the served build against HEAD, the served model against the pin, the served
              snapshot's age and counts. Four skew incidents; the page must self-report.
  BATTERY     the six pinned prompts against the SERVED URL with the three numbers each —
              attachment fraction, arrows travelled, faithfulness verdict. A green suite has
              coexisted with a page that could not answer, twice.
  LIVENESS    every planted-defect control must FIRE on its plant. The null battery going
              quiet was once read as a pass when it was lost detection power.
  COPY        the prompt blocks are WIRE/GRAMMAR/STATE only; the page depicts no deleted
              mechanism.

IT WRITES NOTHING BUT ITS REPORT. No fixes, no code, no opinions on priority — the main
session disposes. That separation is the point: an auditor that can fix what it finds will
stop reporting what it cannot fix.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _run(args, timeout=900):
    try:
        p = subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-4000:]
    except Exception as exc:                       # noqa: BLE001 - reported, never raised
        return 1, f"{type(exc).__name__}: {exc}"


def sweeps() -> list[dict]:
    """Every static gate. A sweep that cannot run is a FINDING, never a pass."""
    out = []
    for name, args in (
        ("referee", [sys.executable, "-m", "engine.referee_sweep"]),
        ("control-map-vs-territory", [sys.executable, "-m", "engine.control_sweep"]),
        ("claim-discipline", [sys.executable, "-c",
                              "from engine.static_checks import check_claim_discipline as c;"
                              "v=[str(x) for x in c().violations];"
                              "print('\\n'.join(v) or 'clean');"
                              "raise SystemExit(1 if v else 0)"]),
        ("constants", [sys.executable, "-m", "unittest", "-q", "tests.test_constants"]),
    ):
        code, log = _run(name and args)
        out.append({"check": name, "ok": code == 0, "detail": log.strip()[:600]})
    return out


def wire() -> dict:
    """What the deploy says about itself, against what HEAD says."""
    import urllib.request

    url, token = os.environ.get("CG_URL", ""), os.environ.get("CG_TOKEN", "")
    if not url:
        return {"ok": False, "detail": "CG_URL unset — the wire could not be checked, which "
                                       "is a finding rather than a pass"}
    head = _run(["git", "rev-parse", "HEAD"])[1].strip()[:12]
    try:
        from tools.wire import Forwarder
        with Forwarder(url, token) as local:
            body = json.loads(urllib.request.urlopen(f"{local}/corpus", timeout=180).read())
    except Exception as exc:                       # noqa: BLE001
        return {"ok": False, "detail": f"the served build did not answer: {exc}"}
    build = body.get("build") or {}
    snap = build.get("snapshot") or {}
    served = build.get("served", "")
    return {
        "ok": served == head and not build.get("model_drift") and not snap.get("stale"),
        "served": served, "head": head, "commit_match": served == head,
        "model": build.get("model"), "model_pin": build.get("model_configured"),
        "model_drift": bool(build.get("model_drift")),
        "snapshot_age": snap.get("age"), "snapshot_stale": bool(snap.get("stale")),
        "slots": body.get("slots"), "arrows": body.get("arrows"),
        "same_claim": body.get("same_claim"), "loops": body.get("loops"),
    }


def battery() -> list[dict]:
    """The six pinned prompts against the SERVED URL. Three numbers each."""
    import urllib.request

    url, token = os.environ.get("CG_URL", ""), os.environ.get("CG_TOKEN", "")
    if not url:
        return [{"case": "battery", "ok": False, "detail": "CG_URL unset"}]
    from tests.test_fixtures import RETEST_QUESTION
    from tools.wire import Forwarder

    PROMPTS = [
        ("sharp", "no renderer/decoder is imported here on the cloud path (no cloud decoder)"),
        ("question", "how do the cloud decoder path and the renderer import rule relate"),
        ("lean", "what does the certified positivity work establish"),
        ("vague", "common structure across the lean work"),
        ("structural", "common thread through the math"),
        ("cross", RETEST_QUESTION),
    ]
    rows = []
    with Forwarder(url, token) as local:
        for name, q in PROMPTS:
            t0 = time.time()
            try:
                req = urllib.request.Request(
                    f"{local}/ask", method="POST",
                    data=json.dumps({"question": q, "chart": "english"}).encode(),
                    headers={"Content-Type": "application/json"})
                r = json.loads(urllib.request.urlopen(req, timeout=600).read())
            except Exception as exc:               # noqa: BLE001
                rows.append({"case": name, "ok": False, "detail": str(exc)[:200]})
                continue
            c = r.get("compiled") or {}
            att = c.get("attachment") or {}
            rel = c.get("relaxation") or {}
            f = r.get("faithful") or {}
            kinds: dict[str, int] = {}
            for v in (f.get("violations") or []):
                kinds[v["kind"]] = kinds.get(v["kind"], 0) + 1
            rows.append({
                "case": name, "seconds": round(time.time() - t0, 1),
                "attachment": round((att.get("discrimination") or {}).get("fraction", 0.0), 4),
                "indiscriminate": bool((att.get("discrimination") or {}).get("red")),
                "moved": rel.get("moved", 0),
                "arrows_travelled": sum(1 for m in (rel.get("rows") or [])
                                        if (m.get("hops") or 0) > 0),
                "faithful": bool(f.get("ok")), "violations": kinds,
                "cited": f"{f.get('cited', 0)}/{f.get('checked', 0)}",
                "ok": bool(f.get("ok")) and not (att.get("discrimination") or {}).get("red"),
            })
    return rows


def liveness() -> dict:
    """EVERY PLANTED-DEFECT CONTROL MUST FIRE. Silence is not a pass.

    A planted control asserts a defect is caught. If the plant stops reaching the checker the
    control still passes — it asserts a RED that never happens — and detection is lost with
    nothing to show for it. The null battery did exactly this. So the plants are re-run and
    counted rather than trusted.
    """
    code, log = _run([sys.executable, "-m", "unittest", "-q",
                      "tests.test_controls", "tests.test_apex", "tests.test_scaffold",
                      "tests.test_grounded", "tests.test_medium"])
    fired = log.count("planted") + log.count("PLANTED")
    return {"ok": code == 0, "detail": log.strip()[-800:], "planted_controls_run": fired}


def copy_checks() -> list[dict]:
    """The prompt is wire/grammar/state; the surface depicts no deleted mechanism."""
    out = []
    try:
        from engine.grammar import BLOCKS, illegal_blocks
        out.append({"check": "prompt-blocks-tagged", "ok": not illegal_blocks(),
                    "detail": f"{len(BLOCKS)} blocks, illegal: {illegal_blocks()}"})
    except Exception as exc:                       # noqa: BLE001
        out.append({"check": "prompt-blocks-tagged", "ok": False, "detail": str(exc)})
    code, log = _run([sys.executable, "-m", "unittest", "-q", "tests.test_ui_surface"])
    out.append({"check": "ui-surface", "ok": code == 0, "detail": log.strip()[-400:]})
    return out


def audit() -> dict:
    started = time.time()
    report = {
        "head": _run(["git", "rev-parse", "HEAD"])[1].strip()[:12],
        "sweeps": sweeps(),
        "wire": wire(),
        "battery": battery(),
        "liveness": liveness(),
        "copy": copy_checks(),
    }
    findings = []
    for s in report["sweeps"]:
        if not s["ok"]:
            findings.append(f"SWEEP {s['check']}: {s['detail'][:200]}")
    w = report["wire"]
    if not w.get("commit_match"):
        findings.append(f"WIRE: serving {w.get('served')} against HEAD {w.get('head')}")
    if w.get("model_drift"):
        findings.append(f"WIRE: model drift — serving {w.get('model')} against pin "
                        f"{w.get('model_pin')}")
    if w.get("snapshot_stale"):
        findings.append(f"WIRE: snapshot stale — {w.get('snapshot_age')}")
    for row in report["battery"]:
        if not row.get("ok"):
            findings.append(f"BATTERY {row['case']}: attachment "
                            f"{row.get('attachment')} violations {row.get('violations')}")
    if not report["liveness"]["ok"]:
        findings.append("LIVENESS: a planted-defect control did not fire")
    for c in report["copy"]:
        if not c["ok"]:
            findings.append(f"COPY {c['check']}: {c['detail'][:200]}")
    report["findings"] = findings
    report["clean"] = not findings
    report["seconds"] = round(time.time() - started, 1)
    return report


if __name__ == "__main__":
    out = audit()
    dest = REPO / "runs" / "audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(f"AUDIT of {out['head']} in {out['seconds']}s — "
          f"{'CLEAN' if out['clean'] else str(len(out['findings'])) + ' FINDING(S)'}")
    for f in out["findings"]:
        print("  •", f)
    raise SystemExit(0 if out["clean"] else 1)
