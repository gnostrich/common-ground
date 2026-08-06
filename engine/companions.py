"""Doc companions: a declaration's own prose, entering the English chart beside it.

A `/-- -/` in Lean, a PEP 257 docstring in Python, a `//` block above a Go declaration — all
three are the same structure, the author's natural-language statement of what the
declaration says, written ON the declaration. That is the tightest possible co-location, and
it is what makes `holes_by_declaration` work for a chart pair at all.

The table is keyed by chart BEHAVIOR, not by chart name, and it lives here rather than in
`engine/router.py` for a specific reason: a chart-name literal in the router is exactly the
seam `seed/LANGUAGES.json` was built to close, and `tests/test_code_charts.py` fails the
build if one appears there. Adding a language's doc convention is an entry in this table.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Callable

from .types import Document

ENGLISH = "english"

#: A Lean declaration docstring (`/-- ... -/`) and a module/section doc (`/-! ... -/`).
_LEAN_DOCSTRING_RE = re.compile(r"/--(.*?)-/", re.DOTALL)
_LEAN_SECTION_DOC_RE = re.compile(r"/-!(.*?)-/", re.DOTALL)
#: The declaration a Lean docstring is attached to: the convention puts the doc immediately
#: before its declaration, so the head that follows is the one being documented.
_NEXT_DECL_RE = re.compile(
    r"\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+"
    r"|nonrec\s+|scoped\s+|local\s+)*"
    r"(theorem|lemma|def|abbrev|structure|class|instance|inductive|axiom)\s+([^\s:({\[]+)")

#: A Go doc comment: `//` lines immediately preceding a top-level declaration. Go's own
#: convention (`go doc` reads exactly this), so the pairing is where the author put the words.
_GO_DOC_RE = re.compile(
    r"((?:^//[^\n]*\n)+)[ \t]*"
    r"(func|type|const|var)\s+(?:\(\s*\w+\s+\*?(\w+)\s*\)\s*)?(\w+)",
    re.MULTILINE)


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def lean_docstrings(name: str, text: str, source: str = "repo_docs") -> list[Document]:
    """A Lean file's docstrings, as ENGLISH claims attached to their declaration.

    `/-- ... -/` documents the declaration that follows it (Lean convention), so the derived
    English document's id names that declaration: `<file>#doc:<declaration>`. `/-! ... -/` is a
    section/module doc with no single owner, so it is attributed to the file.

    This is ADDITIVE and NON-PLASTIC. The Lean document and its address are untouched — `nu`
    still strips docstrings from the Lean surface, so every Lean slot id is byte-identical
    before and after. What changes is that 293k characters of prose which used to be discarded
    at the boundary now enter the English chart, carrying provenance that points at the exact
    declaration they describe. That provenance is what makes them co-located at DECLARATION
    granularity — tighter than any directory.
    """
    out: list[Document] = []
    for match in _LEAN_DOCSTRING_RE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        owner = _NEXT_DECL_RE.match(text, match.end())
        decl = owner.group(2) if owner else ""
        doc_id = f"{name}#doc:{decl}" if decl else f"{name}#doc@{match.start()}"
        doc = Document(doc_id, ENGLISH, _nfc(body), source)
        doc.meta["lean_file"] = name
        if decl:
            doc.meta["declaration"] = decl
            doc.meta["declaration_head"] = owner.group(1)
        out.append(doc)
    for match in _LEAN_SECTION_DOC_RE.finditer(text):
        body = match.group(1).strip()
        if not body:
            continue
        doc = Document(f"{name}#sectiondoc@{match.start()}", ENGLISH, _nfc(body), source)
        doc.meta["lean_file"] = name
        out.append(doc)
    return out


#: A Go doc comment: `//` lines immediately preceding a top-level declaration. Go's own
#: convention (`go doc` reads exactly this), so the pairing is where the author put the words.
_GO_DOC_RE = re.compile(
    r"((?:^//[^\n]*\n)+)[ \t]*"
    r"(func|type|const|var)\s+(?:\(\s*\w+\s+\*?(\w+)\s*\)\s*)?(\w+)",
    re.MULTILINE)


def python_docstrings(name: str, text: str, source: str = "repo_docs") -> list[Document]:
    """A Python file's docstrings, as ENGLISH claims attached to their declaration.

    Same argument as `lean_docstrings`, one language over: PEP 257 puts the docstring as the
    first statement of the `def`/`class` it documents, so the pairing is given by where the
    author wrote the words rather than by any inference. Uses `ast`, which is safe here for
    the reason `_segment_python` gives — this runs on whole files, never on a fuzzed span, and
    a syntax error yields no companions instead of raising.
    """
    import ast as _ast

    try:
        tree = _ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []

    out: list[Document] = []

    def walk(node, prefix: str) -> None:
        for child in _ast.iter_child_nodes(node):
            if not isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                continue
            qual = f"{prefix}.{child.name}" if prefix else child.name
            doc = _ast.get_docstring(child)
            if doc and doc.strip():
                d = Document(f"{name}#doc:{qual}", ENGLISH, _nfc(doc.strip()), source)
                d.meta["source_file"] = name
                d.meta["declaration"] = qual
                d.meta["declaration_head"] = ("class" if isinstance(child, _ast.ClassDef)
                                              else "def")
                out.append(d)
            if isinstance(child, _ast.ClassDef):
                walk(child, qual)
    walk(tree, "")
    module_doc = _ast.get_docstring(tree)
    if module_doc and module_doc.strip():
        d = Document(f"{name}#moduledoc", ENGLISH, _nfc(module_doc.strip()), source)
        d.meta["source_file"] = name
        out.append(d)
    return out


def go_doc_comments(name: str, text: str, source: str = "repo_docs") -> list[Document]:
    """A Go file's doc comments, as ENGLISH claims attached to their declaration.

    Go's convention is a `//` block immediately above the declaration, and `go doc` reads
    exactly that — so this is the same structural pairing as a Lean `/-- -/` or a Python
    docstring, not a proximity heuristic. A method's receiver is part of the name, because
    `T.M` and `U.M` are different declarations.
    """
    out: list[Document] = []
    for m in _GO_DOC_RE.finditer(text):
        body = "\n".join(line.lstrip("/").strip() for line in m.group(1).splitlines()).strip()
        if not body:
            continue
        recv, ident = m.group(3), m.group(4)
        decl = f"{recv}.{ident}" if recv else ident
        d = Document(f"{name}#doc:{decl}", ENGLISH, _nfc(body), source)
        d.meta["source_file"] = name
        d.meta["declaration"] = decl
        d.meta["declaration_head"] = m.group(2)
        out.append(d)
    return out


def python_docstrings(name: str, text: str, source: str = "repo_docs") -> list[Document]:
    """A Python file's docstrings, as ENGLISH claims attached to their declaration.

    Same argument as `lean_docstrings`, one language over: PEP 257 puts the docstring as the
    first statement of the `def`/`class` it documents, so the pairing is given by where the
    author wrote the words rather than by any inference. Uses `ast`, which is safe here for
    the reason `_segment_python` gives — this runs on whole files, never on a fuzzed span, and
    a syntax error yields no companions instead of raising.
    """
    import ast as _ast

    try:
        tree = _ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return []

    out: list[Document] = []

    def walk(node, prefix: str) -> None:
        for child in _ast.iter_child_nodes(node):
            if not isinstance(child, (_ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
                continue
            qual = f"{prefix}.{child.name}" if prefix else child.name
            doc = _ast.get_docstring(child)
            if doc and doc.strip():
                d = Document(f"{name}#doc:{qual}", ENGLISH, _nfc(doc.strip()), source)
                d.meta["source_file"] = name
                d.meta["declaration"] = qual
                d.meta["declaration_head"] = ("class" if isinstance(child, _ast.ClassDef)
                                              else "def")
                out.append(d)
            if isinstance(child, _ast.ClassDef):
                walk(child, qual)
    walk(tree, "")
    module_doc = _ast.get_docstring(tree)
    if module_doc and module_doc.strip():
        d = Document(f"{name}#moduledoc", ENGLISH, _nfc(module_doc.strip()), source)
        d.meta["source_file"] = name
        out.append(d)
    return out


def go_doc_comments(name: str, text: str, source: str = "repo_docs") -> list[Document]:
    """A Go file's doc comments, as ENGLISH claims attached to their declaration.

    Go's convention is a `//` block immediately above the declaration, and `go doc` reads
    exactly that — so this is the same structural pairing as a Lean `/-- -/` or a Python
    docstring, not a proximity heuristic. A method's receiver is part of the name, because
    `T.M` and `U.M` are different declarations.
    """
    out: list[Document] = []
    for m in _GO_DOC_RE.finditer(text):
        body = "\n".join(line.lstrip("/").strip() for line in m.group(1).splitlines()).strip()
        if not body:
            continue
        recv, ident = m.group(3), m.group(4)
        decl = f"{recv}.{ident}" if recv else ident
        d = Document(f"{name}#doc:{decl}", ENGLISH, _nfc(body), source)
        d.meta["source_file"] = name
        d.meta["declaration"] = decl
        d.meta["declaration_head"] = m.group(2)
        out.append(d)
    return out


#: chart behavior -> its doc-companion extractor. See the module docstring for why this is
#: keyed by behavior and why it is not in the router.
COMPANION_BEHAVIORS: dict[str, Callable[[str, str, str], list[Document]]] = {
    "lean": lean_docstrings,
    "python": python_docstrings,
    "go": go_doc_comments,
}


def doc_companions(chart: str, name: str, text: str, source: str) -> tuple[Document, ...]:
    """Companions for `chart`, resolved through its declared behavior. Unknown -> none."""
    from .charts import chart_spec

    try:
        behavior = chart_spec(chart).behavior
    except Exception:
        return ()
    fn = COMPANION_BEHAVIORS.get(behavior)
    return tuple(fn(name, text, source)) if fn else ()
