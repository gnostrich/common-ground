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
#: A LABEL, not an integer: `[e1] -refines-> [l45]`. The bracket is punctuation; the
#: label is the chart letter and the index, and it is the same label space the region
#: emitted, the checker verifies and the answer cites. Brackets optional so the one
#: parser serves the coordinates wire too.
ARROW = re.compile(r"\[?([a-z]?\d+)\]?\s*-(\w+)->\s*\[?([a-z]?\d+)\]?")

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

    src: str
    dst: str
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


def said(prose: str) -> str:
    """The turn's WORDS, with its arrow lines removed. One reply, two roles.

    A turn answers in cited prose AND writes its arrows in that same reply, because they are
    one act — that is what the collapse means. But an arrow line is the extraction channel: it
    has already been harvested into proposals by the time anyone reads this, and leaving it in
    the answer shows the operator a wiring diagram instead of a sentence. On one served run
    turn 1 came back as eighty-four arrow lines and nothing else, and every one of them was
    then parsed as an uncited sentence.

    Removing them is PRESENTATION, not a second turn and not a second parse: the same lines the
    extractor consumed, dropped from the display. If nothing remains, the answer is genuinely
    empty and must read as empty rather than as a diagram — a turn that only related and never
    answered is a real state, and the operator should see that it happened.
    """
    kept = [ln for ln in (prose or "").splitlines() if not _ARROW_ONLY.match(ln.strip())]
    return "\n".join(kept).strip()


#: A LINE THAT IS ONLY AN ARROW. Anchored at both ends, so a sentence that happens to contain
#: an arrow keeps its words — the medium may legitimately write "this refines that, [e1]
#: -refines-> [e7]" and the sentence is not the arrow.
_ARROW_ONLY = re.compile(r"^\[?[a-z]?\d+\]?\s*-\w+->\s*\[?[a-z]?\d+\]?[.;]?$")



#: A CITATION IN A TURN'S PROSE. Same label grammar the checker reads, so "did this turn cite
#: anything" and "did the referee see a citation" cannot disagree.
_CITED = re.compile(r"\[([a-z]?\d+)\]")

#: A LEGAL ABSENCE scoped to the question — answering [b0] by saying the field does not hold it.
_ABSENT_ANY = re.compile(r"\[∅[^\]]*\]")


def answers(turn, attached: set) -> bool:
    """Does this turn ANSWER the boundary condition? Decided structurally, never by reading.

    A turn answers when at least one of its sentences cites something [b0] attached to, or
    carries a legal absence — the field saying it does not hold what was asked is an answer.
    THE BAR IS EXISTENCE, NOT ADEQUACY: whether the answer is any good is the faithfulness
    gate's job and has been all along. A quality judgement here would be the medium grading
    itself, one level up from the interrogator.
    """
    # THE ARROW CHANNEL IS NOT THE ANSWER CHANNEL, and this read the raw reply — so a turn
    # that emitted nothing but `[b0] -bears_on-> [e3]` lines counted as answering, because the
    # arrow line contains `[e3]`. Measured on the frozen fixture: turn 1 came back as seven
    # arrows and no words, the residual saw a citation inside an arrow, declined to fire, and
    # the page displayed an EMPTY answer. `said()` is the same strip the display uses; asking
    # "did it answer" of the words it did not say is asking about a different reply.
    prose = said(getattr(turn, "prose", "") or "")
    if _ABSENT_ANY.search(prose):
        return True
    return bool(set(_CITED.findall(prose)) & set(attached or ()))


