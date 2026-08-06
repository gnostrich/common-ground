# CONTROL-SWEEP: triage of every source-reading control in the suite

> **THE LAW**, in the operator's words:
> *"A control that inspects source text instead of executing the path is testing the MAP, not the
> TERRITORY; any control asserting a runtime property must exercise the runtime."*

---

## 1. What this file is and how it was produced

Every test in the suite that reads a file's text — `.read_text()`, `open()`, `inspect.getsource()`,
`Path(...).read_text()`, a raw `git`/`node` shell-out against source, etc. — was pulled out and
classified one at a time against THE LAW above. Each control got exactly one of three verdicts:

- **MAP** — the control's own name/docstring frames a claim about what happens when code *runs*
  (a request is answered, a file is written, a function is invoked, a value is computed), but the
  assertion body only inspects the *text* of the implementation (`inspect.getsource`, a raw file
  read, a substring/position check) and never executes the path in question. This is a map read
  in place of a territory read — the canonical failure being a `404` grepped out of source next to
  a `403` that would actually ship.
- **SOURCE** — the claim genuinely is about the text: an absence-of-a-mechanism claim ("this module
  contains no tokenizer"), a documentation/manifest-sync claim ("the doc names the same three things
  the code enforces"), a self-test of a static-analysis tool whose entire job is reading source, or
  a read of an *artifact a real execution just produced* (not the module's source). Execution adds
  nothing to these; text is the only faithful instrument.
- **BORDERLINE** — the control's literal check is spelling-shaped, but either (a) the same behavioral
  claim is separately and genuinely exercised elsewhere in the suite, making this control a cheap,
  defeatable-in-isolation proxy riding alongside a real one, or (b) the runtime it would need to
  reach is genuinely hard or impossible to invoke from this repo (no JS toolchain, no Railway
  dry-run), and the source read is the best available stand-in, honestly labeled as such.

**Adversarial verification.** Every MAP verdict was then handed to a second, independent pass whose
only job was to try to *break* the verdict — find real behavioral coverage elsewhere, find that the
"runtime" claim was actually textual on inspection, or find that the proposed upgrade doesn't
actually work in this repo (missing dependency, wrong call site, etc.). This exists so that a
legitimate source-property guard doesn't get bulldozed into a "fix" it doesn't need, and so that a
genuine gap doesn't survive under a rejected-but-plausible-sounding upgrade. Of 20 initial MAP
verdicts, 16 were confirmed and 4 were refuted on reread; the 4 refutations are recorded below and
their controls reassigned to the bucket the adversarial pass actually justified.

---

## 2. COUNTS

| | Count |
|---|---|
| Total source-reading controls classified | **129** |
| SOURCE (classifier pass) | 85 |
| MAP (classifier pass) | 20 |
| BORDERLINE (classifier pass) | 24 |
| MAP verdicts submitted to adversarial verification | 20 / 20 |
| MAP verdicts **confirmed** | **16** |
| MAP verdicts **refuted** | 4 |

**Revised totals after verification:** 87 SOURCE, 26 BORDERLINE, **16 confirmed MAP** (87+26+16 = 129).

### The 4 refuted MAP verdicts, and where they actually belong

| File | Control | Refutation, in one line | Reassigned to |
|---|---|---|---|
| tests/test_access_gate.py | `test_no_endpoint_is_fetched_without_the_token_helper` | Only two `fetch(` sites exist in `ui/index.html`, both centralized in `post()`/`get()`, both already wired through `withToken()` — this is a genuine call-graph invariant, not a coincidental substring match; the one real gap (does `withToken()` itself do anything) is narrower than the original MAP framing implied. | BORDERLINE (closer to SOURCE) |
| tests/test_ui_surface.py | `test_one_act_in_the_javascript_too` | The runtime half of this claim (does clicking the button actually invoke `act()` for both retain states) is separately and genuinely exercised by `tests/test_ui_browser.py`'s Playwright-driven `test_every_render_function_is_invoked_on_some_live_path`. This control's real job — catching a second, dead `propose()`/`ask()` definition lying around in source — is legitimately textual. | SOURCE |
| tests/test_referee_sweep.py | `test_every_exemption_says_why_it_is_a_declared_grammar_or_our_own_text` | The control's actual claim is that every exemption *names* a legitimizing category, forcing documentation and human review of new exemptions — it never claims the underlying vocabulary IS closed. That's the SOURCE pattern ("the reason states X"), not MAP ("behavior X is true, checked by spelling"). A stronger, complementary AST-closure check is a valid addition, not a replacement. | SOURCE |
| tests/test_inbound.py | `InboundIsReadSideOnly.test_it_never_touches_the_tape` | `compile_input`/`land` take no `tape` parameter at all, and nothing in their reachable call graph does either — the "never touches the tape" claim is structurally equivalent to "this module contains no tokenizer" given the actual signatures. One real gap remains uncovered: a future call to `perturb.commit(..., tape=t)` from `inbound.py` wouldn't be caught by this text scan. | BORDERLINE (toward SOURCE) |

---

## 3. THE UPGRADE QUEUE — confirmed MAP controls

Sorted by severity, then file.

| # | File | Control | What it claims | Why it is the map | Upgrade shape | Severity |
|---|---|---|---|---|---|---|
| 1 | tests/test_access_gate.py | `TheDataChannelIsNarrowAndVERIFIED.test_the_endpoint_does_not_exist_without_the_token_variable` | With `CG_SEED_UPLOAD_TOKEN` unset, `POST /seed` returns 404 (not 403) — the upload surface must not exist to be discovered. | Asserts the substring `"404"` sits before `"bad seed token"` inside `inspect.getsource(Handler._seed)` — a text-position check, not an executed response. Would survive a `NameError`, an unreachable branch, or any refactor preserving textual order. | Delete the source-scan assertion outright. `TheSeedEndpointMustACTUALLYRUN.test_with_no_token_variable_the_endpoint_is_404` already boots a real `ThreadingTCPServer` with the var unset and asserts the live HTTP status — the upgrade already exists in the file. | HIGH |
| 2 | tests/test_access_gate.py | `TheDataChannelIsNarrowAndVERIFIED.test_a_digest_is_REQUIRED` | The `/seed` handler requires `X-Seed-Sha256` and rejects an upload missing it. | Greps `inspect.getsource(Handler._seed)` for `"X-Seed-Sha256"` and `"is required"` appearing *anywhere* in the method, not on the same reachable branch. No sibling test in the file ever omits this exact header. | POST to a live server with `X-Seed-Sha256` omitted, reusing `TheSeedEndpointMustACTUALLYRUN`'s own `_serve()`/`_post()` scaffolding; assert a real 400 with the message in the body. | HIGH |
| 3 | tests/test_access_gate.py | `TheDataChannelIsNarrowAndVERIFIED.test_the_write_is_atomic` | The seed write lands beside the target and is only renamed in after verification — no half-written upload is ever visible at the real path. | Greps `inspect.getsource(Handler._seed)` for the literal substrings `"mkstemp"` and `"os.replace"` appearing anywhere, in any order. Says nothing about what the real filesystem shows during a transfer. | `mock.patch("os.replace")` around a live-server POST; assert it is called exactly once with `(tmp_in_target_dir, target)` only after the digest check passes, and zero times on a wrong-digest POST. | HIGH |
| 4 | tests/test_boot.py | `TheSeedingPathMustACTUALLYSHIP.test_the_staging_directory_is_gitignored` | `seed_runs/` is actually ignored by git. | `assertIn("seed_runs/", gitignore_text)` — and `.gitignore` currently contains that exact substring *twice*: once as the real pattern, once inside a comment sentence. Deleting the real pattern would still pass. | Run `git check-ignore -v seed_runs/` as a subprocess and assert `returncode == 0` — the identical, already-working pattern used one file over in `tests/test_corpus_sources.py`. | HIGH |
| 5 | tests/test_faces.py | `AnAnchorIsOnlyAPrior.test_faces_module_creates_no_correspondence_and_touches_no_tape` | An anchor never creates a `Correspondence`, never calls `.propose()`, never invokes `Clamp()` at runtime. | Greps `inspect.getsource(engine.faces)` for three literal call spellings. No function in the module is ever called; an alias, a stored reference, or `getattr` dispatch would all defeat the grep while genuinely creating the forbidden side effect. | Patch `Correspondence`, `FastTape.propose`, and `Clamp` at their real definition modules; call `derive_faces`, `anchors_for_english`, `anchors_for_lean` for real against existing fixtures; assert each mock's `call_count == 0`. | HIGH |
| 6 | tests/test_faithfulness.py | `MeasuredShadowChannel.test_the_measured_defect_never_deflates_a_floor` | A measured shadow defect (`eps_measured`) never subtracts from the cold floor `measure()` computes — only the declared shadow does. | Strips whitespace from `inspect.getsource(measure)` and checks one literal expression substring plus the absence of `"eps_measured"` nearby. A semantics-preserving rename passes/fails independent of the real relationship. | Run the existing offline fixture once plain and once with `measured_shadow` mocked to a large, distinct value; assert the resulting floors are bit-identical while `eps_measured` differs. | HIGH |
| 7 | tests/test_ui.py | `TheProposerLedgerIsVisibleAndReadOnly.test_the_control_surface_writes_only_operational_fields` | `/proposer/control` cannot be used to set a tier, warrant, or promotion field — only the operational set. | AST-walks the branch for `setattr` targets and string constants against an allow-list. No `HTTPServer` is started, no request sent. A `for field in body: setattr(ctl, field, body[field])` refactor introduces zero new literal strings and sails through. | Start the real `HTTPServer` the file already uses elsewhere; POST a body mixing legitimate and forbidden fields; assert the forbidden fields never land in `Control.read()` and the re-fetched ledger's `tier` is unchanged. | HIGH |
| 8 | tests/test_ui_surface.py | `ThePagesScriptMustPARSE.test_every_function_the_page_calls_is_defined` | The `act()`-undefined-for-a-whole-deploy incident: every `onclick` handler the page calls has a matching, callable definition. | Regexes `onclick="fn("` names against the literal substring `"function fn("` in script text. Misses nested/shadowed definitions and `const fn = () => {}` arrow forms; matches inside comments/strings. | Build a minimal stub sandbox (`document`/`location`/`history`/`sessionStorage`/`fetch` no-ops), `vm.runInContext` the real extracted script, assert `typeof sandbox[name] === 'function'` for each `onclick` target — no new dependency needed, `vm` is a Node builtin. | HIGH |
| 9 | tests/test_ui_surface.py | `TheBuildIdentifiesItself.test_the_page_renders_it` | The page renders build/commit info: calls `renderBuild()`, shows "model served:" and warns "PIN DRIFT" on a served/pin mismatch. | Greps raw HTML/script text for three literal substrings. `renderBuild` is never called; a `NameError` or wrong-shape call before the DOM-write line leaves this green. | Stub `document.getElementById` in Node, call `renderBuild({model_drift:true,...})` directly, assert on the captured `innerHTML`; repeat with `model_drift:false` and assert the warning is absent. | HIGH |
| 10 | tests/test_ui_surface.py | `TheBuildNamesItsMATERIALNotOnlyItsCode.test_the_page_renders_the_material_line` | The page displays a "corpus material:" line and gates a staleness indicator on `b.snapshot.stale`. | Greps raw file text for two literal substrings; never confirms `renderBuild` reads the field, applies it to the right conditional, or that real values get interpolated. | Same Node + stub-`document` technique as row 9; call `renderBuild` with `snapshot.stale` true then false, assert the STALE marker appears/disappears in the captured output. | HIGH |
| 11 | tests/test_docstrings.py | `TypeCompatibilityIsAntiCorrelatedAcrossCharts.test_no_bounding_relation_type_filters_cross_chart` (line 308, `holes_by_declaration`/`holes_by_subtree`) | These functions must not type-filter cross-chart — a pair whose src/dst claim-forms disagree must survive. | Greps `inspect.getsource()` of both functions for the literal *absence* of one filter-expression string. A renamed/reordered/helper-ized filter defeats the check while breaking the real property; verified live that reintroducing a filter zeroes the real output from 2 pairs to 0. | Run the lean-`conditional`-vs-english-`assert` fixture (already proven live in this file) through `holes_by_declaration`/`holes_by_subtree`; assert the mismatched-type pair is present in the returned holes, not just that a string is absent from source. | MEDIUM |
| 12 | tests/test_docstrings.py | `TypeCompatibilityIsAntiCorrelatedAcrossCharts.test_no_bounding_relation_type_filters_cross_chart` (line 312, `enumerate_holes`) | `enumerate_holes` must pair across claim-forms cross-chart. | Greps `inspect.getsource(enumerate_holes)` for one literal loop-expression substring. Verified that no test in the suite ever feeds `enumerate_holes` a genuinely cross-type pair — the property is untested behaviorally anywhere. | Build two in-memory `Slot` objects of differing type across charts, call `enumerate_holes` directly, assert the pairing is present in the returned `Hole` set. | MEDIUM |
| 13 | tests/test_faithfulness.py | `GenerativeKeysAreContentAndSeedOnly.test_extraction_is_seeded_on_content_not_identity` | `DeterministicExtractor._spans` seeds its randomness from `doc.content_hash`, not from doc/extractor identity. | Greps `inspect.getsource(_spans)` for the string `"doc.content_hash"` — which, on inspection of the real code, is present only inside a comment describing a *rejected prior design*; the real seed variable is `slot_address`, never checked by this test. | Build two `Document`s with identical `doc_id`/`source` but different text, run the real offline `ingest`/`extract` pipeline (no network/key needed), assert the extracted output differs. | MEDIUM |
| 14 | tests/test_medium.py | `OrderCarriesNoSignal.test_the_salt_travels_on_the_compiled_record` | A real `CompiledInput` carries `order_salt` so a sheet can be reproduced/audited later. | `assertIn('order_salt', inspect.getsource(CompiledInput))` — a declared-but-unassigned or shadowed field on real instances would still pass. | Call the real `compile_input()` against the file's existing offline snapshot fixture; assert the returned object's `.order_salt` is a genuine populated token and that it reproduces the same ordering via `_relaxed_block`. Confirmed reachable and cheap (no network/corpus/key). | MEDIUM |
| 15 | tests/test_ui_surface.py | `TheBuildNamesItsMATERIALNotOnlyItsCode.test_age_comes_from_the_file_not_from_a_field_inside_it` | The reported snapshot age is computed from the file's real mtime, not a spoofable in-object field. | Greps `inspect.getsource(_snapshot_stamp)` for the literal substring `"getmtime"`. A correct reimplementation via `Path.stat().st_mtime` would fail; a broken one that calls `getmtime` and discards the result would pass. | Write a real temp file, `os.utime` it to a known offset, monkeypatch `SNAPSHOT_PATH` (pattern already used one test earlier in the same file), call `_snapshot_stamp`, assert the returned age tracks the real mtime within tolerance. | MEDIUM |
| 16 | tests/test_walk.py | `TheTwoErasAreNeverConflated.test_the_walk_tags_its_answers_with_a_distinct_relation` | When the walk records a region-era answer into the journal, the record is tagged `relation="region"`, keeping pairwise and region answers distinguishable in the ledger forever. | Greps `proposerd.py` source for the literal substring `relation="region"`. Nothing calls `record_ask` and nothing reads a produced record; the string could sit in dead code or a comment and still pass. | Call `Journal(tmp_path).record_ask(..., relation="region", ...)` directly — plain keyword arguments, no LM/transport needed — then read `journal.arrows[-1].relation == "region"` back through the real read/index API, not the raw file. | MEDIUM |

---

## 4. LEGITIMATE SOURCE CONTROLS

Grouped by file/class rather than listed one row per test method (there are 87 of them). Each row
names the source property the group defends so nobody "upgrades" a gate-10 docstring check, an
absence-of-mechanism check, or a checker's own self-test into a runtime check it structurally
cannot be.

| File / class | Controls (n) | Source property defended |
|---|---|---|
| test_access_gate.py — `ThePageCarriesTheTokenToEveryEndpoint` | 2 | Static markup lists exactly these `<option>` tags (dropdown contents ARE the file's text). |
| test_access_gate.py — `TheCorpusIsNEVERInAGitTree` | 1 | Tracked file bytes don't start with the pickle magic header — a byte-content claim, answered by reading bytes. |
| test_walk.py — `ThereIsNoPool` | 3 | Module contains no pool-mechanism identifiers; no import of the pairwise loop; a dataclass's field set IS its `AnnAssign` set. |
| test_walk.py — `AgingIsProposedNotSilentlyChosen` | 2 | Policy doc states these sentences; the aging mechanism has not been implemented anywhere in these two files. |
| test_walk.py — `TheWalkLogShowsWhereItWent` | 1 | Reads the artifact a real `log_step()` call just wrote — territory, not source. |
| test_boot.py — `AFreshVolumeIsSeeded` / `TheLiveJournalIsNeverOverWritten` / `OverwritingIsAnActNotAFlag` | 7 | All read the on-disk result of a real `seed_state()` call — genuine execution artifacts. |
| test_boot.py — `test_the_file_says_WHY_the_two_ignore_lists_differ` | 1 | The doc explains, in its own prose, why the two ignore lists diverge — a documentation-content claim. |
| test_continuous.py — `CompositionIsPrioritized` | 1 | `compose.py` holds no hand-written tuple-keyed dict; the AST shows data loaded from seed, not a literal. |
| test_continuous.py — `ProposerDisciplineIsStatic` (planted pair) | 2 | Self-tests of the AST-walking `check_proposer_discipline` detector itself, against synthetic corrupted source. |
| test_continuous.py — `TheLedgerIsCommittableAndCarriesNoCorpus` | 3 | Reads the real ledger file `export_redacted()` just wrote — a data-content claim on real output. |
| test_amendment.py — `TheAmendmentIsCanonical` | 4 | Doc-sync claims: the amendment states these sentences / names these moves / documents this protocol in full. |
| test_amendment.py — `EveryMechanismModuleCitesItsMove` | 5 | Self-tests of `check_move_citation` (itself a docstring-text checker) against planted real files. |
| test_amendment.py — `ADocstringMayNotDescribeACallGraphThatDoesNotExist` | 6 | The repo's real `check_claim_discipline`/`check_move_citation` run clean; classifier function self-tests on literal strings. |
| test_adapters_audit.py — `SeedLockRoundTrip` / `LexiconPins` / `RepoDocsAdapter` | 4 | All read artifacts (`SEED.lock`, `DECISIONS.json/.md`) that a real production call just wrote. |
| test_medium.py — `TermSelectionIsStructural` / `GroupsAreFIBERSNotClusters` / `HeadersAreREADNotComputed` | 3 | Absence-of-mechanism: no tokenizer, no similarity machinery, no summarisation call anywhere in the module's AST. |
| test_ui.py — `TheDiscipline` / `OpenRouterOnly` | 2 | No path to the API key from `log_message`; no Anthropic endpoint referenced anywhere in `lm.py`. |
| test_ui_surface.py — `TheSurfaceDepictsOnlyLiveMechanisms` (4) + `test_one_act_in_the_javascript_too` (reclassified) | 5 | What the served, unmodified-by-templating HTML/JS text literally depicts to a reader — the served bytes ARE the artifact. |
| test_corpus_sources.py — `ThePointerFileNeverEntersTheRepository` / `NoPathIsNamedInTheEngine` | 3 | Template declares exactly the kinds the loader accepts; retired env-var names and hardcoded paths are absent from source. |
| test_faithfulness.py — `test_an_unclassified_random_stream_is_caught` | 1 | Self-test of `check_generative_keys` (a source-scanning tool) against a fabricated module. |
| test_faces.py — `FacesDeriveOnlyThroughTheSeededRmap` | 1 | No similarity/fuzzy-matching vocabulary anywhere in `engine/faces.py`'s AST. |
| test_inlet.py — `OneWritePath` | 2 | The tape's entry list is appended to in exactly one syntactic place; self-test of the AST audit that proves it. |
| test_languages.py — `TheAuditNowChecksRouting` (3) / `TheContractTextIsTrue` (2) | 5 | Self-tests of the extension-literal detector; absence of a `register*` function contradicting the "no registration API" doc claim. |
| test_mz.py — `QuarantineAndDormantAreOneMechanism` | 1 | `engine/aging.py` does not itself define the three exclusion mechanisms that belong to quarantine — an ownership/definition-site claim. |
| test_probes.py — `TheChartRegistryIsAPlugInSeam` (partial) / `TheChartAuditCanDetectAReintroducedDefect` | 4 | No dispatch site names a chart literal; self-tests of `chart_plugin_audit`'s detector, end-to-end against real files. |
| test_referee_sweep.py — `NoRefereeDecidesByResemblance` / `ThePlantedShapesAreCaught` / `TheExemptionsCarryReasons` / `TheDeletedBagsStayDeleted` | 14 | AST shape-detector self-tests (tokenize/fold/bag-op shapes); registry-coverage claims; exemption reasons name a legitimizing category; deleted lexical machinery stays absent from the AST. |
| test_ui_browser.py — `test_the_page_defines_render_functions_at_all` | 1 | Sanity check that the extraction regex still matches something — guards the *meaningfulness* of the sibling runtime tests, not runtime behavior itself. |
| test_code_charts.py — `TheSeamHeld` | 1 | `router.py` contains no hardcoded chart/extension literal — an exhaustive absence claim over the file's AST. |
| test_correspondence.py — `TheOneWritePath` | 1 | Exhaustive claim that no function in the module bypasses `propose()` — only readable by reading every function, execution can't prove a universal negative like this. |
| test_perturb.py — `test_no_module_imports_the_deleted_loop` | 1 | Import-graph membership, checked correctly via AST (not grep) to dodge the use-vs-mention trap. |
| test_relax.py — `SilenceIsAResultNotADegradation` / `GateTenCatchesAMechanismClaim` | 6 | Import/file-existence absence claims; self-tests of `_mechanism_claims_in`/`check_claim_discipline` (themselves text classifiers) against literal and real-repo input. |

---

## 5. BORDERLINE

24 classifier-pass controls, plus the 2 refuted-MAP controls that landed here (marked `[ex-MAP]`).
For each: the reasoning, and what would settle it one way or the other.

| File | Control | Reasoning | What would settle it |
|---|---|---|---|
| test_access_gate.py | `test_the_seed_path_is_handled_before_the_json_body_parser` | Direct assertion (`src.index(...) < src.index(...)`) is pure MAP on its face, but the real invariant — routing happens before body-parsing — is separately proven by `TheSeedEndpointMustACTUALLYRUN` POSTing raw binary bytes to a live `/seed` and getting a clean non-crash response. | Send a body specifically shaped to crash a JSON parser (unpaired UTF-8, huge binary) directly to a live `/seed` and assert a clean non-500 — makes the claim independently load-bearing instead of inferred from source-text ordering. |
| test_access_gate.py | `test_the_ignore_rules_still_exclude_them` | Checks `.gitignore` text contains the expected patterns, but the *behavioral* claim (these paths never enter a git tree) is separately proven by sibling tests running real `git ls-files`. | Nothing further needed *if* the sibling `git ls-files` tests stay in place; if they're ever removed, this needs the same `git check-ignore` upgrade as row 4 of the queue. |
| test_walk.py | `CompositionCannotManufactureAnIllegalArrow.test_there_is_only_one_composition_rule` | "Is there a second implementation" is a structural claim, but it doubles as a guard against a specific historical defect (hub nodes manufacturing illegal arrows), and that behavior IS separately exercised by `test_planted_a_hub_implies_nothing_between_its_leaves` building a real region. | If the sibling behavioral test were ever deleted, this text search alone wouldn't catch a same-defect regression under a different string — worth a comment cross-referencing the two. |
| test_walk.py | `TheWalkLogShowsWhereItWent.test_a_step_is_appendable_as_one_json_object` | Reads file text via `read_text()`/`json.loads()`, but only *after* calling the real `log_step()` — reading the artifact of real execution, not a proxy for it. Borderline only because the mechanics look identical to the illegitimate source reads used elsewhere in the same file. | Nothing — already correct; flagged for contrast, not for fixing. |
| test_boot.py | `test_the_staging_directory_is_NOT_railwayignored` | Claim is genuinely about Railway's own upload behavior, which cannot be executed from this repo; checking `.railwayignore`'s literal lines is the closest available proxy and avoids the comment-false-positive failure mode seen in the gitignore test. | A Railway dry-run/build-manifest CLI command, if one is ever exposed, invoked against a throwaway project. |
| test_boot.py | `test_the_deploys_own_live_records_are_still_excluded` | Same reasoning as above — no local Railway-equivalent tool exists to fall back to. | Same as above — no honest upgrade exists today. |
| test_continuous.py | `ProposerDisciplineIsStatic.test_the_real_source_is_clean` | AST walk over source text for the "daemon cannot promote" claim, but the real runtime property (a promotable delta is refused) IS separately executed by `NothingIsPromotable.test_a_promotable_delta_is_refused_at_the_daemon`. This is a structural second line of defense, not a lone proxy. | Nothing needed — a legitimate belt-and-suspenders pairing. |
| test_amendment.py | `EveryMechanismModuleCitesItsMove.test_each_citation_names_a_question_the_protocol_defines` | Reimplements a slice of `check_move_citation`'s logic independently (its own regex) rather than calling the production function — could silently diverge from the real gate. | Replace the private reimplementation with a call into `check_move_citation` itself, or add an equality assertion between the two extraction methods. |
| test_adapters_audit.py | `LexiconPins.test_a_label_alone_is_not_a_pin` | The `DECISIONS_PATH.read_text()` call at the top re-asserts the test's own fixture (tautological), but the actual claim (`record_pin` raises `GateViolation` for a label-only pin) is genuinely executed elsewhere in the same test. | Drop the vacuous read; keep the `assertRaises`. |
| test_ui_surface.py | `ThePagesScriptMustPARSE.test_the_inline_script_parses` | Reads page text first, but the assertion shells out to `node --check` and checks the real parser's exit code — a genuine execution, just of a narrow claim ("this text parses"). | Nothing needed for its own claim; it does not (and needn't) prove anything beyond parseability. |
| test_corpus_sources.py | `ThePointerFileNeverEntersTheRepository.test_the_local_pointer_is_gitignored` | Doesn't read file contents at all — shells out to real `git check-ignore` and asserts on the real exit code, i.e. already executes the actual ignore engine. Borderline only in the sense it's the positive exemplar other rows should copy. | Nothing — already the target pattern; see rows above. |
| test_faithfulness.py | `GenerativeKeysAreContentAndSeedOnly.test_the_live_anthropic_arm_is_deleted_not_disabled` | Mixed test: `hasattr`/`assertRaises` half genuinely executes; the `read_text()` + `assertNotIn('anthropic.Anthropic(', ...)` half is checking a claim ("deleted, not disabled") that is *itself* about source-text presence, which execution cannot distinguish from "present but flagged off." | Nothing — the text half is correctly textual for its specific claim; no execution substitutes for "is this code physically absent." |
| test_controls.py | `StudentizationWasTriedAndRejected.test_the_rejected_repair_is_wired_to_nothing` | `getsource`-based "wired to nothing" claim is spelling, but the real decision path is separately pinned by `r.stats['decided_by'] == 'loop_permutation_null_pooled_loo'` executed elsewhere in the class. | Monkeypatch `studentized_loop_thresholds` with a call-counting wrapper and assert zero calls, for a direct non-invocation guarantee. |
| test_controls.py | `ExtractionWasNotContentDetermined.test_the_seed_material_is_now_the_content_hash` | Same pattern — `getsource` grep for the new seeding string, but the class's first test already executes `ingest()` on relabelled duplicates and proves bit-identical extraction behaviorally. | Drop the getsource assertion, or mirror the old-seeding regression test's direct-call pattern for the new seeding. |
| test_probes.py | `P8ProvenanceWalker.test_every_delta_is_fully_provenanced_and_no_key_is_identity_keyed` | The "no key reads identity" half is enforced via a source-scanning manifest/AST check (`check_generative_keys`), not by actually varying identity and observing invariance — but `P2RelabelAndReorderInvariance` in the same file does exactly that at the whole-ledger level. | Fold a per-site "`DRNG(evidence_a) == DRNG(evidence_b_relabelled)`" assertion into this test rather than relying solely on the manifest. |
| test_probes.py | `TheChartRegistryIsAPlugInSeam.test_the_chart_plugin_audit_now_passes` | Genuinely mixed: `manifest_only_possible` really calls `nu()`/`route()`; `blocking_sites` is an AST scan — but the latter's claim ("no dispatch site hardcodes a chart") is intrinsically textual, so both halves are the right check type. | Nothing needed. |
| test_referee_sweep.py | `TheDeletedBagsStayDeleted.test_the_conversation_keyword_bag_is_gone_with_its_stoplist` | The overall claim is legitimately textual, but one of its two checks is a brittle raw substring match (`_STOP = frozenset`) rather than the AST-node check the sibling half uses. | Replace the substring check with an AST scan for an `Assign` whose target id is `_STOP`, mirroring the technique already used in the very next test. |
| test_ui_browser.py | `ThePageMustRUN.test_a_planted_missing_element_reference_is_caught` | Genuinely both: the `assertIn` half checks the test's own plant landed (legitimate SOURCE self-check); the `p.errors`/frozen-header half runs a real Chromium session against the broken fixture (genuine execution). | Nothing — correctly designed. |
| test_ui_browser.py | `NoRenderFunctionIsDEAD.test_every_render_function_is_invoked_on_some_live_path` | Source read only enumerates *which* names to watch; the pass/fail comes from real browser instrumentation across all three live paths. | Nothing — correctly designed; source is the enumerator, runtime is the verifier. |
| test_ui_browser.py | `test_a_planted_dead_render_function_is_caught` | Same shape as above — source builds the candidate-name list, a real Chromium session decides the verdict. | Nothing needed. |
| test_ui_browser.py | `test_every_function_named_in_an_onclick_exists_at_runtime` | Regex over markup only extracts *which* names to check; `typeof window[name]` is evaluated against a real loaded page. | Nothing needed. |
| test_correspondence.py | `Gate8AppliesToCorrespondenceClaims.test_the_static_span_check_is_green_with_the_correspondence_path_present` | The docstring claim is behavioral ("value derives from own content"), checked via a static AST taint-scan, but sibling tests in the same class construct real claims and assert own-content determinism at runtime. | Build two claims with identical own-content but different ambient document context, assert computed slots are byte-identical — exercises the value computation directly instead of the AST shape of the code that computes it. |
| test_mz.py | `AdmissionCarriesItsEvidence.test_it_round_trips_through_the_journal` | Reads file text via `read_text()`/`json.loads()`, but only after `record_admission()` genuinely wrote it — reading a real execution's output, not the module's source. | Replace the raw jsonl parse with a `Journal.read()`/replay API if one exists, purely to remove the surface resemblance to a source-inspection anti-pattern. |
| test_languages.py | `TheAuditNowChecksRouting.test_the_live_router_is_clean` | Bundles a pure source claim (no extension literal in `router.py`) with a genuinely executed one (`routing_reaches()` actually calls `route()` and compares the destination) in the same assertion set. | Nothing needed — the executing half is already present. |
| **[ex-MAP]** test_access_gate.py | `test_no_endpoint_is_fetched_without_the_token_helper` | Only two `fetch(` sites exist in the page, both centralized and already wired through `withToken()` — a genuine, narrow call-graph invariant. The one real gap: nothing proves `withToken()` itself does anything (a no-op would still pass). | Source-check `withToken()`'s own body for a reference to the token constant and query-param assembly — closes the no-op loophole without needing a browser/JS toolchain this repo doesn't have. |
| **[ex-MAP]** test_inbound.py | `InboundIsReadSideOnly.test_it_never_touches_the_tape` | `compile_input`/`land` take no `tape` parameter and nothing in their call graph does either — today this is structurally equivalent to a no-tokenizer-style absence claim. The uncovered vector: a future call to `perturb.commit(..., tape=t)` from `inbound.py`. | Extend the source check to also flag any call to a name bound to `perturb.commit`; as a complementary executing guard, run `land`/`compile_input` against a real `FastTape` and assert its entry count is unchanged before/after. |

---

## 6. WHAT THIS SWEEP CANNOT SEE

This sweep classifies controls that read *source*. It says nothing about controls that correctly
execute the runtime but against a fixture too thin to represent what production actually hands the
code. That is a different failure class, invisible to a MAP-vs-TERRITORY sweep by construction —
the control passed the "did you run it" test and still proved nothing, because what it ran was not
representative. Three known instances surfaced elsewhere in this session:

1. **A stub with no `id` attribute that took a fallback branch.** The test executed real code
   against a real object — but the object was a hand-rolled stand-in missing an attribute the
   production object always has, so the code path exercised was the defensive fallback, not the
   path production actually takes on every real call.
2. **A bound method that serialised as a method.** Execution happened, output was inspected — but
   the output being inspected was a `<bound method ...>` repr, not the value a real serialization
   path would have produced, because the fixture hadn't been called down to a plain value first.
3. **A source scan standing in for an HTTP request**, inside a test whose other assertions genuinely
   execute — i.e. a MAP violation hiding *inside* an otherwise-legitimate executing test, one
   assertion at a time, rather than as the whole control's verdict.

A sweep built to answer "did this control read text instead of running the path" cannot also answer
"did this control run the path against something real." Those are orthogonal audits. Treat a clean
result here as ruling out one specific failure mode, not as a certificate that every executing
control in the suite is measuring the real thing.
