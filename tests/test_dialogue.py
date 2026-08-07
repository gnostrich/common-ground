"""B2's six pre-registered controls, from seed/DIALOGIC.md — written before any code existed.

The spec listed them as "all planted, none written". They are written here against the same
numbering, so a reader can hold the spec beside the file and check that the thing built is the
thing designed. That is OI-28's shape: reasoning designs, measurement tripwires.

  1. No arrow from words.
  2. Testimony never grounds.
  3. Turns come from structure.
  4. The budget binds.
  5. Trajectory kept, counted correctly.
  6. The daemon is untouched.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from engine.dialogue import (ARROW, DIALOGUE_KINDS, TESTIMONY, TURN_BUDGET, Dialogue,
                             Proposal, Turn, arrows_from, converse, implied_unaddressed,
                             interrogate)

REPO = Path(__file__).resolve().parent.parent
MODULE = REPO / "engine" / "dialogue.py"

CITABLE = {1, 2, 3, 7, 12}


def _compiled(citations):
    return {"citations": citations}


class C1_NoArrowFromWords(unittest.TestCase):
    """Spec control 1. The whole protocol rests on this and nothing else does the work."""

    def test_persuasive_prose_with_no_coordinates_yields_NOTHING(self):
        for prose in (
            "These two are obviously the same claim, as anyone can see.",
            "Certified positivity clearly refines the general positivity result.",
            "I am highly confident that object one is an instance of object seven.",
            "same_claim refines instance_of bears_on",          # the tokens, no coordinates
        ):
            with self.subTest(prose=prose[:40]):
                self.assertEqual(arrows_from(prose, CITABLE), [])

    def test_an_arrow_needs_BOTH_coordinates_and_a_kind(self):
        self.assertEqual(arrows_from("[1] and [7] are related.", CITABLE), [])
        self.assertEqual(arrows_from("[1] refines [7]", CITABLE), [],
                         "without the arrow syntax this is prose about a relation")
        self.assertTrue([p for p in arrows_from("[1] -refines-> [7]", CITABLE) if p.ok])

    def test_the_extractor_contains_NO_similarity_machinery(self):
        """AST sweep, as the spec ordered. No tokenizer, no scoring, no fluency judgement —
        and this reads the parsed module rather than grepping text, so a mention inside a
        docstring explaining the prohibition does not trip it."""
        tree = ast.parse(MODULE.read_text())
        banned = {"lower", "casefold", "split", "difflib", "SequenceMatcher", "ratio",
                  "similarity", "token", "tokenize", "stem", "embed", "score"}
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in banned:
                hits.append(node.attr)
            if isinstance(node, ast.Name) and node.id in banned:
                hits.append(node.id)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in getattr(node, "names", []):
                    if a.name.split(".")[0] in banned:
                        hits.append(a.name)
        self.assertEqual(hits, [], f"resemblance machinery in the dialogic extractor: {hits}")

    def test_a_PLANTED_word_reader_would_be_caught(self):
        """The sweep's own control: it must fire on the shape it hunts."""
        tree = ast.parse("def f(prose):\n    return 'refines' in prose.lower()\n")
        self.assertTrue(any(isinstance(n, ast.Attribute) and n.attr == "lower"
                            for n in ast.walk(tree)))


class C2_TestimonyNeverGrounds(unittest.TestCase):
    """Spec control 2. Zero warrant is the ABSENCE of a tier, not a low one."""

    def test_testimony_is_not_a_warrant_tier(self):
        """A testimony comparable to EXTRACTION on the poset is a testimony that could be
        promoted, and the point is that it cannot be."""
        from engine.types import WarrantTier

        names = {t.name for t in WarrantTier}
        self.assertNotIn("TESTIMONY", names)
        self.assertNotIn(TESTIMONY.upper(), names)

    def test_a_turn_records_its_prose_with_NO_warrant(self):
        rec = Turn(n=1, ask="q", prose="the medium said this").as_record()
        self.assertEqual(rec["record_kind"], TESTIMONY)
        self.assertIsNone(rec["warrant"], "testimony carries no warrant at all")

    def test_the_prose_is_KEPT_because_the_trajectory_matters(self):
        """Zero warrant is not a reason to discard it."""
        rec = Turn(n=1, ask="q", prose="what the medium said").as_record()
        self.assertEqual(rec["prose"], "what the medium said")

    def test_the_module_confers_no_tier_anywhere(self):
        body = MODULE.read_text()
        for tier in ("EXTRACTION", "AUTHORSHIP", "KERNEL", "CI_RECEIPT", "PREMINTED"):
            self.assertNotIn(f"WarrantTier.{tier}", body,
                             "the dialogic path must not confer a tier on anything")