def attached_labels(compiled: dict) -> set:
    """What [b0] reached. The set an answering sentence has to touch."""
    # READ OFF THE CITATIONS, which is where the labels are. This used to read the attachment
    # records — which carry kind, tier, chart and nu, and NO label, because the label is
    # assigned downstream by the labeller. So the loop found nothing every single time and the
    # function fell through to its degradation clause on every request: "what [b0] reached"
    # silently meant "every citable object", the residual's condition became "cited anything
    # at all", and after the seating fix that was fifty-nine labels wide. A fallback that runs
    # always is not a fallback; it is the implementation.
    out = {str(c["n"]) for c in ((compiled or {}).get("citations") or ())
           if c.get("n") and c.get("kind") in ("attached", "bears_on")}
    if not out:
        # No attachment record to read: every citable label counts, so the check degrades to
        # "cited anything at all" rather than to "answers nothing" — a residual that fires
        # because a record was missing would re-ask forever.
        out = set(slot_of(compiled))
    return out


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
        i, kind, j = m.group(1), m.group(2), m.group(3)
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
        pair = (min(i, j), max(i, j), kind)   # labels sort as strings; order-free identity
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
        pair = tuple(sorted(str(x) for x in (c.get("joins") or ())))
        if len(pair) == 2:
            joins[str(c["n"])] = pair
            joined.add(pair)
    return joins, joined


#: THE OUTCOMES A RESIDUAL CAN HAVE. Closed, because an outcome resolved against a closed
#: vocabulary is a finding and an outcome inferred from prose is a reading.
RESOLVED, UNDECIDED, UNANSWERED = "resolved", "state-undecided", "unanswered"


def next_residual(compiled: dict, asked: set) -> tuple:
    """The next OPEN residual: its identity, and the question that puts it.

    THE IDENTITY IS THE UNIT, not the question string. An implied pair is `(a, b)`; a contested
    object is `(n,)`. One-tuples and two-tuples cannot collide, and `asked_numbers` unions both
    shapes, so the two residual kinds share one discharged-set without a discriminator field.
    """
    pair = implied_unaddressed(compiled, asked)
    if pair:
        return pair, (f"Composition implies a relation between [{pair[0]}] and [{pair[1]}] that "
                      f"nothing has measured. State it as an arrow, or say the field does not "
                      f"have it with [{pair[0]}] -bears_on-> [{pair[1]}] omitted entirely.")
    contested = sorted({str(c["n"]) for c in (compiled.get("citations") or [])
                        if c.get("contested")} - asked_numbers(asked))
    if contested:
        n = contested[0]
        return (n,), (f"The field holds more than one value for [{n}]. Say which the state "
                      f"supports, citing it, or say the state does not decide it with [∅].")
    return (), ""


def discharge(residual: tuple, turn) -> str:
    """What putting this residual PRODUCED. Structural; never a judgement of quality.

    THE RULE: a residual is discharged when its question receives a LEGAL ANSWER — resolution,
    or the `[∅]` terminal saying the state does not decide it. `state-undecided` is a FINDING,
    not an open item: "contested, and the state does not decide it" is exactly as much of an
    answer as a value would be, and the one thing it is not is a reason to ask again.

    `unanswered` is also recorded, and is also not a reason to ask again. Asking a second time
    cannot make the reply different — that is the records-versus-pairs law at the interrogation
    level, the same law that says a medium restating one arrow in five turns contributed one
    claim. The budget exists for OPEN questions, and a question already put is not one.
    """
    words = said(getattr(turn, "prose", "") or "")
    if len(residual) == 2:
        want = tuple(sorted(residual))
        if any(tuple(sorted((p.src, p.dst))) == want for p in turn.proposals if p.ok):
            return RESOLVED
    elif len(residual) == 1 and residual[0] in set(_CITED.findall(words)):
        return RESOLVED
    return UNDECIDED if _ABSENT_ANY.search(words) else UNANSWERED


