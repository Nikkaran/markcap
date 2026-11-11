"""Tests for src/markcap/propagate.py and the value checks in tree.py.

Source: arXiv:2608.29735, Algorithm 1 (Appendix A) and Sec. 3.
V5: children add up to the parent inside each dimension.
V6: zero parent change gives zero child contributions.
V7: the root contribution equals the root's delta.
"""
import dataclasses
import math
from pathlib import Path

import numpy as np
import pytest

from markcap.propagate import check_additivity, propagate
from markcap.tree import build_tree, load_tree, member_node_id

CONFIG_FILE = Path(__file__).resolve().parents[1] / "configs" / "metric_tree.yaml"
MEMBERS = {"region": ["North", "South"], "category": ["Electronics", "Accessories"]}


def close(a, b):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def v1_tree():
    return load_tree(CONFIG_FILE, MEMBERS)


def worked_values():
    """The Sept -> Oct example: revenue 500,000 -> 486,000 (change -14,000)."""
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


def leaf_sum(tree, result):
    return math.fsum(result[n].contribution for n in tree.nodes if tree.is_leaf(n))


# ---------- the worked example, by hand ----------


def test_v7_root_contribution_equals_root_delta():
    result = propagate(v1_tree(), worked_values())
    assert result["revenue"].contribution == 486_000 - 500_000
    assert result["revenue"].effect_type == "total"


def test_worked_example_every_piece_matches_hand_calculation():
    r = propagate(v1_tree(), worked_values())
    got = {k: v.contribution for k, v in r.items()}
    want = {
        "orders": -54_000,  # delta orders x NEW AOV = -100 x 540
        "aov": 40_000,  # delta AOV x OLD orders = 40 x 1,000
        member_node_id("orders", "region", "North"): -32_400,  # -60 x 540
        member_node_id("orders", "region", "South"): -21_600,  # -40 x 540
        member_node_id("aov", "category", "Electronics", "share"): 50_000,
        member_node_id("aov", "category", "Accessories", "share"): 12_500,
        member_node_id("aov", "category", "Electronics", "rate"): 0,
        member_node_id("aov", "category", "Accessories", "rate"): -22_500,
    }
    for node_id, value in want.items():
        assert close(got[node_id], value), node_id


def test_worked_example_bottom_pieces_add_up_to_root_delta():
    tree = v1_tree()
    assert close(leaf_sum(tree, propagate(tree, worked_values())), -14_000)


def test_v5_worked_example_adds_up_in_every_dimension():
    tree = v1_tree()
    assert check_additivity(tree, propagate(tree, worked_values())) == []


# ---------- V6: zero change ----------


def test_v6_zero_parent_change_gives_zero_child_contributions():
    # Orders stay at 1,000 but move between regions. AOV rises 500 -> 540.
    vals = worked_values()
    vals["orders"] = (1000, 1000)
    vals["revenue"] = (500_000, 540_000)
    vals[member_node_id("orders", "region", "North")] = (600, 650)
    vals[member_node_id("orders", "region", "South")] = (400, 350)
    tree = v1_tree()
    r = propagate(tree, vals)
    assert r[member_node_id("orders", "region", "North")].contribution == 0
    assert r[member_node_id("orders", "region", "South")].contribution == 0
    assert r["orders"].contribution == 0
    assert close(r["aov"].contribution, 40_000)
    assert check_additivity(tree, r) == []


def test_v6_zero_root_change_gives_all_zero_contributions():
    # Orders halve, AOV doubles. Revenue is 500,000 in both periods.
    vals = {
        "revenue": (500_000, 500_000),
        "orders": (1000, 500),
        "aov": (500, 1000),
        member_node_id("orders", "region", "North"): (600, 300),
        member_node_id("orders", "region", "South"): (400, 200),
        member_node_id("aov", "category", "Electronics", "share"): (0.2, 0.2),
        member_node_id("aov", "category", "Electronics", "rate"): (1500, 3000),
        member_node_id("aov", "category", "Accessories", "share"): (0.8, 0.8),
        member_node_id("aov", "category", "Accessories", "rate"): (250, 500),
    }
    tree = v1_tree()
    r = propagate(tree, vals)
    assert all(c.contribution == 0 for c in r.values())
    assert check_additivity(tree, r) == []


# ---------- V5: random trees ----------


def random_values(rng):
    n_reg, n_cat = int(rng.integers(1, 6)), int(rng.integers(1, 6))
    regions = [f"R{i}" for i in range(n_reg)]
    cats = [f"C{i}" for i in range(n_cat)]
    per_region = rng.uniform(10, 500, (n_reg, 2))
    orders = per_region.sum(axis=0)
    share = rng.random((n_cat, 2))
    share = share / share.sum(axis=0)
    rate = rng.uniform(10, 2000, (n_cat, 2))
    aov = (share * rate).sum(axis=0)
    vals = {"revenue": tuple(orders * aov), "orders": tuple(orders), "aov": tuple(aov)}
    for i, name in enumerate(regions):
        vals[member_node_id("orders", "region", name)] = tuple(per_region[i])
    for i, name in enumerate(cats):
        vals[member_node_id("aov", "category", name, "share")] = tuple(share[i])
        vals[member_node_id("aov", "category", name, "rate")] = tuple(rate[i])
    return {"region": regions, "category": cats}, vals


