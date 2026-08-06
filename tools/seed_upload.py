"""Push the corpus to the deploy over the DATA CHANNEL. It never touches a git tree.

The snapshot is data, not code. It may not be committed to a repository, public or private,
and may not ship inside an image — which is exactly why `ui/boot.seed_state` has never
executed: the staging directory is gitignored for publication reasons and Railway skips
gitignored paths, so the correct code was unreachable from the wrong source.

    CG_URL=... CG_TOKEN=... CG_SEED_UPLOAD_TOKEN=... python3 tools/seed_upload.py FILE [NAME]

The digest is computed here and declared in a header; the server hashes what it receives and
refuses the write unless they agree. A truncated transfer that loaded as a smaller corpus
would be indistinguishable from a smaller corpus.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.wire import Forwarder  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    import urllib.request

    src = Path(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else src.name
    digest, size = sha256(src), src.stat().st_size
    print(f"{src} -> {name}: {size:,} bytes, sha256 {digest[:16]}…")

    with Forwarder(os.environ["CG_URL"].rstrip("/"), os.environ["CG_TOKEN"]) as local:
        req = urllib.request.Request(
            f"{local}/seed", data=src.read_bytes(), method="POST",
            headers={"Content-Type": "application/octet-stream",
                     "X-Seed-Token": os.environ["CG_SEED_UPLOAD_TOKEN"],
                     "X-Seed-Name": name,
                     "X-Seed-Sha256": digest})
        with urllib.request.urlopen(req, timeout=1800) as r:
            print(r.read().decode()[:600])


if __name__ == "__main__":
    main()
