"""Tests for src/markcap/rules.py. Covers V1 to V4 in VERIFICATION.md.

Source: arXiv:2608.29735, Table 1.
Each test name says which rule or idea it protects.
"""
import math

import numpy as np
import pytest

from markcap.rules import (
    decompose_product,
    decompose_sum,
    decompose_sum_of_products,
    decompose_weighted_average,
    total,
)

N_RANDOM = 500  # random cases per rule


def close(a, b):
    """Relative 1e-9, plus a 1e-9 floor for values near zero."""
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)


def by_key(effects):
    return {(e.child, e.effect_type): e.value for e in effects}


# ---------- V1: Type 1, sum ----------


def test_type1_sum_regions_hand_example():
    # Orders by region: North lost 60, South lost 40.
    effects = decompose_sum([600, 400], [540, 360], labels=["North", "South"])
    got = by_key(effects)
    assert got[("North", "change")] == -60
    assert got[("South", "change")] == -40
    assert total(effects) == -100


def test_type1_random_pieces_add_up_to_delta():
    rng = np.random.default_rng(1)
    for _ in range(N_RANDOM):
        k = int(rng.integers(1, 9))
        y0 = rng.uniform(-1000, 1000, k)
        y1 = rng.uniform(-1000, 1000, k)
        assert close(total(decompose_sum(y0, y1)), y1.sum() - y0.sum())


# ---------- V2: Type 2, product ----------


def test_type2_hand_example_sept_to_oct():
    # 1,000 orders x Rs 500  ->  900 orders x Rs 540
    got = by_key(decompose_product(1000, 900, 500, 540))
    assert got[("n", "volume")] == -54_000  # delta n * NEW X
    assert got[("X", "rate")] == 40_000  # delta X * BASELINE n
    assert got[("n", "volume")] + got[("X", "rate")] == 486_000 - 500_000


def test_type2_plain_method_credits_units_in_price_cut_example():
    # Price Rs 100 -> 90, units 1,000 -> 1,150. Revenue change +3,500.
    # The plain rule gives units +13,500 and price -10,000.
    # (The causal fix in P4 will correct this. P2 only checks the plain rule.)
    got = by_key(decompose_product(1000, 1150, 100, 90))
    assert got[("n", "volume")] == 13_500
    assert got[("X", "rate")] == -10_000
    assert total(decompose_product(1000, 1150, 100, 90)) == 3_500


def test_type2_uses_new_x_for_volume_and_old_n_for_rate():
    got = by_key(decompose_product(10, 20, 2, 3))
    assert got[("n", "volume")] == (20 - 10) * 3  # X1, not X0
    assert got[("X", "rate")] == (3 - 2) * 10  # n0, not n1


def test_type2_zero_baseline_volume_still_adds_up():
    # n0 = 0 is allowed here. The pieces still add up.
    effects = decompose_product(0, 5, 7, 9)
    assert close(total(effects), 5 * 9 - 0 * 7)


def test_type2_random_pieces_add_up_to_delta():
    rng = np.random.default_rng(2)
    for _ in range(N_RANDOM):
        n0, n1 = rng.uniform(1, 1000, 2)
        x0, x1 = rng.uniform(1, 100, 2)
        assert close(total(decompose_product(n0, n1, x0, x1)), n1 * x1 - n0 * x0)


# ---------- V3: Type 3, sum of products ----------


def test_type3_two_products_hand_example():
    # A: n 100->120, X 10->11.  B: n 50->40, X 20->25.  Revenue 2,000 -> 2,320.
    effects = decompose_sum_of_products(
        [100, 50], [120, 40], [10, 20], [11, 25], labels=["A", "B"]
    )
    got = by_key(effects)
    assert got[("A", "volume")] == 20 * 11
    assert got[("A", "rate")] == 1 * 100
    assert got[("B", "volume")] == -10 * 25
    assert got[("B", "rate")] == 5 * 50
    assert total(effects) == 2_320 - 2_000


def test_type3_random_pieces_add_up_to_delta():
    rng = np.random.default_rng(3)
    for _ in range(N_RANDOM):
        k = int(rng.integers(1, 9))
        n0, n1 = rng.uniform(1, 1000, k), rng.uniform(1, 1000, k)
        x0, x1 = rng.uniform(1, 100, k), rng.uniform(1, 100, k)
        want = float(np.dot(n1, x1) - np.dot(n0, x0))
        assert close(total(decompose_sum_of_products(n0, n1, x0, x1)), want)


# ---------- V4: Type 4, weighted average ----------


def test_type4_category_hand_example():
    # Electronics share 20% -> 25%, rate 1,500 both months.
    # Accessories share 80% -> 75%, rate 250 -> 220.
    # AOV goes from 500 to 540. Change = +40.
    effects = decompose_weighted_average(
        [0.20, 0.80],
        [0.25, 0.75],
        [1500, 250],
        [1500, 220],
        labels=["Electronics", "Accessories"],
    )
    got = by_key(effects)
    assert close(got[("Electronics", "share")], 50.0)
    assert close(got[("Accessories", "share")], 12.5)
    assert close(got[("Electronics", "rate")], 0.0)
    assert close(got[("Accessories", "rate")], -22.5)
    assert close(total(effects), 40.0)


def test_type4_random_shares_and_rates_add_up_to_delta():
    rng = np.random.default_rng(4)
    for _ in range(N_RANDOM):
        k = int(rng.integers(2, 9))
        p0 = rng.random(k)
        p0 /= p0.sum()
        p1 = rng.random(k)
        p1 /= p1.sum()
        r0, r1 = rng.uniform(1, 1000, k), rng.uniform(1, 1000, k)
        want = float(np.dot(p1, r1) - np.dot(p0, r0))
        assert close(total(decompose_weighted_average(p0, p1, r0, r1)), want)


def test_type4_unchanged_rates_and_shares_give_zero_pieces():
    effects = decompose_weighted_average([0.5, 0.5], [0.5, 0.5], [10, 20], [10, 20])
    assert all(e.value == 0 for e in effects)


# ---------- bad input must raise, never be fixed silently ----------


def test_type4_rejects_shares_that_do_not_add_up_to_one():
    with pytest.raises(ValueError):
        decompose_weighted_average([0.5, 0.4], [0.5, 0.5], [1, 2], [1, 2])
    with pytest.raises(ValueError):
        decompose_weighted_average([0.5, 0.5], [0.6, 0.5], [1, 2], [1, 2])


def test_rules_reject_different_lengths():
    with pytest.raises(ValueError):
        decompose_sum([1, 2], [1])
    with pytest.raises(ValueError):
        decompose_sum_of_products([1, 2], [1, 2], [1, 2], [1])


def test_rules_reject_nan_and_infinity():
    with pytest.raises(ValueError):
        decompose_sum([1, float("nan")], [1, 2])
    with pytest.raises(ValueError):
        decompose_product(1, 2, float("inf"), 3)


def test_rules_reject_empty_input():
    with pytest.raises(ValueError):
        decompose_sum([], [])


def test_rules_reject_wrong_number_of_labels():
    with pytest.raises(ValueError):
        decompose_sum([1, 2], [3, 4], labels=["only one"])
