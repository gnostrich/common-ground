"""THE GO SCAFFOLD: import blocks and qualified selector references (`pkg.Symbol`).

2,056 Go slots went in FLAT, one per top-level `func`/`type`/`const`/`var` declaration,
sliced by `engine/extract.py:_segment_go` exactly the way the 12,466 Lean slots and 3,377
Python slots were. This parses the same kind of declared structure back out.

NO GO PARSER EXISTS IN PYTHON. Shelling out to the real `go` toolchain was already refused
for `_nu_go` (gate 1: addressing is a function of the seed, never of a binary that may or may
not be on the machine that runs it) and for `_segment_go` (the same objection). This module
inherits that refusal and is, honestly, a SCANNER rather than a parser: it recognizes Go's
declaration heads and its `.`-selector syntax by pattern, the same register `scaffold_lean.py`
already uses for a language with no Python parser either. What follows states, in full, what
it can and cannot tell apart — read this before trusting a count from it.

THE SAME NORMALIZATION FACT AS PYTHON'S, WITH A DIFFERENT CONSEQUENCE. `_nu_go` collapses
every run of whitespace, including every newline, to one space — a slot's `nu` is one
physical line. Unlike Python, Go's block structure is brace-delimited, not indentation-
sensitive, so collapsing newlines does not break the TEXT the way it breaks a Python `def`'s
body: `{ ... }` still nests correctly one line. What newline-collapse DOES break is Go's
Automatic Semicolon Insertion, which is a lexer-level rule this module never depended on
(it is not running Go's tokenizer), so there is no equivalent of the Python module's
prefix-recovery loop needed here — the whole flattened body is what this scanner reads.

WHAT IS PARSED.
  DECLARED NAME   the identifier after `func` / `type` / `const` / `var`, read from the same
                  grammar `_segment_go`'s own `_GO_DECL_RE` encodes (this module keeps an
                  independent copy so it has no import-time dependency on the extractor).
                  A method's name is qualified with its receiver TYPE (`Recv.Name`), because
                  `T.M` and `U.M` are different declarations — the same reasoning
                  `_segment_go`'s docstring gives for its own locator.
  SELECTOR REFS   every `X.Y` pair in the body, found by scanning for two adjacent Go
                  identifiers joined by a dot (`re.finditer` with a zero-width lookahead, so
                  a three-part chain like `req.Header.Get` yields BOTH `req.Header` and
                  `Header.Get` rather than only the first — still an exact identifier-boundary
                  scan, the same discipline `scaffold_lean.py`'s `_IDENT` regex uses, never an
                  approximate one).
  IMPORT BLOCKS   `import "path"` and `import ( alias "path" ... )`, read by `import_targets`.

THE ONE STRUCTURAL AMBIGUITY THIS SCANNER CANNOT RESOLVE, STATED PLAINLY. Go's `X.Y` syntax
covers BOTH a package-qualified reference (`fmt.Println`) and a value's field or method
selector (`cfg.Name`, `req.Body`) — telling them apart requires knowing `X`'s static type,
which requires a type checker this module does not have and will not approximate with a
guess. The mitigation taken is a REAL Go language rule, not a heuristic: only an EXPORTED
identifier (`Y[0]` uppercase) can be referenced across a package boundary at all, so a
selector whose right-hand name is unexported (`h.fetcher`, `cfg.name`) is excluded — it could
never be a genuine cross-file reference in real Go, full stop. An EXPORTED right-hand name
(`resp.Body`, `svc.Balance`) still cannot be told apart from a same-package value selector
that happens to share a name with something this corpus declares elsewhere; every edge from
such a case is a REAL string match against something this corpus actually declares, but it is
not proof the two are the same thing. That residual is named here, not hidden, and it is why
this module is a scanner and not a parser.

WHAT ELSE IS NOT MODELLED, NAMED RATHER THAN IMPLIED AWAY:
  GENERICS      `type Stack[T any] struct{...}` — the type-parameter list is not read; the
                declared name (`Stack`) is unaffected because the name regex stops at `[`,
                but no dependency on `T`'s constraint is ever extracted.
  BUILD TAGS    `//go:build linux` and `// +build` lines are COMMENTS, already stripped by
                `_nu_go` before this module ever sees a slot's text. A build-constrained
                declaration is indistinguishable here from an unconstrained one; this module
                cannot tell and does not try to.
  STRING LITERALS  the scan is not string-literal-aware, the same simplification `_nu_go`'s
                own comment stripper already carries for `//` inside a string. A selector-
                shaped substring inside a Go string literal will be scanned as if it were code.
  PACKAGE IDENTITY  this corpus addresses individual declarations, never a package as its own
                slot (`_segment_go` never spans a `package` clause), so `import_targets`'s
                output cannot be checked against anything this corpus declares — see its own
                docstring for why `parse()` does not call it.

RESOLVE-OR-VOID, unchanged. A selector reference resolves to exactly one declared slot by
EXACT bare-name lookup or is VOID: `"ambiguous"` if the corpus declares that trailing name
more than once (a plain func, a method on a different receiver, and a `const`/`var` with the
same name all collide under the SAME bare key on purpose — a selector call site never writes
the receiver type, so this module cannot tell them apart either, and the safe response to that
is to void rather than guess), `"undeclared"` otherwise.
"""

