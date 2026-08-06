"""THE META-CONTROL: a referee may not decide anything by resemblance.

THREE TIMES, in three different modules, a guard was built out of word bags:

  * the acceptance guard counted journal RECORDS instead of distinct pairs, so it measured
    how repetitive a model was and reported that as quality;
  * the faithfulness checker took `words(sentence) - words(prompt)` and called the remainder
    an unfaithful proposition;
  * `engine.conversation` intersected keyword sets to decide whether a later turn RESPONDS to
    an earlier claim, which set every verdict in the conversation ledger.

Each was caught by hand, after it shipped, by the operator. The pattern is not a series of
accidents: a referee is exactly where similarity is most tempting, because the thing being
judged is text and text has words in it. `seed/OBJECT-AMENDED.md` records term overlap in the
answer path as DELETED, and the constitution does not exempt the referee — so this module
sweeps for the shape everywhere it could return, and `tests/test_referee_sweep.py` runs it.

WHAT COUNTS AS THE FORBIDDEN SHAPE
  TOKENIZE   a regex over a letter/word character class, or a bare `.split()`, applied to
             text and collected into a set — the manufacture of a word bag.
  FOLD       `.lower()` / `.casefold()` whose result flows into a set or a membership test on
             a set — case folding exists to make bags comparable.
  BAG-OP     a set operator (`&`, `-`, `^`, `|`) between two values whose names say they hold
             tokens, words, keywords or a vocabulary — the comparison itself.

WHAT IS NOT THE FORBIDDEN SHAPE, and why the difference is real rather than convenient:
  * matching a DECLARED, ENUMERATED grammar — a fixed cue list, a chart tag, a citation
    integer, an arrow form. A closed vocabulary the codebase itself defines is structure; an
    open-ended bag built from whatever words happened to appear is resemblance.
  * operating on the project's OWN pinned strings (`seed/SURFACE.json`'s forbidden phrasings)
    rather than on model output. That checks what WE wrote, not what a model produced.
  * extraction, normalisation and lexicon modules, whose declared job is to turn text into
    addresses. They are not referees; they are the base the referees judge over.

THE ALLOWLIST CARRIES REASONS, NOT NAMES. An exemption without a stated reason is how a
sweep dies: the next violation gets added to the list to make the suite green. Every entry
below states why the shape there is a declared grammar and not a resemblance, and the control
asserts that no entry has an empty reason.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent

#: Modules whose job is to GRADE, GUARD, or MEASURE — anything whose output licenses,
#: refuses, scores or flags. Listed explicitly: a registry that must be edited to add a
#: referee is a registry that notices when one is added.
REFEREES = {
    "grounded.py": "licenses answer-first by checking the answer against the trace",
    "battery.py": "the standing battery — grades every deployed build",
    "reading.py": "checks the human surface against the measurement it renders",
    "faithfulness.py": "the theory-object -> control audit",
    "faithfulness_report.py": "renders that audit",
    "static_checks.py": "gate 10 and the mechanism-claim checks",
    "quarantine.py": "decides which stock does not act",
    "staleness.py": "decides whether a build's material is fresh",
    "three_moves.py": "decides whether a change is one of the three moves",
    "three_moves_sweep.py": "sweeps for changes that are not",
    "structure_audit.py": "audits declared structure",
    "structure_sweep.py": "sweeps it",
    "gate6_sweep.py": "gate 6",
    "gate7_sweep.py": "gate 7",
    "chart_plugin_audit.py": "audits chart plugins",
    "audit.py": "the general audit",
    "meter.py": "measures the floor",
    "compose.py": "decides when composition contradicts a recorded answer",
    "conversation.py": "decides which turn answers which claim, and with what verdict",
    "probes.py": "the null battery",
    "probe_report.py": "reports it",
    "atlas.py": "reports what the journal contains",
    "claims_sweep.py": "sweeps claims",
    "seed_lock.py": "decides whether the seed is locked",
    "structure_trace.py": "decides when a question is about shape rather than displacement",
    "export_sheet.py": "renders the portable context sheet",
    "medium.py": "decides which glosses survive the behavioural gate",
    "adjudicate.py": "decides which same_claim declarations are containment",
    # NOT a referee, and registered so the exemption is visible rather than implicit: a
    # nominator returns ADDRESSES. It decides no relation, proposes no arrow, ranks no claim
    # and carries no weight — it changes which neighbourhood a question is sampled from, and
    # `tests/test_nominate.py` asserts its output contains nothing but slot ids.
    "nominate.py": "nominates a region's seed set; decides nothing",
    # It GRADES — it decides whether a constant's provenance is acceptable — so it is swept
    # like every other grader. It reads a declared enumeration (derived/swept/confessed) and
    # a JSON map, never text, which is why the sweep passes it.
    "constants_sweep.py": "grades whether a constant claims a legal provenance",
    # It reads the act off a DECLARED TOKEN in a closed vocabulary, resolve-or-void, and
    # never off prose — a reading inferred from the shape of a sentence would be a fluency
    # judgement steering warrant, which is the one thing that must never happen.
    "posture.py": "reads the utterance's declared act token; infers nothing from prose",
    "control_sweep.py": "decides which controls check text where they claim behaviour",
    "inbound.py": "GROUPS the compiled sheet — groups must be fibers, never clusters. A "
                  "grouping that produced the same groups by similarity would be a different "
                  "mechanism wearing this one's output.",
}

#: Exemptions. Each carries the reason it is a declared grammar rather than a resemblance.
ALLOWED = {
    ("reading.py", "check_wording"):
        "matches seed/SURFACE.json's pinned forbidden phrasings against the surface copy WE "
        "wrote. It grades our own strings, not model output, and the vocabulary is a closed "
        "list in a versioned file.",
    ("conversation.py", "_verdict_of"):
        "matches a DECLARED, ENUMERATED cue list (_REJECT / _SHARPEN) — a closed grammar of "
        "verdict markers defined in this file. Finding a fixed marker is not measuring "
        "resemblance; an open bag built from the turn's own words would be.",
    ("static_checks.py", "*"):
        "gate 10 matches PINNED FORBIDDEN PHRASES against docstrings and comments in THIS "
        "repository. It grades what we wrote about our own mechanisms.",
    ("conversation.py", "_sentences"):
        "counts words to decide whether a fragment is long enough to be a claim. That is "
        "segmentation — a CARDINALITY test that produces no set and compares nothing to "
        "anything. It decides where a claim starts, never which claim answers which.",
    ("audit.py", "_extract_not_claimed"):
        "folds a MARKDOWN HEADING in this repository's own documents to find a declared "
        "section marker ('do not claim'). A closed marker in text we wrote, not model output.",
    ("atlas.py", "_clean_nu"):
        "collapses whitespace in a nu-string on the way to a DISPLAY string — "
        "`' '.join(x.split())`. It produces text, not a set, compares nothing to anything, "
        "and nothing downstream of it gates. Cardinality-free normalisation for reading.",
    ("seed_lock.py", "unresolved_decisions"):
        "folds a JSON `status` field from seed/DECISIONS.json to compare it against a "
        "declared enum of statuses. Closed vocabulary, our own seed file.",
}

_LETTER_CLASSES = ("[a-z", "[A-Z", "[^\\W", "\\w+", "[a-zA-Z")
_BAG_NAMES = ("keyword", "keys", "token", "word", "vocab", "ground", "terms",
              "lexemes", "bag", "phrases", "surfaces")


@dataclass(frozen=True)
class Finding:
    module: str
    line: int
    func: str
    shape: str
    detail: str

    def render(self) -> str:
        return (f"{self.module}:{self.line} in {self.func}() — {self.shape}: {self.detail}")


def _enclosing(tree: ast.AST) -> dict[int, str]:
    """line -> enclosing function name, so a finding can be exempted per function."""
    out: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if hasattr(child, "lineno"):
                    out.setdefault(child.lineno, node.name)
    return out


def _is_numeric(node: ast.AST) -> bool:
    """A number or a `len()` — `len(words) - 1` is arithmetic, not a bag comparison."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return True
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "len")


