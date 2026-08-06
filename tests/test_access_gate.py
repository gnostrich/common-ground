"""The deploy gate, and what it is actually protecting.

Two things sit behind a reachable window, and only the first is obvious. The corpus is
somebody's private material — but `/ask` and `/propose` call OpenRouter with the SERVER's
key, so an ungated public URL is not merely a disclosure, it is an unmetered charge against
the operator's account by anyone who has the link. That is why `serve()` REFUSES to start a
reachable window with no token rather than warning about it: a deployer who forgets gets a
service that will not boot, which is recoverable, and the other way round is not.

Each control is planted against — the gate is exercised with a wrong token, a missing token,
and a token that shares a prefix with the real one.
"""

from __future__ import annotations

import unittest
from unittest import mock


class _Headers(dict):
    def get(self, key, default=None):        # http.client.HTTPMessage is case-insensitive
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default


def _with_token(token: str):
    """Reload the module under a given COMMON_GROUND_TOKEN. The gate reads it at import."""
    import importlib
    import os

    import ui.server as server
    with mock.patch.dict(os.environ, {"COMMON_GROUND_TOKEN": token}):
        return importlib.reload(server)


class AnUngatedDeployIsRefused(unittest.TestCase):
    def test_planted_serve_refuses_to_bind_wide_with_no_token(self):
        """PLANTED: the exact oversight — deploy the window, forget the variable."""
        import os

        server = _with_token("")
        with mock.patch.dict(os.environ, {"PORT": "8080"}, clear=False):
            with self.assertRaises(SystemExit) as caught:
                server.serve()
        message = str(caught.exception)
        self.assertIn("COMMON_GROUND_TOKEN", message)
        self.assertIn("OpenRouter", message, "the refusal must name the SPEND, not just the "
                                             "corpus — the spend is the part that surprises")

    def test_open_on_purpose_is_spelled_out_not_defaulted(self):
        """Running wide open is legitimate; forgetting to decide is not. The opt-out is the
        literal string, so it cannot be reached by leaving a variable unset."""
        server = _with_token("none")
        self.assertTrue(server.OPEN_ON_PURPOSE)
        self.assertEqual(server.ACCESS_TOKEN, "")
        self.assertTrue(server._authorized("/ask", "/ask", _Headers()))

    def test_a_laptop_run_needs_no_token(self):
        server = _with_token("")
        self.assertTrue(server._authorized("/ask", "/ask", _Headers()))


class TheGateChecksEveryCostingPath(unittest.TestCase):
    def setUp(self):
        self.server = _with_token("s3cret")

    def test_the_page_shell_is_open_but_nothing_else_is(self):
        for path in ("/", "/index.html", "/healthz"):
            self.assertTrue(self.server._authorized(path, path, _Headers()),
                            f"{path} holds no corpus and spends nothing")
        for path in ("/ask", "/propose", "/corpus", "/proposer", "/proposer/control"):
            self.assertFalse(self.server._authorized(path, path, _Headers()),
                             f"{path} reads the corpus or spends the key and must be gated")

    def test_planted_a_wrong_token_is_refused(self):
        self.assertFalse(self.server._authorized("/ask", "/ask?t=wrong", _Headers()))

    def test_planted_a_prefix_of_the_token_is_refused(self):
        """A gate compared with `==` leaks its prefix to a patient caller; this one uses
        hmac.compare_digest, and the control names the reason."""
        self.assertFalse(self.server._authorized("/ask", "/ask?t=s3cre", _Headers()))
        self.assertFalse(self.server._authorized("/ask", "/ask?t=s3secret", _Headers()))

    def test_the_right_token_passes_by_query_cookie_or_header(self):
        self.assertTrue(self.server._authorized("/ask", "/ask?t=s3cret", _Headers()))
        self.assertTrue(self.server._authorized(
            "/ask", "/ask", _Headers({"Cookie": "other=1; cg_t=s3cret"})))
        self.assertTrue(self.server._authorized(
            "/ask", "/ask", _Headers({"X-Common-Ground-Token": "s3cret"})))

    def test_an_empty_supplied_token_never_matches(self):
        self.assertFalse(self.server._authorized("/ask", "/ask?t=", _Headers()))
        self.assertFalse(self.server._authorized(
            "/ask", "/ask", _Headers({"Cookie": "cg_t="})))

    def tearDown(self):
        _with_token("")     # leave the module as a laptop run found it


