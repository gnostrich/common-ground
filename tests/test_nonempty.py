"""OI-24, MECHANIZED: success on the empty set is a defect, and it now has a shape.

THE INCIDENT. Kind demotion was applied at snapshot-build time. The on-disk snapshot is built
from corpus material and carries ZERO arrows — the proposer's arrows live in its journal and
are laid over later — so the demotion adjudicated nothing. It reported: 0 records before, 0
demoted, 0 surviving, by_class all zero. Which is exactly what a clean corpus reports. The
defect ran for a cycle and was found by reading the code, because the report could not say it.

WHAT IS ACTUALLY BEING CONTROLLED. Not "does the census have the right numbers" — that is a
different property and other files check it. This one checks that a census over NOTHING is a
DIFFERENT OBJECT from a census that found nothing, at every adjudication site, and that no
consumer can collapse the two by accident. `clean()` is the load-bearing piece: it is the only
sanctioned way to ask "did this find nothing", and it refuses to answer for a refused census.

THE PLANTS below are the two directions. An empty population must be REFUSED — plant one at
each site and require the refusal. A non-empty population must be ANSWERABLE — because a
control that only ever sees refusals would pass on an implementation that refused everything,
which is the vacuous-pass twin of the defect it guards.
"""

from __future__ import annotations

import unittest

from engine.adjudicate import Verdict, adjudicate, pigeonhole
from engine.nonempty import (EmptyAdjudication, RefusedCensus, census, clean, require, size)


class _Rec:
    """The provenance-only record shape `adjudicate` reads. Chart and docs, nothing else."""

    def __init__(self, chart, docs):
        self.chart, self.docs = chart, tuple(docs)


def _pair(same_file: bool = True):
    """A code/prose pair whose prose endpoint came from a docstring. Demotable by provenance."""
    f = "repo||a/b.py"
    prose = _Rec("english", (f"{f}#doc:Widget",))
    code = _Rec("python", (f if same_file else "repo||a/other.py",))
    return prose, code


class TheVocabularyItself(unittest.TestCase):

    def test_a_census_over_nothing_is_refused(self):
        c = census("demo", [], {"violations": 0})
        self.assertTrue(c["refused"])
        self.assertEqual(c["population"], 0)
        self.assertIn("NOT a finding of zero", c["note"])

    def test_a_refused_census_CANNOT_be_read_as_clean(self):
        """The whole point. `violations: 0` is right there, and asking is still refused."""
        c = census("demo", [], {"violations": 0})
        with self.assertRaises(RefusedCensus):
            clean(c)

    def test_a_real_census_that_found_nothing_IS_clean(self):
        """Not vacuous: the same question over a real population answers, and answers yes."""
        self.assertTrue(clean(census("demo", [1, 2, 3], {"violations": 0})))

    def test_a_real_census_that_found_something_is_not_clean(self):
        self.assertFalse(clean(census("demo", [1, 2, 3], {"violations": 2})))

    def test_population_is_never_mistaken_for_a_finding(self):
        """`population` is the denominator, not a violation count. If `clean` counted it, a
        census over a large clean corpus would report dirty — the guard inverted."""
        self.assertTrue(clean(census("demo", list(range(500)), {"violations": 0})))

    def test_require_raises_and_NAMES_the_operation(self):
        with self.assertRaises(EmptyAdjudication) as cm:
            require("demote_containment", [], unit="arrow")
        self.assertIn("demote_containment", str(cm.exception))
        self.assertIn("0 arrow(s)", str(cm.exception))

    def test_require_passes_a_real_population_through(self):
        self.assertEqual(require("op", [1, 2]), 2)

    def test_an_unsized_population_is_a_TypeError_not_a_zero(self):
        """A generator has no length. Guessing zero would put this module's own blind spot
        exactly where the defect it guards lives."""
        with self.assertRaises(TypeError):
            size(x for x in [1, 2, 3])


