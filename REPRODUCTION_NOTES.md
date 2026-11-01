# REPRODUCTION_NOTES — Markcap

Independent implementation of arXiv 2608.29735. Not the authors' code. Updated every phase.

## 1. Status

NOT RUN means no experiment has been run yet. NOT REPRODUCED is used only after we ran the
experiment and the result did not match.

| Paper result | Paper value | Our value | Status |
| --- | --- | --- | --- |
| Case 1a: plain method wrongly blames n; unified and GCM near truth | qualitative | - | NOT RUN |
| Case 1b: unified approach closest to truth | qualitative | - | NOT RUN |
| Case 2a: as 1a, quadratic relation | qualitative | - | NOT RUN |
| Case 2b: as 1b, quadratic relation | qualitative | - | NOT RUN |
| Real-data section (130+ metrics, ~1.6 s year-over-year, ~400x faster than GCM) | as reported | - | NOT ATTEMPTED (Amazon data is not public) |

## 2. Rules fixed before the first simulation run (fill in during P5)

- True attribution in each case (PAPER_SPEC S18): TBD
- Error metric (S19): TBD
- Rule for MATCH / PARTIAL MATCH / NOT REPRODUCED (S19): TBD
- Simulation parameters (S17): TBD, saved in `configs/sim_cases.yaml`

## 3. Deviations from the paper

None recorded yet.

## 4. Assumptions

See the ambiguity table in PAPER_SPEC.md (section 10). Each assumption has an ID (S1, S2, ...).

## 5. Environment

TBD: Python version, `requirements.txt`, random seeds, run date.

## 6. Not claimed

We do not claim the paper's deployed engine numbers (130+ metrics, 1.6 s, 400x). We cannot test them.
