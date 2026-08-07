"""B2, PROSE-FIRST: one dialogue, and the last turn IS the answer.

THE COLLAPSE. There used to be two calls with different jobs — a PROPOSE call that spoke only
in coordinates and a RENDER call that spoke only in prose. That split was an artifact of the
mute-coordinates era: the medium was not allowed to write words on the extraction port, so a
second port had to exist for the words. Once the medium answers in CITED PROSE the two are the
same act, and the final turn of the dialogue is the rendered answer — same grammar, same
checker, no separate call. A render call standing beside a dialogue that already produced prose
would be a second mechanism for one job.

WHAT CROSSES THE BOUNDARY. Arrows come from CITATION COORDINATES AND KIND TOKENS ONLY —
`[7] -refines-> [12]` — never from the words. The prose is for the operator to read. A sentence
with no coordinates yields no arrow however persuasive it is, which is OI-16 (grammar over
instruction) applied to a conversational channel: the medium may write freely, and only the
grammar crosses.

WHAT THE MEDIUM SAYS IS TESTIMONY, AT ZERO WARRANT. Not EXTRACTION — extraction is what a
parsed triple gets. Testimony is the prose itself, kept because the trajectory matters, and it
can never ground, contest, promote or compose. Corpus-inert in exactly the way `bears_on` is.

TURNS COME FROM THE GRAPH, NEVER FROM A READING OF THE REPLY. The next question is chosen by
structure — a pair composition implies that nobody has asked about, or the scaffold neighbour
of something just declined. Never "that answer seemed thin, ask again": a turn selected because
a reply read as unsatisfying is a fluency judgement steering the corpus, which is the medium
grading itself.

CHAT ONLY. The daemon's extraction stays coordinate-only. The unattended walk never runs a
dialogue and never reads prose for arrows; `engine.dialogue` is imported by the interactive
path and by nothing the walk touches.

Spec: seed/DIALOGIC.md, written before this file existed. Its six controls are in
tests/test_dialogue.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .correspondence import KINDS

#: The ONE form an arrow may take in prose. Bracketed numbers the field itself emitted, a kind
#: token from the closed set, and nothing else — no names, no surfaces, no quoted claims. A
#: model that writes an arrow any other way has written prose, and prose yields no arrow.
ARROW = re.compile(r"\[(\d+)\]\s*-(\w+)->\s*\[(\d+)\]")

#: The kinds legal in a dialogue. The base's three, plus `bears_on` for the boundary condition
#: — the same set the region wire allows, because this is the same extraction reaching the same
#: journal, not a second vocabulary for a second channel.
DIALOGUE_KINDS = frozenset(KINDS | {"bears_on"})

#: The declared journal record kind for what the medium SAYS. Zero warrant is not a low tier;
#: it is the absence of one. `WarrantTier` has no member for it and must not gain one — a
#: testimony that could be compared to EXTRACTION on a poset is a testimony that could be
#: promoted, and the whole point is that it cannot.
TESTIMONY = "testimony"

#: How many turns a dialogue may take. An unbounded interrogation is the candidate-list loop
#: with better manners — a budget-capped interrogation beside the sampler is exactly what Q5
#: deleted once already. See seed/CONSTANT_PROVENANCE.json.
TURN_BUDGET = 4


@dataclass(frozen=True, slots=True)
class Proposal:
    """One arrow read off one turn's prose. Resolves to a corpus address or is VOID."""

    src: int
    dst: int
    kind: str
    turn: int
    evidence: str
    void: str = ""

    @property
    def ok(self) -> bool:
        return not self.void

    def as_record(self) -> dict:
        return {"src": self.src, "dst": self.dst, "kind": self.kind, "turn": self.turn,
                "evidence": self.evidence, "void": self.void}


@dataclass
class Turn:
    """One exchange. The prose is testimony; the arrows are the extraction."""

    n: int
    ask: str
    prose: str = ""
    proposals: list = field(default_factory=list)
    moved: int = 0
    interrogation: str = ""

    def as_record(self) -> dict:
        return {"turn": self.n, "ask": self.ask, "prose": self.prose,
                "record_kind": TESTIMONY, "warrant": None,
                "arrows": [p.as_record() for p in self.proposals],
                "resolved": sum(1 for p in self.proposals if p.ok),
                "void": sum(1 for p in self.proposals if not p.ok),
                "moved": self.moved, "interrogation": self.interrogation}