def test_v5_random_trees_add_up_in_every_dimension():
    rng = np.random.default_rng(5)
    for _ in range(200):
        members, vals = random_values(rng)
        tree = load_tree(CONFIG_FILE, members)
        r = propagate(tree, vals)
        assert check_additivity(tree, r) == []
        delta = vals["revenue"][1] - vals["revenue"][0]
        assert close(r["revenue"].contribution, delta)
        assert close(leaf_sum(tree, r), delta)


# ---------- other rules inside a tree ----------


def test_type3_tree_matches_the_rule_values():
    cfg = {
        "root": "revenue",
        "metrics": {"revenue": {"label": "Revenue"}},
        "decompositions": [
            {"parent": "revenue", "rule": "sum_of_products", "dimension": "product",
             "members_from": "product"},
        ],
    }
    tree = build_tree(cfg, {"product": ["A", "B"]})
    vals = {
        "revenue": (2000, 2320),
        member_node_id("revenue", "product", "A", "n"): (100, 120),
        member_node_id("revenue", "product", "A", "x"): (10, 11),
        member_node_id("revenue", "product", "B", "n"): (50, 40),
        member_node_id("revenue", "product", "B", "x"): (20, 25),
    }
    r = propagate(tree, vals)
    assert close(r[member_node_id("revenue", "product", "A", "n")].contribution, 220)
    assert close(r[member_node_id("revenue", "product", "A", "x")].contribution, 100)
    assert close(r[member_node_id("revenue", "product", "B", "n")].contribution, -250)
    assert close(r[member_node_id("revenue", "product", "B", "x")].contribution, 250)
    assert check_additivity(tree, r) == []


def two_dimension_setup():
    cfg = {
        "root": "orders",
        "metrics": {"orders": {"label": "Orders"}},
        "decompositions": [
            {"parent": "orders", "rule": "sum", "dimension": "region", "members_from": "region"},
            {"parent": "orders", "rule": "sum", "dimension": "channel", "members_from": "channel"},
        ],
    }
    tree = build_tree(cfg, {"region": ["North", "South"], "channel": ["Web", "App"]})
    vals = {
        "orders": (1000, 900),
        member_node_id("orders", "region", "North"): (600, 540),
        member_node_id("orders", "region", "South"): (400, 360),
        member_node_id("orders", "channel", "Web"): (700, 650),
        member_node_id("orders", "channel", "App"): (300, 250),
    }
    return tree, vals


def test_two_dimensions_each_add_up_to_the_parent():
    tree, vals = two_dimension_setup()
    r = propagate(tree, vals)
    assert close(r[member_node_id("orders", "region", "North")].contribution, -60)
    assert close(r[member_node_id("orders", "channel", "Web")].contribution, -50)
    assert close(r[member_node_id("orders", "channel", "App")].contribution, -50)
    assert check_additivity(tree, r) == []


def test_zero_baseline_share_with_filled_rate_still_adds_up():
    # Electronics had no orders in the baseline. Its rate is filled with the new rate
    # (so its rate piece is 0). The pieces must still add up.
    vals = worked_values()
    vals["revenue"] = (250_000, 486_000)
    vals["aov"] = (250, 540)
    vals[member_node_id("aov", "category", "Electronics", "share")] = (0.0, 0.25)
    vals[member_node_id("aov", "category", "Accessories", "share")] = (1.0, 0.75)
    tree = v1_tree()
    r = propagate(tree, vals)
    assert r[member_node_id("aov", "category", "Electronics", "rate")].contribution == 0
    assert check_additivity(tree, r) == []
    assert close(leaf_sum(tree, r), 236_000)


# ---------- the audit must really catch errors ----------


def test_check_additivity_catches_a_wrong_number():
    tree = v1_tree()
    r = propagate(tree, worked_values())
    north = member_node_id("orders", "region", "North")
    r[north] = dataclasses.replace(r[north], contribution=r[north].contribution + 1.0)
    gaps = check_additivity(tree, r)
    assert len(gaps) == 1
    assert gaps[0].parent == "orders" and gaps[0].dimension == "region"


# ---------- bad values must raise ----------


def test_missing_and_unknown_ids_raise():
    vals = worked_values()
    del vals["aov"]
    with pytest.raises(ValueError, match="missing values for: aov"):
        propagate(v1_tree(), vals)
    vals = worked_values()
    vals["typo"] = (1, 2)
    with pytest.raises(ValueError, match="unknown node ids"):
        propagate(v1_tree(), vals)


def test_parts_that_do_not_rebuild_the_parent_raise():
    vals = worked_values()
    vals[member_node_id("orders", "region", "South")] = (400, 300)  # regions now give 840
    with pytest.raises(ValueError, match="'orders' by 'region', new"):
        propagate(v1_tree(), vals)


def test_shares_that_do_not_add_up_to_one_raise():
    vals = worked_values()
    vals[member_node_id("aov", "category", "Accessories", "share")] = (0.80, 0.70)
    with pytest.raises(ValueError, match="shares add up to"):
        propagate(v1_tree(), vals)


def test_nan_and_bad_pairs_raise():
    vals = worked_values()
    vals["orders"] = (1000, float("nan"))
    with pytest.raises(ValueError, match="missing or infinite"):
        propagate(v1_tree(), vals)
    vals = worked_values()
    vals["orders"] = 1000
    with pytest.raises(ValueError, match="pair of numbers"):
        propagate(v1_tree(), vals)
