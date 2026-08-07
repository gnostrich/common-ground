"""THE STANDING AUDITOR: read-only, evidence-gathering, files findings and fixes nothing.

THE GOAL METRIC IS INVERTED. It is no longer "how fast was the operator's catch turned into a
fixture" — it is operator-caught regressions per week, target zero, because the auditor caught
them first. Every check here exists because a human found something a green suite did not.

CONSTITUTION.md B3, verbatim, is the charter and the section order below follows it:
  1. REGISTRY     every OI-n in seed/CONSTITUTION.md resolves to a real site/control (B1).
  2. LIVENESS     every planted-defect twin in the suite (named Planted/PLANTED/RED/
                  _can_actually_FIRE) exists AND passes, run for real — the hard one, because
                  a control that cannot fail is not a control, and the null battery going
                  quiet was once read as a pass when it was lost detection power (B2).
  3. BATTERY      the six pinned prompts against the SERVED URL with pre-registered shapes,
                  through tools/acceptance.py's own browser client — reused, not reimplemented.
  4. CONFORMANCE  every `[E: ...]` site named in CONSTITUTION.md exists at its symbol; drift
                  is filed, never silently reconciled.
  5. RAZOR        every LM-facing system prompt, enumerated sentence by sentence; the render
                  path's WIRE/TASK/FORM legality is checked for real (engine/grammar.py).
  6. WIRE         the served build against HEAD, the served model against the pin, the
                  snapshot's age and counts — the page must self-report.
  7. CHANGELOG    a commit landing a design change needs a FEATURE-DIFF block in its message
                  AND an entry in seed/CHANGELOG.md — NEW, added by this lane.

PLUS, load-bearing rather than charter-numbered:
  SWEEPS      referee, control-map-vs-territory, claim discipline, constants — all static,
              all cheap, all reported as findings rather than trusted if they cannot run.
  READ-ONLY   the auditor is incapable of writing to engine/, ui/ or seed/ — asserted, not
              claimed, by fingerprinting those trees before and after every real run.

IT WRITES NOTHING BUT ITS REPORT. No fixes, no code, no opinions on priority — the main
session disposes. That separation is the point: an auditor that can fix what it finds will
stop reporting what it cannot fix.

OI-23, mechanized here rather than merely quoted: "Controls execute the runtime, never
inspect source as proxy." Discovery (finding WHAT to run, by name or by AST) is bookkeeping;
every check that decides ok/not-ok does so by actually calling the real function, importing
the real module, or spawning the real interpreter over the real test — never by grepping for
a substring and calling that a result.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _relpath(p: Path, root: Path | None = None) -> str:
    """`p.relative_to(root)`, falling back to the absolute path when `p` is not under `root`
    — true whenever a twin points discovery or fingerprinting at a scratch directory outside
    the repo, which several planted twins in tests/test_auditor.py do on purpose."""
    root = root or REPO
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def _run(args, timeout=900, cwd=None):
    try:
        p = subprocess.run(args, cwd=cwd or REPO, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout + p.stderr)[-4000:]
    except Exception as exc:                       # noqa: BLE001 - reported, never raised
        return 1, f"{type(exc).__name__}: {exc}"


def sweeps() -> list[dict]:
    """Every static gate. A sweep that cannot run is a FINDING, never a pass."""
    out = []
    for name, args in (
        ("referee", [sys.executable, "-m", "engine.referee_sweep"]),
        ("control-map-vs-territory", [sys.executable, "-m", "engine.control_sweep"]),
        ("claim-discipline", [sys.executable, "-c",
                              "from engine.static_checks import check_claim_discipline as c;"
                              "v=[str(x) for x in c().violations];"
                              "print('\\n'.join(v) or 'clean');"
                              "raise SystemExit(1 if v else 0)"]),
        ("constants", [sys.executable, "-m", "engine.constants_sweep"]),
    ):
        code, log = _run(name and args)
        out.append({"check": name, "ok": code == 0, "detail": log.strip()[:600]})
    return out


def wire() -> dict:
    """B3 item 6: what the deploy says about itself, against what HEAD says."""
    import urllib.request

    url, token = os.environ.get("CG_URL", ""), os.environ.get("CG_TOKEN", "")
    if not url:
        return {"ok": False, "detail": "CG_URL unset — the wire could not be checked, which "
                                       "is a finding rather than a pass"}
    head = _run(["git", "rev-parse", "HEAD"])[1].strip()[:12]
    try:
        from tools.wire import Forwarder
        with Forwarder(url, token) as local:
            body = json.loads(urllib.request.urlopen(f"{local}/corpus", timeout=180).read())
    except Exception as exc:                       # noqa: BLE001
        return {"ok": False, "detail": f"the served build did not answer: {exc}"}
    build = body.get("build") or {}
    snap = build.get("snapshot") or {}
    served = build.get("served", "")
    return {
        "ok": served == head and not build.get("model_drift") and not snap.get("stale"),
        "served": served, "head": head, "commit_match": served == head,
        "model": build.get("model"), "model_pin": build.get("model_configured"),
        "model_drift": bool(build.get("model_drift")),
        "snapshot_age": snap.get("age"), "snapshot_stale": bool(snap.get("stale")),
        "slots": body.get("slots"), "arrows": body.get("arrows"),
        "same_claim": body.get("same_claim"), "loops": body.get("loops"),
    }


def battery() -> list[dict]:
    """B3 item 3: the six-prompt battery against the SERVED URL, pre-registered shapes.

    `tools/acceptance.py` already drives a real browser against the SERVED url — the three
    pinned `seed/BATTERY.json` inputs plus the operator's own three questions, six cases total
    — and screenshots every answer. That IS the client; this function calls it rather than
    opening a second one, per the operator's instruction not to duplicate it.
    """
    url, token = os.environ.get("CG_URL", ""), os.environ.get("CG_TOKEN", "")
    if not url:
        return [{"case": "battery", "ok": False,
                 "detail": "CG_URL unset — the battery could not be run, which is a finding "
                           "rather than a pass"}]

    from tools.acceptance import run as run_acceptance

    out_dir = REPO / "runs" / "acceptance"
    art, last_exc = None, None
    # ONE RETRY. The client has no per-case error recovery — a single screenshot timeout on
    # case 1 of 6 loses every row, observed live in this container under concurrent load — and
    # a control that reports "the battery could not be reached" on ordinary contention is
    # noise, not a finding. A second try that also fails IS reported, not swallowed.
    for attempt in range(2):
        try:
            art = run_acceptance(url, token, out_dir)
            last_exc = None
            break
        except Exception as exc:                   # noqa: BLE001
            last_exc = exc
    if art is None:
        shots = sorted(p.name for p in out_dir.glob("*.png")) if out_dir.exists() else []
        return [{"case": "battery", "ok": False,
                 "detail": f"acceptance run failed twice against the served URL: {last_exc}",
                 "partial_screenshots": shots}]

    rows = []
    for r in art.get("rows", []):
        verdict = r.get("faithful")
        bad = verdict in ("RED", "NO RESPONSE") or not r.get("responded", False)
        rows.append({
            "case": r.get("case"), "text": r.get("text", "")[:160],
            "seconds": r.get("seconds"), "model": r.get("model"),
            "responded": r.get("responded"), "faithful": verdict,
            "answer_chars": r.get("answer_chars"), "rests_on": r.get("rests_on"),
            "screenshot": str((out_dir / r["screenshot"]).relative_to(REPO))
                          if r.get("screenshot") else None,
            "ok": not bad,
        })
    if not rows:
        rows.append({"case": "battery", "ok": False,
                     "detail": "acceptance run returned no rows"})
    return rows


def registry() -> dict:
    """B3 item 1 / B1: every OI-n resolves to real sites and real controls, or the run FAILS.

    A registry naming controls that do not exist is the map-not-territory failure applied to
    the constitution itself — and building it caught three such entries in its first pass,
    one of them because the RESOLVER was wrong (an annotated module constant is an AnnAssign,
    not an Assign, so a symbol that plainly exists reported as missing).

    WEAK entries — enforcement `[P]` only — are reported, never treated as failures. Some
    invariants describe how work is conducted and a control claiming to check them would be
    theatre; the honest move is to name them and shrink the list deliberately.
    """
    try:
        from tools.build_registry import build
        reg = build()
    except Exception as exc:                       # noqa: BLE001
        return {"ok": False, "detail": f"the registry could not be built: {exc}"}
    stale = json.loads((REPO / "seed" / "OI_REGISTRY.json").read_text()) \
        if (REPO / "seed" / "OI_REGISTRY.json").exists() else {}
    drifted = stale.get("entries", {}) != reg["entries"]
    return {"ok": not reg["unresolved"], "count": reg["count"],
            "weak": reg["weak"], "unresolved": reg["unresolved"],
            "committed_registry_is_current": not drifted,
            "detail": (f"{reg['count']} entries, {len(reg['weak'])} WEAK, "
                       f"{len(reg['unresolved'])} unresolvable")}


def conformance() -> dict:
    """B3 item 4: every [E:] site named in CONSTITUTION.md exists at its symbol.

    Drift is a defect in the code OR in the document and is never silently reconciled — the
    auditor reports the mismatch and the operator rules which side moved.
    """
    from tools.build_registry import MAP, resolves
    missing = [f"{oi}: {ref}" for oi, spec in MAP.items()
               for ref in spec.get("E", []) + spec.get("C", []) if not resolves(ref)]
    doc = (REPO / "seed" / "CONSTITUTION.md")
    return {"ok": not missing and doc.exists(),
            "constitution_present": doc.exists(),
            "missing_sites": missing,
            "detail": f"{len(missing)} constitutional site(s) named but absent"}


# ─── B3 ITEM 2 — LIVENESS, discovery + real execution ──────────────────────────────────────

def _words(name: str) -> list[str]:
    """CamelCase/snake_case tokenizer. Used only to FIND candidate fixtures by name — never
    to judge whether their assertions are correct. `already`, `credit`, `shredded` must not
    match on a bare substring scan for `red`; this is why matching is word-level."""
    out: list[str] = []
    for chunk in name.split("_"):
        if chunk:
            out += re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[A-Z]+|\d+", chunk)
    return [w.lower() for w in out]


def _is_planted_name(name: str) -> bool:
    """B2: the suite's planted-defect twins are named with `planted`/`PLANTED` or `red`/`RED`
    as a WHOLE WORD (PlantedX, IsRED, a_red_static_gate, test_planted_...), or the literal
    `_can_actually_FIRE` idiom — the three families the operator named. Word-boundary
    tokenization is what keeps `already`/`credit`/`shredded`/`REQUIRED`/`VERIFIED` out."""
    words = _words(name)
    if "planted" in words or "red" in words:
        return True
    return bool(re.search(r"can_actually_fire", name, re.I))


def discover_planted_defects(tests_dir: Path | None = None) -> dict[str, dict]:
    """Walk every tests/test_*.py by AST and return every unittest.TestCase whose name, or at
    least one of whose test methods, fingerprints it as a planted-defect twin.

    THIS IS BOOKKEEPING, NOT THE CONTROL (OI-23). It never decides pass/fail — it only builds
    the worklist that `liveness()` actually EXECUTES. A class that this misses is invisible to
    liveness; a class it over-includes only costs a few extra seconds of real execution, which
    is the safe direction to be wrong in.
    """
    tests_dir = tests_dir or (REPO / "tests")
    found: dict[str, dict] = {}
    for f in sorted(tests_dir.glob("test_*.py")):
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=str(f))
        except SyntaxError as exc:
            found[f"tests.{f.stem}.<UNPARSEABLE>"] = {
                "file": _relpath(f), "lineno": 0, "class_name_matches": False,
                "matched_methods": [], "parse_error": str(exc)}
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any((isinstance(b, ast.Name) and b.id == "TestCase")
                      or (isinstance(b, ast.Attribute) and b.attr == "TestCase")
                      for b in node.bases):
                continue
            cls_hit = _is_planted_name(node.name)
            methods = [n.name for n in node.body
                      if isinstance(n, ast.FunctionDef) and n.name.startswith("test")
                      and _is_planted_name(n.name)]
            if cls_hit or methods:
                qual = f"tests.{f.stem}.{node.name}"
                found[qual] = {"file": _relpath(f), "lineno": node.lineno,
                               "class_name_matches": cls_hit, "matched_methods": methods}
    return found


def planted_test_ids(found: dict[str, dict] | None = None) -> list[str]:
    """Dotted unittest ids to actually RUN. A class whose NAME fingerprinted it runs whole
    (its other methods are presumed part of the same twin); a class that only had matching
    METHODS runs just those, so an unrelated flaky method elsewhere in a big TestCase does not
    ride along as if it were part of the plant."""
    found = found if found is not None else discover_planted_defects()
    ids: list[str] = []
    for qual, v in found.items():
        if "parse_error" in v:
            continue
        if v["class_name_matches"]:
            ids.append(qual)
        else:
            ids += [f"{qual}.{m}" for m in v["matched_methods"]]
    return ids


_FAIL_LINE = re.compile(r"^(FAIL|ERROR): (\S+) \(([\w.]+)\)", re.M)
_RAN_LINE = re.compile(r"^Ran (\d+) tests? in", re.M)


def run_test_ids(ids: list[str], cwd: Path | None = None, timeout: int = 300) -> dict:
    """EXECUTE the given dotted unittest ids for real (a subprocess `python -m unittest -v`)
    and report what actually happened. This is the control; `discover_planted_defects` above
    is only how the worklist got built.

    Parses unittest's own FAIL:/ERROR: summary lines rather than the per-test dot output,
    because that summary format is stable regardless of verbose docstring formatting and is
    where unittest itself already draws the pass/fail line — reusing it is not source-reading,
    it is reading the tool's verdict.
    """
    if not ids:
        return {"ok": False, "ran": 0, "failed_ids": [], "detail": "no ids to run — an empty "
                "worklist reads as a pass and must not"}
    try:
        p = subprocess.run([sys.executable, "-m", "unittest", "-v", *ids],
                           cwd=cwd or REPO, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:                       # noqa: BLE001
        return {"ok": False, "ran": 0, "failed_ids": [], "detail": f"{type(exc).__name__}: {exc}"}
    log = p.stdout + p.stderr
    failed = [f"{kind}: {name} ({dotted})" for kind, name, dotted in _FAIL_LINE.findall(log)]
    ran_m = _RAN_LINE.search(log)
    ran = int(ran_m.group(1)) if ran_m else None
    ok = p.returncode == 0 and not failed
    return {"ok": ok, "ran": ran, "returncode": p.returncode, "failed_ids": failed,
            "detail": log.strip()[-2000:]}


def liveness() -> dict:
    """B3 item 2 / B2: EVERY PLANTED-DEFECT TWIN MUST FIRE. Silence is not a pass.

    A planted control asserts a defect is caught. If the plant stops reaching the checker the
    control still passes — it asserts a RED that never happens — and detection is lost with
    nothing to show for it. The null battery did exactly this once, so the plants are
    discovered by name across the WHOLE suite (not a fixed module list, which is exactly how
    the previous list under-covered — it named 5 of the 48+ files that actually carry one) and
    RE-RUN for real, every time.
    """
    found = discover_planted_defects()
    ids = planted_test_ids(found)
    result = run_test_ids(ids)
    return {
        "ok": result["ok"],
        "classes_discovered": len(found),
        "test_ids_run": len(ids),
        "tests_ran": result.get("ran"),
        "failed": result["failed_ids"],
        "detail": result["detail"] if not result["ok"] else
                  (f"{len(found)} planted-defect classes across "
                   f"{len({v['file'] for v in found.values()})} files, "
                   f"{result.get('ran')} tests executed, all fired clean"),
        "evidence_sample": sorted(found)[:8],
    }


# ─── B3 ITEM 5 — THE RAZOR ───────────────────────────────────────────────────────────────

def _sentences(text: str) -> list[str]:
    """A HEURISTIC splitter for evidence and counting only — never for a pass/fail judgment.
    Splitting English prose correctly needs a real parser; this is good enough to enumerate
    and to check the two SYNTACTIC properties below, and is never asked to do more than that."""
    return [s.strip() for s in re.split(r"(?<=[.!?:])\s+(?=\S)", text.strip()) if s.strip()]


def prompt_razor() -> dict:
    """B3 item 5: prompt enumeration vs the razor.

    engine/grammar.py is the ONLY place a WIRE/TASK/FORM taxonomy exists in this codebase —
    it governs the render (answer) path. Three OTHER LM-facing prompts exist and are
    enumerated here as evidence (`engine.region.REGION_SYSTEM` for propose/perturb,
    `engine.propose_correspondence.PROPOSE_SYSTEM` for correspondence proposal, and
    `engine.medium.LABEL_SYSTEM` for glossing); none carries a WIRE/TASK/FORM tag scheme and
    none is claimed to. This function REAL-IMPORTS all four and reads their live values — it
    does not grep source for prompt text.

    What is mechanically decidable without inventing a semantic classifier:
      * every render-path block's kind is one of WIRE/TASK/FORM (existing control, reused);
      * the FORM block's sentences reference bracket syntax — codomain syntax IS bracket
        notation per SPEC.md Layer 2, so this is a syntactic fact, not a judgment call;
      * the TASK block is exactly one sentence — SPEC.md calls it "the task verb", singular.
    What is NOT: whether a WIRE- or TASK-tagged sentence is secretly editorial prose, and any
    equivalent judgment for the other three prompts. No classifier for that exists in this
    codebase, hand-rolling one here would be exactly the fluent-fake the operator warned
    against, so it is marked NOT IMPLEMENTED and the full sentence inventory is filed as
    evidence for the operator's own read instead of a fabricated verdict.
    """
    out: dict = {"not_implemented": []}
    try:
        from engine.grammar import BLOCKS, KINDS, illegal_blocks, render_prompt
    except Exception as exc:                       # noqa: BLE001
        return {"ok": False, "detail": f"engine.grammar did not import: {exc}",
                "not_implemented": ["prompt razor: engine.grammar unavailable"]}

    # PASS `BLOCKS` EXPLICITLY. `illegal_blocks()`'s own default argument is bound to the
    # BLOCKS object that existed at import time, once — calling it with no arguments after a
    # twin (or a future engine.grammar edit that reassigns the name) replaces `BLOCKS` would
    # silently keep checking the OLD tuple. Passing the just-imported, live value is what
    # makes this a real check of what's live right now rather than a frozen one.
    illegal = illegal_blocks(BLOCKS)
    render_path = {"blocks": [], "rendered_chars": len(render_prompt())}
    form_ok, task_ok = True, True
    for kind, text in BLOCKS:
        sents = _sentences(text)
        render_path["blocks"].append({"kind": kind, "sentence_count": len(sents),
                                      "sentences": sents})
        if kind == "FORM":
            bad = [s for s in sents if "[" not in s]
            if bad:
                form_ok = False
                render_path["form_sentences_missing_bracket_syntax"] = bad
        if kind == "TASK" and len(sents) != 1:
            task_ok = False
            render_path["task_block_sentence_count"] = len(sents)

    other_prompts = {}
    for modname, attr in (("engine.region", "REGION_SYSTEM"),
                          ("engine.propose_correspondence", "PROPOSE_SYSTEM"),
                          ("engine.medium", "LABEL_SYSTEM")):
        try:
            mod = __import__(modname, fromlist=[attr])
            text = getattr(mod, attr)
            other_prompts[f"{modname}.{attr}"] = {
                "sentence_count": len(_sentences(text)), "chars": len(text)}
        except Exception as exc:                   # noqa: BLE001
            other_prompts[f"{modname}.{attr}"] = {"error": str(exc)}

    out.update({
        "ok": not illegal and form_ok and task_ok,
        "kinds": list(KINDS),
        "illegal_blocks": illegal,
        "render_path": render_path,
        "other_lm_facing_prompts": other_prompts,
        "not_implemented": [
            "per-sentence semantic classification (is this sentence really legend/task-verb/"
            "codomain-syntax and not relocated editorial prose) — no classifier exists in "
            "this codebase for any of the four prompts; sentences are enumerated above as "
            "evidence for the operator's own read, not auto-graded"],
    })
    return out


def copy_checks() -> list[dict]:
    """B3 item 5, folded in: the prompt is WIRE/TASK/FORM; the surface depicts no deleted
    mechanism. `prompt_razor()` above does the sentence-level work; this keeps the page-level
    UI copy check that predates it."""
    out = []
    razor = prompt_razor()
    out.append({"check": "prompt-razor", "ok": razor.get("ok", False),
               "detail": json.dumps({k: razor[k] for k in
                                     ("illegal_blocks", "not_implemented") if k in razor})[:600]})
    code, log = _run([sys.executable, "-m", "unittest", "-q", "tests.test_ui_surface"])
    out.append({"check": "ui-surface", "ok": code == 0, "detail": log.strip()[-400:]})
    return out


# ─── B3 ITEM 7 — CHANGELOG COMPLETENESS (NEW) ──────────────────────────────────────────────

def _design_change_prefixes() -> tuple[str, ...]:
    """Path prefixes that make a commit a "design change" for this check. A small fixed
    vocabulary describing SCOPE, not a tuned number, so it carries no CONSTANT_PROVENANCE.json
    obligation — but it is kept function-local anyway, same as every other value in this
    module, so nothing here can be mistaken for the kind of constant that rule is about."""
    return ("engine/", "ui/", "hooks/", "seed/CONSTITUTION.md", "seed/SPEC.md")


def _touches_design(files: list[str]) -> bool:
    prefixes = _design_change_prefixes()
    return any(f.startswith(prefixes) for f in files)


def _feature_diff_labels() -> tuple[str, ...]:
    """The five labels a sibling, uncommitted pre-push amendment gate (hooks/pre-push, as of
    this run) requires inside a commit's own FEATURE-DIFF block. Named here once rather than
    inferred, so if that gate lands unchanged a commit that passes it also passes here."""
    return ("FEATURE-DIFF", "WHAT", "SUPERSEDES", "CONTROLS", "FIXTURES")


def changelog(window: int = 20) -> dict:
    """B3 item 7, NEW: a commit landing a design change needs a FEATURE-DIFF block in its
    message AND an entry in seed/CHANGELOG.md. Both, not either — a commit-message gate (if
    one lands) can only check the message shape; it cannot know the changelog FILE was
    actually updated, and that is exactly the gap this closes.

    SCOPE, STATED RATHER THAN IMPLIED: only the last `window` commits reachable from HEAD are
    checked. FEATURE-DIFF is a NEW convention as of this run — auditing the whole project
    history against a rule that did not exist when most of it was written would manufacture
    findings out of commits nobody could have complied with. `seed/CHANGELOG.md` not existing
    yet is reported as a finding, per the operator's instruction, never as a crash.
    """
    code, log = _run(["git", "log", f"-{window}", "--format=%H%x1f%s"])
    if code != 0:
        return {"ok": False, "detail": f"git log failed: {log}"}
    commits = [line.split("\x1f", 1) for line in log.strip().splitlines() if line.strip()]

    changelog_path = REPO / "seed" / "CHANGELOG.md"
    changelog_exists = changelog_path.exists()
    changelog_text = changelog_path.read_text(encoding="utf-8") if changelog_exists else ""

    rows = []
    for sha, subject in commits:
        # NOT `--no-patch` + `--name-only` together — git refuses that combination outright
        # (`-s`/`--no-patch` conflicts with `--name-only`), which silently produced an empty
        # file list here on every commit until a planted twin caught it.
        _, files_log = _run(["git", "show", "--format=", "--name-only", sha])
        files = [f for f in files_log.strip().splitlines() if f.strip()]
        if not _touches_design(files):
            continue
        _, msg = _run(["git", "log", "-1", "--format=%B", sha])
        labels = _feature_diff_labels()
        missing_labels = [l for l in labels if l not in msg]
        # 7 hex chars is git's own conventional abbreviation (`git log --oneline`, %h) — a
        # CHANGELOG entry linking a commit is expected to carry at least that much, and a
        # longer form (8 chars, or the full sha in a commit URL) still contains it as a
        # leading substring, so this does not miss a longer citation either.
        in_changelog = changelog_exists and sha[:7] in changelog_text
        ok = not missing_labels and in_changelog
        rows.append({
            "sha": sha[:12], "subject": subject,
            "design_paths": [f for f in files if f.startswith(_design_change_prefixes())][:8],
            "has_feature_diff": not missing_labels,
            "missing_labels": missing_labels,
            "in_changelog_md": in_changelog,
            "ok": ok,
        })

    findings = [] if changelog_exists else [
        f"seed/CHANGELOG.md does not exist — {len(rows)} design-change commit(s) in the last "
        f"{window} could not be checked against it"]
    for r in rows:
        if r["ok"]:
            continue
        bits = []
        if r["missing_labels"]:
            bits.append("missing FEATURE-DIFF label(s) " + ",".join(r["missing_labels"]))
        if changelog_exists and not r["in_changelog_md"]:
            bits.append("no seed/CHANGELOG.md entry")
        findings.append(f"{r['sha']} {r['subject']!r}: {'; '.join(bits)}")

    return {
        "ok": changelog_exists and all(r["ok"] for r in rows),
        "changelog_exists": changelog_exists,
        "window": window,
        "design_change_commits_checked": len(rows),
        "rows": rows,
        "findings": findings,
        "detail": ("CHANGELOG missing" if not changelog_exists else
                   f"{len(rows)} design-change commit(s) in last {window}, "
                   f"{sum(1 for r in rows if r['ok'])} clean"),
    }


# ─── READ-ONLY SELF-CHECK ───────────────────────────────────────────────────────────────

def _fingerprint(roots: list[Path]) -> str:
    """A content fingerprint of every file under the given roots. Order-stable (sorted walk),
    so any write, rename, chmod-that-changes-bytes, or delete under a root changes the digest.
    Not a security boundary — a control proving the auditor stayed read-only, run for real."""
    h = hashlib.sha256()
    for root in sorted(roots, key=str):
        if not root.exists():
            h.update(f"MISSING:{root}\n".encode())
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            h.update(_relpath(p).encode())
            try:
                h.update(p.read_bytes())
            except OSError as exc:
                h.update(f"UNREADABLE:{exc}\n".encode())
    return h.hexdigest()


def assert_read_only(action, roots: list[Path] | None = None) -> dict:
    """Run ACTION for real and prove it touched nothing under `roots` (default engine/, ui/,
    seed/) by fingerprinting before and after. This is the only way to know a function is
    read-only: running it and checking, never reading what it claims to do (OI-23) — a
    docstring promising read-only-ness is exactly the kind of claim this project does not
    trust of itself.
    """
    roots = roots or [REPO / "engine", REPO / "ui", REPO / "seed"]
    before = _fingerprint(roots)
    result = action()
    after = _fingerprint(roots)
    ok = before == after
    return {"ok": ok, "result": result,
            "detail": "unchanged" if ok else
                      "engine/, ui/ or seed/ changed during this run — the auditor is no "
                      "longer read-only and every finding above is suspect"}


# ─── ASSEMBLY ───────────────────────────────────────────────────────────────────────────

def audit() -> dict:
    started = time.time()
    report = {
        "head": _run(["git", "rev-parse", "HEAD"])[1].strip()[:12],
        "sweeps": sweeps(),
        "registry": registry(),
        "conformance": conformance(),
        "prompt_razor": prompt_razor(),
        "wire": wire(),
        "battery": battery(),
        "liveness": liveness(),
        "copy": copy_checks(),
        "changelog": changelog(),
    }
    findings = []
    not_implemented = []

    for s in report["sweeps"]:
        if not s["ok"]:
            findings.append(f"SWEEP {s['check']}: {s['detail'][:200]}")

    r = report["registry"]
    if not r.get("ok"):
        findings.append(f"REGISTRY: unresolvable OI entries — {r.get('unresolved')}")
    if not r.get("committed_registry_is_current", True):
        findings.append("REGISTRY: seed/OI_REGISTRY.json is stale against CONSTITUTION.md")

    c = report["conformance"]
    if not c.get("ok"):
        findings.append(f"CONFORMANCE: {c.get('detail')} — {c.get('missing_sites')}")

    pr = report["prompt_razor"]
    if not pr.get("ok", True):
        findings.append(
            f"RAZOR: illegal_blocks={pr.get('illegal_blocks')} "
            f"form_bracket_violations="
            f"{pr.get('render_path', {}).get('form_sentences_missing_bracket_syntax')} "
            f"task_sentence_count={pr.get('render_path', {}).get('task_block_sentence_count')}")
    not_implemented += pr.get("not_implemented", [])

    w = report["wire"]
    if not w.get("ok") and "served" not in w:
        findings.append(f"WIRE: {w.get('detail')}")
    if not w.get("commit_match", True):
        findings.append(f"WIRE: serving {w.get('served')} against HEAD {w.get('head')}")
    if w.get("model_drift"):
        findings.append(f"WIRE: model drift — serving {w.get('model')} against pin "
                        f"{w.get('model_pin')}")
    if w.get("snapshot_stale"):
        findings.append(f"WIRE: snapshot stale — {w.get('snapshot_age')}")

    for row in report["battery"]:
        if not row.get("ok"):
            findings.append(f"BATTERY {row.get('case')}: faithful={row.get('faithful')} "
                            f"responded={row.get('responded')} "
                            f"detail={row.get('detail')} screenshot={row.get('screenshot')}")

    lv = report["liveness"]
    if not lv["ok"]:
        findings.append(f"LIVENESS: {lv.get('failed') or lv.get('detail')}")

    for cc in report["copy"]:
        if not cc["ok"]:
            findings.append(f"COPY {cc['check']}: {cc['detail'][:200]}")

    ch = report["changelog"]
    findings += [f"CHANGELOG: {f}" for f in ch.get("findings", [])]

    report["findings"] = findings
    report["not_implemented"] = not_implemented
    report["clean"] = not findings
    report["seconds"] = round(time.time() - started, 1)
    return report


if __name__ == "__main__":
    ro = assert_read_only(audit, roots=[REPO / "engine", REPO / "ui", REPO / "seed"])
    out = ro["result"]
    out["read_only"] = {"ok": ro["ok"], "detail": ro["detail"]}
    if not ro["ok"]:
        out["findings"].append(f"READ-ONLY: {ro['detail']}")
        out["clean"] = False

    dest = REPO / "runs" / "audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    print(f"AUDIT of {out['head']} in {out['seconds']}s — "
          f"{'CLEAN' if out['clean'] else str(len(out['findings'])) + ' FINDING(S)'}")
    for f in out["findings"]:
        print("  •", f)
    if out["not_implemented"]:
        print(f"NOT IMPLEMENTED ({len(out['not_implemented'])}):")
        for n in out["not_implemented"]:
            print("  ○", n)
    raise SystemExit(0 if out["clean"] else 1)
