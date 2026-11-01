# PAPER_SPEC — Markcap

This file is the contract for the code.

**Paper:** Zhou, Janzing, Tsang, Blöbaum, Visentini Scarzanella (Amazon). *A Unified Approach to
Interpretable Causal Root Cause Attribution.* KDD '26 TSMO workshop. arXiv:2608.29735.
No official code is used, so no item is FROM_OFFICIAL_CODE.

> **Status, 1 Nov 2026: NOT CHECKED against the paper.**
> This spec comes from the handoff brief (one earlier reading). Every row with `Checked = NO`
> must be checked against arXiv 2608.29735 before code that depends on it is trusted.
> What *was* checked: the algebra of the four local rules and of the causal split
> (sections 4 and 6). That is maths, not a paper check.

Status words: SPECIFIED, PARTIALLY_SPECIFIED, UNSPECIFIED, ASSUMPTION.

## 1. Central contribution

1. Explain a KPI change between two periods with a metric tree (MECE: parts do not overlap and cover everything).
2. Four local rules split a parent's change among its children (section 4).
3. A recursion pushes contributions down the tree. Inside each dimension, children add up to the parent (section 5).
4. Plain splitting assumes sibling metrics are independent. This can blame the wrong metric.
5. Fix: add a few causal links. Fit the baseline relation f0 (for example units vs price). Remove the part of the change that the other metric alone would cause (section 6).
6. Two estimators: full (Eq. 5) and simplified (Eq. 6, only if the slope is stable).
7. Simulation study: four cases compare truth, plain, GCM and unified (section 7).
8. Limits: links must be right; sensitive to outliers; only for metrics that can be decomposed.

## 2. Modules

| Module | File | Input | Output |
| --- | --- | --- | --- |
| Rules | `rules.py` | values for period 0 and 1 of one parent | child effects (floats) |
| Tree | `tree.py` | `configs/metric_tree.yaml` | validated tree, MECE checks |
| Propagate | `propagate.py` | tree + data for both periods | driver table |
| Causal | `causal.py` | daily tables for both periods + one link | corrected contributions |
| Simulate | `simulate.py` | `configs/sim_cases.yaml`, seed | per-run attribution errors |
| Report | `report.py` | driver table | CSV, JSON |

Driver table columns: node_id, parent_id, dimension, rule_type, effect_type (volume, rate, share),
baseline, new, delta, contribution, pct_of_total_change, rank.

Execution order: load data → build tree → local rules per dimension → recursion → causal
correction on linked nodes → driver table.

## 3. Notation

Periods 0 (baseline) and 1 (new). For any quantity z: z0, z1, Δz = z1 − z0.
Non-rate metrics are totals (revenue, orders). Rate metrics are ratios (AOV, conversion rate).

## 4. Local rules (paper Table 1) — algebra checked, paper not checked

```
Type 1  y = Σ_k y_k
        contrib_k = Δy_k

Type 2  y = n · X                      (example: revenue = orders × AOV)
        volume = Δn · X1
        rate   = ΔX · n0
        proof: n1·X1 − n0·X0 = (n1 − n0)·X1 + n0·(X1 − X0)

Type 3  y = Σ_k n_k · X_k
        volume_k = Δn_k · X_k1
        rate_k   = ΔX_k · n_k0
        proof: apply the Type 2 proof to each k, then sum

Type 4  ȳ = Σ_k p_k · ȳ_k             (Σ_k p_k = 1 in both periods)
        share_k = Δp_k · (ȳ_k0 − ȳ_0)
        rate_k  = Δȳ_k · p_k1
        proof: Δȳ = Σ p_k1·Δȳ_k + Σ Δp_k·ȳ_k0, and Σ Δp_k = 0,
               so Σ Δp_k·ȳ_0 = 0 can be subtracted
```

Note: which period each factor uses (new X in volume, baseline n in rate) changes the split, not the
sum. We follow the order above until it is checked against the paper (S1).

**Test vectors** (invented numbers, hand-computed):

- Type 2: n 1000 → 900, X 500 → 540. volume = −100 × 540 = −54,000. rate = 40 × 1000 = +40,000. Sum = −14,000.
- Type 4: shares 0.20 → 0.25 (Electronics, avg 1500 → 1500) and 0.80 → 0.75 (Accessories, avg 250 → 220).
  ȳ_0 = 500, ȳ_1 = 540. share: +50 and +12.5. rate: 0 and −22.5. Total = +40 = Δȳ.
