.PHONY: help status test lock verify nulls demo p0 p1 clean

help:
	@echo "status  — decisions, lock state, phase readiness"
	@echo "test    — unit tests (stdlib unittest, no dependencies)"
	@echo "lock    — write seed/SEED.lock (refuses while any decision is blank)"
	@echo "verify  — gate-4 tripwire: recompute seed hashes, fail on drift"
	@echo "nulls   — P1 null battery on the current seed hash"
	@echo "demo    — synthetic end-to-end smoke run, writes nothing"
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

demo:
	@python3 cli.py demo

p0:
	@python3 cli.py p0

clean:
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "caches removed; runs/ and registry/ are evidence and are left alone"
