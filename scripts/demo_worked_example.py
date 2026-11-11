"""Print the Sept -> Oct worked example as a driver table.

Run from the repo folder:   python scripts/demo_worked_example.py
The numbers are invented for teaching. They are not real data.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from markcap.propagate import check_additivity, propagate  # noqa: E402
from markcap.report import driver_table  # noqa: E402
from markcap.tree import load_tree, member_node_id  # noqa: E402

MEMBERS = {"region": ["North", "South"], "category": ["Electronics", "Accessories"]}
tree = load_tree(ROOT / "configs" / "metric_tree.yaml", MEMBERS)

values = {
    "revenue": (500_000, 486_000),
    "orders": (1000, 900),
    "aov": (500, 540),
    member_node_id("orders", "region", "North"): (600, 540),
    member_node_id("orders", "region", "South"): (400, 360),
    member_node_id("aov", "category", "Electronics", "share"): (0.20, 0.25),
    member_node_id("aov", "category", "Electronics", "rate"): (1500, 1500),
    member_node_id("aov", "category", "Accessories", "share"): (0.80, 0.75),
    member_node_id("aov", "category", "Accessories", "rate"): (250, 220),
}

rows = driver_table(tree, values)
print(f"{'rank':>4}  {'reason':<36}{'kind':<8}{'change (Rs)':>12}{'% of total':>12}")
for r in sorted(rows, key=lambda r: (r["rank"] is not None, r["rank"] or 0)):
    rank = "-" if r["rank"] is None else r["rank"]
    pct = "-" if r["pct_of_total_change"] is None else f"{r['pct_of_total_change']:.1f}"
    print(f"{rank:>4}  {r['label']:<36}{r['effect_type']:<8}{r['contribution']:>12,.0f}{pct:>12}")

result = propagate(tree, values)
leaves = [n for n in tree.nodes if tree.is_leaf(n)]
leaf_sum = sum(result[n].contribution for n in leaves)
print()
print(f"Bottom-level pieces add up to: {leaf_sum:,.0f}")
print(f"Observed change in revenue:    {result['revenue'].contribution:,.0f}")
print(f"Gaps found by the audit:       {len(check_additivity(tree, result))}")
