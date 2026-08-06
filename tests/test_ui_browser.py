"""THE PAGE, IN A BROWSER. The control class that `node --check` cannot reach.

Two page-killing defects shipped in a row while 887 server-side tests were green. The first
was a syntax error; a parse control now catches that. The second PARSED PERFECTLY and threw on
its first statement — `$('temp')` named an element that had been deleted from the markup, so
the top-level script aborted before `corpus()` ran. The header sat on "corpus: loading…"
forever, the operator could not perturb, and every static check on the file was green.

A page is not verified by reading it. It is verified by running it in the thing that has to
run it. These tests load the real HTML in Chromium with a stubbed `/corpus`, `/ask` and
`/propose`, and fail on:

  * ANY uncaught exception or console error during load or interaction,
  * the header still reading "loading…" after the stub answers,
  * a render function the page defines that a live response never invokes (the renderBuild
    lesson: it was dead for a release because a sed patch missed its signature, and nothing
    but archaeology found it),
  * the answer not being rendered ABOVE the scope, or the scope not starting collapsed.

The stub server is local; no key, no corpus, no OpenRouter call.
"""

import http.server
import json
import re
import socketserver
import threading
import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "ui" / "index.html"

try:
    from playwright.sync_api import sync_playwright
    _HAVE = True
except Exception:                                     # pragma: no cover - env without it
    _HAVE = False

def _chromium() -> str:
    """The pinned browser, found by glob. Playwright's directory carries a build number that
    changes with the image; hard-coding it makes this control silently SKIP after an image
    bump, and a control that skips itself is the failure mode this whole file exists against."""
    import glob
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return ""


CHROMIUM = _chromium()

#: A response shaped exactly like `/ask` returns, with one moved row, one attachment, a
#: phases list and a green verdict — so every render path the page has is exercised.
ASK = {
    "answer": "I read your question as bearing on one claim. The cone is positive under the "
              "metric, and nothing else in the field responded.",
    "grounded_on": "FIELD STATE after relaxation.",
    "faithful": {"ok": True, "checked": 2, "cited": 2, "citable": 2, "resolved": [1, 2],
                 "method": "citation-resolution", "violations": []},
    "lm_available": True,
    "phases": [{"stage": "addressing", "at": 0.01}, {"stage": "attaching", "at": 0.02},
               {"stage": "settling", "at": 1.2}, {"stage": "answering", "at": 1.3},
               {"stage": "checking", "at": 2.0}],
    "compiled": {
        "typed": "is the cone positive",
        "conditioned": True,
        "field_status": "RELAXED: 1 slot(s) moved",
        "landings": [{"hit": True, "value": "T", "tier": "EXTRACTION", "contested": False,
                      "fiber": "f1", "block": "b1", "arrows": [], "surface": "the cone"}],
        "relaxation": {"moved": 1, "blocks_settled": 1, "silence": "",
                       "rows": [{"nu": "the cone is positive under the metric",
                                 "chart": "english", "type": "claim", "value": "T",
                                 "tier": "EXTRACTION", "shift": 0.4213, "hops": 1,
                                 "contested": False,
                                 "path": [{"kind": "corresponds", "src_chart": "english",
                                           "dst_chart": "lean"}]}]},
        "attachment": {"proposed": [{"kind": "corresponds", "accepted": True,
                                     "dst_chart": "english", "tier": "EXTRACTION",
                                     "dst_nu": "the cone is positive"}]},
    },
    "corpus_header": {"loaded": True, "slots": 37000, "by_chart": {"english": 20000},
                      "arrows": 16564, "same_claim": 0, "fibers": 900,
                      "contested_slots": 12, "loops": 8, "floor": "0.1215",
                      "build": {"served": "abc123abc123", "model": "google/gemini-2.5-flash",
                                "model_configured": "google/gemini-2.5-flash",
                                "model_drift": False}},
}

#: What `/propose` returns — a settled current plus the retention. Shaped like the real one,
#: because `render()` reads it and a stub that returns the /ask shape would exercise the error
#: path while claiming to exercise the retain path.
PROPOSE = {
    "lm_available": True,
    "proposals_by_source": {"me": 1},
    "proposals": [{"source": "me", "tier": "EXTRACTION", "value": "T", "chart": "english",
                   "type": "claim", "surface": "the cone is positive"}],
    "corpus": {},
    "promotions": [],
    "retention": {"retained_arrows": 1, "note": "one attachment kept as a proposal."},
    "engine": {"by_chart": {"english": 1}, "ledger_summary": {"blocks": 1}, "contested": [],
               "correspondences": [], "verdicts": [],
               "arms": [{"mean_floor": 0.12, "beta": 1.0, "q95": 0.3,
                         "second_fdt_floor": 0.1215, "certificates": []}],
               "status": {"P3": "BLOCKED on D5"}},
}