def interrogate(compiled: dict, asked: set) -> str:
    """The next turn's question, generated MECHANICALLY FROM STRUCTURE.

    Never "that answer seemed thin, ask again". A turn selected because a reply read as
    unsatisfying is a fluency judgement steering the corpus — the medium grading itself — and
    it is the one thing this function must be incapable of. It reads the graph and never the
    prose, which is why `prose` is not a parameter.
    """
    return next_residual(compiled, asked)[1]


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
    return {str(c["n"]): c["slot"] for c in (compiled.get("citations") or [])
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
    #: Every residual PUT to the medium, with what putting it produced. A residual leaves the
    #: open set the moment it is asked and its outcome is recorded here — `state-undecided` is
    #: a finding, not an open item.
    residuals: list = field(default_factory=list)

    @property
    def answer(self) -> str:
        """The last turn that answered THE OPERATOR'S QUESTION — not simply the last turn.

        "The final turn is the answer" holds when the dialogue ends because the graph went
        quiet: the last thing said was said to the operator. It does NOT hold when the budget
        runs out mid-interrogation, and the first run where the interrogator actually fired
        proved it — four turns, budget exhausted, and what displayed was turn 4 replying to
        "the field holds more than one value for [e18], which does the state support?". A
        correct answer to a question the operator never asked.

        An interrogation turn is a measurement, not a reply. The answer is the most recent
        thing the medium said TO THE OPERATOR, which later interrogations improve the field
        for but do not replace.
        """
        for t in reversed(self.turns):
            if t.ask == self.question:
                return said(t.prose)
        return said(self.turns[-1].prose) if self.turns else ""

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
            "residuals": list(self.residuals),
            "answer": self.answer,
        }


def converse(question: str, compiled: dict, transport, settle=None,
             budget: int = TURN_BUDGET, system: str = "", first_turn=None) -> Dialogue:
    """Run the dialogue. Turns 1..n-1 measure; the last turn answers.

    `settle` is INJECTED rather than imported, so this module never reaches the corpus: it
    takes the resolved proposals so far and returns a freshly compiled field. Passing None runs
    the degenerate single-turn case, which is also the common one.
    """
    d = Dialogue(question=question, budget=max(1, int(budget)))
    sys_prompt = system or render_prompt()
    asked: set = set()
    state = compiled

    # A TURN IS LEGITIMATE ONLY AS A RESPONSE TO AN INTERROGATION.
    #
    # This loop used to run one more turn unconditionally after the seeded first turn, and that
    # turn was the render port surviving as a render TURN. On the served fixture it did real
    # damage: turn 1 answered from ten cited claims, the interrogator honestly found nothing
    # left to ask, and a turn 2 ran anyway — re-fed the original question against a degraded
    # summary of turn 1's own work — and its two sentences from two claims are what displayed.
    # The machine answered well, re-answered badly from a bad summary of itself, and showed the
    # bad one. So: no question, no turn. When the interrogator has nothing, the dialogue ENDS
    # and the previous turn's answer stands — it already passed the same grammar and it is
    # gated by the same checker.
    if first_turn is not None:
        d.turns.append(first_turn)
    else:
        raw, _usage = transport(sys_prompt, _put(state, question))
        prose = (raw or "").strip()
        d.turns.append(Turn(n=1, ask=question, prose=prose,
                            proposals=arrows_from(prose, set(slot_of(state)), turn=1)))

    while True:
        turn = d.turns[-1]
        good = [p for p in turn.proposals if p.ok]
        if good and settle is not None:
            fresh = settle(list(d.resolved))
            if isinstance(fresh, dict) and fresh:
                turn.moved = int(((fresh.get("relaxation") or {}).get("moved")) or 0)
                state = fresh
        if len(d.turns) >= d.budget:
            d.stopped = "budget"
            return _close(d, state, transport, sys_prompt, question)
        residual, q = next_residual(state, asked)
        if not q:
            d.stopped = "the graph had nothing left to ask"
            return _close(d, state, transport, sys_prompt, question)
        # PUT, THEREFORE ASKED. The contested branch never recorded anything here, so its
        # residual stayed open forever: on a served run turns 2, 3 and 4 carried the SAME
        # question and the medium returned the SAME reply — "[∅] the state does not decide"
        # — three times, byte for byte, spending three quarters of the budget on a question
        # that had been answered the first time and answered in the exact terms the question
        # itself offered. A discharged residual leaves the set; so does an unanswered one,
        # with its outcome recorded, because asking again cannot make the reply different.
        asked.add(residual)
        turn.interrogation = q
        n = len(d.turns) + 1
        raw, _usage = transport(sys_prompt, _put(state, q))
        prose = (raw or "").strip()
        answer_turn = Turn(n=n, ask=q, prose=prose,
                           proposals=arrows_from(prose, set(slot_of(state)), turn=n))
        d.turns.append(answer_turn)
        d.residuals.append({"residual": list(residual), "question": q, "turn": n,
                            "outcome": discharge(residual, answer_turn)})