- Full tree (Revenue = Orders × AOV; orders by region North −60, South −40; AOV from the Type 4 case,
  × 1000 orders): −32,400, −21,600, +50,000, +12,500, −22,500. Sum = −14,000 = Δrevenue.

## 5. Recursion (paper Algorithm 1)

```
C[root] = Δy_root
for each node v, top-down:
    for each dimension d of v:
        effects = local_rule(v, d)          # computed once per dimension, reused for all children
        for each child c in d:
            C[c] = effects[c] * C[v] / Δy_v     if Δy_v ≠ 0
            C[c] = 0                            if Δy_v = 0
report: non-root nodes ranked by |C|
```

Invariant: if Δy_v ≠ 0, then Σ_{c in d} C[c] = C[v], because the local rule's effects sum to Δy_v.
If Δy_v = 0 the children get 0, which equals C[v] only when C[v] = 0 (check in V6).

## 6. Causal correction (paper section 6) — algebra checked, paper not checked

Problem: if price (AUP) changes and that moves units (n), plain splitting can blame n wrongly.
In Markcap: n = Orders, AUP = AOV, link AOV → Orders.

```
f0: fit n_j = f0(AUP_j) on baseline days j = 1..J

Eq. 5 (full), mean per day:
  RC_n = (1/J) Σ_j [ n1_j − f0(AUP1_j) ] · AUP1_j

Eq. 6 (simplified), only if the slope is stable:
  RC_n = (1/J) [ n1_total − Σ_j f0(AUP1_j) ] · AUP1_period

Everything else goes to AUP:   RC_AUP = Δrevenue_per_day − RC_n
Totals: multiply per-day values by J.

Slope test: OLS on both periods pooled
  n = b0 + b1·AUP + b2·I(period=1) + b3·I(period=1)·AUP
  H0: b3 = 0.  If b3 ≠ 0, use Eq. 5.
```

Split of AUP's share (mean level, algebra checked):
direct = n0·ΔAUP, indirect = [f0(AUP1) − n0]·AUP1, and
RC_n + indirect + direct = (n1 − n0)·AUP1 + n0·ΔAUP = Δrevenue. ✔

Test vector (invented): price 100 → 90, units 1000 → 1150, revenue 100,000 → 103,500.
f0(90) = 1150, so RC_n = (1150 − 1150) × 90 = 0. RC_AUP = +3,500 = direct −10,000 + indirect +13,500.
Plain method gives n = +13,500 and AUP = −10,000 (wrong story).

## 7. Simulation study (paper section 7)

- Variables: AUP; units n (depends on AUP); revenue = n × AUP.
- Baseline period: AUP from a normal distribution; n = f(AUP) + normal noise. New period: raise AUP and/or n.
- 100 observations per period, 100 repeated runs, mean with 95% confidence interval.

| Case | Relation f | What changes | True cause |
| --- | --- | --- | --- |
| 1a | linear | only AUP | AUP |
| 1b | linear | AUP and n | AUP and n |
| 2a | quadratic | only AUP | AUP |
| 2b | quadratic | AUP and n | AUP and n |

Methods: truth (from the data-generating process), plain decomposition, GCM (DoWhy, optional),
unified (ours).
Expected pattern (brief, not checked): in 1a and 2a plain wrongly blames n while unified and GCM
are near truth; in 1b and 2b unified is closest to truth.
If GCM is skipped (D11), we can only compare truth, plain and unified, and the label says so.

## 8. Training and loss

None. The only fits are ordinary least squares (f0 and the slope test).

## 9. Numbers and constants

| Name | Value | Source | Checked |
| --- | --- | --- | --- |
| Observations per period (simulation) | 100 | brief §5.5 | NO |
| Repeated runs | 100 | brief §5.5 | NO |
| Confidence interval | 95% | brief §5.5 | NO |
| Time grain J | daily | D3, ASSUMPTION | n/a |
| Additivity tolerance | 1e-9 × max(1, \|Δy\|) | ours (S14) | n/a |
| Slope-test level | 0.05 | ours (S9) | n/a |
| Random seed | chosen in P5, logged | ours | n/a |

## 10. Ambiguity table

