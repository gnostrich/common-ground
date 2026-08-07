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

#: THE TRANSCRIPT the page must quote. Two calls, both directions, with REAL sha256[:16] of
#: the exact strings above them — so the VERIFIED path is genuinely exercised rather than
#: asserted against digests the page could not fail to match.
def _sha16(t: str) -> str:
    import hashlib
    return hashlib.sha256((t or "").encode("utf-8")).hexdigest()[:16]


def _call(port, system, user, reply, model="google/gemini-2.5-flash", seconds=1.0):
    return {"port": port, "model": model, "seconds": seconds, "system": system, "user": user,
            "reply": reply, "error": "", "system_sha": _sha16(system),
            "user_sha": _sha16(user), "reply_sha": _sha16(reply),
            "chars": {"system": len(system), "user": len(user), "reply": len(reply)}}


#: The propose call's user body carries the operator's bytes as `[b0]` — OI-19's wire — so a
#: page that showed a summary instead of the bytes would fail on this string.
PROPOSE_USER = ("OBJECTS\n[b0] Is The Cone POSITIVE?  Really\n"
                "[e1] \\x01en\\x01the cone is positive under the metric\n\nARROWS (declared)\n(none)")
ASK["transcript"] = [
    _call("propose", "You are completing a partial DIAGRAM.", PROPOSE_USER, "b0 -bears_on-> e1",
          seconds=18.4),
    _call("render", "WIRE\nYou speak only from the state below.",
          "FIELD STATE after relaxation.\n\nBOUNDARY CONDITION:\nIs The Cone POSITIVE?  Really",
          "The cone is positive under the metric [1].", seconds=2.1),
]

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

    def open_wire(self):
        """Ensure the raw-traffic panel is OPEN, then read what is rendered.

        It now opens by default, so this only clicks when it is somehow closed — clicking
        unconditionally would toggle it shut and read an empty panel, which is how a control
        starts passing for the wrong reason. A collapsed `<details>` renders no text, so
        reading it closed would test the markup rather than what is on screen.
        """
        if not self.page.locator("#wire").evaluate("e => e.open"):
            self.page.click("#wiresum")
        self.page.wait_for_function("document.querySelector('#wire').open", timeout=5000)
        return self.page.inner_text("#calls")

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
            self.assertIn("cite a claim that was shown", v)

    def test_a_fully_receipted_answer_NEVER_reads_as_a_fraction_under_one(self):
        """A citation and a legal absence are both RECEIPTS.

        The line read `${cited}/${checked} sentence(s) cite a claim`, which showed 1/3 for an
        answer whose three sentences were all properly receipted — one by a citation, two by
        `[∅]`. The gate treats the two as equally valid; a summary that counts only one of
        them makes a green verdict display as a partial failure, which is the worst possible
        direction for a faithfulness readout to be wrong in.
        """
        payload = json.loads(json.dumps(ASK))
        payload["faithful"] = {"ok": True, "checked": 3, "cited": 1, "asserted_absent": 2,
                               "citable": 36, "resolved": [1], "method": "citation-resolution",
                               "violations": []}
        with _Server(payload=payload) as url, _Page(url) as p:
            p.perturb()
            v = p.page.inner_text("#answer .verdict")
            self.assertIn("3/3 sentence(s) receipted", v, v)
            self.assertNotIn("1/3", v, "a fully receipted answer must not read as 1/3")
            # The split is still reported — receipted-out-of-total is the headline, not a
            # replacement for saying which sentences cited and which asserted an absence.
            self.assertIn("1 cite a claim that was shown", v)
            self.assertIn("2 assert an absence", v)

    def test_a_PARTIALLY_receipted_answer_still_shows_the_shortfall(self):
        """Not vacuous in the other direction: if some sentence is neither cited nor a legal
        absence, the fraction must be under 1 and say so."""
        payload = json.loads(json.dumps(ASK))
        payload["faithful"] = {"ok": True, "checked": 4, "cited": 1, "asserted_absent": 1,
                               "citable": 36, "resolved": [1], "method": "citation-resolution",
                               "violations": []}
        with _Server(payload=payload) as url, _Page(url) as p:
            p.perturb()
            self.assertIn("2/4 sentence(s) receipted", p.page.inner_text("#answer .verdict"))

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
class EveryLMCallIsVISIBLERaw(unittest.TestCase):
    """The operator asked to see every input and output of the LM, including intermediate ones.

    "Visible" is not "shipped in the JSON" — the transcript rode on every `/ask` response for a
    release while the page rendered none of it. So these controls read the RENDERED TEXT of the
    page, and they read the digest badges, because a surface that re-renders the bytes it claims
    to quote is the one failure this whole section exists to rule out.
    """

    def test_both_calls_are_on_the_page(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            txt = p.open_wire()
            self.assertIn("propose", txt, "the ATTACHMENT call decides what the answer can "
                                          "be about; hiding it shows the answer's input and "
                                          "hides its cause")
            self.assertIn("render", txt)

    def test_the_bytes_are_shown_and_not_summarized(self):
        with _Server() as url, _Page(url) as p:
            p.perturb()
            txt = p.open_wire()
            for expected in ("[b0] Is The Cone POSITIVE?  Really",     # OI-19's wire, verbatim
                             "b0 -bears_on-> e1",                      # the propose REPLY, raw
                             "You are completing a partial DIAGRAM.",  # the propose SYSTEM
                             "BOUNDARY CONDITION:",                    # the render USER
                             "The cone is positive under the metric [1]."):
                self.assertIn(expected, txt, f"missing from the raw traffic: {expected!r}")

    def test_every_block_verifies_its_digest(self):
        """Six blocks, two calls x (system, user, reply). All six must say VERIFIED."""
        with _Server() as url, _Page(url) as p:
            p.perturb()
            p.open_wire()
            p.page.wait_for_function(
                "!document.querySelector('#calls').innerText.includes('checking…')", timeout=15000)
            txt = p.page.inner_text("#calls")
            self.assertEqual(txt.count("VERIFIED"), 6, txt[:2000])
            self.assertNotIn("MISMATCH", txt)
            self.assertNotIn("UNVERIFIED", txt)

    def test_a_TAMPERED_digest_is_reported_ON_the_block(self):
        """RED CONDITION. If the page displayed bytes other than the ones the server hashed,
        the operator must be told on the block — not in a console nobody reads."""
        payload = json.loads(json.dumps(ASK))
        payload["transcript"][1]["reply"] = "Something the model never said."
        with _Server(payload=payload) as url, _Page(url) as p:
            p.perturb()
            p.open_wire()
            p.page.wait_for_function(
                "!document.querySelector('#calls').innerText.includes('checking…')", timeout=15000)
            txt = p.page.inner_text("#calls")
            self.assertIn("DIGEST MISMATCH", txt)
            self.assertIn("NOT what crossed the socket", txt)

    def test_a_reply_cannot_rewrite_the_page_that_quotes_it(self):
        """The raw bytes go in through textContent. A model that emits markup is quoted, not
        obeyed — otherwise the transparency surface is an injection point."""
        payload = json.loads(json.dumps(ASK))
        hostile = '<img src=x onerror="window.__pwned=1"><b>bold</b>'
        payload["transcript"][1]["reply"] = hostile
        payload["transcript"][1]["reply_sha"] = _sha16(hostile)
        with _Server(payload=payload) as url, _Page(url) as p:
            p.perturb()
            self.assertIn(hostile, p.open_wire(), "the markup must be QUOTED")
            self.assertIsNone(p.page.evaluate("window.__pwned ?? null"))
            self.assertEqual(0, p.page.locator("#calls img").count())

    def test_no_calls_is_a_STATE_and_says_so(self):
        payload = json.loads(json.dumps(ASK))
        payload["transcript"] = []
        with _Server(payload=payload) as url, _Page(url) as p:
            p.perturb()
            self.assertIn("no call", p.open_wire().lower())

    def test_the_traffic_sits_below_the_answer(self):
        """Answer-first is load-bearing and a raw dump is the most tempting thing to hoist."""
        with _Server() as url, _Page(url) as p:
            p.perturb()
            self.assertLess(p.page.locator("#answer").bounding_box()["y"],
                            p.page.locator("#wire").bounding_box()["y"])

    def test_it_starts_OPEN(self):
        """RESTATED, on the operator's third asking.

        This required the panel to start COLLAPSED, by analogy with the scope: answer-first is
        constitutional and a raw dump is the most tempting thing to hoist above it. The
        analogy was wrong. The scope is an inspection surface somebody consults when a result
        surprises them; the raw traffic is a STANDING REQUIREMENT — "every input and output of
        the LM, even intermediate ones, should be visible raw" — and a thing you must click to
        see has not been shown, it has been filed. It was also sitting below four panels
        nobody asked for. Answer-first is unaffected: the answer is still above it.
        """
        with _Server() as url, _Page(url) as p:
            p.perturb()
            self.assertTrue(p.page.locator("#wire").evaluate("e => e.open"),
                            "the raw traffic must be visible without a click")

    def test_it_sits_DIRECTLY_under_the_answer(self):
        """Above every other panel. It was at y=904 behind the proposals, the current, the
        floor and the gate — available, and not shown."""
        with _Server() as url, _Page(url) as p:
            p.perturb()
            ans = p.page.locator("#answer").bounding_box()
            wire = p.page.locator("#wire").bounding_box()
            scope = p.page.locator("#scope").bounding_box()
            self.assertLess(ans["y"], wire["y"], "answer-first still holds")
            self.assertLess(wire["y"], scope["y"], "the raw traffic sits above the scope")
            others = p.page.locator("h2").first.bounding_box()
            self.assertLess(wire["y"], others["y"],
                            "the raw traffic must precede the panels nobody asked for")


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
        against the answer path would leave `render` and `renderLedger` permanently
        unexercised and would have to declare them expected exceptions — an allowlist that
        grows until the control means nothing. So the test drives every live path and then
        asserts the set is empty.

        UPDATED AT THE NULL SURFACE: the retain path is gone, so `render` is now reached by
        the reset button instead of by a checkbox. The control did not weaken — the same
        function is still required to run — only the route to it changed, which is exactly
        what this control exists to keep true as routes move.
        """
        names = self._defined()
        with _Server() as url, _Page(url) as p:
            p.page.evaluate(self._INSTRUMENT, names)
            p.perturb()                                    # THE ACT: /ask
            p.page.click("button:has-text('reset current')")   # CURRENT: /reset -> render()
            p.page.wait_for_timeout(400)
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
