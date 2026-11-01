# VERIFICATION — Markcap

Status values: PASS, FAIL, UNVERIFIED. All rows start UNVERIFIED.
"Paper reference" comes from the handoff brief and is **not yet checked** against the paper.
Code and test paths are planned, not written yet.

| ID | Requirement | Paper reference | Code location | Test | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| V1 | Type 1: contributions sum to Δy | Table 1 | src/markcap/rules.py | tests/test_rules.py | UNVERIFIED | |
| V2 | Type 2: volume uses new-period X, rate uses baseline n, sum equals Δy | Table 1, Fig. 1 | src/markcap/rules.py | tests/test_rules.py | UNVERIFIED | Algebra checked in PAPER_SPEC §4 |
| V3 | Type 3: per-product volume and rate sum to Δy | Table 1 | src/markcap/rules.py | tests/test_rules.py | UNVERIFIED | |
| V4 | Type 4: shares add to 1; share + rate effects sum to Δȳ | Table 1 | src/markcap/rules.py | tests/test_rules.py | UNVERIFIED | Algebra checked in PAPER_SPEC §4 |
| V5 | Children's contributions add up to the parent's within each dimension | Algorithm 1 | src/markcap/propagate.py | tests/test_propagate.py | UNVERIFIED | |
| V6 | Zero parent change gives zero child contributions | Algorithm 1 | src/markcap/propagate.py | tests/test_propagate.py | UNVERIFIED | |
| V7 | Root contribution equals the root's Δ | Algorithm 1 | src/markcap/propagate.py | tests/test_propagate.py | UNVERIFIED | |
| V8 | Eq. 5 is unbiased on simulated data (mean error near 0 over 100 runs) | Theorem 6.1 | src/markcap/causal.py | tests/test_causal.py | UNVERIFIED | |
| V9 | Eq. 6 matches Eq. 5 when the slope is stable | Proposition 6.2 | src/markcap/causal.py | tests/test_causal.py | UNVERIFIED | |
| V10 | Slope test flags a case where the slope changes | Section 6 | src/markcap/causal.py | tests/test_causal.py | UNVERIFIED | |
| V11 | Cases 1a and 2a: plain method over-blames n; causal version is close to truth | Section 7 | src/markcap/simulate.py | tests/test_simulation.py | UNVERIFIED | |
| V12 | Cases 1b and 2b: causal version is closer to truth than the plain method | Section 7 | src/markcap/simulate.py | tests/test_simulation.py | UNVERIFIED | |
| V13 | Number guard rejects text with a changed number | Our design | src/markcap/narrator/number_guard.py | tests/test_number_guard.py | UNVERIFIED | |
| V14 | App stays within memory and load-time targets (set in P8) | Our design | app/streamlit_app.py | manual | UNVERIFIED | |
| V15 | No secrets or personal paths in the repo | Our design | whole repo | scan in P10 | UNVERIFIED | |
