"""The four local change rules (Types 1 to 4).

Source: Zhou et al., "A Unified Approach to Interpretable Causal Root Cause
Attribution", arXiv:2608.29735, Table 1 (Sec. 3).
This is an independent implementation. It is not the authors' code.

Every rule takes baseline (period 0) and new (period 1) values.
Every rule returns a list of Effect pieces.
The pieces add up exactly to the change in the parent metric.
Bad input raises ValueError. Nothing is fixed silently.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

SHARE_TOL = 1e-9  # shares must add up to 1 within this tolerance


@dataclass(frozen=True)
class Effect:
    """One piece of a parent's change."""

    child: str  # which child the piece belongs to
    effect_type: str  # "change" | "volume" | "rate" | "share"
    value: float  # the piece, in the parent's own unit


def total(effects: Sequence[Effect]) -> float:
    """Sum of all pieces (exact summation). Should equal the parent's change."""
    return math.fsum(e.value for e in effects)


# ---------- input checks (private) ----------


def _vec(name: str, values) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name} must be a non-empty list of numbers")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} has a missing or infinite value")
    return arr


def _num(name: str, value) -> float:
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} must be a finite number")
    return x


def _same_length(**arrays: np.ndarray) -> None:
    sizes = {k: v.size for k, v in arrays.items()}
    if len(set(sizes.values())) != 1:
        raise ValueError(f"inputs must have the same length, got {sizes}")


def _labels(labels: Optional[Sequence[str]], k: int) -> list:
    if labels is None:
        return [str(i) for i in range(k)]
    labels = list(labels)
    if len(labels) != k:
        raise ValueError(f"expected {k} labels, got {len(labels)}")
    return labels


# ---------- the four rules ----------


def decompose_sum(y0, y1, labels=None) -> list:
    """Type 1, sum: y = sum of y_k. (Table 1, row 1)

    Piece for child k = delta y_k.
    """
    y0, y1 = _vec("y0", y0), _vec("y1", y1)
    _same_length(y0=y0, y1=y1)
    names = _labels(labels, y0.size)
    return [Effect(n, "change", float(d)) for n, d in zip(names, y1 - y0)]


def decompose_product(n0, n1, x0, x1) -> list:
    """Type 2, product: y = n * X. (Table 1, row 2; Fig. 1)

    volume (n) = delta n * X1    <- uses the NEW-period X
    rate   (X) = delta X * n0    <- uses the BASELINE n
    """
    n0, n1 = _num("n0", n0), _num("n1", n1)
    x0, x1 = _num("x0", x0), _num("x1", x1)
    return [
        Effect("n", "volume", (n1 - n0) * x1),
        Effect("X", "rate", (x1 - x0) * n0),
    ]


def decompose_sum_of_products(n0, n1, x0, x1, labels=None) -> list:
    """Type 3, sum of products: y = sum of n_k * X_k. (Table 1, row 3)

    volume_k = delta n_k * X_k1
    rate_k   = delta X_k * n_k0
    """
    n0, n1 = _vec("n0", n0), _vec("n1", n1)
    x0, x1 = _vec("x0", x0), _vec("x1", x1)
    _same_length(n0=n0, n1=n1, x0=x0, x1=x1)
    names = _labels(labels, n0.size)
    vol = (n1 - n0) * x1
    rate = (x1 - x0) * n0
    out = []
    for name, v, r in zip(names, vol, rate):
        out.append(Effect(name, "volume", float(v)))
        out.append(Effect(name, "rate", float(r)))
    return out


def decompose_weighted_average(p0, p1, r0, r1, labels=None) -> list:
    """Type 4, weighted-average rate: ybar = sum of p_k * ybar_k. (Table 1, row 4)

    p = shares (must add up to 1 in each period). r = rate of each group.
    share_k = delta p_k * (ybar_k0 - ybar_0)   <- centred on the BASELINE overall rate
    rate_k  = delta ybar_k * p_k1
    ybar_0 is computed here as sum(p0 * r0), which is the paper's definition.
    """
    p0, p1 = _vec("p0", p0), _vec("p1", p1)
    r0, r1 = _vec("r0", r0), _vec("r1", r1)
    _same_length(p0=p0, p1=p1, r0=r0, r1=r1)
    for name, p in (("p0", p0), ("p1", p1)):
        if abs(float(p.sum()) - 1.0) > SHARE_TOL:
            raise ValueError(f"{name} must add up to 1, got {float(p.sum())!r}")
    names = _labels(labels, p0.size)
    overall0 = float(np.dot(p0, r0))
    share = (p1 - p0) * (r0 - overall0)
    rate = (r1 - r0) * p1
    out = []
    for name, s, r in zip(names, share, rate):
        out.append(Effect(name, "share", float(s)))
        out.append(Effect(name, "rate", float(r)))
    return out