def arrows_from(prose: str, citable: set, turn: int = 0) -> list:
    """Every `[i] -kind-> [j]` in one turn, resolved against what the field actually showed.

    RESOLVE-OR-VOID, and there is nothing here for a fuzzy match to attach to: the medium
    writes integers the field emitted, so an index outside the citable set has no nearest
    neighbour to fall back on. Four ways to be void, all decidable without reading a word:
    an unknown kind, an index the field never showed, i == j, and a duplicate of a pair this
    same turn already named.
    """
    out, seen = [], set()
    for m in ARROW.finditer(prose or ""):
        i, kind, j = int(m.group(1)), m.group(2), int(m.group(3))
        ev = m.group(0)
        if kind not in DIALOGUE_KINDS:
            out.append(Proposal(i, j, kind, turn, ev,
                                void=f"{kind!r} is not one of {sorted(DIALOGUE_KINDS)}"))
            continue
        missing = [n for n in (i, j) if n not in citable]
        if missing:
            out.append(Proposal(i, j, kind, turn, ev,
                                void=f"the field never showed {missing}"))
            continue
        if i == j:
            out.append(Proposal(i, j, kind, turn, ev,
                                void="one object is not a correspondence"))
            continue
        pair = (min(i, j), max(i, j), kind)
        if pair in seen:
            # NOT AN ERROR AND NOT A SECOND ARROW. Restating a relation in the same turn is
            # one claim and two records — the records-vs-pairs law at dialogue level.
            out.append(Proposal(i, j, kind, turn, ev, void="restated in this turn"))
            continue
        seen.add(pair)
        out.append(Proposal(i, j, kind, turn, ev))
    return out


def implied_unaddressed(compiled: dict, asked: set) -> tuple:
    """A pair composition IMPLIES that no turn has put to the medium. Already computed.

    This is the highest-value question in the graph and it costs nothing to find: the implied
    arrows are in the compiled field because composition put them there. Returning the first
    unasked one is a graph walk, not a judgement.
    """
    joins, _ = _arrow_pairs(compiled)
    for n, pair in sorted(joins.items()):
        if pair not in asked:
            return pair
    return ()


def _arrow_pairs(compiled: dict) -> tuple:
    joins, joined = {}, set()
    for c in (compiled.get("citations") or []):
        if c.get("kind") != "arrow":
            continue
        pair = tuple(sorted(int(x) for x in (c.get("joins") or ())))
        if len(pair) == 2:
            joins[int(c["n"])] = pair
            joined.add(pair)
    return joins, joined


def interrogate(compiled: dict, asked: set) -> str:
    """The next turn's question, generated MECHANICALLY FROM STRUCTURE.

    Never "that answer seemed thin, ask again". A turn selected because a reply read as
    unsatisfying is a fluency judgement steering the corpus — the medium grading itself — and
    it is the one thing this function must be incapable of. It reads the graph and never the
    prose, which is why `prose` is not a parameter.
    """
    pair = implied_unaddressed(compiled, asked)
    if pair:
        return (f"Composition implies a relation between [{pair[0]}] and [{pair[1]}] that "
                f"nothing has measured. State it as an arrow, or say the field does not have "
                f"it with [{pair[0]}] -bears_on-> [{pair[1]}] omitted entirely.")
    contested = sorted({int(c["n"]) for c in (compiled.get("citations") or [])
                        if c.get("contested")} - asked_numbers(asked))
    if contested:
        n = contested[0]
        return (f"The field holds more than one value for [{n}]. Say which the state supports, "
                f"citing it, or say the state does not decide it with [∅].")
    return ""


def asked_numbers(asked: set) -> set:
    out = set()
    for pair in asked:
        out.update(pair)
    return out


#: THE ARROW FORM, as a prompt block. FLAG 1 ruled this CODOMAIN SYNTAX — the same razor
#: category as "[n] per sentence" — so it is type information about the output, not editorial,
#: and it belongs in the prompt as FORM. Stated as tersely as the legend allows: one sentence,
#: the shape, the closed kind list. The prompt grows because it grew LEGALLY.
ARROW_FORM = ("When two numbered objects are related and no ARROW line already says so, write "
              "the relation on its own as [i] -kind-> [j], kind one of same_claim, refines, "
              "instance_of.")


def blocks(base=None) -> tuple:
    """The dialogue's prompt: the render grammar plus the arrow form, in the same tagging."""
    from .grammar import BLOCKS

    return tuple(base or BLOCKS) + (("FORM", ARROW_FORM),)


