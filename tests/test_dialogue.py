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

#: LABELS, not integers — the label space is the region's and it runs end to end. A fixture
#: change, not a property change: what the extractor resolves against is still an exact set.
CITABLE = {"e1", "e2", "e3", "l7", "l12"}


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
        self.assertTrue([p for p in arrows_from("[e1] -refines-> [l7]", CITABLE) if p.ok])

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
        c = _compiled([{"n": "e1"}, {"n": "l7"},
                       {"n": "x9", "kind": "arrow", "joins": ["e1", "l7"]}])
        q = interrogate(c, asked=set())
        self.assertIn("[e1]", q)
        self.assertIn("[l7]", q)
        self.assertIn("Composition implies", q)

    def test_it_does_not_re_ask_a_pair_already_put(self):
        c = _compiled([{"n": "e1"}, {"n": "l7"},
                       {"n": "x9", "kind": "arrow", "joins": ["e1", "l7"]}])
        self.assertEqual(interrogate(c, asked={("e1", "l7")}), "",
                         "asking the same pair twice is an interrogation loop, not a measure")

    def test_it_falls_through_to_a_CONTESTED_object(self):
        c = _compiled([{"n": "e3", "contested": True}])
        self.assertIn("[e3]", interrogate(c, asked=set()))
        self.assertIn("more than one value", interrogate(c, asked=set()))

    def test_it_returns_EMPTY_rather_than_inventing_a_question(self):
        """No structure left to ask about ends the dialogue. Manufacturing one more turn
        because the budget allows it is the candidate list with better manners."""
        self.assertEqual(interrogate(_compiled([{"n": "e1"}]), asked=set()), "")


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
        prose = " ".join(["[e1] -same_claim-> [l7]."] * 5)
        ps = arrows_from(prose, CITABLE, turn=2)
        self.assertEqual(len(ps), 5, "every utterance is recorded")
        self.assertEqual(sum(1 for p in ps if p.ok), 1, "they are one claim")
        self.assertEqual([p.void for p in ps[1:]], ["restated in this turn"] * 4)

    def test_the_record_says_WHICH_it_is_counting(self):
        t = Turn(n=2, ask="q", proposals=arrows_from("[e1] -same_claim-> [l7]. " * 3, CITABLE))
        rec = t.as_record()
        self.assertEqual(len(rec["arrows"]), 3)
        self.assertEqual(rec["resolved"], 1)
        self.assertEqual(rec["void"], 2)

    def test_every_proposal_carries_its_TURN(self):
        """Both survive with their turn recorded — a revision at turn 6 does not erase turn 2."""
        for p in arrows_from("[e1] -refines-> [l7]", CITABLE, turn=6):
            self.assertEqual(p.turn, 6)

    def test_a_direction_flip_is_a_DIFFERENT_record_but_the_same_pair(self):
        """`refines` is directed, so [1]->[7] and [7]->[1] are different assertions. The
        dedupe is on the unordered pair AND the kind, so the second is a restatement of the
        pair — recorded, not silently dropped — and the operator can see both."""
        ps = arrows_from("[e1] -refines-> [l7]. [l7] -refines-> [e1].", CITABLE)
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
                "citations": citations or [{"n": "e1", "slot": "s1"}, {"n": "l7", "slot": "s7"}]}

    def _transport(self, replies):
        seen = []

        def t(system, user):
            seen.append({"system": system, "user": user})
            return (replies[len(seen) - 1] if len(seen) <= len(replies) else replies[-1]), {}

        return t, seen

    def test_a_question_with_nothing_to_interrogate_costs_ONE_call(self):
        t, seen = self._transport(["The cone is positive [e1]."])
        d = converse("is the cone positive", self._field(), t)
        self.assertEqual(len(seen), 1, "the two-port split spent two; this must spend one")
        self.assertEqual(len(d.turns), 1)
        self.assertEqual(d.answer, "The cone is positive [e1].")
        self.assertEqual(d.stopped, "the graph had nothing left to ask")

    def test_the_last_turn_IS_the_answer(self):
        t, _ = self._transport(["first [e1].", "second [e1].", "third [e1]."])
        d = converse("q", self._field(), t)
        self.assertEqual(d.answer, d.turns[-1].prose)

    def test_NO_QUESTION_NO_TURN(self):
        """RESTATED, and it is the rule the design always had.

        This required an interrogation turn to be FOLLOWED by an answer turn. That extra turn
        was the render port surviving as a render TURN, and on the served fixture it did real
        damage: turn 1 answered from ten cited claims, the interrogator honestly found nothing
        left to ask, and a turn ran anyway against a degraded summary of turn 1's own work —
        its two sentences from two claims are what displayed. The machine answered well,
        re-answered badly from a summary of itself, and showed the bad one.

        A turn is legitimate ONLY as a response to an interrogation. When the interrogator has
        nothing, the dialogue ends and the previous turn's answer STANDS — it already passed
        the same grammar and it is gated by the same checker.
        """
        t, seen = self._transport(["turn one, answered [e1]."])
        d = converse("q", self._field(), t)
        self.assertEqual(len(d.turns), 1)
        self.assertEqual(len(seen), 1, "a second call with nothing asked is an unasked turn")
        self.assertEqual(d.answer, "turn one, answered [e1].")

    def test_every_turn_after_the_first_HAS_a_preceding_engine_question(self):
        """The planted control the rule needs: a turn record with no interrogation before it
        is RED. Checked over the whole dialogue, so an unasked turn anywhere is caught, not
        only one appended at the end."""
        field = self._field([{"n": "e1", "slot": "s1"}, {"n": "l7", "slot": "s7"},
                             {"n": "x9", "kind": "arrow", "joins": ["e1", "l7"]}])
        t, _ = self._transport(["a [e1].", "b [l7].", "c [e1].", "d [e1]."])
        d = converse("q", field, t)
        for i, turn in enumerate(d.turns):
            with self.subTest(turn=turn.n):
                if i == 0:
                    self.assertEqual(turn.ask, "q", "turn 1 answers the operator")
                else:
                    prior = d.turns[i - 1].interrogation
                    self.assertTrue(prior, f"turn {turn.n} ran with nothing asked before it")
                    self.assertEqual(turn.ask, prior,
                                     "a turn must answer the question that summoned it")

    def test_a_seeded_dialogue_with_nothing_to_ask_makes_NO_further_call(self):
        """The exact served shape: turn 1 already happened, the graph is quiet."""
        t, seen = self._transport(["should not be called"])
        t1 = Turn(n=1, ask="q", prose="turn one's comprehensive answer [e1].",
                  proposals=arrows_from("[e1] -refines-> [l7]", {"e1", "l7"}, 1))
        d = converse("q", self._field(), t, first_turn=t1)
        self.assertEqual(len(seen), 0, "an unasked render turn")
        self.assertEqual(d.answer, "turn one's comprehensive answer [e1].")

    def test_the_interrogation_is_the_ENGINE_speaking_and_is_recorded_as_the_ask(self):
        field = self._field([{"n": "e1", "slot": "s1"}, {"n": "l7", "slot": "s7"},
                             {"n": "x9", "kind": "arrow", "joins": ["e1", "l7"]}])
        t, _ = self._transport(["a [e1].", "b [l7].", "c [e1]."])
        d = converse("q", field, t)
        mid = [x for x in d.turns if x.ask != "q"]
        self.assertTrue(mid, "no interrogation turn ran")
        self.assertIn("Composition implies", mid[0].ask)

    def test_the_budget_BINDS_even_when_the_graph_keeps_asking(self):
        """Spec control 4, at the loop. A graph with an endless supply of unasked pairs must
        still stop — the budget is the ceiling, not a suggestion."""
        cites = [{"n": f"e{i}", "slot": f"s{i}"} for i in range(1, 20)]
        cites += [{"n": f"x{100 + k}", "kind": "arrow", "joins": [f"e{k}", f"e{k+1}"]}
          for k in range(1, 15)]
        t, seen = self._transport(["x [e1]."])
        d = converse("q", {"compiled": "F", "citations": cites}, t, budget=3)
        self.assertLessEqual(len(d.turns), 3 + 1, "budget + the one answer turn, never more")
        self.assertEqual(d.stopped, "budget")
        self.assertLessEqual(len(seen), 4)

    def test_a_budget_of_one_still_answers(self):
        t, seen = self._transport(["only [e1]."])
        d = converse("q", self._field(), t, budget=1)
        self.assertEqual(len(seen), 1)
        self.assertEqual(d.answer, "only [e1].")

    def test_the_FIELD_SETTLES_between_turns(self):
        """The settle callback receives every resolved proposal so far, and the freshly
        compiled field is what the next turn is put against."""
        field = self._field([{"n": "e1", "slot": "s1"}, {"n": "l7", "slot": "s7"},
                             {"n": "x9", "kind": "arrow", "joins": ["e1", "l7"]}])
        got = []

        def settle(props):
            got.append(len(props))
            return {"compiled": f"SETTLED-{len(props)}", "citations": field["citations"],
                    "relaxation": {"moved": 5}}

        t, seen = self._transport(["[e1] -refines-> [l7] and so on [e1].", "b [l7].", "c [e1]."])
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
        t, _ = self._transport(["[e1] -refines-> [l7]. [e1] -refines-> [l7]. [e1] -refines-> [l7]."])
        r = converse("q", self._field(), t).as_record()
        self.assertEqual(r["records"], 3)
        self.assertEqual(r["resolved_records"], 1)
        self.assertEqual(r["distinct_claims"], 1)

    def test_distinct_claims_spans_the_WHOLE_dialogue_not_one_turn(self):
        """A medium restating one arrow across five TURNS contributed one claim. The per-turn
        dedupe cannot see across turns, so the dialogue-level count is the one that must."""
        field = self._field([{"n": "e1", "slot": "s1"}, {"n": "l7", "slot": "s7"},
                             {"n": "x9", "kind": "arrow", "joins": ["e1", "l7"]}])
        t, _ = self._transport(["[e1] -refines-> [l7] a."] * 5)
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

        shown = ARROW_FORM.replace("[i] -kind-> [j]", "[e1] -refines-> [l7]")
        self.assertTrue([p for p in arrows_from(shown, {"e1", "l7"}) if p.ok],
                        "the prompt shows a shape the extractor does not accept")

    def test_every_kind_the_prompt_NAMES_is_one_the_extractor_accepts(self):
        from engine.dialogue import ARROW_FORM

        named = [k for k in ("same_claim", "refines", "instance_of") if k in ARROW_FORM]
        self.assertEqual(len(named), 3)
        for k in named:
            with self.subTest(kind=k):
                self.assertTrue([p for p in arrows_from(f"[e1] -{k}-> [l7]", {"e1", "l7"}) if p.ok])

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


