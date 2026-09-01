"""Characterization tests for the canonical multi-image numeric reconciliation contract."""
import canonical_engine
from tests.test_erss_runtime import eye, result

core = canonical_engine.core


def _numeric_result(filename, field, value, provenance="table"):
    e = eye(True, "NORMAL_SYMMETRIC", filename)
    e[field] = value
    e["field_provenance"] = {field: [filename]}
    e["table_verified_numeric_fields"] = [field] if provenance == "table" else []
    e["map_fallback_numeric_fields"] = [field] if provenance == "fallback" else []
    return result(e, filename)


def test_44_5_vs_44_6_same_provenance_uses_higher():
    merged = core.merge_extractions([
        _numeric_result("a.jpg", "K1_D", 44.5),
        _numeric_result("b.jpg", "K1_D", 44.6),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] == 44.6
    assert not any("K1_D" in str(x) for x in od.get("data_conflicts", []))


def test_exactly_one_percent_full_spread_is_accepted_and_higher_retained():
    merged = core.merge_extractions([
        _numeric_result("a.jpg", "K1_D", 49.5),
        _numeric_result("b.jpg", "K1_D", 50.0),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] == 50.0
    assert not any("K1_D" in str(x) for x in od.get("data_conflicts", []))


def test_lower_is_retained_for_safety_limiting_fields_within_one_percent():
    cases = (("Rmin_mm", 7.03, 7.09, 7.03),)
    for field, first, second, expected in cases:
        merged = core.merge_extractions([
            _numeric_result("a.jpg", field, first),
            _numeric_result("b.jpg", field, second),
        ])
        od = merged["eyes"][0]
        assert od[field] == expected
        assert not any(field in str(x) for x in od.get("data_conflicts", []))


def test_exclusive_labeled_box_fields_retain_first_without_cross_screen_conflict():
    for field, first, second in (
        ("Kmax_D", 47.5, 48.1),
        ("ARTmax_um", 584.0, 600.0),
        ("pachy_thinnest_um", 521.0, 524.0),
    ):
        merged = core.merge_extractions([
            _numeric_result("a.jpg", field, first),
            _numeric_result("b.jpg", field, second),
        ])
        od = merged["eyes"][0]
        assert od[field] == first
        assert not any(field in str(x) for x in od.get("data_conflicts", []))
        assert field not in od.get("numeric_reconciliation", {})


def test_labeled_table_has_priority_over_map_fallback():
    merged = core.merge_extractions([
        _numeric_result("table.jpg", "K1_D", 44.5, "table"),
        _numeric_result("map.jpg", "K1_D", 44.6, "fallback"),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] == 44.5


def test_three_values_with_full_spread_within_one_percent_use_highest():
    merged = core.merge_extractions([
        _numeric_result("a.jpg", "K1_D", 44.50),
        _numeric_result("b.jpg", "K1_D", 44.70),
        _numeric_result("c.jpg", "K1_D", 44.90),
    ])
    od = merged["eyes"][0]
    assert od["K1_D"] == 44.90
    assert not any("K1_D" in str(x) for x in od.get("data_conflicts", []))


def test_full_spread_over_one_percent_is_not_reconciled_even_if_adjacent_pairs_are_close():
    merged = core.merge_extractions([
        _numeric_result("a.jpg", "K1_D", 44.0),
        _numeric_result("b.jpg", "K1_D", 44.3),
        _numeric_result("c.jpg", "K1_D", 44.6),
    ])
    od = merged["eyes"][0]
    assert any("K1_D" in str(x) for x in od.get("data_conflicts", [])) or any(
        "K1_D" in str(x) and "conflict" in str(x).lower()
        for x in merged.get("critical_input_issues", [])
    )
