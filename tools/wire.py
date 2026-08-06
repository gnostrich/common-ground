"""A LOCAL HOP TO THE SERVED DEPLOY, so a real browser can be pointed at it.

Chromium cannot use this session's egress proxy — every CONNECT comes back
ERR_CONNECTION_RESET — so a headless browser cannot navigate to the Railway URL directly.
The standing rule is that nothing is landed until the BROWSER agrees, and a rule that cannot
be executed is not a rule, so the hop is made explicit instead of the rule being dropped.

WHAT THIS IS AND IS NOT. `urllib` reaches the deploy fine through the proxy. This forwards
every request — the page, /corpus, /ask, /propose, /proposer — to the served URL and returns
the response bytes unchanged. The HTML the browser parses and the JSON it renders are the
deploy's. What is local is one transport hop and nothing else: no fixture, no stub, no
recorded response. A test using this is testing the deployed build; it is not testing
Railway's edge, and that limit is stated rather than glossed.
"""

from __future__ import annotations

import http.server
import socketserver
import threading
import urllib.error
import urllib.request

_HOP = ("connection", "keep-alive", "transfer-encoding", "content-encoding",
        "content-length")


class Forwarder:
    def __init__(self, upstream: str, token: str = ""):
        self.upstream, self.token = upstream.rstrip("/"), token
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def _url(self):
                path = self.path
                if outer.token and "t=" not in path:
                    path += ("&" if "?" in path else "?") + "t=" + outer.token
                return outer.upstream + path

            def _relay(self, body=None):
                req = urllib.request.Request(self._url(), data=body,
                                             method=self.command)
                # RELAY THE HEADERS THE REQUEST CARRIES, not one hand-picked field. Forwarding
                # only Content-Type silently dropped X-Seed-Token and turned a correct upload
                # into a 401 — a forwarder that edits what it forwards is not a forwarder.
                for k, v in self.headers.items():
                    if k.lower() in ("host", "content-length", "connection", "accept-encoding"):
                        continue
                    req.add_header(k, v)
                try:
                    with urllib.request.urlopen(req, timeout=600) as r:
                        payload, status, hdrs = r.read(), r.status, r.headers
                except urllib.error.HTTPError as e:
                    payload, status, hdrs = e.read(), e.code, e.headers
                self.send_response(status)
                for k, v in hdrs.items():
                    if k.lower() not in _HOP:
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_GET(self):
                self._relay()

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                self._relay(self.rfile.read(n))

        self._srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
        self._srv.daemon_threads = True
        self.port = self._srv.server_address[1]

    def __enter__(self) -> str:
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{self.port}"

    def __exit__(self, *a):
        self._srv.shutdown()
        self._srv.server_close()