class TheANSWERIsWhatWasSaidToTheOPERATOR(unittest.TestCase):
    """Found on column C-prime, the first run where the interrogator actually fired.

    Making the contest visible in the input gave the interrogator something to ask about, it
    asked three times, the budget ran out, and what displayed was turn 4 replying to "the field
    holds more than one value for [e18] — which does the state support?". A correct answer to a
    question the operator never asked, presented as the answer.

    "The final turn is the answer" holds when the dialogue ends because the graph went quiet.
    It does not hold when the budget runs out mid-interrogation. An interrogation turn is a
    MEASUREMENT; the answer is the most recent thing the medium said TO THE OPERATOR.
    """

    def _field(self):
        return {"compiled": "F",
                "citations": [{"n": "e1", "slot": "s1"}, {"n": "l7", "slot": "s7"},
                              {"n": "e3", "contested": True},
                              {"n": "e4", "contested": True},
                              {"n": "e5", "contested": True}]}

    def _transport(self, replies):
        seen = []

        def t(system, user):
            seen.append(user)
            return (replies[len(seen) - 1] if len(seen) <= len(replies) else replies[-1]), {}

        return t, seen

    def test_a_budget_exhausted_dialogue_answers_the_OPERATORS_question(self):
        t, _ = self._transport(["THE ANSWER, to the operator [e1].",
                                "interrogation reply one [e3].",
                                "interrogation reply two [e4].",
                                "interrogation reply three [e5]."])
        d = converse("the operator's question", self._field(), t, budget=4)
        self.assertEqual(d.stopped, "budget", "this control needs the budget to bind")
        self.assertGreater(len(d.turns), 1, "and needs interrogations to have fired")
        self.assertEqual(d.answer, "THE ANSWER, to the operator [e1].")
        self.assertNotEqual(d.answer, d.turns[-1].prose,
                            "the last turn replied to the engine, not to the operator")

    def test_a_quiet_graph_still_answers_from_the_last_turn(self):
        """The original rule is untouched where it was right."""
        t, _ = self._transport(["only turn, and the answer [e1]."])
        d = converse("q", {"compiled": "F", "citations": [{"n": "e1", "slot": "s1"}]}, t)
        self.assertEqual(len(d.turns), 1)
        self.assertEqual(d.answer, d.turns[-1].prose)

    def test_a_later_turn_that_RE_ASKS_the_question_wins(self):
        """Most recent thing said to the operator — not the first thing."""
        d = Dialogue(question="q")
        d.turns = [Turn(n=1, ask="q", prose="early [e1]."),
                   Turn(n=2, ask="engine asks", prose="measurement [e2]."),
                   Turn(n=3, ask="q", prose="later and better [e1][e2].")]
        self.assertEqual(d.answer, "later and better [e1][e2].")


