"""Build seed/OI_REGISTRY.json from CONSTITUTION.md, and RESOLVE every entry.

B1 says the auditor fails if any OI-n lacks a resolvable entry, so the entries have to name
things that exist — a registry of plausible-sounding control names would be the map-not-
territory failure applied to the constitution itself. Every `E:` site is checked for its
symbol and every `C:` control for its test class, and anything unresolvable is reported rather
than written as though it resolved.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "seed" / "CONSTITUTION.md"
OUT = REPO / "seed" / "OI_REGISTRY.json"

#: OI-n -> {"E": [site...], "C": [control...], "P": bool}. Hand-mapped to REAL symbols and
#: REAL test classes, because the point of the registry is resolution, not plausibility.
MAP: dict[str, dict] = {
    "OI-1":  {"C": ["tests/test_amendment.py:EveryMechanismModuleCitesItsMove"], "E": ["engine/three_moves.py"]},
    "OI-2":  {"P": True},
    "OI-3":  {"C": ["tests/test_battery.py:OneCodePath"], "E": ["engine/perturb.py"]},
    "OI-4":  {"C": ["tests/test_constants_sweep.py:EveryEngineConstantCLAIMSAProvenance",
                    "tests/test_constants_sweep.py:PlantedDefects",
                    "tests/test_apex.py:DeviationCostIsIndependentOfK",
                    "tests/test_walk.py:ExplorationPressureIsDERIVEDAndSelfExtinguishing"],
              "E": ["engine/constants_sweep.py", "seed/CONSTANT_PROVENANCE.json",
                    "engine/aging.py"]},
    "OI-5":  {"P": True},
    "OI-6":  {"C": ["tests/test_referee_sweep.py"], "E": ["engine/referee_sweep.py"]},
    "OI-7":  {"C": ["tests/test_nominate.py:ItDECIDESNothing"], "E": ["engine/nominate.py"]},
    "OI-8":  {"C": ["tests/test_lexicon.py"], "E": ["engine/lexicon.py"]},
    "OI-9":  {"C": ["tests/test_battery.py"], "E": ["engine/battery.py"]},
    "OI-10": {"C": ["tests/test_scaffold.py:ResolveOrVoid", "tests/test_apex.py:TheFactorizationIsAStar"],
              "E": ["engine/adjudicate.py", "engine/blocks.py:edges_from_fibers"]},
    "OI-11": {"C": ["tests/test_scaffold.py:ItIsNotACorrespondenceAndCannotBeMisKinded"],
              "E": ["engine/scaffold.py:Scaffold"]},
    "OI-12": {"C": ["tests/test_scaffold.py:ResolveOrVoid", "tests/test_scaffold.py:NoInferenceOnlyParse"],
              "E": ["engine/scaffold_lean.py:parse"]},
    "OI-13": {"C": ["tests/test_grounded.py:HonestNegativesHaveALegalForm"],
              "E": ["engine/grounded.py:warrants_held", "engine/aging.py"]},
    "OI-14": {"C": ["tests/test_inlet.py"], "E": ["engine/inlet.py"]},
    "OI-15": {"C": ["tests/test_ui_surface.py:TheBuildNamesItsMATERIALNotOnlyItsCode"],
              "E": ["ui/lm.py", "ui/build.py"]},
    "OI-16": {"C": ["tests/test_grounded.py:TheWeldRule", "tests/test_grounded.py:TheContestRule"],
              "E": ["engine/grammar.py"]},
    "OI-17": {"C": ["tests/test_fixtures.py"], "E": ["engine/region.py"]},
    "OI-18": {"C": ["tests/test_grounded.py:ThePromptIsWIREGrammarAndNothing"],
              "E": ["engine/grammar.py:BLOCKS"]},
    "OI-19": {"C": ["tests/test_bias_bytes.py:TheOperatorsBytesReachTheProposeCall",
                    "tests/test_bias_bytes.py:TheOperatorsBytesReachTheRenderCall",
                    "tests/test_bias_bytes.py:PlantedNormalizationIsRED",
                    "tests/test_bias_bytes.py:TheCorpusObjectsAreUNCHANGED"],
              "E": ["engine/perturb.py", "engine/region.py:Member",
                    "engine/region.py:render_region"]},
    "OI-20": {"C": ["tests/test_perturb.py"], "E": ["engine/perturb.py", "engine/hashing.py"]},
    "OI-21": {"C": ["tests/test_battery.py"], "E": ["engine/battery.py", "seed/BATTERY.json"]},
    "OI-22": {"C": ["tests/test_ui_browser.py:ThePageMustRUN",
                    "tests/test_ui_surface.py:TheBuildNamesItsMATERIALNotOnlyItsCode"],
              "E": ["ui/build.py", "tools/auditor.py"]},
    "OI-23": {"C": ["tests/test_control_sweep.py:TheSweepKnowsItsOwnBlindSpot",
                    "tests/test_access_gate.py:TheSeedEndpointMustACTUALLYRUN"],
              "E": ["engine/control_sweep.py"]},
    "OI-24": {"C": ["tests/test_nonempty.py:TheVocabularyItself",
                    "tests/test_nonempty.py:TheFinestGrainIsOnePAIR",
                    "tests/test_nonempty.py:EveryAdjudicationSiteCENSUSES",
                    "tests/test_nonempty.py:PlantedSuccessOnTheEmptySet"],
              "E": ["engine/nonempty.py:census", "engine/nonempty.py:clean",
                    "engine/adjudicate.py:Verdict", "engine/corpus_state.py"]},
    "OI-25": {"C": ["tests/test_ui_surface.py"], "E": ["engine/inbound.py"]},
    "OI-26": {"P": True},
    "OI-27": {"C": ["tests/test_battery.py"], "E": ["engine/battery.py:MIN_RATE_N"]},
    "OI-28": {"P": True},
    "OI-29": {"C": ["tests/test_fixtures.py:TheSubstrateRepairRetest"],
              "E": ["tests/test_fixtures.py:RETEST_PRE_REPAIR"]},
    "OI-30": {"P": True},
    "OI-31": {"C": ["tests/test_conversation.py:VerdictsCarryTheEraThatPairedThem",
                    "tests/test_medium.py:GlossesArePerMedium"],
              "E": ["engine/quarantine.py", "engine/conversation.py"]},
    "OI-32": {"C": ["tests/test_inlet.py"], "E": ["engine/inlet.py"]},
    "OI-33": {"C": ["tests/test_mz.py"], "E": ["engine/mz.py:WRITE_POINTS", "engine/aging.py"]},
    "OI-34": {"C": ["tests/test_mz.py"], "E": ["engine/mz.py:consider_site"]},
    "OI-35": {"C": ["tests/test_access_gate.py:TheCorpusIsNEVERInAGitTree",
                    "tests/test_push_gate.py:TheGateActuallyREFUSES"],
              "E": ["hooks/pre-push", "ui/server.py"]},
    "OI-36": {"C": ["tests/test_reflexivity.py:TheDetectorDETECTS",
                    "tests/test_reflexivity.py:TheAuditIsACensusAndObeysOI24",
                    "tests/test_reflexivity.py:TheREALCorpusIsClean"],
              "E": ["engine/reflexivity.py:audit", "engine/reflexivity.py:matches"]},
    "OI-37": {"C": ["tests/test_key_exposure.py:NoKeySHAPEIsCommitted",
                    "tests/test_key_exposure.py:NoREALKeyIsCommittedOrEverWas",
                    "tests/test_key_exposure.py:TheScratchpadIsOutsideTheTree"],
              "E": ["tests/test_key_exposure.py:shape_hits", ".gitignore"]},
    "OI-38": {"P": True},
    "OI-39": {"C": ["tests/test_fixtures.py"], "E": ["tools/auditor.py"]},
    "OI-40": {"P": True},
    "OI-43": {"C": ["tests/test_posture.py:TheConservativeDirectionINVERTS",
                    "tests/test_posture.py:ACorrectionRestampsWithAnERATRAIL"],
              "E": ["engine/posture.py"]},
    "OI-42": {"C": ["tests/test_claim.py:TheTwoByTwoIsForcedAndComplete",
                    "tests/test_mode.py:AllFourCellsAreMeaningful"],
              "E": ["engine/mode.py", "engine/claim.py"]},
    "OI-41": {"C": ["tests/test_claim.py:ThereIsNoThirdLift",
                    "tests/test_claim.py:TheLaunderingLock"],
              "E": ["engine/claim.py", "engine/mz.py:consider_site"]},
}


def statements() -> dict[str, str]:
    body = DOC.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"^\*\*(OI-\d+)\*\*\s+(.+?)(?=\n\n)", body, re.S | re.M):
        out[m.group(1)] = " ".join(m.group(2).split())[:400]
    return out


def resolves(ref: str) -> bool:
    """Does this site/control actually exist, at its symbol?"""
    path, _, symbol = ref.partition(":")
    p = REPO / path
    if not p.exists():
        return False
    if not symbol:
        return True
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except Exception:
        return symbol in p.read_text(encoding="utf-8")
    head = symbol.split(".")[0]
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.name == head:
            return True
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == head for t in node.targets):
            return True
        # ANNOTATED assignment. `BLOCKS: tuple[...] = (...)` is an AnnAssign, not an Assign,
        # and missing it reported a symbol that plainly exists as unresolvable — the resolver
        # itself failing the resolution check it performs.
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == head:
            return True
    return False


def build() -> dict:
    stmts = statements()
    entries, weak, unresolved = {}, [], []
    for oi in sorted(stmts, key=lambda k: int(k.split("-")[1])):
        spec = MAP.get(oi, {})
        e = [r for r in spec.get("E", [])]
        c = [r for r in spec.get("C", [])]
        bad = [r for r in e + c if not resolves(r)]
        unresolved += [f"{oi}: {r}" for r in bad]
        is_weak = not c
        if is_weak:
            weak.append(oi)
        entries[oi] = {"statement": stmts[oi], "enforcement_sites": e, "controls": c,
                       "process_only": is_weak, "unresolved": bad}
    return {"schema": "common-ground/oi-registry/v0",
            "note": ("Machine-readable per CONSTITUTION.md B1. An OI with no [C:] control is "
                     "WEAK and listed for mechanization; the auditor FAILS if any entry is "
                     "unresolvable, because a registry naming controls that do not exist is "
                     "the map-not-territory failure applied to the constitution itself."),
            "count": len(entries), "weak": weak, "unresolved": unresolved,
            "entries": entries}


if __name__ == "__main__":
    reg = build()
    OUT.write_text(json.dumps(reg, indent=1) + "\n", encoding="utf-8")
    print(f"{reg['count']} OI entries")
    print(f"WEAK (process-only, need mechanizing): {len(reg['weak'])} -> {', '.join(reg['weak'])}")
    print(f"UNRESOLVED references: {len(reg['unresolved'])}")
    for u in reg["unresolved"]:
        print("   ", u)
