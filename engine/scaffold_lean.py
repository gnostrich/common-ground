"""THE LEAN SCAFFOLD: namespace containment and theorem-uses-definition, parsed from source.

12,466 Lean slots went in FLAT. Every one of them carries its own declaration text — the
keyword, the declared name, the binders and the statement — so the dependency graph was
sitting in the material the whole time and was discarded at ingest. This parses it.

WHAT IS PARSED, and nothing else is:
  DECLARED NAME   the identifier after `theorem` / `lemma` / `def` / `abbrev` / `structure` /
                  `instance` / `class` / `axiom` / `example`. That is Lean's grammar, not a
                  guess about what the line means.
  REFERENCES      the identifiers appearing in the declaration's statement. Each one is
                  resolved against the declared-name index by EXACT match on the name.

RESOLVE-OR-VOID, and the voids are the measurement. A reference resolves to exactly one
declared slot or it is VOID with its reason: `undeclared` (nothing in this corpus declares
that name — typically mathlib, which is not ingested), or `ambiguous` (several slots declare
it and nothing in the source says which). An ambiguous reference is NOT resolved by
proximity, by file, or by picking the first: a guess would be a similarity mechanism wearing a
parser's clothes, and the void count is the honest statement of how much of Lean's declared
structure this corpus actually contains.

THERE IS NO SIMILARITY HERE. An identifier either matches a declared name character for
character or it does not. No edit distance, no case folding, no prefix matching, no embedding.
`engine/referee_sweep` sweeps this module like any other.

SCOPE, stated because it is a real limitation rather than an oversight: resolution is by
plain declared name, corpus-wide. Lean's actual scoping — `open`, `namespace`, aliases,
`export` — is not modelled, so a reference that Lean would resolve through an open namespace
is VOID here rather than wrong. Under-reporting is the failure direction chosen on purpose: a
missing edge is a gap, an invented edge is a fabrication, and this project has already paid
once for the second.
"""

from __future__ import annotations

import re

from .scaffold import DEPENDS_ON, Scaffold, ScaffoldParse

#: Lean's declaration keywords. A closed, declared grammar — not a heuristic about line shape.
DECLARERS = ("theorem", "lemma", "def", "abbrev", "structure", "instance", "class",
             "axiom", "noncomputable def", "protected theorem", "private theorem")

#: A Lean identifier: letters, digits, underscores, primes and dots for qualified names.
#: This is the language's own lexical rule, applied to the language's own source.
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_'!?]*(?:\.[A-Za-z_][A-Za-z0-9_'!?]*)*")

#: Lean keywords and syntax that are not references to declarations. Closed list, from the
#: language, not a stopword list about meaning.
_SYNTAX = frozenset("""
theorem lemma def abbrev structure instance class axiom example
by simp rfl exact intro intros apply refine cases rcases induction
have show from fun let in with at using this
if then else match do return
Type Prop Sort universe variable variables open namespace end section
noncomputable protected private partial mutual where deriving
""".split())


def declared_name(nu: str) -> str:
    """The name this slot declares, or "" if the line declares nothing."""
    body = nu
    if body.startswith("\x01"):
        end = body.find("\x01", 1)
        if end != -1:
            body = body[end + 1:]
    body = body.strip()
    for kw in sorted(DECLARERS, key=len, reverse=True):
        if body.startswith(kw + " "):
            rest = body[len(kw) + 1:].lstrip()
            m = _IDENT.match(rest)
            return m.group(0) if m else ""
    return ""


#: Binder groups. Lean declares its local variables INSIDE the statement — `{PXV : Type*}`,
#: `(a : PXV)`, `[DivInvMonoid PXV]` — so a name bound there is not a reference to a
#: declaration and never could be. Reading them out is parsing the language's own binding
#: form, not guessing which identifiers "look local".
_BINDER = re.compile(r"[\{\(\[⦃]([^:\}\)\]⦄]*?):")


def bound_names(statement: str) -> set:
    """Names this declaration BINDS. They cannot resolve to anything and must not void.

    Counting them as unresolved references was a real defect and the void ledger is what
    exposed it: `PXV` was the single most "referenced but absent" name in the corpus at 4,102
    occurrences, and it is a type variable bound in the very statements that mention it. A
    wishlist topped by an artefact of the parser is a wishlist that reads as a corpus finding
    and is a parser finding.
    """
    out = set()
    for m in _BINDER.finditer(statement):
        for piece in m.group(1).split():
            im = _IDENT.fullmatch(piece)
            if im:
                out.add(piece)
    return out


def _statement(nu: str) -> str:
    """Everything after the declared name — the binders and the statement."""
    body = nu
    if body.startswith("\x01"):
        end = body.find("\x01", 1)
        if end != -1:
            body = body[end + 1:]
    body = body.strip()
    for kw in sorted(DECLARERS, key=len, reverse=True):
        if body.startswith(kw + " "):
            rest = body[len(kw) + 1:].lstrip()
            m = _IDENT.match(rest)
            return rest[m.end():] if m else rest
    return ""


def declaration_index(snapshot) -> tuple[dict, set]:
    """(name -> the one slot declaring it, names declared by MORE THAN ONE slot).

    An ambiguous name is kept out of the resolving index and its slots are recorded, so a
    reference to it voids as `ambiguous` rather than being resolved to whichever came first.
    """
    seen: dict[str, list] = {}
    for sid, rec in (getattr(snapshot, "slots", None) or {}).items():
        if getattr(rec, "chart", "") != "lean":
            continue
        name = declared_name(getattr(rec, "nu", "") or "")
        if name:
            seen.setdefault(name, []).append(sid)
    index = {n: s[0] for n, s in seen.items() if len(s) == 1}
    ambiguous = {n for n, s in seen.items() if len(s) > 1}
    return index, ambiguous


def parse(snapshot, era: str = "") -> ScaffoldParse:
    """Every Lean slot's references, resolved against the declared-name index."""
    index, ambiguous = declaration_index(snapshot)
    out = ScaffoldParse()
    for sid, rec in sorted((getattr(snapshot, "slots", None) or {}).items()):
        if getattr(rec, "chart", "") != "lean":
            continue
        nu = getattr(rec, "nu", "") or ""
        statement = _statement(nu)
        if not statement:
            continue
        emitted = set()
        bound = bound_names(statement)
        for m in _IDENT.finditer(statement):
            name = m.group(0)
            if name in _SYNTAX or len(name) < 2 or name in bound:
                continue
            out.symbols += 1
            target = index.get(name)
            if target is None:
                reason = "ambiguous" if name in ambiguous else "undeclared"
                out.void.append((sid, name, reason))
                continue
            if target == sid or (sid, target) in emitted:
                continue
            emitted.add((sid, target))
            docs = list(getattr(rec, "docs", None) or ())
            out.edges.append(Scaffold(
                chart="lean", src_slot=sid, dst_slot=target, kind=DEPENDS_ON,
                symbol=name, era=era, provenance=str(docs[0]) if docs else ""))
    return out