from __future__ import annotations

import re

from .scaffold import DEPENDS_ON, Scaffold, ScaffoldParse

#: Go's own declaration grammar for the four kinds this corpus addresses, anchored at the
#: start of the (already tag-stripped, single-line) slot body — position 0 is always the
#: declaration head, because that is exactly what `_segment_go` sliced the span on. Kept as
#: an independent copy of `_segment_go`'s `_GO_DECL_RE` rather than an import of it, so this
#: module has no load-time dependency on the extractor.
_GO_DECL_RE = re.compile(
    r"^(?:func\s+(?:\(\s*\w+\s+\*?(?P<recv>\w+)\s*\)\s*)?(?P<fn>\w+)"
    r"|type\s+(?P<ty>\w+)"
    r"|(?:const|var)\s+(?P<cv>\w+))")

#: A Go identifier: ASCII letters, digits, underscore, not starting with a digit. Go permits
#: Unicode identifiers too; this scanner is ASCII-only, a stated narrowing, not a defect —
#: every declared name actually observed in this corpus is ASCII.
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"

#: A zero-width lookahead, not a consuming match: `finditer` over this pattern reports EVERY
#: position where an `IDENT.IDENT` pair starts, including overlapping ones, so a chain like
#: `req.Header.Get` yields both `req.Header` and `Header.Get` rather than only the first (a
#: consuming regex would swallow `req.Header` and resume scanning after it, missing the
#: second pair entirely). The leading negative lookbehind is load-bearing, not decorative: a
#: zero-width match advances the scan by one character, so without it `pkg.Helper` would ALSO
#: match starting at `kg.Helper`, `g.Helper`, one spurious hit per character of `pkg` — the
#: lookbehind refuses a start position that is itself inside another identifier, so `lhs`
#: only ever begins at a real token boundary.
_SELECTOR_RE = re.compile(rf"(?<![A-Za-z0-9_])(?=(?P<lhs>{_IDENT})\.(?P<rhs>{_IDENT}))")

#: `import "path"` (bare) or `import ( ["alias"] "path" ... )` (block). Read from whatever
#: text is handed to `import_targets`; never from a corpus slot in practice — see that
#: function's docstring.
_IMPORT_STMT_RE = re.compile(r'import\s*(?:\((?P<block>[\s\S]*?)\)|(?P<single>[^\n;]*"[^"]*"))')
_IMPORT_ENTRY_RE = re.compile(rf'(?:(?P<alias>{_IDENT})\s+)?"(?P<path>[^"]*)"')


def _strip_tag(nu: str) -> str:
    """Drop the `\\x01go\\x01` chart tag `nu()` wraps every go address in."""
    if nu.startswith("\x01"):
        end = nu.find("\x01", 1)
        if end != -1:
            return nu[end + 1:]
    return nu


def declared_name(nu: str) -> str:
    """The name this slot declares: `Name`, or `Recv.Name` for a method, or "" if the body's
    leading token is none of `func`/`type`/`const`/`var`."""
    body = _strip_tag(nu).strip()
    m = _GO_DECL_RE.match(body)
    if not m:
        return ""
    if m.group("fn"):
        recv = m.group("recv")
        return f"{recv}.{m.group('fn')}" if recv else m.group("fn")
    if m.group("ty"):
        return m.group("ty")
    if m.group("cv"):
        return m.group("cv")
    return ""


