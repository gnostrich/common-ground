"""THE OUTPUT GRAMMAR: what the renderer may write, stated once, every rule checker-backed.

WHY THIS FILE EXISTS. The renderer prompt had grown to 4,889 characters, and most of it was
editorial: how to open, whose voice to prefer, what not to apologise for, an exhortation to
say what is not there, and the citation rule stated three times in three registers. None of
that is a rule — a rule is something a checker enforces. Prose telling a model to prefer a
voice is a hope, it drifts with every edit, and it accreted precisely because each defect this
week got answered with another sentence instead of another control.

So the prompt is now BLOCKS, each tagged with what it is, and only three tags are legal:

  WIRE     what the input format is — the shape of the state the renderer receives.
  GRAMMAR  a rule the output must satisfy, EVERY ONE OF WHICH `engine/grounded.py` checks.
  STATE    the settled state itself, supplied per request.

A style instruction has no legal tag, so it cannot be added without failing a control. That is
the whole design: the prompt is not short because brevity is a virtue, it is short because
everything that was in it and is not here was unenforceable.

THE RULES, and where each is checked:
  CITATION   every sentence ends in [n] or an absence marker  -> Uncited / Unresolved
  ABSENCE    [0], [0:n,m], [0<warrant>] from a closed list    -> Vacuous / Unwarranted
  WELD       a sentence citing claims from different groups may not assert a relation
             between them without citing the arrow, or marking [0rel]  -> Welded
  CONTEST    a sentence citing a contested claim carries [!]  -> Uncontested
(The absence marker is U+2205; this docstring writes it as 0 to stay ASCII in source prose.)

THE WELD RULE came from a measured failure. An answer wrote "certified positivity relates to
mode spectrum measurement [21]" — two co-present claims fused by a conjunction, each half
correctly cited, and the RELATION between them never declared anywhere. The citation grammar
could not see it: it checks that every claim is SHOWN, never that an asserted relation between
two of them exists. That is the same failure class as the whole fiber repair — asserting
structure the declarations do not license — arriving one level up, in prose.
"""

from __future__ import annotations

#: The only legal kinds of prompt block. A style instruction has no tag here, which is what
#: makes "no editorial content" checkable rather than aspirational.
KINDS = ("WIRE", "TASK", "FORM")

#: Why the field is silent. Closed, and every name resolves against something the relaxation
#: record actually reports — see `engine.grounded.warrants_held`.
WARRANTS = ("gap", "cap", "cut", "attach", "anchor", "indiscriminate", "void", "rel")

