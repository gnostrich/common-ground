"""THE ACCEPTANCE SESSION. What declares the window usable — not a green suite.

Every question is typed into the SERVED page in a real browser, the response is screenshotted
as the operator would see it, and the row records latency, the model that actually served it,
the faithfulness verdict, and whether the field responded at all. A green test suite has twice
now coexisted with a page that could not answer; this artefact is what "usable" means instead.

Run:  CG_URL=... CG_TOKEN=... python3 tools/acceptance.py [--out DIR]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.battery import BATTERY_PATH  # noqa: E402
from tools.wire import Forwarder  # noqa: E402


def chromium() -> str:
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    raise SystemExit("no chromium")


#: THE OPERATOR'S OWN QUESTIONS. A battery of three pinned inputs answers whether the
#: mechanism is graded; these answer whether it is USEFUL, which is a different question and
#: the one that decides usable.
OPERATOR_QUESTIONS = [
    "what is the relationship between the second fundamental form and the spectral gap",
    "does this corpus contain anything about holonomy",
    "what won't reconcile",
]


def battery_inputs() -> list[tuple[str, str]]:
    spec = json.loads(Path(BATTERY_PATH).read_text(encoding="utf-8"))
    return [(i.get("id", "?"), i.get("text", "")) for i in spec.get("inputs", [])]


def run(url: str, token: str, out: Path) -> dict:
    from playwright.sync_api import sync_playwright

    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    cases = [(f"battery-{k}", t) for k, t in battery_inputs()]
    cases += [(f"operator-{i+1}", q) for i, q in enumerate(OPERATOR_QUESTIONS)]

    with Forwarder(url, token) as local, sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=chromium())
        page = browser.new_page(viewport={"width": 1100, "height": 1400})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: errors.append(f"console.error: {m.text}")
                if m.type == "error" else None)
        page.goto(f"{local}/?t={token}", wait_until="networkidle")
        header, build = page.inner_text("#corpushdr"), page.inner_text("#buildhdr")
        print(f"HEADER  {header}\nBUILD   {build}\n")
        page.screenshot(path=str(out / "00-loaded.png"), full_page=True)

        for name, text in cases:
            page.fill("#text", text)
            t0 = time.time()
            page.click("button.go")
            try:
                page.wait_for_function(
                    "document.querySelector('#answer .answer')"
                    " || document.querySelector('#answer .err')", timeout=300_000)
            except Exception as exc:
                rows.append({"case": name, "text": text, "seconds": round(time.time() - t0, 1),
                             "faithful": "NO RESPONSE", "error": str(exc)[:200]})
                print(f"{name:22s} TIMED OUT")
                continue
            secs = round(time.time() - t0, 1)
            block = page.inner_text("#answer")
            verdict = ("RED" if "FAITHFULNESS RED" in block
                       else "faithful: []" if "faithful: []" in block else "no verdict")
            page.screenshot(path=str(out / f"{name}.png"), full_page=True)
            page.eval_on_selector("#scope", "e => e.open = true")
            page.screenshot(path=str(out / f"{name}-scope.png"), full_page=True)
            page.eval_on_selector("#scope", "e => e.open = false")
            m = re.search(r"model served:\s*(\S+)", page.inner_text("#buildhdr"))
            rows.append({
                "case": name, "text": text, "seconds": secs, "faithful": verdict,
                "model": m.group(1) if m else "?",
                "responded": "DID NOT RESPOND" not in page.inner_text("#scopehead"),
                "answer_chars": len(page.inner_text("#answer .answer") or ""),
                "rests_on": page.inner_text("#answer .rests")[:200],
                "screenshot": f"{name}.png",
            })
            print(f"{name:22s} {secs:6.1f}s  {verdict:14s} {rows[-1]['model']}  "
                  f"{rows[-1]['answer_chars']} chars")
        browser.close()

    art = {"url": url, "header": header, "build": build, "page_errors": errors, "rows": rows}
    (out / "acceptance.json").write_text(json.dumps(art, indent=1))
    return art


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/acceptance")
    a = ap.parse_args()
    run(os.environ["CG_URL"].rstrip("/"), os.environ["CG_TOKEN"], Path(a.out))