#: TURN 1's PROMPT. The region wire's legend, plus the citation grammar, plus the arrow form.
#:
#: THE DAEMON'S PROMPT FORBIDS PROSE — "Nothing else: no prose, no JSON, no claim text" — which
#: is correct for an unattended coordinate walk and is exactly what made the collapse
#: impossible until now. Turn 1 of a DIALOGUE is a conversational turn, so it gets a
#: conversational prompt: relate the objects AND say what the field establishes, in one reply,
#: in one grammar. The daemon's prompt is untouched and remains the default at the call site.
TURN_ONE_FORM = (
    "Objects are labelled with a chart letter and a number, like e1 or l45. Cite a label by "
    "writing it in brackets — [e1]. Relate two objects by writing [i] -kind-> [j] on its own, "
    "kind one of same_claim, refines, instance_of; an arrow to the boundary condition [b0] "
    "takes the kind bears_on. Relate what is genuinely related and nothing else. Then answer "
    "the question from these objects, ending each sentence with the labels it rests on, or "
    "with [∅] for something these objects do not contain. Two or more labels on one sentence "
    "assert that those objects are related: only write that when you have also written the "
    "arrow saying so, otherwise give each object its own sentence, or write [∅rel].")


def turn_one_prompt() -> str:
    """The region's own legend, then the dialogue's grammar. One prompt, both jobs.

    COMPOSED FROM THE SHARED LEGEND, never sliced out of the daemon's prompt. The first version
    did `REGION_SYSTEM.split("Emit only lines")`, which the no-similarity sweep caught — rightly,
    since a referee module that starts splitting strings is one edit from matching them, and a
    slice keyed on a phrase breaks silently the day that phrase is reworded.
    """
    from .region import REGION_LEGEND

    return REGION_LEGEND + "\n\n" + TURN_ONE_FORM


def _close(d, state: dict, transport, sys_prompt: str, question: str):
    """THE UNANSWERED QUESTION IS A RESIDUAL, and the dialogue may not close on one.

    Same class as a contested claim or an unnamed cluster: a piece of structure the field can
    point at, unresolved. When no turn's cited prose addresses [b0], the interrogator's next
    question IS the operator's question, re-asked against the live settled state.

    THIS IS NOT THE RENDER FOSSIL RETURNING, and the difference is exactly the one that made
    the fossil harmful. The fossil ran ALWAYS — answered or not, one more call every time, from
    a degraded compile. This fires ONLY on a measured absence and NEVER when an answering turn
    already exists. Conditional-on-debt, not unconditional-stage, and both directions are
    controlled.
    """
    attached = attached_labels(state)
    # ONLY TURNS THAT WERE ASKED THE OPERATOR'S QUESTION COUNT, because only those are turns
    # `Dialogue.answer` will ever display. This scanned every turn, and on the served build it
    # produced the exact failure the residual exists to prevent: turn 1 came back as arrows and
    # no words, three interrogation turns answered their interrogations citing attached labels,
    # `answers()` saw one of those and declined to fire — and the page showed an EMPTY answer.
    # The residual's condition and the answer's condition must be the same condition; two
    # predicates for "did this get answered" is the same defect shape as two mechanisms for
    # one job.
    if any(t.ask == question and answers(t, attached) for t in d.turns):
        return d
    n = len(d.turns) + 1
    raw, _usage = transport(sys_prompt, _put(state, question))
    prose = (raw or "").strip()
    d.turns.append(Turn(n=n, ask=question, prose=prose,
                        proposals=arrows_from(prose, set(slot_of(state)), turn=n)))
    d.stopped = (d.stopped or "") + "; [b0] had no answering turn, so it was re-asked"
    return d