RED_ASK = json.loads(json.dumps(ASK))
RED_ASK["answer"] = "Perelman settled the Poincare conjecture some years ago."
RED_ASK["faithful"] = {
    "ok": False, "checked": 2, "cited": 1, "citable": 2, "resolved": [],
    "method": "citation-resolution",
    "violations": [
        {"kind": "uncited", "numbers": [],
         "sentence": "Perelman settled the Poincare conjecture some years ago."},
        {"kind": "unresolved", "numbers": [99],
         "sentence": "The cone is positive under the ambient metric [99]."},
    ]}


class _Stub(http.server.BaseHTTPRequestHandler):
    payload = ASK
    page_path = PAGE

    def log_message(self, *a):
        pass

    def _json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/corpus"):
            return self._json(ASK["corpus_header"])
        if self.path.startswith("/proposer"):
            return self._json({"totals": {}, "control": {}, "status": {}, "recent": []})
        body = type(self).page_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path.startswith("/propose"):
            return self._json(PROPOSE)
        if self.path.startswith("/proposer"):
            return self._json({"totals": {}, "control": {}, "status": {}, "recent": []})
        self._json(type(self).payload)


class _Server:
    def __init__(self, payload=ASK, page=None):
        _Stub.payload = payload
        _Stub.page_path = page or PAGE
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), _Stub)
        self.port = self.httpd.server_address[1]
        self.t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.t.start()

    def __enter__(self):
        return f"http://127.0.0.1:{self.port}/"

    def __exit__(self, *a):
        self.httpd.shutdown()
        self.httpd.server_close()


class _Page:
    """One browser, one page, every console error and pageerror collected."""

    def __init__(self, url):
        self.url, self.errors = url, []

    def __enter__(self):
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(executable_path=CHROMIUM)
        self.page = self.browser.new_page()
        self.page.on("pageerror", lambda e: self.errors.append(f"pageerror: {e}"))
        self.page.on("console", lambda m: self.errors.append(f"console.{m.type}: {m.text}")
                     if m.type == "error" else None)
        self.page.goto(self.url, wait_until="networkidle")
        return self

    def __exit__(self, *a):
        self.browser.close()
        self._pw.stop()

    def perturb(self, text="is the cone positive"):
        self.page.fill("#text", text)
        self.page.click("button.go")
        self.page.wait_for_function("document.querySelector('#answer').innerHTML.includes('rests')"
                                    " || document.querySelector('#answer .err')", timeout=15000)


@unittest.skipUnless(_HAVE and CHROMIUM and Path(CHROMIUM).exists(), "no chromium/playwright here")
class ThePageMustRUN(unittest.TestCase):

    def test_loading_the_page_throws_nothing(self):
        with _Server() as url, _Page(url) as p:
            self.assertEqual([], p.errors, "the page threw on load")

    def test_the_corpus_header_stops_saying_loading(self):
        # THE EXACT DEFECT: a top-level throw leaves this string on screen forever, and every
        # static check stays green. The operator saw it for two releases.
        with _Server() as url, _Page(url) as p:
            hdr = p.page.inner_text("#corpushdr")
            self.assertNotIn("loading", hdr.lower(), f"header never rendered: {hdr!r}")
            self.assertIn("37,000", hdr)

    def test_a_planted_missing_element_reference_is_caught(self):
        # RED CONDITION for this control: put back the SHAPE of the defect — a top-level
        # statement touching an element that is not in the markup — and it must fail.
        import tempfile
        src = PAGE.read_text().replace(
            "const tagcls =", "$('does_not_exist').oninput = null;\nconst tagcls =", 1)
        self.assertIn("does_not_exist", src, "the plant did not apply")
        with tempfile.TemporaryDirectory() as d:
            broken = Path(d) / "broken.html"
            broken.write_text(src)
            with _Server(page=broken) as url, _Page(url) as p:
                self.assertTrue(p.errors, "a null-element deref must be caught")
                self.assertIn("loading", p.page.inner_text("#corpushdr").lower())


