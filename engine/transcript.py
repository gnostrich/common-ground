"""EVERY LM CALL, BOTH CHANNELS, RAW. The peripheral's traffic, inspectable.

The operator asked to see what goes into the LM and got a dump — and the dump immediately
found a defect no test had: twenty-four numbered state lines carrying no claim text. That is
the argument for this module. The LM is a peripheral with two ports, and the bytes crossing
them are the one place where "the code does X" and "X is what the model saw" can differ
silently. Wire-truth applied to the peripheral's own input side.

WHAT IS RECORDED. Every call, not only the visible one. A perturbation makes at least two —
the ATTACHMENT call that completes the region diagram, and the RENDER call that voices the
settled state — and the attachment call is the one that decides what the answer can possibly
be about. Recording only the last would show the answer's input and hide its cause.

RAW MEANS RAW. The system text and the user text as sent, byte for byte, and the reply as
returned before any parsing. Not a summary, not a trimmed preview, not the parsed result: the
parse is what this exists to let somebody check. A digest of each is carried alongside so the
displayed bytes can be verified to be the sent bytes rather than a re-render of them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def digest(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Call:
    """One crossing of the boundary, both directions."""

    port: str                  # "propose" | "render"
    system: str
    user: str
    reply: str
    model: str = ""
    seconds: float = 0.0
    error: str = ""

    def as_record(self) -> dict[str, object]:
        return {"port": self.port, "model": self.model, "seconds": round(self.seconds, 2),
                "system": self.system, "user": self.user, "reply": self.reply,
                "error": self.error,
                # THE DIGESTS make "what you are shown is what was sent" checkable rather
                # than promised: the page hashes what it displays and compares.
                "system_sha": digest(self.system), "user_sha": digest(self.user),
                "reply_sha": digest(self.reply),
                "chars": {"system": len(self.system or ""), "user": len(self.user or ""),
                          "reply": len(self.reply or "")}}


@dataclass
class Transcript:
    """Every call one act made, in order."""

    calls: list = field(default_factory=list)

    def record(self, port: str, system: str, user: str, reply: str,
               model: str = "", seconds: float = 0.0, error: str = "") -> None:
        self.calls.append(Call(port=port, system=system or "", user=user or "",
                               reply=reply or "", model=model, seconds=seconds, error=error))

    def as_record(self) -> list[dict]:
        return [c.as_record() for c in self.calls]

    @property
    def ports(self) -> list[str]:
        return [c.port for c in self.calls]


#: The transcript of the act in progress. A module-level sink for the same reason
#: `engine.inbound.DIAGNOSTICS` is one: the call sites are deep in the perturbation path and
#: threading a recorder through every signature would put plumbing in the physics.
CURRENT = Transcript()


def start() -> Transcript:
    CURRENT.calls.clear()
    return CURRENT