def _is_bag_name(node: ast.AST) -> bool:
    name = ""
    if isinstance(node, ast.Name):
        name = node.id
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        name = node.func.attr
    return any(b in name.lower() for b in _BAG_NAMES)


def sweep_module(path: Path) -> list[Finding]:
    """Every forbidden shape in one referee, with the function it sits in."""
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    where = _enclosing(tree)
    mod = path.name
    found: list[Finding] = []

    def emit(node, shape, detail):
        func = where.get(getattr(node, "lineno", 0), "<module>")
        if (mod, func) in ALLOWED or (mod, "*") in ALLOWED:
            return
        found.append(Finding(mod, node.lineno, func, shape, detail))

    for node in ast.walk(tree):
        # TOKENIZE — a letter-class regex, or a bare .split(), producing tokens.
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            if attr in ("findall", "finditer") and node.args:
                pat = node.args[0]
                lit = pat.value if isinstance(pat, ast.Constant) else ""
                if isinstance(lit, str) and any(c in lit for c in _LETTER_CLASSES):
                    emit(node, "TOKENIZE", f"{attr}({lit!r}) manufactures a word bag")
            if attr == "split" and not node.args:
                emit(node, "TOKENIZE", "bare .split() over text")
            if attr in ("lower", "casefold"):
                emit(node, "FOLD", f".{attr}() — case folding exists to compare bags")
        # BAG-OP — a set operator where EITHER side is a token collection. Requiring both
        # sides to be token-named missed the shape that actually shipped:
        # `p_keys & _keywords(r.claim)` — the left name did not match the list, so a real
        # violation passed a sweep written to catch it. One side is enough; a set operator
        # against a word bag is a word-bag comparison whatever the other operand is called.
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.BitAnd, ast.Sub,
                                                               ast.BitXor, ast.BitOr)):
            sides = (node.left, node.right)
            if any(_is_bag_name(x) for x in sides) and not any(_is_numeric(x) for x in sides):
                emit(node, "BAG-OP",
                     f"{type(node.op).__name__} against a token collection")
    return found


def sweep(root: Path | None = None) -> list[Finding]:
    """Every referee in the registry. A registered module that is missing is itself reported."""
    base = (root or ENGINE)
    out: list[Finding] = []
    for name in sorted(REFEREES):
        p = base / name
        if not p.exists():
            out.append(Finding(name, 0, "<module>", "MISSING",
                               "registered as a referee but not present"))
            continue
        out.extend(sweep_module(p))
    return out


def render(findings: list[Finding]) -> str:
    if not findings:
        return "referee sweep: clean — no referee decides anything by resemblance."
    return "referee sweep RED:\n" + "\n".join("  " + f.render() for f in findings)


if __name__ == "__main__":                                     # pragma: no cover
    print(render(sweep()))