class TheFinestGrainIsOnePAIR(unittest.TestCase):
    """`demote=False` meant two things: read-and-kept, and could-not-be-read."""

    def test_a_missing_endpoint_is_UNADJUDICATED_not_kept(self):
        v = adjudicate(None, _Rec("python", ("repo||a/b.py",)))
        self.assertFalse(v.demote)
        self.assertFalse(v.adjudicated, "an unreadable pair is not a surviving same_claim")
        self.assertFalse(v.as_record()["adjudicated"])

    def test_both_endpoints_missing_is_also_unadjudicated(self):
        self.assertFalse(adjudicate(None, None).adjudicated)

    def test_a_pair_that_WAS_read_and_kept_is_adjudicated(self):
        """The distinguishing case. Out-of-class is a READING, not an absence."""
        v = adjudicate(_Rec("english", ()), _Rec("english", ()))
        self.assertFalse(v.demote)
        self.assertTrue(v.adjudicated)

    def test_a_docstringless_prose_endpoint_was_read(self):
        prose, code = _pair()
        v = adjudicate(_Rec("english", ("repo||a/b.md",)), code)
        self.assertFalse(v.demote)
        self.assertTrue(v.adjudicated, "no #doc: fragment is a finding, not a failure to look")

    def test_a_demotion_is_adjudicated(self):
        v = adjudicate(*_pair())
        self.assertTrue(v.demote)
        self.assertTrue(v.adjudicated)

    def test_the_default_is_adjudicated_so_no_construction_site_silently_opts_out(self):
        self.assertTrue(Verdict(False, "x").adjudicated)


class EveryAdjudicationSiteCENSUSES(unittest.TestCase):
    """Site by site: empty in, refused out. Non-empty in, answerable out."""

    def test_pigeonhole_over_no_pairs_is_refused(self):
        c = pigeonhole(set(), {})
        self.assertTrue(c["refused"])
        with self.assertRaises(RefusedCensus):
            clean(c, "over_declared", "excess_pairs")

    def test_pigeonhole_over_real_pairs_answers(self):
        prose, code = _pair()
        slots = {"u": prose, "v": code}
        c = pigeonhole({("u", "v")}, slots)
        self.assertFalse(c["refused"])
        self.assertEqual(c["population"], 1)
        self.assertTrue(clean(c, "over_declared", "excess_pairs"))

    def test_pigeonhole_counts_pairs_it_could_not_read(self):
        c = pigeonhole({("u", "missing")}, {"u": _pair()[0]})
        self.assertEqual(c["unadjudicated_pairs"], 1)
        self.assertEqual(c["docstrings"], 0)

    def test_demote_containment_over_no_arrows_is_refused(self):
        """THE ORIGINAL INCIDENT, reproduced. This is the call that shipped."""
        from engine.corpus_state import _demote_containment

        _out, c = _demote_containment([], [], {})
        self.assertTrue(c["refused"], "zero arrows in, and the census said 'clean'")
        with self.assertRaises(RefusedCensus):
            clean(c, "demoted_records")

    def test_demote_containment_over_real_arrows_answers(self):
        from engine.correspondence import Correspondence
        from engine.corpus_state import _demote_containment
        from engine.normalize import address
        from engine.types import Slot, WarrantTier

        f = "repo||a/b.py"
        pu, nu_u = address("english", "the widget holds", "assert")
        pv, nu_v = address("python", "def widget(): ...", "assert")
        slots = [Slot(id=pu, chart="english", type="assert", nu=nu_u),
                 Slot(id=pv, chart="python", type="assert", nu=nu_v)]
        docs = {pu: {f"{f}#doc:widget"}, pv: {f}}
        arrow = Correspondence(src_chart="english", src_slot=pu, dst_chart="python",
                               dst_slot=pv, kind="same_claim", tier=WarrantTier.EXTRACTION,
                               proposer="lm", prompt_hash="t", evidence=("seed",))
        out, c = _demote_containment([arrow], slots, docs)
        self.assertFalse(c["refused"])
        self.assertEqual(c["population"], 1)
        self.assertEqual(c["demoted_records"], 1, "a docstring/own-definition pair demotes")
        self.assertEqual(out[0].kind, "refines")

    def test_ambiguity_census_over_a_lean_free_snapshot_is_refused(self):
        from engine.corpus_state import CorpusSnapshot
        from engine.scaffold import ambiguity_census

        c = ambiguity_census(CorpusSnapshot(slots={}, arrows=()), lambda nu: nu)
        self.assertTrue(c["refused"], "no lean material is not a finding about ambiguity")
        with self.assertRaises(RefusedCensus):
            clean(c, "ambiguous_names")

    def test_ambiguity_census_over_lean_material_answers(self):
        from engine.corpus_state import CorpusSnapshot, SlotRecord

        from engine.scaffold import ambiguity_census

        slots = {f"s{i}": SlotRecord(slot=f"s{i}", chart="lean", type="assert",
                                     nu=f"theorem t{i}", value="true", confidence=1.0,
                                     tier="EXTRACTION", docs=("r||f.lean",))
                 for i in range(3)}
        c = ambiguity_census(CorpusSnapshot(slots=slots, arrows=()), lambda nu: nu.split()[-1])
        self.assertFalse(c["refused"])
        self.assertEqual(c["population"], 3)