class ThePageCarriesTheTokenToEveryEndpoint(unittest.TestCase):
    """A gate the page cannot get through is a gate that just breaks the window."""

    def test_no_endpoint_is_fetched_without_the_token_helper(self):
        from engine.constants import REPO_ROOT

        text = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        bare = [line.strip() for line in text.splitlines()
                if "fetch('/" in line and "withToken" not in line]
        self.assertEqual(bare, [], "every call must go through withToken(), or it will 401 "
                                   "on a deployed window")

    def test_every_CONTENT_chart_is_offered_in_the_window(self):
        """PLANTED against the two that were missing: the selectors listed four charts for
        weeks after python and go were routing.

        The rule is CONTENT charts, and the refinement is not a loosening. A chart you can
        type a boundary condition into is a chart whose claims are about the world.
        `correspondence` is what arrows land in, and `medium` carries glosses — statements
        about how a model reads a word. Neither is something an operator asserts, and
        `engine/medium.py`'s CONTENT_CHARTS is the same positive list that keeps a gloss out
        of settlement, so the window and the firewall cannot disagree about which is which.
        """
        from engine.charts import chart_names
        from engine.constants import REPO_ROOT
        from engine.medium import CONTENT_CHARTS

        text = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        for name in chart_names():
            if name == "correspondence" or name not in CONTENT_CHARTS:
                continue
            self.assertIn(f"<option>{name}</option>", text,
                          f"the {name} chart exists but cannot be selected in the window")

    def test_an_INTERFACE_chart_is_NOT_offered_as_something_to_type_into(self):
        """THE FIREWALL, REACHING THE UI. A gloss is about how a medium reads a word; it is
        not a claim an operator makes about the world. Offering `medium` in the entry
        selector would let one be typed straight into content settlement, past the
        firewall — the breach coming in through the surface rather than through the engine.
        """
        from engine.charts import chart_names
        from engine.constants import REPO_ROOT
        from engine.medium import CONTENT_CHARTS, MEDIUM_CHART

        text = (REPO_ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        interface = [n for n in chart_names() if n not in CONTENT_CHARTS]
        self.assertIn(MEDIUM_CHART, interface, "the medium chart must be an interface chart")
        for name in interface:
            self.assertNotIn(f"<option>{name}</option>", text,
                             f"{name} is an interface chart and must not be typeable")


if __name__ == "__main__":
    unittest.main()


class TheDataChannelIsNarrowAndVERIFIED(unittest.TestCase):
    """The corpus arrives over the wire or not at all — and only under conditions.

    It may not enter a git tree, public or private, and may not ship inside an image. That
    constraint is what made `ui/boot.seed_state` unreachable: the staging directory is
    gitignored for publication reasons, Railway skips gitignored paths, and correct code sat
    unexecuted for every deploy that has ever run. The channel replaces the source, not the
    rule.
    """

    def test_the_endpoint_does_not_exist_without_the_token_variable(self):
        # NOT 403. A deploy with the variable unset must have no upload surface to find —
        # a 403 advertises what is behind it.
        import ui.server as srv
        self.assertEqual("CG_SEED_UPLOAD_TOKEN", srv.SEED_UPLOAD_ENV)
        src = __import__("inspect").getsource(srv.Handler._seed)
        self.assertIn("404", src.split("bad seed token")[0])

    def test_the_writable_names_are_a_FIXED_set_not_a_caller_path(self):
        # An upload endpoint that takes a filename is an arbitrary-write endpoint wearing a
        # narrower name.
        import ui.server as srv
        self.assertEqual({"corpus.snapshot", "proposer.journal.jsonl"}, srv.UPLOADABLE)

    def test_a_digest_is_REQUIRED(self):
        # An unverified upload that truncates lands a short file that loads as a smaller
        # corpus, and nothing downstream could tell the difference.
        import inspect

        import ui.server as srv
        src = inspect.getsource(srv.Handler._seed)
        self.assertIn("X-Seed-Sha256", src)
        self.assertIn("is required", src)

    def test_the_write_is_atomic(self):
        # A half-written snapshot at the real path is a corpus nobody can distinguish from a
        # smaller one. Bytes land beside the target and are renamed only after verification.
        import inspect

        import ui.server as srv
        src = inspect.getsource(srv.Handler._seed)
        self.assertIn("mkstemp", src)
        self.assertIn("os.replace", src)

    def test_the_upload_size_ceiling_is_stated(self):
        import ui.server as srv
        self.assertEqual(256 * 1024 * 1024, srv.MAX_UPLOAD)

    def test_the_seed_path_is_handled_before_the_json_body_parser(self):
        # The corpus is tens of megabytes of pickle. Running it through a JSON parser fails on
        # the first byte, and a socket cannot be read twice.
        import inspect

        import ui.server as srv
        src = inspect.getsource(srv.Handler.do_POST)
        self.assertLess(src.index('path == "/seed"'), src.index("self._body()"))

    def test_the_seed_path_is_still_behind_the_ordinary_access_gate(self):
        import ui.server as srv
        self.assertNotIn("/seed", srv.OPEN_PATHS)


class TheCorpusIsNEVERInAGitTree(unittest.TestCase):
    """PERMANENT. Snapshot bytes in any git object is RED, now and afterwards."""

    def _tracked(self):
        import subprocess
        from engine.constants import REPO_ROOT
        out = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True,
                             text=True, timeout=120)
        return out.stdout.splitlines()

    def test_no_snapshot_or_journal_is_tracked_now(self):
        bad = [p for p in self._tracked()
               if p.endswith(("corpus.snapshot", "proposer.journal.jsonl", "pool.jsonl"))]
        self.assertEqual([], bad, f"corpus bytes are tracked: {bad}")

    def test_no_staging_directory_is_tracked(self):
        bad = [p for p in self._tracked() if p.startswith("seed_runs/")]
        self.assertEqual([], bad, f"the staging copy is tracked: {bad}")

    def test_no_tracked_file_carries_a_python_pickle_header(self):
        # The snapshot is a pickle. A pickle in the tree is corpus bytes under another name,
        # whatever the path says.
        from engine.constants import REPO_ROOT
        for rel in self._tracked():
            p = REPO_ROOT / rel
            if not p.is_file() or p.stat().st_size < 4096:
                continue
            with p.open("rb") as fh:
                head = fh.read(2)
            self.assertNotEqual(b"\x80\x05", head, f"{rel} is a pickle")

    def test_the_ignore_rules_still_exclude_them(self):
        from engine.constants import REPO_ROOT
        body = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        for name in ("runs/corpus.snapshot", "runs/proposer.journal.jsonl", "seed_runs/"):
            self.assertIn(name, body)


