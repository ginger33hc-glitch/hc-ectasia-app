"""Direct equivalence tests for clean ablation selection."""
import canonical_engine

from clean_engine.ablation import select_ablation

legacy = canonical_engine.core


def legacy_value(actual, sphere, cylinder, zone, platform):
    warnings = []
    return legacy.estimate_ablation({
        "ablation_um": actual,
        "intended_sphere_D": sphere,
        "intended_cylinder_magnitude_D": cylinder,
        "optical_zone_mm": zone,
        "laser_platform": platform,
    }, warnings)


def clean_value(actual, sphere, cylinder, zone, platform):
    return select_ablation(
        actual_ablation_um=actual,
        intended_sphere_d=sphere,
        intended_cylinder_magnitude_d=cylinder,
        optical_zone_mm=zone,
        laser_platform=platform,
    ).ablation_um


def test_actual_ablation_precedence_and_range_match_runtime():
    for actual in (0, 60, 400, -0.001, 400.001, "bad"):
        assert clean_value(actual, -3, 1, 6.5, "Alcon EX500") == legacy_value(actual, -3, 1, 6.5, "Alcon EX500")


def test_ex500_zone_specific_estimates_match_runtime():
    for zone in (6.0, 6.5, 7.0):
        assert clean_value(None, -3, 1, zone, "Alcon EX500") == legacy_value(None, -3, 1, zone, "Alcon EX500")


def test_platform_normalization_matches_runtime():
    for platform in ("Alcon EX500", "alconex500", "ALCON EX500", "Other Laser", None):
        assert clean_value(None, -3, 1, 6.5, platform) == legacy_value(None, -3, 1, 6.5, platform)


def test_hyperopic_or_mixed_positive_sphere_requires_actual_ablation():
    assert clean_value(None, 2, 1, 6.5, "Alcon EX500") is None
    assert clean_value(None, 2, 1, 6.5, "Alcon EX500") == legacy_value(None, 2, 1, 6.5, "Alcon EX500")


def test_missing_or_unsupported_estimate_inputs_match_runtime():
    cases = [
        (None, None, 1, 6.5, "Alcon EX500"),
        (None, -3, None, 6.5, "Alcon EX500"),
        (None, -3, 1, 6.25, "Alcon EX500"),
        (None, -3, 1, 6.5, "Other"),
    ]
    for args in cases:
        assert clean_value(*args) == legacy_value(*args)
