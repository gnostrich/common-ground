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
KINDS = ("WIRE", "GRAMMAR", "STATE")

#: Why the field is silent. Closed, and every name resolves against something the relaxation
#: record actually reports — see `engine.grounded.warrants_held`.
WARRANTS = ("gap", "cap", "cut", "attach", "anchor", "indiscriminate", "void", "rel")

BLOCKS: tuple[tuple[str, str], ...] = (
    ("WIRE",
     "The input is a settled field. Each line is one object: its chart in brackets, its "
     "claim, and a number in square brackets. Lines marked ARROW state a measured relation "
     "between two numbered objects. Lines marked ABSENT state something the field reports it "
     "does not have. A line marked (!) is CONTESTED: the field holds more than one value for "
     "it."),
    ("GRAMMAR",
     "Every sentence ends with either bracketed numbers naming the objects it rests on — [4] "
     "or [2][7] — or an absence marker. A sentence resting on several objects names all of "
     "them."),
    ("GRAMMAR",
     "Absence markers: [∅] for absent from the whole input, [∅:3,7] for absent from "
     "those lines, and [∅gap] [∅cap] [∅cut] [∅attach] [∅anchor] "
     "[∅indiscriminate] [∅void] to name why the field is silent. Use only a marker "
     "the input states."),
    ("GRAMMAR",
     "A sentence asserting a relation between objects must cite the ARROW line that states "
     "that relation. Objects appearing together in the input are not thereby related. Where "
     "no arrow states it, the sentence carries [∅rel]."),
    ("GRAMMAR",
     "A sentence citing a contested object carries [!] as well as its numbers."),
    ("GRAMMAR",
     "Numbers resolve against the lines shown. A number not shown, a marker the input does "
     "not state, and a sentence with neither are each flagged."),
)


def render_prompt(blocks: tuple[tuple[str, str], ...] = BLOCKS) -> str:
    """The system prompt. Nothing but the blocks, in order."""
    return "\n\n".join(text for _, text in blocks)


def illegal_blocks(blocks: tuple[tuple[str, str], ...] = BLOCKS) -> list[str]:
    """Blocks whose kind is not one of the three. A style instruction cannot be tagged."""
    return [f"{kind}: {text[:60]}" for kind, text in blocks if kind not in KINDS]