class TheSeedEndpointMustACTUALLYRUN(unittest.TestCase):
    """BEHAVIOURAL, not source-reading. The last set of controls read the handler's TEXT.

    Every assertion about /seed was a substring check over `inspect.getsource`, so a
    `NameError` on the first line that touches the filesystem passed all of them: the suite
    was green, the deployed endpoint died before sending a byte, and Railway returned
    "Application failed to respond". That is the third time in this session a control has
    been simpler than the thing it stands for — the bound-method `id`, the stub with no `id`,
    and now a source scan standing in for a request. So this class starts a real server and
    posts to it.
    """

    def _serve(self, token="probe-token"):
        import importlib
        import os
        import socketserver
        import threading

        os.environ["CG_SEED_UPLOAD_TOKEN"] = token
        os.environ["CG_OPEN"] = "1"
        import ui.server as srv
        importlib.reload(srv)
        httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), srv.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"

    def _post(self, url, data, **headers):
        import urllib.error
        import urllib.request
        req = urllib.request.Request(url + "/seed", data=data, method="POST",
                                     headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_a_verified_upload_is_written(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path

        import engine.corpus_state as cs
        keep = cs.SNAPSHOT_PATH
        with tempfile.TemporaryDirectory() as d:
            cs.SNAPSHOT_PATH = str(Path(d) / "corpus.snapshot")
            httpd, url = self._serve()
            try:
                import ui.server as srv
                srv.SNAPSHOT_PATH = cs.SNAPSHOT_PATH
                body = b"y" * 4096
                code, out = self._post(
                    url, body, **{"X-Seed-Token": "probe-token",
                                  "X-Seed-Name": "corpus.snapshot",
                                  "X-Seed-Sha256": hashlib.sha256(body).hexdigest()})
                self.assertEqual(200, code, out[:400])
                rec = json.loads(out)
                self.assertTrue(rec["ok"])
                self.assertEqual(4096, rec["bytes"])
                self.assertEqual(body, Path(cs.SNAPSHOT_PATH).read_bytes())
            finally:
                httpd.shutdown()
                cs.SNAPSHOT_PATH = keep

    def test_a_WRONG_digest_is_refused_and_nothing_is_written(self):
        import tempfile
        from pathlib import Path

        import engine.corpus_state as cs
        keep = cs.SNAPSHOT_PATH
        with tempfile.TemporaryDirectory() as d:
            cs.SNAPSHOT_PATH = str(Path(d) / "corpus.snapshot")
            httpd, url = self._serve()
            try:
                import ui.server as srv
                srv.SNAPSHOT_PATH = cs.SNAPSHOT_PATH
                code, out = self._post(url, b"z" * 4096,
                                       **{"X-Seed-Token": "probe-token",
                                          "X-Seed-Name": "corpus.snapshot",
                                          "X-Seed-Sha256": "00" * 32})
                self.assertEqual(400, code)
                self.assertIn(b"sha256 mismatch", out)
                self.assertFalse(Path(cs.SNAPSHOT_PATH).exists())
            finally:
                httpd.shutdown()
                cs.SNAPSHOT_PATH = keep

    def test_a_bad_seed_token_is_401(self):
        httpd, url = self._serve()
        try:
            code, _ = self._post(url, b"x", **{"X-Seed-Token": "wrong",
                                               "X-Seed-Name": "corpus.snapshot",
                                               "X-Seed-Sha256": "00" * 32})
            self.assertEqual(401, code)
        finally:
            httpd.shutdown()

    def test_an_unlisted_name_is_400(self):
        httpd, url = self._serve()
        try:
            code, out = self._post(url, b"x", **{"X-Seed-Token": "probe-token",
                                                 "X-Seed-Name": "../../etc/passwd",
                                                 "X-Seed-Sha256": "00" * 32})
            self.assertEqual(400, code)
            self.assertIn(b"not an uploadable name", out)
        finally:
            httpd.shutdown()

    def test_with_no_token_variable_the_endpoint_is_404(self):
        import os
        httpd, url = self._serve(token="")
        os.environ.pop("CG_SEED_UPLOAD_TOKEN", None)
        try:
            code, _ = self._post(url, b"x", **{"X-Seed-Name": "corpus.snapshot",
                                               "X-Seed-Sha256": "00" * 32})
            self.assertEqual(404, code)
        finally:
            httpd.shutdown()
