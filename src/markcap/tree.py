"""Metric tree: nodes, YAML config loader, and number checks.

Source: Zhou et al., arXiv:2608.29735, Sec. 3 (metric tree T with root r; each
child c has a rule type(c) and a dimension label dim(c); the MECE principle).
Independent implementation. Not the authors' code.

Two kinds of node:
  - named metrics from the config (revenue, orders, aov). They can have children.
  - member nodes made from data members (regions, categories). They are leaves.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

TOL = 1e-9  # relative tolerance (plus a 1e-9 floor) for every "adds up" check

# rule name -> Table 1 type number
RULE_TYPES = {"sum": 1, "product": 2, "sum_of_products": 3, "weighted_average": 4}
# the jobs a child can do inside each rule
ROLES = {
    "sum": ("y",),
    "product": ("n", "x"),
    "sum_of_products": ("n", "x"),
    "weighted_average": ("share", "rate"),
}
# rules.py effect_type -> role of the child that receives that piece
ROLE_OF_EFFECT = {
    "sum": {"change": "y"},
    "product": {"volume": "n", "rate": "x"},
    "sum_of_products": {"volume": "n", "rate": "x"},
    "weighted_average": {"share": "share", "rate": "rate"},
}
GROUPED = ("sum", "sum_of_products", "weighted_average")  # rules that have members


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    parent: str | None = None  # None only for the root
    rule: str | None = None  # rule that links this node to its parent
    dimension: str | None = None  # dim(c) in the paper
    role: str | None = None  # "n", "x", "y", "share" or "rate"
    group: str | None = None  # the member (region, category), if the rule has members


def member_node_id(parent: str, dimension: str, member: str, role: str | None = None) -> str:
    """The id of a member node. The data code (P6) uses this to key its values."""
    base = f"{parent}|{dimension}={member}"
    return base if role is None else f"{base}|{role}"


class Tree:
    """A checked metric tree. Children keep the order they were built in."""

    def __init__(self, root: str, nodes: Sequence[Node]):
        self.root = root
        self.nodes = {n.id: n for n in nodes}
        if len(self.nodes) != len(nodes):
            raise ValueError("two nodes have the same id")
        self._children = {nid: [] for nid in self.nodes}
        for n in nodes:
            if n.parent in self._children:
                self._children[n.parent].append(n)
        self._check_structure()

    def children(self, node_id: str, dimension: str | None = None) -> list:
        kids = self._children[node_id]
        return kids if dimension is None else [k for k in kids if k.dimension == dimension]

    def dimensions(self, node_id: str) -> list:
        return list(dict.fromkeys(k.dimension for k in self._children[node_id]))

    def is_leaf(self, node_id: str) -> bool:
        return not self._children[node_id]

    def _check_structure(self) -> None:
        roots = [n.id for n in self.nodes.values() if n.parent is None]
        if roots != [self.root]:
            raise ValueError(f"the tree must have exactly one root '{self.root}', got {roots}")
        for n in self.nodes.values():
            if n.parent is None:
                continue
            if n.parent not in self.nodes:
                raise ValueError(f"node '{n.id}' has unknown parent '{n.parent}'")
            if n.rule not in RULE_TYPES:
                raise ValueError(f"node '{n.id}' has unknown rule '{n.rule}'")
            if not n.dimension:
                raise ValueError(f"node '{n.id}' has no dimension")
            if n.role not in ROLES[n.rule]:
                raise ValueError(f"node '{n.id}' has role '{n.role}', wrong for '{n.rule}'")
        for n in self.nodes.values():  # every node must lead up to the root
            seen, cur = set(), n.id
            while cur != self.root:
                if cur in seen:
                    raise ValueError(f"node '{n.id}' is in a loop")
                seen.add(cur)
                cur = self.nodes[cur].parent
        for parent in self.nodes:
            for dim in self.dimensions(parent):
                self._check_dimension(parent, dim)

    def _check_dimension(self, parent: str, dim: str) -> None:
        kids = self.children(parent, dim)
        rules = {k.rule for k in kids}
        if len(rules) != 1:
            raise ValueError(f"'{parent}' by '{dim}' mixes rules {sorted(rules)}")
        rule = kids[0].rule
        slots = [(k.group, k.role) for k in kids]
        if len(set(slots)) != len(slots):
            raise ValueError(f"'{parent}' by '{dim}' has a repeated member or role")
        groups = list(dict.fromkeys(k.group for k in kids))
        if rule == "product":
            ok = groups == [None] and sorted(k.role for k in kids) == ["n", "x"]
        else:
            ok = None not in groups and all(
                sorted(k.role for k in kids if k.group == g) == sorted(ROLES[rule])
                for g in groups
            )
        if not ok:
            raise ValueError(f"'{parent}' by '{dim}' lacks the children rule '{rule}' needs")


# ---------- config -> tree ----------

_DECOMP_KEYS = {"parent", "rule", "dimension", "n_metric", "x_metric", "members_from"}


def load_config(path) -> dict:
    import yaml  # imported here so build_tree works without PyYAML

    with open(Path(path), encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, Mapping):
        raise ValueError("the config file must hold a mapping at the top level")
    return config


def load_tree(path, members: Mapping[str, Sequence[str]] | None = None) -> Tree:
    return build_tree(load_config(path), members)


def build_tree(config: Mapping, members: Mapping[str, Sequence[str]] | None = None) -> Tree:
    """Build a Tree from a config dict. `members` names the regions, categories, etc."""
    members = members or {}
    metrics = config.get("metrics")
    if not isinstance(metrics, Mapping) or not metrics:
        raise ValueError("the config needs a 'metrics' section")
    labels = {}
    for mid, spec in metrics.items():
        label = spec.get("label") if isinstance(spec, Mapping) else None
        labels[str(mid)] = str(label or mid)
    root = str(config.get("root"))
    if root not in labels:
        raise ValueError(f"root '{root}' is not listed under metrics")

    nodes = [Node(root, labels[root])]
    placed = set()
    used_dims = set()
    for i, d in enumerate(config.get("decompositions") or [], start=1):
        extra = set(d) - _DECOMP_KEYS
        if extra:
            raise ValueError(f"unknown key(s) in decomposition {i}: {sorted(extra)}")
        parent, rule, dim = d.get("parent"), d.get("rule"), d.get("dimension")
        if parent not in labels:
            raise ValueError(f"decomposition {i} has unknown parent '{parent}'")
        if rule not in RULE_TYPES:
            raise ValueError(f"decomposition {i} has unknown rule '{rule}'")
        if not dim:
            raise ValueError(f"decomposition {i} needs a dimension")
        if (parent, dim) in used_dims:
            raise ValueError(f"dimension '{dim}' is used twice under '{parent}'")
        used_dims.add((parent, dim))

        if rule == "product":
            n_m, x_m = d.get("n_metric"), d.get("x_metric")
            for m in (n_m, x_m):
                if m not in labels:
                    raise ValueError(f"decomposition {i} uses unknown metric '{m}'")
                if m == parent:
                    raise ValueError(f"metric '{m}' cannot be a child of itself")
                if m == root:
                    raise ValueError(f"root '{root}' cannot be a child")
                if m in placed:
                    raise ValueError(f"metric '{m}' is already a child of another node")
            if n_m == x_m:
                raise ValueError(f"decomposition {i}: n_metric and x_metric must be different")
            placed.update((n_m, x_m))
            nodes.append(Node(n_m, labels[n_m], parent, rule, dim, "n"))
            nodes.append(Node(x_m, labels[x_m], parent, rule, dim, "x"))
            continue

        name = d.get("members_from")
        if name not in members:
            raise ValueError(
                f"no members given for '{name}' (needed by '{parent}'); "
                f"pass members={{'{name}': [...]}}"
            )
        names = [str(m).strip() for m in members[name]]
        if not names or "" in names:
            raise ValueError(f"'{name}' has no members, or an empty member name")
        if len(set(names)) != len(names):
            raise ValueError(f"'{name}' has duplicate members")
        plabel = labels[parent]
        for m in names:
            if rule == "sum":
                mid = member_node_id(parent, dim, m)
                nodes.append(Node(mid, f"{plabel} - {m}", parent, rule, dim, "y", m))
                continue
            first, second = ("share", "rate") if rule == "weighted_average" else ("n", "x")
            text = {
                "share": f"{m}: share",
                "rate": f"{m}: {plabel}",
                "n": f"{m}: volume",
                "x": f"{m}: rate",
            }
            for role in (first, second):
                mid = member_node_id(parent, dim, m, role)
                nodes.append(Node(mid, text[role], parent, rule, dim, role, m))

    for m in labels:
        if m != root and m not in placed:
            raise ValueError(f"metric '{m}' is not attached to the tree")
    return Tree(root, nodes)


# ---------- number checks (the MECE idea, checked on real values) ----------


def _show(items, n=5) -> str:
    items = [str(i) for i in items]
    more = f" (+{len(items) - n} more)" if len(items) > n else ""
    return ", ".join(items[:n]) + more


def _parts_total(rule: str, kids, vals, t: int) -> float:
    by = {(k.group, k.role): vals[k.id][t] for k in kids}
    groups = list(dict.fromkeys(k.group for k in kids))
    if rule == "sum":
        return math.fsum(by[(g, "y")] for g in groups)
    if rule == "product":
        return by[(None, "n")] * by[(None, "x")]
    if rule == "sum_of_products":
        return math.fsum(by[(g, "n")] * by[(g, "x")] for g in groups)
    return math.fsum(by[(g, "share")] * by[(g, "rate")] for g in groups)


def check_values(tree: Tree, values: Mapping, tol: float = TOL) -> dict:
    """Check that the numbers fit the tree. Returns clean floats, or raises ValueError.

    values: {node_id: (baseline, new)} for every node.
    Checks: no missing or extra ids, finite numbers, and in both periods the
    children rebuild their parent (exclusive and exhaustive, in the numbers).
    """
    problems = []
    missing = [i for i in tree.nodes if i not in values]
    if missing:
        problems.append(f"missing values for: {_show(missing)}")
    extra = [k for k in values if k not in tree.nodes]
    if extra:
        problems.append(f"unknown node ids in values: {_show(extra)}")
    clean = {}
    for nid, pair in values.items():
        if nid not in tree.nodes:
            continue
        try:
            a, b = pair
            v0, v1 = float(a), float(b)
        except (TypeError, ValueError):
            problems.append(f"'{nid}' must be a (baseline, new) pair of numbers")
            continue
        if not (math.isfinite(v0) and math.isfinite(v1)):
            problems.append(f"'{nid}' has a missing or infinite value")
            continue
        clean[nid] = (v0, v1)
    if problems:
        raise ValueError("values do not fit the tree:\n" + "\n".join(problems))

    for parent in tree.nodes:
        for dim in tree.dimensions(parent):
            kids = tree.children(parent, dim)
            rule = kids[0].rule
            for t, period in ((0, "baseline"), (1, "new")):
                whole = clean[parent][t]
                parts = _parts_total(rule, kids, clean, t)
                if not math.isclose(parts, whole, rel_tol=tol, abs_tol=tol):
                    problems.append(
                        f"'{parent}' by '{dim}', {period}: the parts give {parts!r} "
                        f"but '{parent}' is {whole!r}"
                    )
                if rule == "weighted_average":
                    shares = math.fsum(clean[k.id][t] for k in kids if k.role == "share")
                    if not math.isclose(shares, 1.0, rel_tol=tol, abs_tol=tol):
                        problems.append(
                            f"'{parent}' by '{dim}', {period}: shares add up to {shares!r}, not 1"
                        )
    if problems:
        raise ValueError("values do not fit the tree:\n" + "\n".join(problems))
    return clean
