"""The router seam: routing is manifest-driven, and the audit can prove it isn't.

`chart_plugin_audit` reported PASS for two weeks while `route()` decided Lean with
`name.endswith(".lean")`. Addressing was declarative, routing was compiled in, and the audit
only measured the first — so a chart could be named, tagged, normalized, classified and
segmented and still have nothing reach it. These controls cover the half that was missing,
and each is planted against.
"""

from __future__ import annotations

import ast
import shutil
import tempfile
import unittest
from pathlib import Path

from engine import EngineError
from engine.chart_plugin_audit import audit_routing, routing_reaches, verdict
from engine.constants import REPO_ROOT
from engine.languages import CHART, CLASSIFY, REFERENCE, SHELF, extension_of, rule_for, rules
from engine.router import route


class TheManifestDecidesRouting(unittest.TestCase):
    def test_lean_enters_by_manifest_row_not_by_a_literal(self):
        self.assertEqual(rule_for("repo||a.lean").cls, CHART)
        self.assertEqual(rule_for("repo||a.lean").chart, "lean")
        self.assertEqual(route("repo||a.lean", "theorem t : True := trivial").destination,
                         "lean")

    def test_prose_extensions_are_classified_by_content(self):
        self.assertEqual(rule_for("repo||a.md").cls, CLASSIFY)
        self.assertEqual(route("repo||a.md", "The cone is positive.").destination, "english")

    def test_a_held_language_is_counted_not_walked_past(self):
        """A language with no chart must SAY so, with a reason, not vanish silently.

        `.py` was the example until the repo-intake rebase gave it a chart; `.go` carries the
        case now, and that swap is the point — the class is what matters, not the extension.
        """
        self.assertEqual(rule_for("repo||m.go").cls, REFERENCE)
        got = route("repo||m.go", "package main\nfunc main() {}\n")
        self.assertEqual(got.destination, "shelf")
        self.assertIn("reference-tier", got.reason)
        self.assertIsNone(got.document, "a held language must not reach an extractor")

    def test_python_now_enters_its_own_chart_by_manifest_row(self):
        """The seam, exercised: a chart added by manifest + behaviors, routed with NO edit
        to engine/router.py."""
        self.assertEqual(rule_for("repo||m.py").chart, "python")
        self.assertEqual(route("repo||m.py", "def f():\n    return 1\n").destination, "python")

    def test_a_filename_rule_wins_over_its_extension(self):
        self.assertEqual(rule_for("repo||package-lock.json").cls, SHELF)
        self.assertEqual(rule_for("repo||Makefile").cls, REFERENCE)

    def test_an_undeclared_extension_is_shelved_not_read_as_prose(self):
        self.assertEqual(rule_for("repo||thing.qqq").cls, SHELF)

    def test_binary_and_config_are_shelved_by_manifest(self):
        self.assertEqual(rule_for("repo||x.png").cls, SHELF)
        self.assertEqual(route("repo||x.png", "binary").destination, "shelf")

    def test_the_default_is_declared_in_the_manifest_not_in_code(self):
        self.assertIn("*", rules(), "the '*' row is what makes the default auditable")
        self.assertEqual(rules()["*"].cls, SHELF, "an undeclared extension is not prose")
        self.assertEqual(rules()[""].cls, CLASSIFY, "no extension at all: content decides")
        # a chat message id has no extension and must behave exactly as it did before
        self.assertEqual(route("claude||3f2a-11bb:7", "A claim about the cone.").destination,
                         "english")

    def test_extension_parsing_cannot_be_fooled_by_a_uuid_or_a_dotted_directory(self):
        self.assertEqual(extension_of("claude||3f2a-11bb-cc:7"), "")
        self.assertEqual(extension_of("repo||src.v2/notes"), "")
        self.assertEqual(extension_of("repo||a/b.c/d.lean"), ".lean")
        self.assertEqual(extension_of("repo||File.LEAN"), ".lean")
        self.assertEqual(extension_of("repo||x.lean#doc:foo"), ".lean")


class TheManifestIsValidated(unittest.TestCase):
    def test_a_row_naming_an_undeclared_chart_is_refused(self):
        """PLANTED: a manifest that could route to a chart which does not exist."""
        import engine.languages as mod

        original = mod.LANGUAGES_PATH
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "LANGUAGES.json").write_text(
                '{"rules":[{"ext":".zz","class":"chart","chart":"klingon"},'
                '{"ext":"*","class":"classify"}]}', encoding="utf-8")
            mod.LANGUAGES_PATH = tmp / "LANGUAGES.json"
            mod.rules.cache_clear()
            with self.assertRaises(EngineError) as ctx:
                mod.rules()
            self.assertIn("klingon", str(ctx.exception))
        finally:
            mod.LANGUAGES_PATH = original
            mod.rules.cache_clear()
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_manifest_with_no_default_row_is_refused(self):
        import engine.languages as mod

        original = mod.LANGUAGES_PATH
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "LANGUAGES.json").write_text(
                '{"rules":[{"ext":".lean","class":"chart","chart":"lean"}]}', encoding="utf-8")
            mod.LANGUAGES_PATH = tmp / "LANGUAGES.json"
            mod.rules.cache_clear()
            with self.assertRaises(EngineError) as ctx:
                mod.rules()
            self.assertIn("'*' row", str(ctx.exception))
        finally:
            mod.LANGUAGES_PATH = original
            mod.rules.cache_clear()
            shutil.rmtree(tmp, ignore_errors=True)


