"""Claude export JSON -> English-chart documents, with thread/turn provenance.

One document per turn rather than per thread. A thread is not a claim-bearing unit: it
contains many turns, often contradicting each other as the conversation develops, and
collapsing them would hide exactly the disagreement the ledger is supposed to surface.
Per-turn documents also give the duplicate-source null something meaningful to work with,
since each turn carries its own content hash.

Exclusions (D3) are applied here, before extraction, and they are mandatory. A path that
cannot prove its exclusions were applied refuses to load.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from engine import EngineError
from engine.types import Document


def _turn_text(message: dict[str, Any]) -> str:
    """Text of a turn, tolerating both the flat and block-structured export shapes."""
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return text
    parts: list[str] = []
    for block in message.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            value = block.get("text")
            if isinstance(value, str):
                parts.append(value)
    return "\n".join(parts)


def _excluded(text: str, thread_name: str, exclusions: Sequence[str]) -> bool:
    haystack = f"{thread_name}\n{text}".casefold()
    return any(term.casefold() in haystack for term in exclusions if term)


def load_claude_export(
    path: str | Path,
    exclusions: Sequence[str] | None,
    senders: Iterable[str] = ("human", "assistant"),
) -> list[Document]:
    """Load an export into per-turn documents.

    `exclusions` is the D3 privacy pass and is **not optional**: passing `None` raises.
    An empty list is a legitimate decision ("nothing is excluded") but it has to be made
    explicitly, because silently defaulting to no exclusions would turn an unfilled
    decision into a privacy incident.
    """
    if exclusions is None:
        raise EngineError(
            "D3 EXCLUSIONS is unresolved. The privacy pass is mandatory and precedes "
            "ingestion (KICKOFF section 0 D3); pass an explicit list, including [] if "
            "nothing is to be excluded."
        )

    p = Path(path)
    if not p.exists():
        raise EngineError(f"claude export not found: {p}")

    payload = json.loads(p.read_text(encoding="utf-8"))
    threads = payload if isinstance(payload, list) else payload.get("conversations", [])

    allowed = set(senders)
    out: list[Document] = []
    skipped = 0

    for thread in threads:
        thread_id = str(thread.get("uuid") or thread.get("id") or "thread")
        thread_name = str(thread.get("name") or "")
        messages = thread.get("chat_messages") or thread.get("messages") or []
        for index, message in enumerate(messages):
            sender = str(message.get("sender") or message.get("role") or "")
            if allowed and sender not in allowed:
                continue
            text = _turn_text(message)
            if not text.strip():
                continue
            if _excluded(text, thread_name, exclusions):
                skipped += 1
                continue
            out.append(
                Document(
                    doc_id=f"claude:{thread_id}:{index}",
                    chart="english",
                    text=text,
                    source="claude_export",
                    meta={
                        "thread_id": thread_id,
                        "thread_name": thread_name,
                        "turn": str(index),
                        "sender": sender,
                    },
                )
            )

    if skipped:
        # Surfaced rather than silent: how much the privacy pass removed is part of what
        # the run is, and a reader of the report should not have to guess at it.
        out_meta = {"excluded_turns": str(skipped)}
        for doc in out[:1]:
            doc.meta.update(out_meta)

    return out