def render_prompt() -> str:
    from .grammar import render_prompt as _r

    return _r(blocks())


def slot_of(compiled: dict) -> dict:
    """citation number -> corpus slot. The whole resolution: an array lookup, nothing else."""
    return {int(c["n"]): c["slot"] for c in (compiled.get("citations") or [])
            if c.get("n") is not None and c.get("slot")}


def _put(state: dict, ask: str) -> str:
    """The user body for one turn: the settled field, then the thing being asked."""
    return str(state.get("compiled", "")) + "\n\nQUESTION:\n" + str(ask)


@dataclass
class Dialogue:
    """One conversation. The last turn's prose IS the answer.

    THE COLLAPSE. There is no separate render call, and no separate render TURN when the graph
    has nothing to ask: a question with no interrogation costs ONE call, and that call's prose
    is the answer — strictly fewer calls than the two-port split it replaces. When
    interrogations do run, a final turn re-puts the operator's question to the settled field,
    because an interrogation turn answers the interrogation and the operator asked something
    else.
    """

    question: str
    turns: list = field(default_factory=list)
    budget: int = TURN_BUDGET
    stopped: str = ""

    @property
    def answer(self) -> str:
        return self.turns[-1].prose if self.turns else ""

    @property
    def resolved(self) -> list:
        return [p for t in self.turns for p in t.proposals if p.ok]

    @property
    def claims(self) -> set:
        """DISTINCT relations across the whole dialogue. The unit is the claim, not the
        utterance — a medium restating one arrow in five turns contributed one claim."""
        return {(min(p.src, p.dst), max(p.src, p.dst), p.kind) for p in self.resolved}

    def as_record(self) -> dict:
        return {
            "question": self.question,
            "turns": [t.as_record() for t in self.turns],
            "turn_count": len(self.turns),
            "budget": self.budget,
            "stopped": self.stopped,
            # RECORDS AND CLAIMS, BOTH NAMED, because every count must say which it counts.
            "records": sum(len(t.proposals) for t in self.turns),
            "resolved_records": len(self.resolved),
            "distinct_claims": len(self.claims),
            "answer": self.answer,
        }


def converse(question: str, compiled: dict, transport, settle=None,
             budget: int = TURN_BUDGET, system: str = "") -> Dialogue:
    """Run the dialogue. Turns 1..n-1 measure; the last turn answers.

    `settle` is INJECTED rather than imported, so this module never reaches the corpus: it
    takes the resolved proposals so far and returns a freshly compiled field. Passing None runs
    the degenerate single-turn case, which is also the common one.
    """
    d = Dialogue(question=question, budget=max(1, int(budget)))
    sys_prompt = system or render_prompt()
    asked: set = set()
    ask = question
    state = compiled

    for n in range(1, d.budget + 1):
        raw, _usage = transport(sys_prompt, _put(state, ask))
        prose = (raw or "").strip()
        proposals = arrows_from(prose, set(slot_of(state)), turn=n)
        turn = Turn(n=n, ask=ask, prose=prose, proposals=proposals)
        d.turns.append(turn)

        if [p for p in proposals if p.ok] and settle is not None:
            fresh = settle(list(d.resolved))
            if isinstance(fresh, dict) and fresh:
                turn.moved = int(((fresh.get("relaxation") or {}).get("moved")) or 0)
                state = fresh

        if n == d.budget:
            d.stopped = "budget"
            break
        q = interrogate(state, asked)
        if not q:
            d.stopped = "the graph had nothing left to ask"
            break
        pair = implied_unaddressed(state, asked)
        if pair:
            asked.add(pair)
        turn.interrogation = q
        ask = q

    # THE FINAL TURN IS THE ANSWER. If the dialogue ended on an interrogation the medium's last
    # words answer the INTERROGATION, and the operator asked something else. One more turn puts
    # the question to the field the interrogations settled. A dialogue that never interrogated
    # is already answered by turn 1 and makes no extra call.
    if d.turns and d.turns[-1].ask != question:
        raw, _usage = transport(sys_prompt, _put(state, question))
        prose = (raw or "").strip()
        n = len(d.turns) + 1
        d.turns.append(Turn(n=n, ask=question, prose=prose,
                            proposals=arrows_from(prose, set(slot_of(state)), turn=n)))
    return d