class TheAuditNowChecksRouting(unittest.TestCase):
    """The hole that let the audit pass while routing was hardcoded."""

    def test_the_live_router_is_clean(self):
        self.assertEqual(audit_routing(), [], "an extension literal is deciding routing")
        self.assertTrue(verdict()["routing_is_declarative"])
        self.assertTrue(verdict()["manifest_routes_to_lean"])

    def _planted(self, edit):
        root = Path(tempfile.mkdtemp())
        (root / "engine").mkdir()
        src = (REPO_ROOT / "engine" / "router.py").read_text(encoding="utf-8")
        (root / "engine" / "router.py").write_text(edit(src), encoding="utf-8")
        try:
            return audit_routing(root)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_reintroduced_extension_literal_makes_it_red(self):
        """PLANTED: exactly the line this repair removed."""
        found = self._planted(lambda s: s.replace(
            "    rule = rule_for(name)",
            '    is_lean_file = name.endswith(".lean")\n    rule = rule_for(name)'))
        self.assertTrue(found, "the reintroduced `.lean` literal was not caught")
        self.assertIn(".lean", found[0].hardcodes)
        self.assertEqual(found[0].severity, "dispatch")

    def test_a_literal_for_a_DIFFERENT_extension_is_also_caught(self):
        """The check is shaped to the FORM, not to the one extension that was wrong."""
        found = self._planted(lambda s: s.replace(
            "    rule = rule_for(name)",
            '    if name.endswith(".py"):\n        pass\n    rule = rule_for(name)'))
        self.assertTrue(found, "a new hardcoded extension would go unnoticed")
        self.assertIn(".py", found[0].hardcodes)

    def test_a_literal_inside_a_docstring_is_not_a_false_positive(self):
        found = self._planted(lambda s: s.replace(
            '"""Ingestion routing',
            '"""Ingestion routing (this mentions .lean and .py in prose)'))
        self.assertEqual(found, [], "a docstring mention must not trip the check")

    def test_declarative_source_that_routes_nothing_still_fails(self):
        """PLANTED-shaped: no literals AND no routing would pass an AST-only check."""
        import engine.languages as mod

        original = mod.LANGUAGES_PATH
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "LANGUAGES.json").write_text(
                '{"rules":[{"ext":"*","class":"classify"}]}', encoding="utf-8")
            mod.LANGUAGES_PATH = tmp / "LANGUAGES.json"
            mod.rules.cache_clear()
            ok, why = routing_reaches("lean")
            self.assertFalse(ok, "a manifest routing nothing to lean must not report reachable")
            self.assertIn("no LANGUAGES.json row", why)
        finally:
            mod.LANGUAGES_PATH = original
            mod.rules.cache_clear()
            shutil.rmtree(tmp, ignore_errors=True)


class TheContractTextIsTrue(unittest.TestCase):
    """CHARTS.json claimed 'three registered functions'. There is no registration API."""

    def test_the_behavior_tables_are_dict_literals_and_the_note_says_so(self):
        import json

        note = json.loads((REPO_ROOT / "seed" / "CHARTS.json").read_text())["note"]
        self.assertIn("DICT LITERALS", note)
        self.assertIn("NO registration API", note)
        self.assertIn("LANGUAGES.json", note)

        for rel, table in (("engine/normalize.py", "_NORMALIZERS"),
                           ("engine/normalize.py", "_CLASSIFIERS"),
                           ("engine/extract.py", "_SEGMENTERS")):
            tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"), filename=rel)
            literal = any(
                isinstance(n, (ast.Assign, ast.AnnAssign))
                and any(getattr(t, "id", "") == table
                        for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))
                and isinstance(getattr(n, "value", None), ast.Dict)
                for n in ast.walk(tree))
            self.assertTrue(literal,
                            f"{rel}:{table} is no longer a dict literal — if a registration "
                            "API now exists, the CHARTS.json note must be corrected again")

    def test_no_register_function_exists_to_contradict_the_note(self):
        for rel in ("engine/normalize.py", "engine/extract.py", "engine/charts.py"):
            src = (REPO_ROOT / rel).read_text(encoding="utf-8")
            tree = ast.parse(src, filename=rel)
            names = [n.name for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            self.assertFalse([n for n in names if n.startswith("register")],
                             f"{rel} defines a register* function; the note must be updated")


if __name__ == "__main__":
    unittest.main()
