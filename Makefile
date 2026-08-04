.PHONY: help status test lock verify nulls demo p0 p1 pin gate6 gate7 faithfulness probes three-moves structure claims report clean

help:
	@echo "status  — decisions, lock state, lexicon pins, phase readiness"
	@echo "test    — unit tests (stdlib unittest, no dependencies)"
	@echo "lock    — write seed/SEED.lock (refuses while any decision is blank)"
	@echo "verify  — gate-4 tripwire: recompute seed hashes, fail on drift"
	@echo "nulls   — P1 null battery + positive controls on the current seed hash"
	@echo "pin     — record a landed D8 artifact: cli.py pin <source> --path ..."
	@echo "gate6   — statistical-band conformance sweep (GATES.md sentence 6)"
	@echo "gate7   — generative-key sweep (GATES.md sentence 7)"
	@echo "faithfulness — theory object -> code site -> control audit"
	@echo "probes  — commitment -> probe -> status battery + chart plug-in audit"
	@echo "claims  — gate 10: every claimed property (complexity/index/exactness) is warranted by a control"
	@echo "structure — the live factor graph IS the algebra (nodes/factors/frustration; declared gaps fenced)"
	@echo "three-moves — belonging audit: every extension = swap-base/add-measure/add-morphism (seed/OBJECT.md)"
	@echo "demo    — synthetic end-to-end smoke run, writes nothing"
	@echo "report  — usable surface: render the fixture run (reports/fixture-report.md + .html)"
	@echo "p0 / p1 — phase gates"

status:
	@python3 cli.py status

test:
	@python3 -m unittest discover -s tests -t . -v

lock:
	@python3 cli.py lock

verify:
	@python3 cli.py verify

nulls p1:
	@python3 cli.py p1

gate6:
	@python3 -m engine.gate6_sweep

gate7:
	@python3 -m engine.gate7_sweep

faithfulness:
	@python3 -m engine.faithfulness_report

probes:
	@python3 -m engine.probe_report

three-moves:
	@python3 -m engine.three_moves_sweep

structure:
	@python3 -m engine.structure_sweep

claims:
	@python3 -m engine.claims_sweep

report:
	@python3 cli.py report --md reports/fixture-report.md --html reports/fixture-report.html

demo:
	@python3 cli.py demo

p0:
	@python3 cli.py p0

clean:
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "caches removed; runs/ and registry/ are evidence and are left alone"
