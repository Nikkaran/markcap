# Markcap

**Explain why a KPI moved.**

Markcap takes data for two periods and splits a KPI change (for example revenue) into reasons
whose numbers add up exactly. It also corrects for reasons that affect each other, and writes a
short plain-English summary. Python computes every number. The AI only writes the words.

> **Status: work in progress (P0 setup and P1 spec done).** No paper result is reproduced yet.

## Independent implementation

This is an independent implementation of the method in:

> Zhou, Janzing, Tsang, Blöbaum, Visentini Scarzanella (Amazon).
> *A Unified Approach to Interpretable Causal Root Cause Attribution.*
> KDD '26 Workshop on Two-sided Marketplace Optimization.
> [arXiv:2608.29735](https://arxiv.org/abs/2608.29735)

It is **not** the authors' code. It is not affiliated with Amazon or the authors.

## What it will do

- Split a KPI change over a metric tree (for example Revenue = Orders × AOV).
- Prove the parts add up to the total change.
- Correct for a reason that causes another (for example a price cut that lifts orders).
- Show the result as a table (the driver table, a table of reasons), a waterfall chart and a short summary.

## What it does not do

- It does not reproduce the paper's real-data results (Amazon data is not public).
- It does not use the paper's authors' code.

## Reproduction status

| Paper result | Paper value | Our value | Status |
| --- | --- | --- | --- |
| Sim case 1a (linear, only price changed) | qualitative | - | NOT RUN |
| Sim case 1b (linear, both changed) | qualitative | - | NOT RUN |
| Sim case 2a (quadratic, only price changed) | qualitative | - | NOT RUN |
| Sim case 2b (quadratic, both changed) | qualitative | - | NOT RUN |

Details: [REPRODUCTION_NOTES.md](REPRODUCTION_NOTES.md), [VERIFICATION.md](VERIFICATION.md),
[PAPER_SPEC.md](PAPER_SPEC.md).

## Quick start (Windows, Command Prompt)

```
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## License

MIT. See [LICENSE](LICENSE).
