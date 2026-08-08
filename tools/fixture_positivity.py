"""COLUMN D: THE FROZEN FIXTURE AT TWO TIERS. One model per process, everything else identical.

The fixture's re-run rule is "against the SERVED url, never local code", and it is the right
rule: a fixture that measures the working tree measures something nobody is using. This tool
is the ONE deviation the two-tier question forces, and it is stated rather than quietly taken.
The deploy is pinned to a single model. Measuring a second tier on the deploy would mean
repointing the thing the operator is about to test, and leaving it repointed is exactly the
kind of accident that gets discovered at 9am. So both tiers run HERE, on one commit, from one
corpus snapshot — which also makes the comparison stronger than served-vs-local would have
been, because the model is then the only variable rather than one of three.

WHAT IT RUNS. The shipped handler, not a re-implementation of it. `ui.server.Handler` is bound
to a loopback port and the question is POSTed to `/ask` exactly as the page posts it. Every
line of the compile → attach → converse → check path is the deployed line; nothing about the
measurement is re-derived here, because a harness that re-implements the path it measures can
only report on itself.

THE MODEL COMES FROM `OPENROUTER_MODEL`, which is the build's own pin and the only selection
mechanism there is. There is deliberately no `--model` flag: a second way to choose the model
is a second mechanism for one job, and the tier that is measured must be the tier a deploy
would serve if it were set the same way. The run stamps what the PROVIDER said answered, not
what was asked for.

COST IS AN INSTRUMENT, NOT A BUILD CHANGE. `ui.lm._http_post` already fills a usage dict with
what OpenRouter reports it charged; nothing downstream keeps it. This wraps the transport to
keep a copy per call. It delegates to the real function and alters no byte in either
direction — an ammeter on the wire, not a change to the circuit. Cost is reported ONLY when
the provider reported it; a token count multiplied by a remembered rate is a fabricated
number, and this file does not produce those.

Run:  OPENROUTER_MODEL=google/gemini-2.5-flash python3 tools/fixture_positivity.py \
          --out runs/fixture-D/flash.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from collections import Counter
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: THE QUESTION, verbatim and unchanging. It is frozen in seed/FIXTURE-CERTIFIED-POSITIVITY.md
#: and copied here rather than parameterized: a fixture whose question is a command-line
#: argument is not a fixture.
QUESTION = "what does the certified positivity work establish"


def instrument() -> list[dict]:
    """Keep what the provider reported about every call. Must run before any LMClient exists.

    `LMClient` resolves its transport at construction (`transport or _http_post`), so patching
    the module global afterwards would silently miss every client already built. Clients are
    built per request, inside the handler, so patching at process start catches all of them —
    but the ordering is load-bearing and is why this is called first in `main`.
    """
    from ui import lm as _lm

    inner = _lm._http_post
    calls: list[dict] = []

    def recorder(key, body, usage=None):
        seen: dict = {} if usage is None else usage
        t0 = time.time()
        try:
            return inner(key, body, seen)
        finally:
            calls.append({
                "asked_for": body.get("model", ""), "served": seen.get("model", ""),
                "prompt_tokens": seen.get("prompt_tokens"),
                "completion_tokens": seen.get("completion_tokens"),
                # None, not 0.0, when unreported: a missing price and a free call are
                # different facts and must not print the same.
                "cost": seen.get("cost"), "seconds": round(time.time() - t0, 2),
            })

    _lm._http_post = recorder
    return calls


def loopback() -> tuple[str, ThreadingHTTPServer]:
    """The shipped handler on an ephemeral loopback port."""
    from ui import server as _server

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}", httpd


def ask(base: str, question: str, turns: int) -> dict:
    """POST /ask the way the page does. Proxy handlers explicitly emptied — this environment
    exports HTTPS_PROXY, and a loopback request routed through an egress proxy fails in a way
    that reads as the server being broken."""
    payload = json.dumps({"question": question, "chart": "english", "turns": turns})
    req = urllib.request.Request(f"{base}/ask", data=payload.encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=3600) as resp:
        return json.load(resp)


def by_tag(labels) -> dict:
    """Region composition, read off the labels the medium was actually shown."""
    return dict(Counter(str(x)[:1] for x in labels))


def row(out: dict, calls: list[dict], seconds: float) -> dict:
    """The fixture's rows, every one of them read off the response the page would render."""
    comp = out.get("compiled") or {}
    att = comp.get("attachment") or {}
    labels = list(att.get("labels") or ())
    attached = list(att.get("attachment") or ())
    relax = comp.get("relaxation") or {}
    moved_rows = list(relax.get("rows") or ())
    dlg = out.get("dialogue") or {}
    verdict = out.get("faithful") or {}
    region = by_tag(labels)
    seated = dict(Counter(str(a.get("chart", "?")) for a in attached))
    costs = [c["cost"] for c in calls if c.get("cost") is not None]
    return {
        "question": QUESTION,
        "asked_for": os.environ.get("OPENROUTER_MODEL", ""),
        "served": next((c["served"] for c in reversed(calls) if c.get("served")), ""),
        "region": region,
        "region_size": len(labels),
        # DISCRIMINATION TRAVELS WITH EVERY ATTACHMENT NUMBER, permanently, after column F.
        # A boundary metric reported without it can be read as a crossing when it is a
        # degeneracy: lean 19 of 19 looked like the two-tier measurement's whole question
        # answered, and it was 19 of 19 because EVERYTHING was 59 of 59. A boundary crossed at
        # fraction 1.0 was not crossed.
        "discrimination": (att.get("discrimination") or {}),
        # AND THE ARROWS UNDER IT. The read view is the pickle PLUS the proposer journal, and
        # the journal is deployment-local: 0 arrows here against 19,385 served, over an
        # identical 80,566-slot base. Turn 1's system prompt was byte-identical across the two
        # and its user body was 6,921 characters against 42,235, because with no arrows
        # `build_region` finds no arrow-rich anchor and falls back to a fixed region with an
        # empty declared section. Two measurements at different arrow counts are two
        # measurements of two corpora.
        "corpus_arrows": ((out.get("corpus_header") or {}).get("arrows")),
        "attached_by_chart": seated,
        "attached": len(attached),
        # THE NUMBER UNDER TEST. Lean objects seated in the region, lean objects the medium
        # related the question to. Column A recorded 0 of 19.
        "lean_attached": seated.get("lean", 0),
        "lean_in_region": region.get("l", 0),
        "propagation": {"moved": len(moved_rows),
                        "over_declared_arrows": sum(1 for r in moved_rows
                                                    if int(r.get("hops") or 0) > 0)},
        "turns": dlg.get("turn_count", 0),
        "stopped": dlg.get("stopped", ""),
        "arrows": {"records": dlg.get("records", 0),
                   "resolved": dlg.get("resolved_records", 0),
                   "distinct_claims": dlg.get("distinct_claims", 0)},
        "faithful": {
            "ok": verdict.get("ok"),
            "checked": verdict.get("checked", 0),
            "cited": verdict.get("cited", 0),
            "asserted_absent": verdict.get("asserted_absent", 0),
            # RECEIPTED OUT OF TOTAL: citations and legal absences count together. A fully
            # receipted answer never displays as a fraction under 1.
            "receipted": int(verdict.get("cited", 0)) + int(verdict.get("asserted_absent", 0)),
            "citable": verdict.get("citable", 0),
            "violations": len(verdict.get("violations") or ()),
            # THE VIOLATIONS THEMSELVES, not only their count. Three times now a referee has
            # convicted a correct answer, and each time the count alone would have read as the
            # answer being bad. What was cited, and what the checker held citable, both travel.
            "detail": list(verdict.get("violations") or ()),
            "citable_labels": sorted(str(c.get("n")) for c in (comp.get("citations") or ())),
        },
        "seconds": round(seconds, 1),
        "calls": len(calls),
        "cost_usd": round(sum(costs), 6) if len(costs) == len(calls) and calls else None,
        "tokens": {"prompt": sum(int(c.get("prompt_tokens") or 0) for c in calls),
                   "completion": sum(int(c.get("completion_tokens") or 0) for c in calls)},
        "call_detail": calls,
        "answer_chars": len(out.get("answer") or ""),
        "answer": out.get("answer") or "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--turns", type=int, default=4)
    a = ap.parse_args()
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY is not set; this fixture calls a real provider")
    if not os.environ.get("OPENROUTER_MODEL"):
        raise SystemExit("OPENROUTER_MODEL is not set; the tier under test must be named")

    calls = instrument()
    base, httpd = loopback()
    t0 = time.time()
    try:
        out = ask(base, QUESTION, a.turns)
    finally:
        httpd.shutdown()
    if out.get("error"):
        raise SystemExit(f"the handler returned an error: {out['error']}")
    rec = row(out, calls, time.time() - t0)
    rec["build"] = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                  text=True).stdout.strip()[:12]
    rec["corpus"] = out.get("corpus_header") or {}
    path = Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items()
                      if k not in ("answer", "call_detail", "corpus")}, indent=1))


if __name__ == "__main__":
    main()