#: THE PROMPT. Three blocks and nothing else.
#:
#: THE GRAMMAR SPEC IS NOT HERE, and that is the fix rather than an omission. The previous
#: version stated six rules — every sentence ends with citations, absence markers take these
#: forms, relations need arrows, contested objects carry [!] — and the model RECITED THEM. It
#: answered by describing the format it had been given, because a page of rules is the most
#: salient text in the context and a rule is a thing a model can talk about.
#:
#: A spec that is not in the prompt cannot be recited. The CHECKER is what enforces the
#: grammar — `engine.grounded.check_answer` flags uncited, unresolved, vacuous, unwarranted,
#: welded and uncontested sentences — and enforcement was always where the rules lived. What
#: the model needs is the minimum to COMPLY: how to write a citation, and how to write the
#: absence marker it cannot otherwise express. That is FORM, and it is one block.
#:
#: THE TASK BLOCK IS THE STRIP'S MISSING MINIMUM. Removing the editorial codex also removed
#: the only sentence that said what to DO, leaving state and rules and no verb — so the model
#: did the only thing state-plus-rules affords: it described them. "Answer the question from
#: this state" is not a style instruction; it is the task, and a prompt without one is not
#: minimal, it is incomplete.
BLOCKS: tuple[tuple[str, str], ...] = (
    ("WIRE",
     "Below is a settled field and a question. Each line is one object: its chart in "
     "brackets, its claim, and a number in square brackets. ARROW lines state a measured "
     "relation between two numbered objects. ABSENT lines state what the field reports it "
     "does not have. (!) marks an object the field holds more than one value for."),
    ("TASK",
     "Answer the question from this state."),
    ("FORM",
     "End each sentence with the bracketed numbers it rests on — [4] or [2][7]. For "
     "something the field does NOT contain, write [∅] instead."),
    # THE WELD RULE, STATED. It was checked and never stated, and that is the one arrangement
    # a rule may not have: a sentence co-citing two objects was convicted for asserting a
    # relation the field lacks, while nothing in the prompt said co-citation asserted anything.
    # The frozen fixture measured four such convictions in one answer — every one of them a
    # true statement, listed rather than related, from a medium that had no way to know a list
    # was a claim. A rule the medium cannot comply with is a rule that only ever convicts.
    #
    # WHY THIS IS NOT THE RECITED CODEX RETURNING. The codex was six rules and a page of prose,
    # and the model answered by describing it. This is one clause of CODOMAIN SYNTAX — the
    # same category FLAG 1 ruled ARROW_FORM into: type information about the shape of the
    # output, not a standard to live up to. It says what a sentence may carry, in the same
    # breath as "[4] or [2][7]", and it names the two ways to comply rather than the failure.
    ("FORM",
     "[2][7] on one sentence asserts that [2] and [7] are related, so write it only with the "
     "ARROW line's own number cited alongside them — otherwise give each object its own "
     "sentence, or write [∅rel] for a relation the field does not declare. An object the "
     "state marks (!) is cited as [7][!]."),
    # THE ROSTER SHAPE, NAMED — as a MEASUREMENT, never as a loosening of the referee.
    #
    # A live answer ended with nine near-identical sentences of the form "X [l56] is an
    # instance of A [l39], B [l14], ... R [l59]" — nineteen labels under one verb, then a pure
    # comma list. The weld rule reads that as asserting every pair in it, so nine sentences
    # demanded 1,345 of the 1,376 pairwise joins the whole answer was convicted for: 97.8% of
    # the severity from one serialization habit.
    #
    # THE REFEREE WAS NOT WIDENED, and the reason is on the record. A shape test keyed on
    # list-conjunction grammar is airtight on the sentences observed and breaks on "A [1] and
    # B [2] are related." — where the relational predicate follows the list. Telling that apart
    # from "the file contains A and B" requires knowing whether the verb is distributive or
    # symmetric, which is a hand-tuned verb list wearing a shape test's clothes, and that is
    # the deleted move this project refuses on sight.
    #
    # SO THE MEDIUM IS TOLD INSTEAD. The rule was already compliable — both escapes stated,
    # neither used — and this names the specific shape that fails it. If the habit survives
    # explicit instruction, that is a measured limitation of the medium and the count stays red
    # and true.
    #
    # AND IT DID NOT SURVIVE MEASUREMENT. THERE IS NO ROSTER CLAUSE HERE, and this comment is
    # the record of why — a deletion with no explanation invites the next person to try it
    # again.
    #
    # BISECT, same commit, same corpus, same model, the clause the only variable, three draws
    # per arm: WITH it, attachment collapsed to 0 of 59 and discrimination read 0.0; WITHOUT
    # it, 8 of 59 at 0.136 with ZERO violations. On the served build the same clause drove
    # attachment the other way — 59 of 59 at fraction 1.0, which the discrimination guard calls
    # indiscriminate. Opposite poles, one instability: "split a roster into one sentence per
    # object" reads as MENTION EVERYTHING, and a medium told to mention everything either
    # relates to everything or gives up.
    #
    # ITERATION 2 constrained shape without inviting coverage — "at most two labels per
    # sentence", plus "a claim needs a sentence only if the answer rests on it". Three draws:
    # attachment 2 of 59, and a FIFTY-NINE-THOUSAND-CHARACTER answer over 370 sentences. A
    # third failure mode from a second razor-legal wording.
    #
    # Two wordings, two degeneracies, so the clause is gone and the 13 enumeration-shaped
    # convictions return as the KNOWN, RECORDED, HONEST COST. A working system with understood
    # convictions beats a degenerate system with a lower count. See seed/INVENTORY.md row 530.
    #
    # TEMPLATE BYTES ARE STEERING BYTES. Any future wording here gets a code-grade acceptance:
    # three draws on the frozen fixture, discrimination reported, before it lands.
)


def render_prompt(blocks: tuple[tuple[str, str], ...] = BLOCKS) -> str:
    """The system prompt. Nothing but the blocks, in order."""
    return "\n\n".join(text for _, text in blocks)


def illegal_blocks(blocks: tuple[tuple[str, str], ...] = BLOCKS) -> list[str]:
    """Blocks whose kind is not one of the three. A style instruction cannot be tagged."""
    return [f"{kind}: {text[:60]}" for kind, text in blocks if kind not in KINDS]
