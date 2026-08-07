"""Turn a recorded live run into a committable fixture: bracket skeleton, no corpus prose.

WHY THIS EXISTS. The live-fire battery's acceptance is that it TRIPS on the defects the
operator caught by hand, which means the recorded transcripts of those runs have to live in the
repository beside the tests. Those transcripts carry corpus claim text — the operator's private
material — and this repository is public.

WHAT SURVIVES: the bracket skeleton. Every citation, arrow, absence marker and contest mark
verbatim, every word replaced by a `<w>` of proportional length, line structure intact. That is
exactly what the checks read — they count brackets, compare labels against the shown sheet, and
hash replies for equality — so a fixture built this way exercises every check the real bytes
would, and carries none of the meaning.

DETERMINISTIC, which one check depends on: two identical replies redact to two identical
skeletons, so "the same question got the same answer twice" survives redaction intact.

EXPLICIT WHITELIST, never a spread. The first version copied unknown keys through and two of
them carried prose — an answer nested inside the dialogue record, and the arrow evidence lines.
A redactor that copies what it does not name leaks the day a field is added.

Run:  python3 tools/redact_run.py <recorded.json> <fixture.json>
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

BRACKET = re.compile(r"\[[^\]]*\]")


def skeleton(text: str) -> str:
    """Brackets verbatim, words as `<w>`, lines preserved."""
    out = []
    for line in (text or "").splitlines():
        pos, parts = 0, []
        for m in BRACKET.finditer(line):
            if m.start() > pos and line[pos:m.start()].strip():
                parts.append("<w>" * max(1, (m.start() - pos) // 40 + 1))
            parts.append(m.group(0))
            pos = m.end()
        if pos < len(line) and line[pos:].strip():
            parts.append("<w>" * max(1, (len(line) - pos) // 40 + 1))
        out.append("".join(parts))
    return "\n".join(out)


def _call(c: dict) -> dict:
    """One transcript call. The SYSTEM prompt is engine-authored and kept verbatim — the
    licence check reads it, and it contains no corpus material. The USER body is the region
    itself and is replaced wholesale."""
    system, user, reply = c.get("system") or "", "<region>", skeleton(c.get("reply"))
    sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]   # noqa: E731
    return {"port": c.get("port"), "model": c.get("model"), "system": system,
            "user": user, "reply": reply, "system_sha": sha(system),
            "user_sha": sha(user), "reply_sha": sha(reply)}


def redact(run: dict) -> dict:
    dlg = run.get("dialogue") or {}
    ver = run.get("faithful") or {}
    comp = run.get("compiled") or {}
    return {
        "answer": skeleton(run.get("answer")),
        "dialogue": {
            "question": dlg.get("question", ""), "turn_count": dlg.get("turn_count"),
            "stopped": dlg.get("stopped", ""), "records": dlg.get("records"),
            "resolved_records": dlg.get("resolved_records"),
            "turns": [{"turn": t.get("turn"), "ask": t.get("ask", ""),
                       "prose": skeleton(t.get("prose")), "resolved": t.get("resolved"),
                       "interrogation": t.get("interrogation", "")}
                      for t in (dlg.get("turns") or ())],
            "residuals": [{"residual": r.get("residual"), "question": r.get("question", ""),
                           "turn": r.get("turn"), "outcome": r.get("outcome")}
                          for r in (dlg.get("residuals") or ())]},
        "faithful": {k: ver.get(k) for k in ("ok", "checked", "cited", "asserted_absent",
                                             "citable")} | {
            "violations": [{"kind": v.get("kind"), "numbers": v.get("numbers", []),
                            "sentence": skeleton(v.get("sentence")),
                            "warrant": v.get("warrant", "")}
                           for v in (ver.get("violations") or ())]},
        "compiled": {
            "scope": "",
            "citations": [{k: c[k] for k in ("n", "kind", "chart", "group", "contested")
                           if k in c} for c in (comp.get("citations") or ())],
            "attachment": {"labels": (comp.get("attachment") or {}).get("labels", [])}},
        "transcript": [_call(c) for c in (run.get("transcript") or ())],
    }


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    out = redact(json.loads(src.read_text(encoding="utf-8")))
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{dst}: {len(out['dialogue']['turns'])} turn(s), "
          f"{len(out['faithful']['violations'])} violation(s), "
          f"{len(out['transcript'])} call(s)")
