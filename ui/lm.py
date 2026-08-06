"""The LM in the loop: a proposer INTO D (move-3), extraction-tier, never clamps.

OPENROUTER ONLY, model `openrouter/auto`. There is no Anthropic path: the transport, the
key lookup and the model selection all refuse a non-`sk-or-` key outright. A fallback would
let a stray key in the environment silently reroute the operator's window to another
provider, which is the kind of thing that is only noticed after it has already happened.

The LM does four things, all as *proposals* the engine then disposes:

1. `LMProposer` — an `Extractor` subclass, so its deltas are stamped `WarrantTier.EXTRACTION`
   by the sealed `extract()` (gate 3). An extraction-tier warrant is not clamp-eligible, so
   `Clamp(...)` refuses it: the LM literally cannot clamp, by construction.
2. `propose_resolution` — for a contested block, the LM argues variant_a / variant_b /
   coexist / abstain, with reasoning. A proposal object; the engine's settlement decides.
3. `propose_bridges` — cross-chart "this English ~ that Lean" suggestions.
4. `answer` — a conversational reply, grounded on engine facts injected by the server.

The call goes through a plain stdlib `urllib` transport so the app needs no SDK.
The transport is injectable (`LMClient(transport=...)`) so tests exercise the whole loop
against a canned response without a network or a key. The key is never logged.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Callable, Iterable

from engine.extract import Extractor, Span
from engine.types import BValue, Document

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# OpenRouter keys start with sk-or-; the operator asked for auto model-selection.
#: PINNED, not `auto`. A model selector is a mechanism parameter, and `openrouter/auto`
#: means the mechanism is chosen by a vendor's cost heuristic per call.
#:
#: Measured, one region, same prompt, same temperature 0.0:
#:   auto -> gemini-2.5-flash-lite   1,789 lines / 51 distinct pairs / 35.1 repeats / 0 same_claim
#:   gemini-2.5-flash                   24 lines / 24 distinct pairs /  1.0 repeats / 5 same_claim
#:   claude-sonnet-4                    16 lines / 16 distinct pairs /  1.0 repeats / 2 same_claim
#:   gpt-4o-mini                        15 lines / 15 distinct pairs /  1.0 repeats / 0 same_claim
#:
#: `auto` served 448 of 465 historical calls with the LITE model, and `same_claim` is the only
#: loop-eligible relation — so a model that never emits it cannot grow a fiber, close a cycle
#: or produce a floor. The corpus's forest topology is downstream of this default.
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")


#: What actually answered, most recently. Empty until the first call.
LAST_SERVED = ""

_VALID_TYPES = ("assert", "define", "conditional", "normative")
_VALID_B: tuple[BValue, ...] = ("T", "F", "B", "N")


def _is_openrouter(key: str) -> bool:
    return key.startswith("sk-or-")


def api_key(explicit: str | None = None) -> str:
    """OPENROUTER ONLY. An explicit request key, else `OPENROUTER_API_KEY`.

    There is deliberately NO `ANTHROPIC_API_KEY` fallback: every LM call the engine makes on
    the operator's behalf goes through OpenRouter, and a fallback would let a stray Anthropic
    key in the environment silently reroute the whole window to a different provider.
    """
    return (explicit or os.environ.get("OPENROUTER_API_KEY") or "").strip()


def model_for(key: str) -> str:
    """The PINNED model. Overridable by `OPENROUTER_MODEL`, never routed per call."""
    if key and not _is_openrouter(key):
        raise RuntimeError(
            "refusing a non-OpenRouter key: this build calls OpenRouter only "
            "(keys start with sk-or-). No Anthropic path exists.")
    return OPENROUTER_MODEL


def lm_available(explicit: str | None = None) -> bool:
    return bool(api_key(explicit))


Transport = Callable[[str, dict], str]


def _http_post(key: str, body: dict, usage: dict | None = None) -> str:
    """POST to OpenRouter (OpenAI-format) and return the text. OpenRouter only.

    `usage`, if given, is filled in place with what the provider REPORTED: token counts and,
    because the request asks for it, OpenRouter's own `cost`. It is left empty when the
    provider says nothing. The caller must then report cost as unavailable rather than
    multiply tokens by a guessed rate — an estimate presented as a running total is a
    fabricated number, and this build does not produce those.
    """
    if _is_openrouter(key):
        or_body = {
            "model": body["model"],
            "temperature": body.get("temperature", 0.3),
            "max_tokens": body.get("max_tokens", 1500),
            "usage": {"include": True},        # ask OpenRouter to report what it charged
            "messages": ([{"role": "system", "content": body["system"]}] if body.get("system")
                         else []) + body["messages"],
        }
        req = urllib.request.Request(
            OPENROUTER_URL, data=json.dumps(or_body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                     "X-Title": "common-ground window"},
            method="POST")
        with urllib.request.urlopen(req, timeout=180) as resp:
            payload = json.load(resp)
        if usage is not None:
            reported = payload.get("usage") or {}
            usage.update({k: reported[k] for k in
                          ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
                          if k in reported})
            usage["model"] = payload.get("model", "")
            # THE LAST SERVED MODEL, module-level, so the header can report what actually
            # answered rather than what was configured. Code-truth != wire-truth has now bitten
            # three times — the HTML, the commit stamp, and an env override beating the pin —
            # and each time the fix was making the served thing self-report.
            global LAST_SERVED
            LAST_SERVED = usage["model"]
        if payload.get("error"):
            raise RuntimeError(f"openrouter error: {payload['error'].get('message', '?')}")
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError(f"openrouter returned no choices (model={payload.get('model')})")
        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content")
        if content:
            return content
        # Auto model-selection can land on a REASONING model (e.g. gpt-5-nano). Those put
        # their tokens in `reasoning` and return `content: null` — and when the budget runs
        # out mid-thought, `finish_reason` is "length" and there is no answer at all. Silently
        # returning "" would look like the model declined; say what actually happened.
        if choice.get("finish_reason") == "length":
            raise RuntimeError(
                f"openrouter: response truncated before any content "
                f"(model={payload.get('model')}, finish_reason=length). A reasoning model "
                "spent the budget thinking; raise max_tokens."
            )
        reasoning = message.get("reasoning")
        if reasoning:
            return reasoning
        raise RuntimeError(
            f"openrouter: empty content (model={payload.get('model')}, "
            f"finish_reason={choice.get('finish_reason')})")
    raise RuntimeError("non-OpenRouter key reached the transport; there is no Anthropic path")


class LMClient:
    """A thin OpenRouter client; injectable transport for tests."""

    def __init__(self, key: str, model: str | None = None, transport: Transport | None = None):
        import inspect

        self._key = key
        self.model = model or model_for(key)
        self._transport = transport or _http_post
        #: What the provider reported for the LAST call: tokens and, when OpenRouter supplies
        #: it, `cost`. Empty when nothing was reported. Never estimated.
        self.last_usage: dict = {}
        try:
            self._wants_usage = len(inspect.signature(self._transport).parameters) >= 3
        except (TypeError, ValueError):
            self._wants_usage = False        # a builtin or C callable: no usage channel

    def complete(self, system: str, user: str, temperature: float, max_tokens: int = 1500) -> str:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": max(0.0, min(1.0, float(temperature))),
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        self.last_usage = {}
        if self._wants_usage:
            return self._transport(self._key, body, self.last_usage)
        return self._transport(self._key, body)


def _parse_json_block(raw: str) -> object:
    """Tolerant JSON extraction — accepts a bare object/array or a ```json fenced block."""
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1).strip()
    start = min((i for i in (raw.find("{"), raw.find("[")) if i != -1), default=-1)
    if start == -1:
        return {}
    try:
        return json.loads(raw[start:], strict=False)
    except json.JSONDecodeError:
        # trim trailing prose after the last closing brace/bracket
        end = max(raw.rfind("}"), raw.rfind("]"))
        return json.loads(raw[start:end + 1], strict=False) if end > start else {}


_EXTRACT_SYS = (
    "You extract claims from text into typed deltas for a reconciliation engine. Return ONLY "
    "JSON: {\"claims\":[{\"surface\":str,\"type\":one of "
    "['assert','define','conditional','normative'],\"value\":one of "
    "['T','F','B','N'],\"confidence\":0..1}]}. value: T=asserted true, F=negated, "
    "B=explicitly contested/both, N=hedged/unknown. Be faithful; do not invent claims."
)


class LMProposer(Extractor):
    """LM extraction as an `Extractor` — deltas are EXTRACTION-tier and cannot clamp."""

    def __init__(self, extractor_id: str, prompt_id: str, client: LMClient, temperature: float):
        super().__init__(extractor_id, prompt_id)
        self.client = client
        self.temperature = temperature

    def _spans(self, doc: Document) -> Iterable[Span]:
        raw = self.client.complete(_EXTRACT_SYS, doc.text, self.temperature, max_tokens=2000)
        payload = _parse_json_block(raw)
        claims = payload.get("claims", []) if isinstance(payload, dict) else []
        for i, c in enumerate(claims):
            typ = c.get("type") if c.get("type") in _VALID_TYPES else "assert"
            val = c.get("value") if c.get("value") in _VALID_B else "T"
            surface = str(c.get("surface", "")).strip()
            if not surface:
                continue
            yield Span(
                surface=surface, type=typ, value=val,
                confidence=float(c.get("confidence", 0.6)), locator=f"lm:{self.extractor_id}:{i}",
            )


_RESOLVE_SYS = (
    "You are a PROPOSER for a reconciliation engine. A block of claims is contested. Argue "
    "which resolution the evidence favors. Return ONLY JSON: "
    "{\"choice\":one of ['variant_a','variant_b','coexist','abstain'],\"reasoning\":str}. "
    "coexist = both stand as legitimately different claims; abstain = evidence is insufficient. "
    "You PROPOSE only; the engine's settlement and gates decide. You never clamp."
)


def propose_resolution(client: LMClient, block_id: str, variants: list[dict],
                       temperature: float) -> dict:
    desc = f"Contested block {block_id}. Competing claims:\n" + "\n".join(
        f"- [{v.get('chart')}] value={v.get('value')} :: {v.get('nu', '')}" for v in variants)
    raw = client.complete(_RESOLVE_SYS, desc, temperature, max_tokens=800)
    out = _parse_json_block(raw)
    out = out if isinstance(out, dict) else {}
    choice = out.get("choice")
    return {
        "block": block_id,
        "choice": choice if choice in ("variant_a", "variant_b", "coexist", "abstain") else "abstain",
        "reasoning": str(out.get("reasoning", "")).strip() or "(no reasoning returned)",
        "tier": "extraction/proposal — NOT clamped",
    }


_BRIDGE_SYS = (
    "You propose cross-chart bridges for a reconciliation engine: pairs of claims from "
    "different charts (english/lean/tabular/conversation) that state the same thing. Return "
    "ONLY JSON: {\"bridges\":[{\"a\":str,\"b\":str,\"why\":str}]}. Propose only clear matches. "
    "These are PROPOSALS; the engine decides whether to fiber them. You never clamp."
)


def propose_bridges(client: LMClient, slots: list[dict], temperature: float) -> list[dict]:
    listing = "\n".join(f"- [{s.get('chart')}] {s.get('nu', '')}" for s in slots)
    raw = client.complete(_BRIDGE_SYS, f"Claims across charts:\n{listing}", temperature, max_tokens=900)
    out = _parse_json_block(raw)
    bridges = out.get("bridges", []) if isinstance(out, dict) else []
    return [{"a": str(b.get("a", "")), "b": str(b.get("b", "")), "why": str(b.get("why", "")),
             "tier": "extraction/proposal — NOT clamped"}
            for b in bridges if b.get("a") and b.get("b")]


_ASK_SYS = (
    "You answer questions about a reconciliation engine's state. You are GROUNDED: only speak "
    "to what the engine facts below hold. If the facts don't cover it, say so. Do not invent "
    "slots, floors, or verdicts. The engine settles and gates; you propose and explain.\n\n"
    "ENGINE FACTS (authoritative):\n{facts}"
)


def answer(client: LMClient, question: str, engine_facts: str, temperature: float) -> str:
    return client.complete(_ASK_SYS.replace("{facts}", engine_facts), question,
                           temperature, max_tokens=1200).strip()