class TheArrowLinesAreNotTheANSWER(unittest.TestCase):
    """One reply, two roles — and only one of them is what the operator reads.

    A turn answers in cited prose AND writes its arrows in the same reply, because they are one
    act; that is what the collapse means. But an arrow line is the extraction channel, already
    harvested into proposals by the time anyone reads the answer. On a served run turn 1 came
    back as eighty-four arrow lines and nothing else, every one of them was then parsed as an
    uncited sentence, and the operator was shown a wiring diagram.

    Removing them is PRESENTATION. Not a second turn, not a second parse — the same lines the
    extractor consumed, dropped from the display.
    """

    def test_arrow_lines_are_stripped_and_the_prose_survives(self):
        from engine.dialogue import said

        got = said("e3 -bears_on-> b0\nThe work establishes positivity [e7].\n"
                   "[e1] -refines-> [e2]")
        self.assertEqual(got, "The work establishes positivity [e7].")

    def test_a_turn_that_ONLY_related_reads_as_EMPTY_not_as_a_diagram(self):
        """A turn that never answered is a real state and the operator should see it happened,
        rather than being handed the wiring as though it were prose."""
        from engine.dialogue import said

        self.assertEqual(said("e1 -refines-> e2\ne3 -refines-> e4"), "")

    def test_a_SENTENCE_containing_an_arrow_keeps_its_words(self):
        """Anchored at both ends. The medium may legitimately write a sentence with an arrow
        in it, and the sentence is not the arrow."""
        from engine.dialogue import said

        line = "It refines it, [e1] -refines-> [e7], clearly [e1]."
        self.assertEqual(said(line), line)

    def test_the_arrows_are_still_EXTRACTED_from_the_unstripped_prose(self):
        """Stripping is for the display only. The extractor reads the reply as sent."""
        prose = "e1 -refines-> e7\nThe answer [e1]."
        self.assertEqual(len([p for p in arrows_from(prose, {"e1", "e7"}) if p.ok]), 1)

    def test_the_dialogue_answer_uses_the_stripped_form(self):
        d = Dialogue(question="q")
        d.turns = [Turn(n=1, ask="q", prose="e1 -refines-> e7\nThe answer [e1].")]
        self.assertEqual(d.answer, "The answer [e1].")


