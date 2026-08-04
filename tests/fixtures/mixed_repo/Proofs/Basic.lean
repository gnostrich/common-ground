-- Tiny, self-contained fixture theorem. Not real Mathlib, and this fixture does not
-- elaborate it (no toolchain is pinned here; see adapters/lean_corpus.py -- clamps
-- refuse outright without a pinned toolchain, D6).
theorem two_plus_two : 2 + 2 = 4 := by decide

def Doubled (n : Nat) : Nat := n + n
