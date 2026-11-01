# Rules for the coding agent (Markcap)

1. PAPER_SPEC.md is the contract. The paper (arXiv 2608.29735) is the source of truth.
2. Never silently invent an algorithm detail. Mark it [UNSPECIFIED], [PARTIALLY_SPECIFIED] or
   [ASSUMPTION] and add a row to the ambiguity table in PAPER_SPEC.md.
3. Keep paper references (table, equation) in comments next to the code.
4. Before changing behaviour, say which requirement it satisfies.
5. Small, testable functions. Test identities, additivity and edge cases.
   Run the smallest relevant test after every change.
6. No speed work until correctness tests pass.
7. Never say a paper result is reproduced unless that exact experiment was run.
   Allowed labels: MATCH, PARTIAL MATCH, NOT REPRODUCED.
8. Keep REPRODUCTION_NOTES.md (deviations) and VERIFICATION.md (checks) up to date.
9. The AI model never does arithmetic. Every number a user sees comes from Python
   and passes the number guard.
10. No client or employer data, no API keys, no personal paths in the repo.
11. Keep the app light: small data, no heavy libraries (no TensorFlow).
12. At the end of each phase: files changed, commands run, test results, remaining risks.

## Working style
- Use the name Markcap everywhere (package `markcap`, repo `markcap`).
- Simple English, short sentences. Define a new term once.
- In chat say "reasons". In code and docs the table of reasons is called the driver table.
- One phase per chat. Explain the plan in at most 8 lines, build after "go".