class TheUnansweredQuestionIsARESIDUAL(unittest.TestCase):
    """The dialogue may not close while [b0] has no answering turn.

    Same class as a contested claim or an unnamed cluster: structure the field can point at,
    unresolved. NOT the render fossil returning — the fossil ran ALWAYS, answered or not, one
    more call every time, from a degraded compile. This fires ONLY on a measured absence and
    NEVER when an answering turn exists. Conditional-on-debt, not unconditional-stage, and
    both directions are controlled below.
    """

    def _field(self, attached=("e7",)):
        return {"compiled": "SETTLED STATE",
                "citations": [{"n": "e7", "slot": "s7"}, {"n": "e1", "slot": "s1"},
                              {"n": "l9", "slot": "s9"}],
                "attachment": {"attachment": [{"n": a} for a in attached]}}

    def _transport(self, replies):
        seen = []

        def t(system, user):
            seen.append(user)
            return (replies[len(seen) - 1] if len(seen) <= len(replies) else replies[-1]), {}

        return t, seen

    def test_c1_a_dialogue_CANNOT_close_with_zero_answering_turns(self):
        """Turn 1 related and never answered — the served shape that prompted the ruling."""
        t, seen = self._transport(["e1 -refines-> l9\ne1 -refines-> e7",
                                   "The work establishes positivity [e7]."])
        d = converse("q", self._field(), t)
        self.assertEqual(len(seen), 2, "the re-ask did not fire on a measured absence")
        self.assertIn("no answering turn", d.stopped)
        self.assertEqual(d.answer, "The work establishes positivity [e7].")

    def test_c2_the_re_ask_does_NOT_fire_when_a_turn_already_answered(self):
        """The fossil's defining property was running unconditionally. This must not."""
        t, seen = self._transport(["The work establishes positivity [e7]."])
        d = converse("q", self._field(), t)
        self.assertEqual(len(seen), 1, "an unconditional extra call is the fossil")
        self.assertNotIn("no answering turn", d.stopped)

    def test_c3_the_re_asks_input_is_the_SETTLED_state(self):
        """Never a summary. The settled state is what the earlier turns moved."""
        t, seen = self._transport(["e1 -refines-> l9", "answered [e7]."])
        settled = {"compiled": "THE SETTLED MOVED REGION", "citations": self._field()["citations"],
                   "attachment": self._field()["attachment"], "relaxation": {"moved": 3}}
        converse("q", self._field(), t, settle=lambda props: settled)
        self.assertIn("THE SETTLED MOVED REGION", seen[-1])

    def test_an_absence_scoped_to_the_question_COUNTS_as_answering(self):
        """The field saying it does not hold what was asked IS an answer."""
        t, seen = self._transport(["The field does not contain that [∅]."])
        d = converse("q", self._field(), t)
        self.assertEqual(len(seen), 1)
        self.assertNotIn("no answering turn", d.stopped)

    def test_the_bar_is_EXISTENCE_not_adequacy(self):
        """A thin but cited answer still answers. Whether it is any good is the faithfulness
        gate's job — a quality judgement here would be the medium grading itself."""
        t, seen = self._transport(["Yes [e7]."])
        converse("q", self._field(), t)
        self.assertEqual(len(seen), 1)

    def test_citing_something_b0_did_NOT_attach_to_is_not_answering(self):
        """Structural, and it has to actually discriminate: a sentence about an unrelated
        corner of the field is not an answer to the question."""
        from engine.dialogue import answers

        self.assertFalse(answers(Turn(n=1, ask="q", prose="Something else [l9]."), {"e7"}))
        self.assertTrue(answers(Turn(n=1, ask="q", prose="The thing [e7]."), {"e7"}))

    def test_a_missing_attachment_record_degrades_to_cited_ANYTHING(self):
        """A residual that fires because a RECORD was missing would re-ask forever."""
        from engine.dialogue import attached_labels

        got = attached_labels({"citations": [{"n": "e7", "slot": "s"}], "attachment": {}})
        self.assertEqual(got, {"e7"})


if __name__ == "__main__":
    unittest.main()
