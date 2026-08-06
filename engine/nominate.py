"""SURFACE-FORM NOMINATION: which neighbourhood a question is sampled from, not what it means.

THE DEFECT THIS ANSWERS, measured on the live corpus. Region seeding drew its eligible set
from the arrow-richest slots by declared degree. That set is 71% one repository — Autosynth,
which is 15% of the material — while Perp-Options-AMM is 47% of the material and 15% of the
seed set, and the entire Lean corpus (12,466 slots, 1.7% touched by any arrow, maximum degree
11 against an eligibility threshold of 4) contributes almost nothing. A question about
certified positivity could not assemble a certified-positivity region: that provenance holds 2
of the 512 eligible slots. Arrow density is self-reinforcing — walked material gets arrows,
arrows make it eligible, eligibility routes questions there, those questions produce more
arrows — so the walk's own history answers every topic regardless of what was asked.

WHAT THIS IS, PRECISELY, BECAUSE THE LINE IS THE WHOLE POINT. A phrase occurring literally in
a claim is a DECLARED FACT ABOUT THAT CLAIM'S TEXT, read off the material in the same class as
a code file's adjacency to its own docstring. It NOMINATES a lineup and does nothing else:

  * no arrow is created, proposed, or evidenced;
  * no relation is decided — every relation still comes from the medium completing a diagram
    through the one inlet, at EXTRACTION tier, gated;
  * no claim is ranked against another. There is no score, no overlap fraction, no distance.
    A slot carries the phrase or it does not, and every slot that carries it is nominated
    equally;
  * what changes is WHERE the region is sampled from. It remains a SAMPLE and still says so.

This is the operator's own lexicon-lane ruling — "nomination is provenance, never matching...
it nominates the lineup; it never creates arrows" — applied to the seeding question it was
always the answer to.

AND IT IS NOT A WORD BAG, which the sweep proved by refusing the first version. That one
tokenized the question, lowercased both sides, and picked the rarest word — which on a real
question chose the verb `establish` over `certified positivity`, because rarest-word is not
most-specific-topic. What replaced it compares CONTIGUOUS PHRASES by literal containment,
longest first, against the corpus's own normal form produced by the corpus's own normalizer.
No set is built, no case is folded, and the unit is the phrase the operator actually typed.
`engine/referee_sweep` sweeps this module like any other and the registration says what it is
rather than exempting it.
"""

from __future__ import annotations

#: Shortest phrase worth nominating on, in characters. A three-letter fragment occurs
#: everywhere, and a nomination that selects most of the corpus is the same as no nomination
#: while looking like a result.
MIN_PHRASE = 8

#: Most words a candidate phrase spans. Long questions otherwise generate a quadratic number
#: of candidates, and a phrase longer than this is not going to occur verbatim in a claim.
MAX_WORDS = 6

#: Above this many carriers a phrase is too common to be a neighbourhood. Seeding falls back
#: and SAYS it fell back, rather than returning an arbitrary slice and calling it a region.
MAX_NOMINATED = 400


def _words(text: str) -> list[str]:
    """Whitespace-delimited runs. Not a tokenizer: nothing is collected, compared or folded —
    these are cut points for rebuilding contiguous phrases of the operator's own string."""
    out, cur = [], []
    for ch in text:
        if ch.isspace():
            if cur:
                out.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        out.append("".join(cur))
    return out


def phrases(text: str, chart: str = "english") -> list[str]:
    """Contiguous phrases of the typed text, in the CORPUS'S normal form, longest first.

    Normalisation goes through the chart's own `nu`, so the comparison is against the same
    form the corpus stored rather than against a lowercase approximation of it. That is why
    no case folding appears here: the normalizer already decided what form these strings take,
    and re-deciding it locally would be a second answer to a settled question.
    """
    from .normalize import nu

    body = nu(chart, text or "")
    if body.startswith("\x01"):
        end = body.find("\x01", 1)
        if end != -1:
            body = body[end + 1:]
    words = _words(body)
    out: list[str] = []
    for n in range(min(MAX_WORDS, len(words)), 0, -1):
        for i in range(len(words) - n + 1):
            p = " ".join(words[i:i + n])
            if len(p) >= MIN_PHRASE:
                out.append(p)
    return out


def nominate(snapshot, text: str, chart: str = "english",
             cap: int = MAX_NOMINATED) -> dict:
    """Slots whose claims literally contain the LONGEST phrase of the question they contain.

    Longest-first is what makes this a neighbourhood rather than a census: a question naming
    "certified positivity" and also "the work" is nominated somewhere specific by the first
    and everywhere by the second, and the longer literal string is the more declared fact
    about the text. Candidates are tried in that order and the first with any carrier wins.
    """
    cands = phrases(text, chart)
    if not cands:
        return {"slots": (), "phrase": "",
                "reason": "the typed text has no phrase long enough to nominate on"}

    slots = getattr(snapshot, "slots", None) or {}

    # BY CHARACTER LENGTH, NOT WORD COUNT — and the difference decided the design. Ranking by
    # word count picked "what does the" over "certified positivity" on a real question: three
    # function words beat two content words, and the nomination landed in the wrong corpus for
    # a purely grammatical reason. A longer literal STRING is a more specific declared fact
    # about the text, and it needs no stopword list to say so, which matters because a
    # stopword list is a vocabulary judgement and this module is not allowed to make one.
    ordered = sorted(set(cands), key=lambda p: (-len(p), p))
    for phrase in ordered:
        found = [sid for sid, rec in slots.items() if phrase in (getattr(rec, "nu", "") or "")]
        if not found:
            continue
        if len(found) > cap:
            return {"slots": (), "phrase": phrase, "occurrences": len(found),
                    "reason": (f"the phrase {phrase!r} occurs in {len(found):,} claims — too "
                               f"broad to be a neighbourhood, so seeding falls back rather "
                               f"than returning an arbitrary slice of it")}
        return {"slots": tuple(sorted(found)), "phrase": phrase, "occurrences": len(found),
                "reason": (f"{len(found)} claim(s) carry the phrase {phrase!r} literally — the "
                           f"longest literal string from the typed text this corpus contains")}
    return {"slots": (), "phrase": "",
            "reason": "no phrase of the typed text occurs literally in any claim here"}
