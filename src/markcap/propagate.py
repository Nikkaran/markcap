"""Recursive change decomposition (the paper's Algorithm 1, Appendix A).

Source: Zhou et al., arXiv:2608.29735, Sec. 3 and Algorithm 1.
Independent implementation. Not the authors' code.

C_root = delta y_root.
For each parent v, each dimension k, and each child c in k:
    C_c = contrib_c * C_v / delta y_v     if delta y_v != 0   (Algorithm 1, line 10)
    C_c = 0                               otherwise           (Algorithm 1, line 12)
The local rule (rules.py) is run once per dimension and reused for all its children.
Result: inside each dimension, the children's contributions add up to the parent's.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from markcap import rules
from markcap.tree import ROLE_OF_EFFECT, TOL, Tree, check_values


@dataclass(frozen=True)
class Contribution:
    node_id: str
    effect_type: str  # "total" for the root, else "change", "volume", "rate" or "share"
    local: float  # the piece from the local rule, before scaling
    contribution: float  # C_c, after scaling by C_v / delta y_v


@dataclass(frozen=True)
class Gap:
    parent: str
    dimension: str
    children_sum: float
    parent_contribution: float


def _node_id(kids, group, role) -> str:
    for k in kids:
        if k.group == group and k.role == role:
            return k.id
    raise KeyError((group, role))


def _local_effects(tree: Tree, vals: dict, parent: str, dim: str) -> list:
    """Run the local rule once for one dimension. Returns [(child_id, Effect)]."""
    kids = tree.children(parent, dim)
    rule = kids[0].rule
    by = {(k.group, k.role): vals[k.id] for k in kids}
    groups = list(dict.fromkeys(k.group for k in kids))

    def col(role: str, t: int) -> list:
        return [by[(g, role)][t] for g in groups]

    if rule == "sum":
        effects = rules.decompose_sum(col("y", 0), col("y", 1), labels=groups)
    elif rule == "product":
        n0, n1 = by[(None, "n")]
        x0, x1 = by[(None, "x")]
        effects = rules.decompose_product(n0, n1, x0, x1)
    elif rule == "sum_of_products":
        effects = rules.decompose_sum_of_products(
            col("n", 0), col("n", 1), col("x", 0), col("x", 1), labels=groups
        )
    else:  # weighted_average
        effects = rules.decompose_weighted_average(
            col("share", 0), col("share", 1), col("rate", 0), col("rate", 1), labels=groups
        )
    out = []
    for e in effects:
        group = None if rule == "product" else e.child
        out.append((_node_id(kids, group, ROLE_OF_EFFECT[rule][e.effect_type]), e))
    return out


def propagate(tree: Tree, values: dict, tol: float = TOL) -> dict:
    """Return {node_id: Contribution} for every node, root included."""
    vals = check_values(tree, values, tol)
    d_root = vals[tree.root][1] - vals[tree.root][0]
    out = {tree.root: Contribution(tree.root, "total", d_root, d_root)}

    def visit(v: str) -> None:
        c_v = out[v].contribution
        d_v = vals[v][1] - vals[v][0]
        for dim in tree.dimensions(v):
            for child_id, eff in _local_effects(tree, vals, v, dim):
                scaled = eff.value * (c_v / d_v) if d_v != 0 else 0.0
                out[child_id] = Contribution(child_id, eff.effect_type, eff.value, scaled)
        for child in tree.children(v):
            visit(child.id)

    visit(tree.root)
    return out


def check_additivity(tree: Tree, contributions: dict, tol: float = TOL) -> list:
    """Audit: in every dimension, do the children add up to the parent? Returns the gaps."""
    gaps = []
    for parent in tree.nodes:
        for dim in tree.dimensions(parent):
            total = math.fsum(contributions[k.id].contribution for k in tree.children(parent, dim))
            want = contributions[parent].contribution
            if not math.isclose(total, want, rel_tol=tol, abs_tol=tol):
                gaps.append(Gap(parent, dim, total, want))
    return gaps