class C3_TurnsComeFromStructure(unittest.TestCase):
    """Spec control 3. Never 'that answer seemed thin, ask again'."""

    def test_interrogate_CANNOT_see_the_prose(self):
        """Impossibility by construction: the reply is not a parameter, so no future edit can
        quietly start reading it without changing the signature."""
        import inspect

        params = set(inspect.signature(interrogate).parameters)
        self.assertEqual(params, {"compiled", "asked"})
        for forbidden in ("prose", "reply", "answer", "text", "turn"):
            self.assertNotIn(forbidden, params)

    def test_it_asks_about_an_implied_pair_nobody_has_measured(self):
        c = _compiled([{"n": 1}, {"n": 7},
                       {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        q = interrogate(c, asked=set())
        self.assertIn("[1]", q)
        self.assertIn("[7]", q)
        self.assertIn("Composition implies", q)

    def test_it_does_not_re_ask_a_pair_already_put(self):
        c = _compiled([{"n": 1}, {"n": 7},
                       {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        self.assertEqual(interrogate(c, asked={(1, 7)}), "",
                         "asking the same pair twice is an interrogation loop, not a measure")

    def test_it_falls_through_to_a_CONTESTED_object(self):
        c = _compiled([{"n": 3, "contested": True}])
        self.assertIn("[3]", interrogate(c, asked=set()))
        self.assertIn("more than one value", interrogate(c, asked=set()))

    def test_it_returns_EMPTY_rather_than_inventing_a_question(self):
        """No structure left to ask about ends the dialogue. Manufacturing one more turn
        because the budget allows it is the candidate list with better manners."""
        self.assertEqual(interrogate(_compiled([{"n": 1}]), asked=set()), "")


class C4_TheBudgetBinds(unittest.TestCase):
    """Spec control 4. An unbounded interrogation is what Q5 deleted once already."""

    def test_the_budget_is_declared_and_small(self):
        self.assertIsInstance(TURN_BUDGET, int)
        self.assertGreaterEqual(TURN_BUDGET, 1)
        self.assertLessEqual(TURN_BUDGET, 8, "a large budget is an unbounded loop with a cap")

    def test_the_budget_carries_a_provenance_entry(self):
        """Every constant argues for itself or confesses. engine/constants_sweep.py enforces
        this; asserting it here means the dialogue lane fails on its own terms first."""
        import json

        d = json.loads((REPO / "seed" / "CONSTANT_PROVENANCE.json").read_text())
        self.assertIn("TURN_BUDGET", d["constants"])


class C5_TrajectoryKeptCountedCorrectly(unittest.TestCase):
    """Spec control 5. The unit is the distinct claim, not the utterance."""

    def test_five_restatements_are_ONE_claim_and_FIVE_records(self):
        prose = " ".join(["[1] -same_claim-> [7]."] * 5)
        ps = arrows_from(prose, CITABLE, turn=2)
        self.assertEqual(len(ps), 5, "every utterance is recorded")
        self.assertEqual(sum(1 for p in ps if p.ok), 1, "they are one claim")
        self.assertEqual([p.void for p in ps[1:]], ["restated in this turn"] * 4)

    def test_the_record_says_WHICH_it_is_counting(self):
        t = Turn(n=2, ask="q", proposals=arrows_from("[1] -same_claim-> [7]. " * 3, CITABLE))
        rec = t.as_record()
        self.assertEqual(len(rec["arrows"]), 3)
        self.assertEqual(rec["resolved"], 1)
        self.assertEqual(rec["void"], 2)

    def test_every_proposal_carries_its_TURN(self):
        """Both survive with their turn recorded — a revision at turn 6 does not erase turn 2."""
        for p in arrows_from("[1] -refines-> [7]", CITABLE, turn=6):
            self.assertEqual(p.turn, 6)

    def test_a_direction_flip_is_a_DIFFERENT_record_but_the_same_pair(self):
        """`refines` is directed, so [1]->[7] and [7]->[1] are different assertions. The
        dedupe is on the unordered pair AND the kind, so the second is a restatement of the
        pair — recorded, not silently dropped — and the operator can see both."""
        ps = arrows_from("[1] -refines-> [7]. [7] -refines-> [1].", CITABLE)
        self.assertEqual(len(ps), 2)
        self.assertEqual(sum(1 for p in ps if p.ok), 1)


class C6_TheDaemonIsUntouched(unittest.TestCase):
    """Spec control 6. Two paths, and only the interactive one is conversational."""

    def test_no_unattended_module_imports_the_dialogue(self):
        for rel in ("engine/continuous.py", "engine/walk.py", "engine/propose_correspondence.py",
                    "proposerd.py"):
            p = REPO / rel
            if not p.exists():
                continue
            with self.subTest(module=rel):
                self.assertNotIn("dialogue", p.read_text(),
                                 f"{rel} is on the unattended path and must never run a dialogue")

    def test_the_walks_region_prompt_carries_no_dialogic_grammar(self):
        from engine.region import REGION_SYSTEM

        self.assertNotIn("-refines-> [", REGION_SYSTEM,
                         "the coordinate wire must not learn the prose form")


class TheLoopAndTheCollapse(unittest.TestCase):
    """Piece 2. The last turn IS the answer; there is no render call.

    THE COLLAPSE IS A COST FACT, not only a design one: the two-port split spent two calls on
    every question. A question the graph has nothing to interrogate about now spends ONE, and
    that one call's prose is the answer. Anything that reintroduces a second unconditional
    call has undone the ruling, so the call COUNT is asserted, not just the shape.
    """

    def _field(self, citations=None, compiled="FIELD"):
        return {"compiled": compiled,
                "citations": citations or [{"n": 1, "slot": "s1"}, {"n": 7, "slot": "s7"}]}

    def _transport(self, replies):
        seen = []

        def t(system, user):
            seen.append({"system": system, "user": user})
            return (replies[len(seen) - 1] if len(seen) <= len(replies) else replies[-1]), {}

        return t, seen

    def test_a_question_with_nothing_to_interrogate_costs_ONE_call(self):
        t, seen = self._transport(["The cone is positive [1]."])
        d = converse("is the cone positive", self._field(), t)
        self.assertEqual(len(seen), 1, "the two-port split spent two; this must spend one")
        self.assertEqual(len(d.turns), 1)
        self.assertEqual(d.answer, "The cone is positive [1].")
        self.assertEqual(d.stopped, "the graph had nothing left to ask")

    def test_the_last_turn_IS_the_answer(self):
        t, _ = self._transport(["first [1].", "second [1].", "third [1]."])
        d = converse("q", self._field(), t)
        self.assertEqual(d.answer, d.turns[-1].prose)

    def test_an_interrogation_turn_is_FOLLOWED_by_an_answer_turn(self):
        """An interrogation turn answers the interrogation. The operator asked something else,
        so the dialogue must not hand back the reply to its own follow-up as the answer."""
        field = self._field([{"n": 1, "slot": "s1"}, {"n": 7, "slot": "s7"},
                             {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        t, seen = self._transport(["turn one [1].", "turn two [7].", "THE ANSWER [1]."])
        d = converse("the operator's question", field, t)
        self.assertGreaterEqual(len(d.turns), 2)
        self.assertEqual(d.turns[-1].ask, "the operator's question")
        self.assertNotIn("Composition implies", d.turns[-1].ask)
        self.assertEqual(d.answer, d.turns[-1].prose)

    def test_the_interrogation_is_the_ENGINE_speaking_and_is_recorded_as_the_ask(self):
        field = self._field([{"n": 1, "slot": "s1"}, {"n": 7, "slot": "s7"},
                             {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        t, _ = self._transport(["a [1].", "b [7].", "c [1]."])
        d = converse("q", field, t)
        mid = [x for x in d.turns if x.ask != "q"]
        self.assertTrue(mid, "no interrogation turn ran")
        self.assertIn("Composition implies", mid[0].ask)

    def test_the_budget_BINDS_even_when_the_graph_keeps_asking(self):
        """Spec control 4, at the loop. A graph with an endless supply of unasked pairs must
        still stop — the budget is the ceiling, not a suggestion."""
        cites = [{"n": i, "slot": f"s{i}"} for i in range(1, 20)]
        cites += [{"n": 100 + k, "kind": "arrow", "joins": [k, k + 1]} for k in range(1, 15)]
        t, seen = self._transport(["x [1]."])
        d = converse("q", {"compiled": "F", "citations": cites}, t, budget=3)
        self.assertLessEqual(len(d.turns), 3 + 1, "budget + the one answer turn, never more")
        self.assertEqual(d.stopped, "budget")
        self.assertLessEqual(len(seen), 4)

    def test_a_budget_of_one_still_answers(self):
        t, seen = self._transport(["only [1]."])
        d = converse("q", self._field(), t, budget=1)
        self.assertEqual(len(seen), 1)
        self.assertEqual(d.answer, "only [1].")

    def test_the_FIELD_SETTLES_between_turns(self):
        """The settle callback receives every resolved proposal so far, and the freshly
        compiled field is what the next turn is put against."""
        field = self._field([{"n": 1, "slot": "s1"}, {"n": 7, "slot": "s7"},
                             {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        got = []

        def settle(props):
            got.append(len(props))
            return {"compiled": f"SETTLED-{len(props)}", "citations": field["citations"],
                    "relaxation": {"moved": 5}}

        t, seen = self._transport(["[1] -refines-> [7] and so on [1].", "b [7].", "c [1]."])
        d = converse("q", field, t, settle=settle)
        self.assertTrue(got, "the field never settled between turns")
        self.assertEqual(d.turns[0].moved, 5, "the turn must record what moved")
        self.assertIn("SETTLED-", seen[1]["user"],
                      "the next turn must be put against the SETTLED field, not the old one")

    def test_no_settlement_runs_when_no_arrow_RESOLVED(self):
        """Settling on nothing is a wasted relaxation and a census over an empty population."""
        got = []
        t, _ = self._transport(["prose with no coordinates at all."])
        converse("q", self._field(), t, settle=lambda p: got.append(1))
        self.assertEqual(got, [])

    def test_the_record_names_RECORDS_and_CLAIMS_separately(self):
        t, _ = self._transport(["[1] -refines-> [7]. [1] -refines-> [7]. [1] -refines-> [7]."])
        r = converse("q", self._field(), t).as_record()
        self.assertEqual(r["records"], 3)
        self.assertEqual(r["resolved_records"], 1)
        self.assertEqual(r["distinct_claims"], 1)

    def test_distinct_claims_spans_the_WHOLE_dialogue_not_one_turn(self):
        """A medium restating one arrow across five TURNS contributed one claim. The per-turn
        dedupe cannot see across turns, so the dialogue-level count is the one that must."""
        field = self._field([{"n": 1, "slot": "s1"}, {"n": 7, "slot": "s7"},
                             {"n": 9, "kind": "arrow", "joins": [1, 7]}])
        t, _ = self._transport(["[1] -refines-> [7] a."] * 5)
        d = converse("q", field, t)
        self.assertGreater(len(d.resolved), 1, "several turns each resolved it")
        self.assertEqual(len(d.claims), 1, "and it is one claim")


class ThePromptGrewLEGALLY(unittest.TestCase):
    """FLAG 1's ruling: the arrow form is codomain syntax, so it is FORM and it is allowed.

    The razor's constraint is sentence-TYPE membership, never character count. These check the
    type, and deliberately do not check the length — a length assertion would re-impose the
    constraint the ruling removed.
    """

    def test_every_block_carries_a_legal_kind(self):
        from engine.dialogue import blocks
        from engine.grammar import illegal_blocks

        self.assertEqual(illegal_blocks(blocks()), [])

    def test_the_arrow_form_is_tagged_FORM(self):
        from engine.dialogue import ARROW_FORM, blocks

        tagged = {text: kind for kind, text in blocks()}
        self.assertEqual(tagged[ARROW_FORM], "FORM")

    def test_the_prompt_TEACHES_exactly_the_form_the_extractor_parses(self):
        """A prompt that shows a form its own parser refuses is a defect only this comparison
        finds — and this project has shipped that defect once, in the ACT grammar."""
        from engine.dialogue import ARROW_FORM

        shown = ARROW_FORM.replace("[i] -kind-> [j]", "[1] -refines-> [7]")
        self.assertTrue([p for p in arrows_from(shown, {1, 7}) if p.ok],
                        "the prompt shows a shape the extractor does not accept")

    def test_every_kind_the_prompt_NAMES_is_one_the_extractor_accepts(self):
        from engine.dialogue import ARROW_FORM

        named = [k for k in ("same_claim", "refines", "instance_of") if k in ARROW_FORM]
        self.assertEqual(len(named), 3)
        for k in named:
            with self.subTest(kind=k):
                self.assertTrue([p for p in arrows_from(f"[1] -{k}-> [7]", {1, 7}) if p.ok])

    def test_the_render_grammar_is_INHERITED_not_reimplemented(self):
        """Same grammar, same checker. A second copy of the citation rules would drift."""
        from engine.dialogue import blocks
        from engine.grammar import BLOCKS

        self.assertEqual(blocks()[:len(BLOCKS)], BLOCKS)


class ThePipelineIsONEDialogue(unittest.TestCase):
    """Piece 3, over HTTP. The render call is gone and the last turn is the answer.

    Checked at the wire rather than by reading ui/server.py: a substring check over a handler
    is the map-not-territory failure this project has shipped, and the property here is about
    how many times the model is actually called.
    """

    def _serve(self):
        import threading
        from http.server import HTTPServer

        from ui.server import Handler

        srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv, f"http://127.0.0.1:{srv.server_address[1]}"

    def _ask(self, base, payload):
        import json as _j
        import urllib.request

        req = urllib.request.Request(base + "/ask", data=_j.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            return _j.load(r)

    def test_the_response_carries_the_DIALOGUE_not_a_render_reply(self):
        srv, base = self._serve()
        try:
            out = self._ask(base, {"question": "is the cone positive", "chart": "english"})
        finally:
            srv.shutdown()
        self.assertIn("dialogue", out, "the response must carry the conversation")
        self.assertIn("answer", out)
        self.assertIn("faithful", out, "the gate is unchanged by the collapse")

    def test_the_transcript_is_labelled_by_TURN_not_by_port(self):
        """FLAG 2's ruling. `propose`/`render` stop meaning anything once there is one
        dialogue, and a panel that keeps them would name a split the engine no longer has."""
        import ui.server as server

        body = Path(server.__file__).read_text()
        self.assertNotIn('TRANSCRIPT.record("render"', body)
        self.assertIn('TRANSCRIPT.record(f"turn ', body)

    def test_no_second_unconditional_call_survives_in_the_handler(self):
        """The collapse is a cost fact. A `client.complete` outside the turn function would be
        the render call by another name."""
        import re as _re

        import ui.server as server

        body = Path(server.__file__).read_text()
        calls = _re.findall(r"client\.complete\(", body)
        self.assertEqual(len(calls), 1,
                         f"{len(calls)} model calls in the handler; the dialogue makes them")

    def test_the_INBOUND_render_prompt_is_no_longer_what_ask_sends(self):
        """The dialogue's prompt inherits the render grammar and adds the arrow FORM. If /ask
        still sent the bare render prompt, the medium would never be told how to write an
        arrow and the extraction half of the dialogue would be silently dead."""
        from engine.dialogue import ARROW_FORM, render_prompt as dprompt
        from engine.inbound import INBOUND_SYSTEM

        self.assertIn(ARROW_FORM, dprompt())
        self.assertNotIn(ARROW_FORM, INBOUND_SYSTEM)
        self.assertNotEqual(dprompt(), INBOUND_SYSTEM)


class TheDaemonNeverConverses(unittest.TestCase):
    """Spec control 6 again, at the pipeline. Two paths, and only one is conversational."""

    def test_the_unattended_path_makes_no_dialogue_call(self):
        for rel in ("engine/continuous.py", "engine/walk.py", "proposerd.py",
                    "engine/propose_correspondence.py"):
            f = REPO / rel
            if not f.exists():
                continue
            with self.subTest(module=rel):
                body = f.read_text()
                self.assertNotIn("converse(", body)
                self.assertNotIn("dialogue", body)


if __name__ == "__main__":
    unittest.main()