class PlantedSuccessOnTheEmptySet(unittest.TestCase):
    """The control's own control: rebuild the defect by hand and watch it read as clean.

    Without this the file would prove only that `refused` is present, which a `refused: False`
    constant would also satisfy. The plant reconstructs the census the incident actually
    emitted — the literal dict, all zeroes — and shows there is no question you can ask it
    that distinguishes it from a real clean run. That indistinguishability IS the defect.
    """

    #: The census `_demote_containment` emitted at snapshot-build time, verbatim in shape.
    THE_INCIDENT = {"era": "docstring", "same_claim_records_before": 0,
                    "same_claim_pairs_before": 0, "demoted_records": 0,
                    "surviving_pairs": 0, "by_class": {"same-file": 0, "cross-document": 0}}

    def test_the_incidents_census_is_indistinguishable_from_a_clean_one(self):
        real = dict(self.THE_INCIDENT, same_claim_records_before=4000, surviving_pairs=4000)
        empty = dict(self.THE_INCIDENT)
        self.assertEqual(empty["demoted_records"], 0)
        self.assertEqual(real["demoted_records"], 0)
        # No key tells them apart on the question that matters, and the old shape had no
        # other key to consult. That is why the population had to go IN the record.
        self.assertNotIn("population", empty)
        self.assertNotIn("refused", empty)

    def test_the_same_two_states_ARE_distinguishable_now(self):
        empty = census("demote_containment", [], self.THE_INCIDENT)
        real = census("demote_containment", list(range(4000)), self.THE_INCIDENT)
        self.assertTrue(empty["refused"])
        self.assertFalse(real["refused"])
        self.assertTrue(clean(real, "demoted_records"))
        with self.assertRaises(RefusedCensus):
            clean(empty, "demoted_records")

    def test_a_census_that_LIED_about_its_population_would_still_be_caught_at_the_site(self):
        """`census()` derives the population from the population, not from an argument a
        caller supplies — so a site cannot claim a population it did not examine."""
        c = census("demote_containment", [], dict(self.THE_INCIDENT, population=4000))
        self.assertEqual(c["population"], 0)
        self.assertTrue(c["refused"])


class ThereIsOnlyONEAdjudication(unittest.TestCase):
    """`survivors()` was a second implementation of `_demote_containment`'s adjudication with
    no caller and no control — free to drift from the live one silently. It was deleted, and
    this control is what keeps it deleted."""

    def test_no_second_demotion_implementation_exists(self):
        import engine.adjudicate as A

        self.assertFalse(hasattr(A, "survivors"),
                         "two implementations of one adjudication is the forbidden shape")


if __name__ == "__main__":
    unittest.main()
