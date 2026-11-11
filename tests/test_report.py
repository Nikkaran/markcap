"""Tests for src/markcap/report.py (the driver table)."""
import math
from pathlib import Path

from markcap.report import COLUMNS, driver_table
from markcap.tree import load_tree, member_node_id

CONFIG_FILE = Path(__file__).resolve().parents[1] / "configs" / "metric_tree.yaml"
MEMBERS = {"region": ["North", "South"], "category": ["Electronics", "Accessories"]}


def worked_values():
    return {
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


def table():
    return driver_table(load_tree(CONFIG_FILE, MEMBERS), worked_values())


def test_one_row_per_node_with_the_agreed_columns():
    rows = table()
    assert len(rows) == 9
    assert all(list(r.keys()) == COLUMNS for r in rows)
    assert rows[0]["node_id"] == "revenue"


def test_root_row_holds_the_total_change():
    root = table()[0]
    assert root["effect_type"] == "total"
    assert root["contribution"] == -14_000
    assert root["pct_of_total_change"] == 100.0
    assert root["rank"] is None
    assert root["parent_id"] is None and root["rule_type"] is None


def test_rank_one_is_the_largest_absolute_contribution():
    rows = table()
    by_rank = {r["rank"]: r for r in rows if r["rank"] is not None}
    assert sorted(by_rank) == list(range(1, 9))
    assert by_rank[1]["node_id"] == "orders"  # |-54,000| is the largest
    sizes = [abs(by_rank[i]["contribution"]) for i in range(1, 9)]
    assert sizes == sorted(sizes, reverse=True)


def test_percentages_of_each_dimension_add_up_to_100():
    rows = table()
    top = [r for r in rows if r["parent_id"] == "revenue"]
    assert math.isclose(sum(r["pct_of_total_change"] for r in top), 100.0, abs_tol=1e-9)


def test_rule_type_is_the_table_1_number():
    rows = {r["node_id"]: r for r in table()}
    assert rows["orders"]["rule_type"] == 2
    assert rows[member_node_id("orders", "region", "North")]["rule_type"] == 1
    assert rows[member_node_id("aov", "category", "Electronics", "share")]["rule_type"] == 4


def test_percent_is_none_when_the_total_change_is_zero():
    vals = worked_values()
    vals["revenue"] = (500_000, 500_000)
    vals["orders"] = (1000, 500)
    vals["aov"] = (500, 1000)
    vals[member_node_id("orders", "region", "North")] = (600, 300)
    vals[member_node_id("orders", "region", "South")] = (400, 200)
    vals[member_node_id("aov", "category", "Electronics", "share")] = (0.2, 0.2)
    vals[member_node_id("aov", "category", "Electronics", "rate")] = (1500, 3000)
    vals[member_node_id("aov", "category", "Accessories", "share")] = (0.8, 0.8)
    vals[member_node_id("aov", "category", "Accessories", "rate")] = (250, 500)
    rows = driver_table(load_tree(CONFIG_FILE, MEMBERS), vals)
    assert all(r["pct_of_total_change"] is None for r in rows)
    assert all(r["contribution"] == 0 for r in rows)