@unittest.skipUnless(_HAVE and CHROMIUM and Path(CHROMIUM).exists(), "no chromium/playwright here")
class TheAnswerIsFIRST(unittest.TestCase):

    def test_the_answer_renders_above_the_scope(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            ans = p.page.locator("#answer").bounding_box()
            scope = p.page.locator("#scope").bounding_box()
            self.assertLess(ans["y"], scope["y"], "the scope is above the answer")

    def test_the_scope_starts_collapsed(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            self.assertFalse(p.page.eval_on_selector("#scope", "e => e.open"))

    def test_the_answer_text_is_on_the_page_in_full(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            self.assertIn("the cone is positive under the metric",
                          p.page.inner_text("#answer").lower())

    def test_what_the_answer_rests_on_is_stated_in_the_answer_not_the_scope(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            rests = p.page.inner_text("#answer .rests")
            self.assertIn("bearing on", rests)

    def test_a_green_verdict_is_shown_with_the_answer(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            v = p.page.inner_text("#answer .verdict")
            self.assertIn("faithful: []", v)
            self.assertIn("cites a claim that was shown", v)

    def test_a_red_verdict_is_shown_ON_the_answer_with_its_failing_sentences(self):
        with _Server(RED_ASK) as url, _Page(url) as p:
            p.perturb()
            block = p.page.inner_text("#answer")
            self.assertIn("FAITHFULNESS RED", block)
            # Both structural failures are named on the answer, not filed in the scope.
            self.assertIn("rests on nothing shown", block)
            self.assertIn("99", block)

    def test_the_movers_and_phases_land_in_the_scope(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            p.page.eval_on_selector("#scope", "e => e.open = true")
            self.assertIn("0.4213", p.page.inner_text("#movers"))
            self.assertIn("VIA corresponds", p.page.inner_text("#movers"))
            self.assertIn("settling", p.page.inner_text("#phases"))


@unittest.skipUnless(_HAVE and CHROMIUM and Path(CHROMIUM).exists(), "no chromium/playwright here")
class NoRenderFunctionIsDEAD(unittest.TestCase):
    """The renderBuild lesson, made a control.

    `renderBuild` shipped dead for a release: a patch targeted a signature that had changed, so
    the function existed, was referenced, and was never called. Nothing failed. Here every
    `render*` function the page defines is instrumented before the response arrives, and one
    that a live response does not invoke is RED — dead-looking-wired is a failure, not an
    archaeology find.
    """

    def _defined(self):
        src = "\n".join(re.findall(r"<script>(.*?)</script>", PAGE.read_text(), re.S))
        return sorted(set(re.findall(r"function\s+(render\w*)\s*\(", src)))

    def test_the_page_defines_render_functions_at_all(self):
        self.assertTrue(self._defined(), "no render functions found — the scan is broken")

    _INSTRUMENT = ("names => { window.__hit = {}; for (const n of names) {"
                   "  const f = window[n];"
                   "  if (typeof f !== 'function') { window.__hit[n] = 'MISSING'; continue; }"
                   "  window[n] = function(...a){ window.__hit[n] = true; return f.apply(this, a); };"
                   "} }")

    def test_every_render_function_is_invoked_on_some_live_path(self):
        """EVERY path, not just /ask — which is the point.

        `renderBuild` was dead because nothing drove the path that reaches it. Asserting only
        against the release path would leave `render` (retain) and `renderLedger` (the
        proposer refresh) permanently unexercised and would have to declare them expected
        exceptions — an allowlist that grows until the control means nothing. So the test
        drives all three live paths and then asserts the set is empty.
        """
        names = self._defined()
        with _Server() as url, _Page(url) as p:
            p.page.evaluate(self._INSTRUMENT, names)
            p.perturb()                                    # RELEASE: /ask
            p.page.check("#retain")
            p.page.click("button.go")                      # RETAIN: /propose
            p.page.wait_for_function(
                "document.querySelector('#answer').innerHTML.includes('RETAINED')"
                " || document.querySelector('#answer .err')", timeout=15000)
            p.page.click("button:has-text('refresh')")     # LEDGER: /proposer
            p.page.wait_for_timeout(400)
            hits = p.page.evaluate("() => window.__hit")
            dead = [n for n in names if hits.get(n) is not True]
            self.assertEqual([], dead, f"render function(s) never invoked on any path: {dead}")

    def test_a_planted_dead_render_function_is_caught(self):
        # RED: a function that matches the scan and is never called must be reported.
        names = self._defined() + ["renderNeverCalled"]
        with _Server() as url, _Page(url) as p:
            p.page.evaluate("() => { window.renderNeverCalled = function(){}; }")
            p.page.evaluate(self._INSTRUMENT, names)
            p.perturb()
            hits = p.page.evaluate("() => window.__hit")
            self.assertNotEqual(True, hits.get("renderNeverCalled"))

    def test_every_function_named_in_an_onclick_exists_at_runtime(self):
        src = PAGE.read_text()
        called = sorted(set(re.findall(r'onclick="(\w+)\(', src)))
        self.assertTrue(called)
        with _Server() as url, _Page(url) as p:
            missing = [n for n in called
                       if p.page.evaluate(f"() => typeof window['{n}']") != "function"]
            self.assertEqual([], missing, f"onclick names nothing: {missing}")


if __name__ == "__main__":
    unittest.main()
