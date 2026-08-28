"""Characterize the refraction boundary before production shadow wiring."""
from clean_engine.refraction_boundary import (
    classify_normalized_refraction,
    clean_refraction_compatibility,
)


def test_normalized_minus_cylinder_categories_match_canonical_meridian_definition():
    cases = [
        ((-3.0, 0.0), "MYOPIC"),
        ((-1.0, 2.0), "MYOPIC"),
        ((0.0, 2.0), "SIMPLE_MYOPIC_ASTIGMATISM"),
        ((0.0, 0.0), "PLANO"),
        ((3.0, 1.0), "HYPEROPIC"),
        ((3.0, 3.0), "SIMPLE_HYPEROPIC_ASTIGMATISM"),
        ((1.0, 2.0), "MIXED_ASTIGMATISM"),
    ]
    for values, expected in cases:
        assert classify_normalized_refraction(*values) == expected


def test_myopic_normalized_patterns_are_shadow_eligible():
    for values in ((-3.0, 0.0), (-1.0, 2.0), (0.0, 2.0), (0.0, 0.0)):
        assert clean_refraction_compatibility(*values).supported is True


def test_hyperopic_and_mixed_are_explicitly_unsupported_not_silently_dropped():
    for values in ((3.0, 1.0), (3.0, 3.0), (1.0, 2.0)):
        out = clean_refraction_compatibility(*values)
        assert out.supported is False
        assert "not yet modeled equivalently" in out.reasons[0]


def test_negative_cylinder_is_rejected_at_normalized_boundary():
    out = clean_refraction_compatibility(-3.0, -1.0)
    assert out.supported is False
    assert out.category == "INVALID_NORMALIZED_CYLINDER"


def test_missing_values_are_not_inferred():
    assert clean_refraction_compatibility(None, 1.0).category == "UNAVAILABLE"
    assert clean_refraction_compatibility(-2.0, None).category == "UNAVAILABLE"