| ID | Decision | Status | Evidence | Chosen value | Alternatives | Checked |
| --- | --- | --- | --- | --- | --- | --- |
| S1 | Types 1–4 formulas and which period each factor uses | SPECIFIED | brief §5.2; algebra | section 4 | other period order | NO |
| S2 | Recursion scaling and zero-change rule | SPECIFIED | brief §5.3 | section 5 | none | NO |
| S3 | Local rule computed once per dimension | SPECIFIED | brief §5.3 | as written | none | NO |
| S4 | Which nodes are reported as root causes, and how many | PARTIALLY_SPECIFIED | "largest absolute contribution" | rank all non-root nodes by \|C\|, show top 5 | threshold | NO |
| S5 | How corrected contributions enter the recursion | UNSPECIFIED | brief is silent | replace C for the two linked children (Orders, AOV) with RC values, keep the rest of the recursion | correct only at leaves | NO |
| S6 | Model for f0 | PARTIALLY_SPECIFIED | brief: linear and quadratic in simulation (D4) | OLS polynomial, degree 1 or 2, set in config | splines | NO |
| S7 | Scale of Eq. 5 and 6 | PARTIALLY_SPECIFIED | brief: mean per day | per-day value × J for totals | none | NO |
| S8 | AUP1_period in Eq. 6 | PARTIALLY_SPECIFIED | brief gives the symbol only | period revenue ÷ period units | mean of daily AUP | NO |
| S9 | Slope test: test type, level, quadratic case | UNSPECIFIED | brief gives the linear model only | t-test on b3 at 0.05; for quadratic f0 always use Eq. 5 | F-test | NO |
| S10 | Default estimator | ASSUMPTION | brief: Eq. 6 only if slope stable | always Eq. 5; show Eq. 6 as a cross-check when the slope is stable | follow the test | NO |
| S11 | Day-level split of AUP's share into direct and indirect | PARTIALLY_SPECIFIED | brief gives mean-level form | v1 reports RC_n and RC_AUP only; direct/indirect at mean level | none | NO |
| S12 | Periods with different numbers of days (for example Sept 30 vs Oct 31) | UNSPECIFIED | brief default D6 is month-over-month | v1 requires equal J; the app aligns windows and says so. This changes D6. | per-day averages as the KPI | NO |
| S13 | Daily AOV | ASSUMPTION | none | daily revenue ÷ daily orders; skip days with 0 orders and report them | none | NO |
| S14 | Additivity tolerance | ASSUMPTION | brief says 1e-9 | \|Σ − Δy\| ≤ 1e-9 × max(1, \|Δy\|) | pure absolute | n/a |
| S15 | Zero or negative baseline values; tiny Δy_v | UNSPECIFIED | D7 | flag and skip the node, list it in caveats; treat \|Δy_v\| < 1e-12 as zero | smoothing | NO |
| S16 | effect_type label for Type 1 rows | ASSUMPTION | schema lists volume, rate, share | volume | new label "sum" | n/a |
| S17 | Simulation parameters | UNSPECIFIED | brief: calibrated from real data | chosen in P5, saved in `configs/sim_cases.yaml` | none | NO |
| S18 | True attribution in each case | UNSPECIFIED | brief: known from the data-generating process | defined in P5, written here before any run | none | NO |
| S19 | Error metric and MATCH / PARTIAL MATCH / NOT REPRODUCED rule | UNSPECIFIED | none | written in REPRODUCTION_NOTES before the first run | none | NO |
| S20 | GCM baseline settings | UNSPECIFIED | D11 stretch goal | skip in v1; if added, DoWhy defaults with versions logged | none | NO |
| S21 | Outlier handling | ASSUMPTION | brief: method is outlier-sensitive | none in v1; show a caveat | trimming | NO |

## 11. Paper check list (do when the paper is open)

Replace `Checked = NO` with the section, table or equation number once confirmed.

- Table 1: four rules and the period order (S1)
- Algorithm 1: scaling, zero rule, reporting (S2–S4)
- Eq. 5 and Eq. 6: symbols, scale, AUP1_period (S7, S8)
- Section 6: where corrected contributions enter the tree (S5); slope test text (S9); Theorem 6.1 and Proposition 6.2 conditions (V8, V9)
- Section 7 and appendix: parameters, true attribution, error metric (S17–S19)
- Whether the paper handles periods of different length (S12)
