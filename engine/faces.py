"""Formal faces derived from the operator's OWN Lean corpus — the term-level anchor layer.

The lexicon's Mathlib import is blocked (D8), so there are no `compact ↔ IsCompact` bindings
to rank candidate holes by. But the corpus already contains exactly the vocabulary its prose
discusses: 2,128 Lean files whose declaration names *are* formal faces. A general dictionary
would mostly carry terms this corpus never uses; the corpus's own names carry the ones it does.

**Faces derive only through the seeded R-map.** `engine/rmap.render` decamelizes a name and
substitutes the abbreviation table declared in `seed/CONSTANTS.json` (hashed into the lock,
plastic under gate 4). There is no similarity anywhere in face generation: no threshold, no
edit distance, no embedding. A face is a *declared rendering* of a name, and a name either
renders to it or does not.

**What an anchor is, and what it is not.** An anchor says: *this English slot mentions a term
this Lean declaration is named for.* That makes it a PRIOR on candidate generation — it decides
which holes are worth asking about — and nothing more. It never creates a correspondence, never
enters the structure, and never grounds anything. The LM still proposes, the engine still
disposes, and every arrow still arrives as a claim through the one inlet at extraction tier.

**Warrant.** A derived face is `REPO_DOC`: it has repo provenance (file + declaration) but
nothing verified it, and nobody authored it. It is deliberately NOT authorship-tier — deriving
a face is a mechanical transform of the operator's files, not the operator's confirmation.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Sequence

from .rmap import render
from .types import WarrantTier

#: The declaration heads a face can be derived from. `example` is excluded: it is anonymous
#: scratch work, not a named term the prose could be discussing.
FACE_HEADS = ("theorem", "lemma", "def", "abbrev", "structure", "class", "instance",
              "inductive", "axiom")

_DECL_RE = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|partial\s+|unsafe\s+"
    r"|nonrec\s+|scoped\s+|local\s+)*"
    r"(" + "|".join(FACE_HEADS) + r")\s+([^\s:({\[]+)",
    re.MULTILINE,
)

#: A face must be a real phrase to anchor anything. One-character renders and pure numbers
#: would match everywhere; they are dropped rather than allowed to anchor by accident.
_MIN_FACE_CHARS = 4

#: Faces this common in English are not discriminating (they would anchor half the corpus).
#: Declared, not tuned: these are the closed-class words the R-map can emit from a name like
#: `is_of_the_form`. Not a similarity threshold — a fixed, seed-visible stop list.
_STOP_FACES = frozenset({
    "is", "of", "the", "to", "in", "on", "at", "and", "or", "not", "eq", "ne", "le", "lt",
    "ge", "gt", "add", "sub", "mul", "div", "zero", "one", "two", "self", "aux", "def",
    "type", "prop", "set", "map", "fun", "val", "get", "mk", "elim", "intro", "cases",
})


@dataclass(frozen=True, slots=True)
class FormalFace:
    """One declaration name, its declared English rendering, and where it came from."""

    formal_name: str            # e.g. "IsPositive" / "Cone.comp_pos"
    face: str                   # the R-map rendering, e.g. "is positive"
    head: str                   # theorem | def | ...
    file: str                   # provenance: which Lean file
    tier: WarrantTier = WarrantTier.REPO_DOC   # derived, NOT authorship

    def as_record(self) -> dict[str, object]:
        return {"formal_name": self.formal_name, "face": self.face, "head": self.head,
                "file": self.file, "tier": self.tier.name}


def declarations(text: str) -> list[tuple[str, str]]:
    """(head, name) for every named declaration. Exact regex, no inference."""
    return [(m.group(1), m.group(2)) for m in _DECL_RE.finditer(text)]


def derive_faces(documents: Sequence) -> list[FormalFace]:
    """Every declaration in the Lean documents, rendered through the SEEDED R-map.

    Deterministic and total: a name renders or it does not, and the rendering depends only on
    the name plus the hashed abbreviation table.
    """
    out: list[FormalFace] = []
    seen: set[tuple[str, str]] = set()
    for doc in documents:
        if getattr(doc, "chart", None) != "lean":
            continue
        path = doc.meta.get("path", doc.doc_id) if getattr(doc, "meta", None) else doc.doc_id
        for head, name in declarations(doc.text):
            face = render(name).strip()
            if len(face) < _MIN_FACE_CHARS or face in _STOP_FACES:
                continue
            key = (name, face)
            if key in seen:
                continue
            seen.add(key)
            out.append(FormalFace(formal_name=name, face=face, head=head, file=str(path)))
    return out


def face_index(faces: Iterable[FormalFace]) -> dict[str, list[FormalFace]]:
    """face string -> the declarations that render to it."""
    idx: dict[str, list[FormalFace]] = defaultdict(list)
    for f in faces:
        idx[f.face].append(f)
    return dict(idx)


def first_word_index(index: dict[str, list[FormalFace]]) -> dict[str, tuple[str, ...]]:
    """INVERTED index: first word of a face -> the faces beginning with it.

    This is what makes anchoring a lookup instead of a scan. Without it, testing a slot means
    walking every face — which is the enumeration-wearing-an-index's-clothes defect this build
    has already deleted twice. Built once per corpus, in O(faces).
    """
    out: dict[str, list[str]] = defaultdict(list)
    for face in index:
        out[face.split(" ", 1)[0]].append(face)
    return {w: tuple(sorted(fs)) for w, fs in out.items()}


_WORD_RE = re.compile(r"[a-z0-9]+")


def _phrase_in(haystack: str, phrase: str) -> bool:
    """Exact word-boundary containment. No stemming, no fuzz, no scoring."""
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", haystack) is not None


def anchors_for_english(nu_body: str, by_first: dict[str, tuple[str, ...]]) -> list[str]:
    """Which declared faces this English slot mentions, by exact word-boundary containment.

    INDEX-DRIVEN: iterate the slot's own words and look each up in the inverted index, so only
    faces that *begin with a word this slot actually contains* are ever tested. Cost is
    O(words in the slot x faces sharing that first word) — independent of the total face count.

    An earlier version looped over every face and filtered inside the loop, which made this
    O(slots x faces) while the docstring claimed the bound below. The claim was wrong and the
    operator caught it; the index is now real rather than described.
    """
    body = nu_body.casefold()
    hits: list[str] = []
    for word in set(_WORD_RE.findall(body)):
        for face in by_first.get(word, ()):
            if _phrase_in(body, face):
                hits.append(face)
    return hits


#: nu wraps every body in a control-character chart tag. The declaration regex anchors on
#: `^\s*`, and `\x01` is not whitespace, so the tag must come off before parsing — without
#: this, EVERY Lean slot silently yields no face (measured: 0 of 12,041, in 0s).
_TAG_RE = re.compile(r"^\x01[a-z]+\x01")


def anchors_for_lean(nu_body: str, index: dict[str, list[FormalFace]]) -> list[str]:
    """Which declared faces this Lean slot's own declaration name renders to.

    The Lean slot's nu *is* the declaration, so its face comes from parsing its own head —
    not from matching prose. Exact, by construction.
    """
    out: list[str] = []
    for _head, name in declarations(_TAG_RE.sub("", nu_body, count=1)):
        face = render(name).strip()
        if face in index:
            out.append(face)
    return out