def selector_references(body: str) -> list[str]:
    """Every EXPORTED trailing name of an `X.Y` selector pair in `body`, in scan order,
    duplicates included. Unexported `Y` (Go's own visibility rule: it could never be a real
    cross-declaration reference) is excluded here, structurally, not by a stopword list.
    """
    out = []
    for m in _SELECTOR_RE.finditer(body):
        rhs = m.group("rhs")
        if rhs[:1].isupper():
            out.append(rhs)
    return out


def import_targets(text: str) -> list[tuple[str, str]]:
    """(alias-or-"", import path) for every `import` statement `text` declares.

    Handles a bare `import "path"` and a parenthesized block, each entry optionally aliased.
    Exercised directly by this module's tests against synthetic Go source — NEVER against a
    real corpus slot's `nu`: Go requires every `import` to appear before any top-level
    declaration in a file, and `_segment_go` (which this module mirrors) only ever spans a
    slot from a `func`/`type`/`const`/`var` head to the next such head, so an import
    statement can never fall inside one. Measured: 0 of 2,056 real Go slots contain the
    literal substring "import". `parse()` does not call this for exactly that reason — calling
    it per slot would be a census over an empty population dressed up as a scan, the failure
    class `engine/nonempty.py` names (OI-24): silently succeeding at finding nothing is not
    the same as having looked. This function exists, and is tested, for what it is: a real
    capability with a corpus-shaped reason it is currently inert.
    """
    out: list[tuple[str, str]] = []
    for stmt in _IMPORT_STMT_RE.finditer(text):
        region = stmt.group("block") if stmt.group("block") is not None else stmt.group("single") or ""
        for entry in _IMPORT_ENTRY_RE.finditer(region):
            out.append((entry.group("alias") or "", entry.group("path")))
    return out


def declaration_index(snapshot) -> tuple[dict[str, str], set[str]]:
    """(bare trailing name -> the one slot declaring it, names declared by MORE THAN ONE
    slot), keyed on the BARE name a selector call site actually writes.

    A method `Recv.Name` is indexed under the bare `Name`, alongside any plain `func Name`
    or `type`/`const`/`var Name` — a call site never writes the receiver type (`obj.Name()`,
    never `obj.Recv.Name()`), so resolving by the qualified form would make every method
    reference unreachable. Two DIFFERENT receivers declaring the same method name collide
    under this bare key and correctly go `"ambiguous"`, the same conservative choice
    `scaffold_lean.py` makes for any name declared more than once.
    """
    seen: dict[str, list[str]] = {}
    for sid, rec in (getattr(snapshot, "slots", None) or {}).items():
        if getattr(rec, "chart", "") != "go":
            continue
        name = declared_name(getattr(rec, "nu", "") or "")
        if not name:
            continue
        bare = name.rsplit(".", 1)[-1]
        seen.setdefault(bare, []).append(sid)
    index = {n: s[0] for n, s in seen.items() if len(s) == 1}
    ambiguous = {n for n, s in seen.items() if len(s) > 1}
    return index, ambiguous


def parse(snapshot, era: str = "") -> ScaffoldParse:
    """Every Go slot's selector references, resolved against the declared bare-name index."""
    index, ambiguous = declaration_index(snapshot)
    out = ScaffoldParse()
    for sid, rec in sorted((getattr(snapshot, "slots", None) or {}).items()):
        if getattr(rec, "chart", "") != "go":
            continue
        nu = getattr(rec, "nu", "") or ""
        body = _strip_tag(nu).strip()
        if not body:
            continue
        emitted: set[tuple[str, str]] = set()
        docs = list(getattr(rec, "docs", None) or ())
        for name in selector_references(body):
            out.symbols += 1
            target = index.get(name)
            if target is None:
                reason = "ambiguous" if name in ambiguous else "undeclared"
                out.void.append((sid, name, reason))
                continue
            if target == sid or (sid, target) in emitted:
                continue
            emitted.add((sid, target))
            out.edges.append(Scaffold(
                chart="go", src_slot=sid, dst_slot=target, kind=DEPENDS_ON,
                symbol=name, era=era, provenance=str(docs[0]) if docs else ""))
    return out
