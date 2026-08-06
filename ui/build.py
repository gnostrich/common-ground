"""WHICH BUILD IS ACTUALLY SERVING. Stamped into the image, read at import.

Deploy skew has now happened twice, and both times it was invisible: the backend changed and
the served page did not, and every check I ran was against the code in front of me rather
than the bytes on the wire. A build that cannot say which commit it is cannot be caught
serving an old one — so it says, in the header, on every response.

The stamp is written at image build time into `runs/BUILD` (or the `CG_COMMIT` env a platform
supplies). Read at IMPORT, not per request: the working tree inside a running container is not
the thing that was deployed, and reading it per request would report the wrong answer
confidently.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

STAMP_PATH = Path(__file__).resolve().parent.parent / "runs" / "BUILD"


def _read() -> str:
    env = (os.environ.get("CG_COMMIT") or "").strip()
    if env:
        return env[:12]
    if STAMP_PATH.exists():
        return STAMP_PATH.read_text(encoding="utf-8").strip()[:12]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             timeout=5, cwd=str(STAMP_PATH.parent.parent))
        if out.returncode == 0:
            return out.stdout.strip()[:12]
    except Exception:
        pass
    return ""


#: Resolved ONCE, at import.
SERVED = _read()


def stamp() -> dict[str, str]:
    """What the window reports about itself. `unknown` is a state, not a pass.

    A build with no stamp cannot be checked, and saying so is the point: silence here is
    exactly what let a pre-unification page serve a unified backend without anyone noticing.
    """
    if not SERVED:
        return {"served": "unknown",
                "warning": "THIS BUILD CANNOT SAY WHICH COMMIT IT IS. A deploy that cannot "
                           "identify itself cannot be caught serving a stale page."}
    return {"served": SERVED}
