"""The driver table: one row per node, in the schema the app and the narrator read.

Columns: node_id, label, parent_id, dimension, rule_type, effect_type, baseline, new,
delta, contribution, pct_of_total_change, rank.
(rule_type is the Table 1 type number 1 to 4. The root row has effect_type "total".)
"""
from __future__ import annotations

from markcap.propagate import propagate
from markcap.tree import RULE_TYPES, TOL, Tree, check_values

COLUMNS = [
    "node_id", "label", "parent_id", "dimension", "rule_type", "effect_type",
    "baseline", "new", "delta", "contribution", "pct_of_total_change", "rank",
]


def driver_table(tree: Tree, values: dict, tol: float = TOL) -> list:
    """Run the whole method. Returns a list of row dicts (root first, then tree order)."""
    vals = check_values(tree, values, tol)
    contribs = propagate(tree, vals, tol)
    root_delta = contribs[tree.root].contribution

    rows = []

    def add(node_id: str) -> None:
        node = tree.nodes[node_id]
        v0, v1 = vals[node_id]
        c = contribs[node_id]
        pct = (100.0 * c.contribution / root_delta + 0.0) if root_delta else None  # +0.0: no -0.0
        rows.append({
            "node_id": node_id,
            "label": node.label,
            "parent_id": node.parent,
            "dimension": node.dimension,
            "rule_type": RULE_TYPES[node.rule] if node.rule else None,
            "effect_type": c.effect_type,
            "baseline": v0,
            "new": v1,
            "delta": v1 - v0,
            "contribution": c.contribution,
            "pct_of_total_change": pct,
            "rank": None,
        })
        for child in tree.children(node_id):
            add(child.id)

    add(tree.root)
    ranked = sorted(
        (r for r in rows if r["node_id"] != tree.root),
        key=lambda r: abs(r["contribution"]),
        reverse=True,
    )
    for i, r in enumerate(ranked, start=1):
        r["rank"] = i
    return rows
