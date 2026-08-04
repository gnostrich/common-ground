"""Local, single-machine application layer over the common-ground engine.

Everything here is a *view + front-end*: it drives the LM (a proposer INTO D, extraction
tier), renders the engine's settled state, and hosts the live memory kernel and the
cross-instance coupling. It adds no base, measure, or morphism to the object itself beyond
what the engine already exposes — the LM proposer, K-live, and the persons base-swap are
engine-level moves, classified in engine/three_moves.py; this package is the surface over
them. Localhost only; the API key is read from the environment or the request and is never
logged or written to disk.
"""
