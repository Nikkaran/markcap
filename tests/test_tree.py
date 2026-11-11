"""Tests for src/markcap/tree.py. Source: arXiv:2608.29735, Sec. 3 (tree, type(c), dim(c), MECE)."""
import copy
from pathlib import Path

import pytest

from markcap.tree import build_tree, load_tree, member_node_id

CONFIG_FILE = Path(__file__).resolve().parents[1] / "configs" / "metric_tree.yaml"
MEMBERS = {"region": ["North", "South"], "category": ["Electronics", "Accessories"]}


def base_config():
    return {
        "root": "revenue",
        "metrics": {
            "revenue": {"label": "Revenue"},
            "orders": {"label": "Orders"},
            "aov": {"label": "Average order value"},
        },
        "decompositions": [
            {"parent": "revenue", "rule": "product", "dimension": "split",
             "n_metric": "orders", "x_metric": "aov"},
            {"parent": "orders", "rule": "sum", "dimension": "region",
             "members_from": "region"},
            {"parent": "aov", "rule": "weighted_average", "dimension": "category",
             "members_from": "category"},
        ],
    }


def test_yaml_file_builds_the_v1_tree():
    tree = load_tree(CONFIG_FILE, MEMBERS)
    assert tree.root == "revenue"
    assert len(tree.nodes) == 9  # 3 metrics + 2 regions + 2 categories x 2 roles
    assert tree.dimensions("revenue") == ["orders_x_aov"]
    assert [k.id for k in tree.children("revenue")] == ["orders", "aov"]
    assert [k.role for k in tree.children("revenue")] == ["n", "x"]
    assert tree.nodes["orders"].rule == "product"  # Type 2 links Orders to Revenue


def test_member_node_ids_are_predictable():
    tree = load_tree(CONFIG_FILE, MEMBERS)
    assert member_node_id("orders", "region", "North") in tree.nodes
    assert member_node_id("aov", "category", "Electronics", "share") in tree.nodes
    assert member_node_id("aov", "category", "Accessories", "rate") in tree.nodes
    assert member_node_id("orders", "region", "North") == "orders|region=North"


def test_leaves_are_the_member_nodes():
    tree = load_tree(CONFIG_FILE, MEMBERS)
    leaves = {n for n in tree.nodes if tree.is_leaf(n)}
    assert len(leaves) == 6
    assert "orders" not in leaves and "revenue" not in leaves


def test_member_names_are_taken_as_text():
    tree = build_tree(base_config(), {"region": [1, 2], "category": ["A", "B"]})
    assert member_node_id("orders", "region", "1") in tree.nodes


def test_missing_members_raise():
    with pytest.raises(ValueError, match="no members given for 'category'"):
        build_tree(base_config(), {"region": ["North"]})


def test_empty_or_duplicate_members_raise():
    with pytest.raises(ValueError, match="has no members"):
        build_tree(base_config(), {"region": [], "category": ["A"]})
    with pytest.raises(ValueError, match="duplicate members"):
        build_tree(base_config(), {"region": ["N", "N"], "category": ["A"]})


def test_unknown_rule_parent_or_key_raise():
    cfg = base_config()
    cfg["decompositions"][1]["rule"] = "average"
    with pytest.raises(ValueError, match="unknown rule"):
        build_tree(cfg, MEMBERS)
    cfg = base_config()
    cfg["decompositions"][1]["parent"] = "nothing"
    with pytest.raises(ValueError, match="unknown parent"):
        build_tree(cfg, MEMBERS)
    cfg = base_config()
    cfg["decompositions"][1]["membres_from"] = "region"
    with pytest.raises(ValueError, match="unknown key"):
        build_tree(cfg, MEMBERS)


def test_root_must_be_listed():
    cfg = base_config()
    cfg["root"] = "profit"
    with pytest.raises(ValueError, match="not listed under metrics"):
        build_tree(cfg, MEMBERS)


def test_metric_that_is_not_attached_raises():
    cfg = base_config()
    cfg["metrics"]["lonely"] = {"label": "Lonely"}
    with pytest.raises(ValueError, match="not attached"):
        build_tree(cfg, MEMBERS)


def test_metric_cannot_be_a_child_twice():
    cfg = base_config()
    cfg["metrics"]["extra"] = {"label": "Extra"}
    cfg["decompositions"].append(
        {"parent": "aov", "rule": "product", "dimension": "again",
         "n_metric": "orders", "x_metric": "extra"}
    )
    with pytest.raises(ValueError, match="already a child"):
        build_tree(cfg, MEMBERS)


def test_n_and_x_must_differ_and_root_cannot_be_a_child():
    cfg = base_config()
    cfg["decompositions"][0]["x_metric"] = "orders"
    with pytest.raises(ValueError, match="must be different"):
        build_tree(cfg, MEMBERS)
    cfg = base_config()
    cfg["decompositions"][0]["n_metric"] = "revenue"
    with pytest.raises(ValueError, match="cannot be a child of itself"):
        build_tree(cfg, MEMBERS)


def test_same_dimension_twice_under_one_parent_raises():
    cfg = base_config()
    cfg["decompositions"].append(copy.deepcopy(cfg["decompositions"][1]))
    with pytest.raises(ValueError, match="used twice"):
        build_tree(cfg, MEMBERS)


def test_two_different_dimensions_under_one_parent_are_allowed():
    cfg = {
        "root": "orders",
        "metrics": {"orders": {"label": "Orders"}},
        "decompositions": [
            {"parent": "orders", "rule": "sum", "dimension": "region", "members_from": "region"},
            {"parent": "orders", "rule": "sum", "dimension": "channel", "members_from": "channel"},
        ],
    }
    tree = build_tree(cfg, {"region": ["N", "S"], "channel": ["Web", "App"]})
    assert tree.dimensions("orders") == ["region", "channel"]
