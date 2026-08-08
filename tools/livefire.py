"""THE STANDING LIVE-FIRE BATTERY. What replaces the operator's eyeballs.

Every check in this file is a defect class the OPERATOR caught personally, by reading a live
transcript, after a green suite of sixteen hundred tests had already passed. That is the whole
argument for the file: the suite tests the mechanism against itself, and every defect in the
list below was a disagreement between two parts of the mechanism that each looked correct
alone. Only the served bytes can settle those.

WHAT IT IS. An executable suite against the SERVED url — the six frozen prompts, the frozen
certified-positivity fixture, and the dialogue-era probes — where each probe's response is
checked for SHAPE, not for whether the answer reads well. Reading well is not checkable and
this file does not try; every check below returns a finding a person can act on or nothing.

THE ACCEPTANCE, and it is not "the checks pass". A battery is accepted when it TRIPS on the
defects that were caught by hand: `tests/test_livefire.py` replays the recorded transcripts of
the three defects the operator caught, and each must produce a finding. A battery that goes
green on a run that was already known to be broken measures nothing.

THE METRIC: operator-caught defects per week, target zero. A defect the operator catches that
this file did not is not merely a bug — it is a MISSING CHECK, and the fix is two commits: the
defect, and the check that would have caught it.

Run:  CG_URL=... CG_TOKEN=... python3 tools/livefire.py [--out DIR] [--probe ID]
Exit: 0 clean, 1 findings, 2 the battery itself could not run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.battery import BATTERY_PATH  # noqa: E402
from tools.redact_run import redact, skeleton  # noqa: E402

#: THE OPERATOR'S OWN QUESTIONS, the same three `tools/acceptance.py` runs. Together with the
#: three frozen battery inputs these are the six frozen prompts.
OPERATOR_QUESTIONS = [
    "what is the relationship between the second fundamental form and the spectral gap",
    "does this corpus contain anything about holonomy",
    "what won't reconcile",
]

#: THE FROZEN FIXTURE's question. Verbatim; see seed/FIXTURE-CERTIFIED-POSITIVITY.md.
FIXTURE_QUESTION = "what does the certified positivity work establish"

#: DIALOGUE-ERA PROBES. The collapse created states the older battery cannot reach, so each of
#: these targets one: a question that SHOULD raise residuals, one that should not, and one on
#: material thin enough that the honest answer is an absence.
DIALOGUE_PROBES = [
    ("residual-rich",
     "what does the corpus hold about positive definiteness across lean and english",
     "a question over material dense enough to seat a cluster: residuals are EXPECTED, and a "
     "run with none is a signal the interrogator went quiet, not that the field was clean"),
    ("residual-free",
     "what is the toolchain version",
     "a narrow question whose answer is one claim. Interrogations here would mean the "
     "interrogator is generating questions the graph did not raise"),
    ("thin-material",
     "what does this corpus establish about sheaf cohomology on rigid analytic spaces",
     "material the corpus does not hold. The honest answer is an ABSENCE, and a confident "
     "answer here is the failure the absence grammar exists to make visible"),
]


@dataclass
class Finding:
    """One defect, named by the class it belongs to and by the probe that raised it."""

    check: str
    probe: str
    detail: str
    evidence: object = None
    #: How many times this exact finding was raised on this probe. One finding, N records.
    seen: int = 1

    def __post_init__(self) -> None:
        """THE EVIDENCE IS REDACTED WHERE IT IS BUILT, not where it is written out.

        These artifacts attach to issues on a PUBLIC repository, and a finding's evidence is
        the one place raw corpus prose reaches them: `sentence` and `lines` are copied straight
        off the served response. Two of them did exactly that before this existed, and were
        caught on the way into git rather than by design — which is the argument for doing it
        at construction, where every present and future check passes through, instead of at
        the boundary, where the next check to be written will forget.
        """
        if isinstance(self.evidence, dict):
            ev = dict(self.evidence)
            if isinstance(ev.get("sentence"), str):
                ev["sentence"] = skeleton(ev["sentence"])
            if isinstance(ev.get("lines"), list):
                ev["lines"] = [skeleton(str(x)) for x in ev["lines"]]
            object.__setattr__(self, "evidence", ev) if False else setattr(self, "evidence", ev)

    def as_record(self) -> dict:
        return {"check": self.check, "probe": self.probe, "detail": self.detail,
                "evidence": self.evidence, "seen": self.seen}


def probes() -> list:
    """Every probe, in order. The six frozen prompts, the fixture, the dialogue-era three."""
    spec = json.loads(Path(BATTERY_PATH).read_text(encoding="utf-8"))
    out = [(f"battery-{i.get('id', '?')}", i.get("text", ""), "frozen battery input")
           for i in spec.get("inputs", [])]
    out += [(f"operator-{n + 1}", q, "the operator's own question")
            for n, q in enumerate(OPERATOR_QUESTIONS)]
    out += [("fixture-certified-positivity", FIXTURE_QUESTION, "the frozen fixture question")]
    out += list(DIALOGUE_PROBES)
    return out


# ─── THE SHEET ────────────────────────────────────────────────────────────────────────────

def shown_labels(run: dict) -> set:
    """Every label the medium was SHOWN, across both sheets it reads.

    Turn 1 reads the region render; later turns read the compiled block. After the seating fix
    these are one set, and this function exists so that a future divergence shows up as a
    finding here rather than as a verdict against a correct answer.
    """
    compiled = run.get("compiled") or {}
    att = compiled.get("attachment") or {}
    out = {str(x) for x in (att.get("labels") or ())}
    out |= {str(c.get("n")) for c in (compiled.get("citations") or ()) if c.get("n")}
    # [b0] IS SHOWN AND IS DELIBERATELY NOT CITABLE. It is the operator's question, and an
    # answer resting on the question rests on nothing — so a conviction for citing it is
    # CORRECT, and counting it as shown here would report the referee for doing its job. That
    # the medium keeps citing it is a separate finding, and its fix is the same as every other
    # in this class: the prompt has to say so.
    return out - {"b0"}


def citable_labels(run: dict) -> set:
    compiled = run.get("compiled") or {}
    return {str(c.get("n")) for c in (compiled.get("citations") or ()) if c.get("n")}


# ─── THE CHECKS. One per defect class the operator caught by hand. ────────────────────────

def check_citations_resolve_against_the_shown_sheet(name: str, run: dict) -> list:
    """ROW 525. The checker's resolvable set IS the shown set.

    The failure mode is not "the answer cited something wrong" — it is the REFEREE holding a
    smaller sheet than the medium was given, and convicting a correct citation. So this reads
    the verdict, not the prose: any UNRESOLVED naming a label the medium was demonstrably shown
    is a defect in the checker, not in the answer.
    """
    shown = shown_labels(run)
    out = []
    for v in ((run.get("faithful") or {}).get("violations") or ()):
        sentence = str(v.get("sentence") or "")
        if v.get("kind") == "unresolved":
            wrongly = sorted(str(n) for n in (v.get("numbers") or ()) if str(n) in shown)
            if wrongly:
                out.append(Finding(
                    "citations-resolve-against-the-shown-sheet", name,
                    f"the checker ruled {wrongly} unresolved, and the medium was shown every "
                    f"one of them. The resolvable set and the shown set have diverged.",
                    {"labels": wrongly, "sentence": sentence[:200],
                     "shown": len(shown), "citable": len(citable_labels(run))}))
        elif v.get("kind") == "uncited":
            # THE SAME DIVERGENCE, WEARING THE OTHER VERDICT. `uncited` means the referee saw
            # NO citation in the sentence. If the sentence visibly carries a bracket holding a
            # label the medium was shown, the citation is there and the referee could not read
            # it — which is what a delimiter the parser did not accept looks like from here,
            # and is how ten `uncited` convictions landed on a fully-cited answer.
            visible = sorted({n for tok in re.findall(r"\[([^\]]*)\]", sentence)
                              for n in (x.strip() for x in tok.split(","))
                              if n in shown})
            if visible:
                out.append(Finding(
                    "citations-resolve-against-the-shown-sheet", name,
                    f"the checker ruled a sentence UNCITED while it carries {visible}, every "
                    f"one of them shown. The referee could not read a citation that is there.",
                    {"labels": visible, "sentence": sentence[:200]}))
    return out


def check_a_red_verdict_names_a_compliable_rule(name: str, run: dict) -> list:
    """ROW 523. A rule the medium cannot comply with is a rule that only ever convicts.

    For every verdict kind returned, the LICENCE — the token the medium would have had to write
    to avoid it — must be present in the bytes actually sent. Checked against the wire, not the
    source, because the source has been right while the wire was wrong three times.
    """
    licence = {"uncited": "[", "vacuous": "∅", "welded": "∅rel", "uncontested": "[!]"}
    # EVERY PROMPT, not their concatenation. Any turn's reply can become the answer, so the
    # licence has to be present in the sheet that turn was given — joining them lets one
    # prompt's licence excuse another prompt's silence, which is exactly the arrangement that
    # hid the contest gap: `[!]` is in the render prompt and is not in turn 1's, and turn 1 is
    # what usually answers.
    systems = [str(c.get("system") or "") for c in (run.get("transcript") or ())]
    out = []
    for v in ((run.get("faithful") or {}).get("violations") or ()):
        token = licence.get(v.get("kind"))
        if not token or not systems:
            continue
        missing = [i + 1 for i, sysmsg in enumerate(systems) if token not in sysmsg]
        if missing:
            out.append(Finding(
                "a-red-verdict-names-a-compliable-rule", name,
                f"the checker returned {v['kind']} while call(s) {missing} went out with no "
                f"{token!r} anywhere in the prompt — a turn that answered from one of those "
                f"sheets could not have complied",
                {"kind": v.get("kind"), "token": token, "calls_without_it": missing}))
    return out


def check_no_turn_without_a_preceding_question(name: str, run: dict) -> list:
    """THE UNASKED TURN. Every turn answers something that was asked.

    The render fossil survived once as a render TURN — an unconditional extra call re-putting
    the operator's question against a degraded summary of the previous turn's own work. A turn
    is legitimate only as a response to the operator's question or to a recorded interrogation.
    """
    dlg = run.get("dialogue") or {}
    turns = list(dlg.get("turns") or ())
    question = str(dlg.get("question") or "")
    legal = {question}
    out = []
    for t in turns:
        ask = str(t.get("ask") or "")
        if ask not in legal:
            out.append(Finding(
                "no-turn-without-a-preceding-question", name,
                f"turn {t.get('turn')} answered a question no prior turn raised",
                {"turn": t.get("turn"), "ask": ask[:160]}))
        if t.get("interrogation"):
            legal.add(str(t["interrogation"]))
    return out


def check_residuals_are_scoped_to_the_perturbation(name: str, run: dict) -> list:
    """A residual names objects THIS perturbation showed, or it is about something else."""
    # SCOPED TO WHAT THE PERTURBATION REACHED, not merely to what is citable. After the seating
    # fix every object in the region is citable, so "citable" stopped discriminating and the
    # check went quiet while three of four turns were spent on contested claims the question
    # never touched. The set that matters is attached / bears_on / moved.
    compiled = run.get("compiled") or {}
    reached = {str(c.get("n")) for c in (compiled.get("citations") or ())
               if c.get("kind") in ("attached", "bears_on", "moved") and c.get("n")}
    out = []
    for r in ((run.get("dialogue") or {}).get("residuals") or ()):
        ident = [str(x) for x in (r.get("residual") or ())]
        # ("lex", <group>) names a declared group, not a label; only label-shaped elements are
        # scoped against the reached set.
        stray = sorted(x for x in ident
                       if re.fullmatch(r"[a-z]?\d+", x) and x not in reached)
        if stray:
            out.append(Finding(
                "residuals-are-scoped-to-the-perturbation", name,
                f"a residual named {stray}, which this perturbation never REACHED — "
                f"the budget went on the sample rather than on what was asked",
                {"residual": ident, "turn": r.get("turn")}))
    return out


def check_no_mechanism_prose_on_the_wire(name: str, run: dict) -> list:
    """THE RAZOR, applied to the BYTES rather than to the source.

    Field statistics describe the MEASUREMENT, not the field, and a medium handed them
    enumerates them — it once answered a question about certified positivity by reciting how
    many lines were void. The scope view is where they live. This asserts no line of the scope
    view reached any prompt, using the run's OWN scope text rather than a hand-kept list of
    forbidden phrases, which would rot the first time the wording changed.
    """
    # THE SCOPE VIEW IS A SUPERSET OF THE COMPILED BLOCK, which the first version of this check
    # did not know: `engine.inbound` builds one list of lines, keeps ALL of them as the scope
    # and sends the STATE subset as the prompt. Comparing the whole scope against the wire
    # therefore flagged every state line as a leak — 96 of them on one probe, all correct
    # behaviour. What must not travel is the NON-state remainder: the mechanism prose and the
    # field statistics. The predicate is imported from the compiler rather than restated, so
    # the two cannot disagree about what a state line is.
    from engine.inbound import _is_state

    scope = str((run.get("compiled") or {}).get("scope") or "")
    # THE OPERATOR'S OWN QUESTION IS IN THE SCOPE AND BELONGS ON THE WIRE. It is the one line
    # of the scope view that is not mechanism prose, and flagging it would report the machine
    # for asking what it was asked.
    typed = str((run.get("compiled") or {}).get("typed") or "").strip()
    lines = [ln.strip() for ln in scope.splitlines()
             if len(ln.strip()) >= 40 and not _is_state(ln)
             and (not typed or typed not in ln)]
    sent = "\n".join(str(c.get("system") or "") + "\n" + str(c.get("user") or "")
                     for c in (run.get("transcript") or ()))
    leaked = [ln for ln in lines if ln in sent]
    if leaked:
        return [Finding("no-mechanism-prose-on-the-wire", name,
                        f"{len(leaked)} line(s) of the scope view reached a prompt",
                        {"lines": [ln[:120] for ln in leaked[:5]]})]
    return []


def check_no_degenerate_turn_left_unretried(name: str, run: dict) -> list:
    """THE EMPTY ANSWER. A turn that only related and never answered is a real state; a page
    that DISPLAYS it is not. The residual exists for exactly this and must have fired."""
    dlg = run.get("dialogue") or {}
    turns = list(dlg.get("turns") or ())
    if not turns:
        return []
    answer = str(run.get("answer") or "").strip()
    if answer:
        return []
    return [Finding("no-degenerate-turn-left-unretried", name,
                    f"{len(turns)} turn(s) ran, "
                    f"{sum(int(t.get('resolved') or 0) for t in turns)} arrows resolved, and "
                    f"the answer is EMPTY — the residual did not fire",
                    {"turns": len(turns), "stopped": dlg.get("stopped", "")})]


def check_panel_hashes_verify(name: str, run: dict) -> list:
    """The displayed bytes ARE the sent bytes. A digest nobody recomputes is decoration."""
    out = []
    for i, call in enumerate(run.get("transcript") or ()):
        for side, key in (("system", "system_sha"), ("user", "user_sha"),
                          ("reply", "reply_sha")):
            got = hashlib.sha256((call.get(side) or "").encode("utf-8")).hexdigest()[:16]
            if got != call.get(key):
                out.append(Finding("panel-hashes-verify", name,
                                   f"call {i + 1}: the {side} digest does not match its bytes",
                                   {"call": i + 1, "side": side,
                                    "claimed": call.get(key), "recomputed": got}))
    return out


def check_no_question_asked_twice_with_the_same_reply(name: str, run: dict) -> list:
    """THE SPENT QUESTION. Asking again cannot make the reply different.

    Records versus pairs at the interrogation level: a residual put twice is one question and
    two records, and the budget exists for open questions.
    """
    seen: dict = {}
    out = []
    for t in ((run.get("dialogue") or {}).get("turns") or ()):
        key = (str(t.get("ask") or ""),
               hashlib.sha256((t.get("prose") or "").encode("utf-8")).hexdigest())
        if key in seen:
            out.append(Finding("no-question-asked-twice-with-the-same-reply", name,
                               f"turn {t.get('turn')} repeated turn {seen[key]}'s question AND "
                               f"its reply, byte for byte",
                               {"turns": [seen[key], t.get("turn")],
                                "ask": str(t.get("ask") or "")[:160]}))
        else:
            seen[key] = t.get("turn")
    return out


def check_uncited_sentences_are_not_escaped_arrow_lines(name: str, run: dict) -> list:
    """THE AUDITOR'S OWN FINDING, encoded. Named by it, verified by it, then written here.

    `said()` strips a line that is ONLY an arrow. The auditor found the escape shapes by
    execution — `- [e1] -relates-> [l45]`, `* …`, `1. …`, and `[e1] --relates--> [l45]` — every
    one of which survived into the DISPLAYED ANSWER and was then convicted as an uncited
    sentence. A wiring diagram shown to the operator as prose, marked RED for not citing
    anything.

    The gap it also named: when such a line survives in its UNBRACKETED form, the citation
    parser finds no brackets, `check_citations_resolve_against_the_shown_sheet` finds none
    either, and the battery reports a clean `uncited` verdict over a defect one function
    upstream. So this check asks the opposite question of an uncited sentence: is it prose that
    rests on nothing, or is it an arrow that escaped by a hair?
    """
    from engine.dialogue import ARROW

    out = []
    for v in ((run.get("faithful") or {}).get("violations") or ()):
        if v.get("kind") != "uncited":
            continue
        sentence = str(v.get("sentence") or "").strip()
        if not sentence or not ARROW.search(sentence):
            continue
        # An arrow inside a real sentence is legitimate — "this refines that, [e1] -refines->
        # [e7]" is prose. What is not is a sentence that is NOTHING BUT an arrow once its
        # decoration is removed.
        bare = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", sentence).strip()
        if ARROW.fullmatch(bare.rstrip(".;")):
            out.append(Finding(
                "uncited-sentences-are-not-escaped-arrow-lines", name,
                "a sentence convicted UNCITED is an arrow line that escaped `said()` and "
                "reached the answer — the extraction channel displayed as prose, then marked "
                "RED for resting on nothing",
                {"sentence": sentence[:200]}))
    return out


#: THE FROZEN BASELINE. Declared in seed, not here — a baseline a tool could edit is not one.
BASELINE_PATH = Path(__file__).resolve().parent.parent / "seed" / "BASELINE.json"


def baseline() -> dict:
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def check_discrimination_is_in_the_sane_band(name: str, run: dict) -> list:
    """A DEGENERACY IS NOT A LOW SCORE, and this is the check that says so.

    At or above the engine's own INDISCRIMINATE threshold the medium drew an arrow to
    essentially every object it was shown, so the attachment carries no information about which
    claims the input bears on. At the other pole the field did not respond at all.

    Column F sat at 1.00, and its lean-attachment figure read as the boundary this project has
    chased since column A — it was 19 of 19 because EVERYTHING was 59 of 59. A BOUNDARY CROSSED
    AT FRACTION 1.0 WAS NOT CROSSED. This is a battery check rather than a note because the
    number that made it look crossed was already on the record and nothing contradicted it.
    """
    att = (run.get("compiled") or {}).get("attachment") or {}
    disc = att.get("discrimination") or {}
    fraction = disc.get("fraction")
    if fraction is None:
        return []
    band = baseline().get("bands") or {}
    low, high = float(band.get("discrimination_low", 0.05)), float(
        band.get("discrimination_high", 0.9))
    shown = int(disc.get("shown") or 0)
    # A THIN REGION HAS NO SANE BAND. With almost nothing shown, attaching to all of it is a
    # small field rather than a degeneracy, and convicting it would fire on every narrow
    # question the operator asks.
    if shown < 10:
        return []
    if fraction >= high:
        return [Finding("discrimination-is-in-the-sane-band", name,
                        f"attachment fraction {fraction} at or above {high}: the medium drew an "
                        f"arrow to essentially everything it was shown, so this attachment "
                        f"carries no information about which claims the input bears on",
                        {"fraction": fraction, "attached": disc.get("attached"),
                         "shown": shown, "engine_red": disc.get("red")})]
    if fraction <= low:
        return [Finding("discrimination-is-in-the-sane-band", name,
                        f"attachment fraction {fraction} at or below {low}: the field did not "
                        f"respond to a region of {shown} object(s)",
                        {"fraction": fraction, "attached": disc.get("attached"),
                         "shown": shown})]
    return []


def check_a_violation_count_carries_its_composition(name: str, run: dict) -> list:
    """A COUNT WITHOUT ITS COMPOSITION IS NOT A MEASUREMENT.

    Three violations became sixty when the referee was repaired and reach doubled, and every
    part of that increase was the machine working — only the composition said which. This
    asserts the verdict can always produce one: a violations list that lost its kinds would let
    a count be reported bare, which is the reporting failure ruled against after column E.
    """
    violations = (run.get("faithful") or {}).get("violations") or []
    kindless = [v for v in violations if not v.get("kind")]
    if kindless:
        return [Finding("a-violation-count-carries-its-composition", name,
                        f"{len(kindless)} of {len(violations)} violation(s) carry no kind, so "
                        f"this count cannot be reported with its composition",
                        {"total": len(violations), "kindless": len(kindless)})]
    return []


#: EVERY CHECK, in order. Each one is a defect the operator caught by reading a transcript.
CHECKS = (
    check_citations_resolve_against_the_shown_sheet,
    check_a_red_verdict_names_a_compliable_rule,
    check_no_turn_without_a_preceding_question,
    check_residuals_are_scoped_to_the_perturbation,
    check_no_mechanism_prose_on_the_wire,
    check_no_degenerate_turn_left_unretried,
    check_panel_hashes_verify,
    check_no_question_asked_twice_with_the_same_reply,
    check_uncited_sentences_are_not_escaped_arrow_lines,
    # THE BASELINE'S TWO DEFENDERS, added when the baseline was frozen. Neither is a defect the
    # operator caught in a transcript — they are the two ways column F's degeneracy could have
    # been reported as progress, turned into checks so it cannot happen twice.
    check_discrimination_is_in_the_sane_band,
    check_a_violation_count_carries_its_composition,
)


def audit(name: str, run: dict) -> list:
    """Every check against one probe's response. Findings, never a score.

    DEDUPED BY (check, detail). Twenty-seven identical licence findings are ONE finding seen
    twenty-seven times — the records-versus-pairs law turned on the auditor itself — and a
    report that lists them all buries the other four classes. The count travels on the record
    so nothing is hidden by the folding.
    """
    raw = []
    for check in CHECKS:
        try:
            raw.extend(check(name, run))
        except Exception as exc:                       # a broken check must not hide the rest
            raw.append(Finding("battery-check-raised", name,
                               f"{check.__name__} raised {type(exc).__name__}: {exc}"))
    seen: dict = {}
    for f in raw:
        key = (f.check, f.detail)
        if key in seen:
            seen[key].seen += 1
        else:
            seen[key] = f
    return list(seen.values())


def ask(url: str, token: str, question: str, timeout: int = 600, tries: int = 2) -> dict:
    """ONE RETRY, because a bare 502 from the platform is not a defect in the build.

    The auditor hit exactly that: a probe returned `502 Bad Gateway` from the deploy's
    infrastructure and succeeded immediately on retry. Reported unretried, it becomes a
    `probe-did-not-respond` finding about a build that answered fine — and a battery that cries
    wolf on infra flake is a battery whose findings get skimmed.

    Deliberately ONE retry, not a backoff loop: a deploy that needs three attempts to answer is
    a finding, and this must not paper over it.
    """
    body = json.dumps({"question": question, "chart": "english"}).encode("utf-8")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    last: Exception | None = None
    for attempt in range(max(1, tries)):
        req = urllib.request.Request(f"{url}/ask?t={token}", data=body,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        try:
            with opener.open(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as exc:
            last = exc
    raise last if last else RuntimeError("ask made no attempt")


def run_battery(url: str, token: str, only: str = "") -> dict:
    rows, findings = [], []
    for name, text, why in probes():
        if only and only != name:
            continue
        t0 = time.time()
        try:
            got = ask(url, token, text)
        except Exception as exc:
            findings.append(Finding("probe-did-not-respond", name,
                                    f"{type(exc).__name__}: {exc}"))
            rows.append({"probe": name, "text": text, "why": why, "error": str(exc)[:200]})
            continue
        secs = round(time.time() - t0, 1)
        if got.get("error"):
            findings.append(Finding("probe-returned-an-error", name, str(got["error"])[:300]))
        found = audit(name, got)
        findings.extend(found)
        dlg = got.get("dialogue") or {}
        verdict = got.get("faithful") or {}
        rows.append({
            "probe": name, "text": text, "why": why, "seconds": secs,
            "turns": dlg.get("turn_count"), "stopped": dlg.get("stopped"),
            "arrows": dlg.get("records"), "resolved": dlg.get("resolved_records"),
            "residuals": dlg.get("residuals"),
            "faithful": {k: verdict.get(k) for k in
                         ("ok", "checked", "cited", "asserted_absent", "citable")},
            "violations": len(verdict.get("violations") or ()),
            "answer_chars": len(got.get("answer") or ""),
            "findings": [f.as_record() for f in found],
            # THE TRANSCRIPT TRAVELS WITH THE FINDING. A finding without the bytes that raised
            # it is a claim, and this file exists because claims were not enough. It travels
            # REDACTED — bracket skeleton, every citation and arrow verbatim, every word
            # replaced — because these artifacts are attached to issues on a public repository
            # and the answers quote the operator's private corpus. The redaction keeps exactly
            # what the checks read, so an artifact is enough to re-run the audit offline.
            "run": redact(got),
        })
    return {"url": url, "rows": rows, "findings": [f.as_record() for f in findings],
            "clean": not findings, "probes": len(rows)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runs/livefire")
    ap.add_argument("--probe", default="")
    a = ap.parse_args()
    url, token = os.environ.get("CG_URL", "").rstrip("/"), os.environ.get("CG_TOKEN", "")
    if not url:
        print("CG_URL is not set; this battery measures the SERVED build", file=sys.stderr)
        return 2
    art = run_battery(url, token, a.probe)
    try:
        head = ask(url, token, "ping")
        art["build"] = ((head.get("corpus_header") or {}).get("build") or {}).get("served", "?")
    except Exception:
        art["build"] = "?"
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{art['build']}.json").write_text(json.dumps(art, indent=1), encoding="utf-8")
    for row in art["rows"]:
        print(f"{row['probe']:32s} {row.get('seconds', 0):6}s turns={row.get('turns')} "
              f"viol={row.get('violations')} findings={len(row.get('findings') or ())}")
    for f in art["findings"]:
        times = f" (x{f['seen']})" if f.get("seen", 1) > 1 else ""
        print(f"  FINDING [{f['check']}] {f['probe']}{times}: {f['detail']}")
    print(f"\n{len(art['findings'])} finding(s) over {art['probes']} probe(s) "
          f"on build {art['build']}")
    return 0 if art["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
