"""Equivalence-oriented tests for the clean reconciliation primitive."""
from clean_engine.reconciliation import (
    LABELED_TABLE,
    PERMITTED_MAP_FALLBACK,
    NumericObservation,
    reconcile_numeric,
    within_one_percent,
)


def obs(value, source=LABELED_TABLE):
    return NumericObservation(value, source)


def test_locked_examples():
    assert reconcile_numeric([obs(44.5), obs(44.6)]) == 44.6
    assert reconcile_numeric([obs(49.5), obs(50.0)]) == 50.0
    assert reconcile_numeric([obs(44.50), obs(44.70), obs(44.90)]) == 44.90


def test_safety_limiting_lower_fields_use_lower_within_one_percent():
    for field, values, expected in (
        ("pachy_thinnest_um", (500.0, 504.0), 500.0),
        ("ARTmax_um", (350.0, 353.0), 350.0),
        ("Rmin_mm", (7.03, 7.09), 7.03),
    ):
        assert reconcile_numeric([obs(value) for value in values], field=field) == expected


def test_full_spread_not_adjacent_pairs_controls_acceptance():
    assert reconcile_numeric([obs(44.0), obs(44.3), obs(44.6)]) is None


def test_old_ten_micron_pachymetry_rule_is_not_present():
    assert reconcile_numeric([obs(500.0), obs(509.0)]) is None


def test_labeled_table_priority_over_map_fallback():
    assert reconcile_numeric([
        obs(44.5, LABELED_TABLE),
        obs(44.6, PERMITTED_MAP_FALLBACK),
    ]) == 44.5


def test_map_fallback_can_reconcile_when_no_labeled_table_exists():
    assert reconcile_numeric([
        obs(44.5, PERMITTED_MAP_FALLBACK),
        obs(44.6, PERMITTED_MAP_FALLBACK),
    ]) == 44.6


def test_one_percent_math_boundary():
    assert within_one_percent([49.5, 50.0])
    assert not within_one_percent([49.49, 50.0])
