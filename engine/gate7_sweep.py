"""`python -m engine.gate7_sweep` — print the generative-key sweep.

Sentence 7: all generative keys are content-and-seed only; artifact identity lives in
provenance exclusively. Non-zero exit means a random stream somewhere in `engine/` is not
classified, or is keyed on identity, or is keyed on identity by design without citing the
ruling that requires it.
"""

from __future__ import annotations

from .static_checks import check_generative_keys, generative_key_report

_MARK = {
    "identity": "IDENTITY-KEYED",
    "design": "identity-by-design",
    "seed": "seed-keyed",
    "content": "content-keyed",
}


def main() -> int:
    result = check_generative_keys()
    for site in generative_key_report():
        print(f"{site['site']:<52}{_MARK[str(site['keying'])]:<20}{site['key']}")
    print(f"\n{result.checked_functions} DRNG site(s) across {result.checked_files} files")
    for v in result.violations:
        print(f"UNRESOLVED: {v}")
    if not result.ok:
        print("Classify it in static_checks.GENERATIVE_KEY_SITES, or key it on content.")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
