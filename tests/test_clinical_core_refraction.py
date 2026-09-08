import pytest

from clinical_core.refraction import (
    HYPEROPIC,
    MIXED,
    MYOPIC,
    normalize_minus_cylinder,
    refractive_group,
    scalar_final_k_is_valid,
)


def test_minus_cylinder_is_preserved_with_axis_normalized():
    ref = normalize_minus_cylinder(-5.0, -2.0, 180.0)
    assert ref.sphere_d == -5.0
    assert ref.cylinder_d == -2.0
    assert ref.axis_deg == 0.0
    assert ref.mrse_d == -6.0


def test_plus_cylinder_transposes_to_equivalent_minus_cylinder():
    ref = normalize_minus_cylinder(-7.0, +2.0, 10.0)
    assert ref.sphere_d == -5.0
    assert ref.cylinder_d == -2.0
    assert ref.axis_deg == 100.0
    assert ref.mrse_d == -6.0


def test_equivalent_plus_and_minus_notation_have_identical_mrse_and_meridians():
    plus = normalize_minus_cylinder(-7.0, +2.0, 10.0)
    minus = normalize_minus_cylinder(-5.0, -2.0, 100.0)
    assert plus == minus
    assert plus.principal_meridians_d == minus.principal_meridians_d


def test_refractive_group_uses_both_principal_meridians():
    assert refractive_group(normalize_minus_cylinder(-4.0, -2.0, 90)) == MYOPIC
    assert refractive_group(normalize_minus_cylinder(+4.0, -2.0, 90)) == HYPEROPIC
    assert refractive_group(normalize_minus_cylinder(+1.0, -2.0, 90)) == MIXED


def test_mixed_astigmatism_cannot_use_scalar_final_k_model():
    mixed = normalize_minus_cylinder(+1.0, -2.0, 90)
    assert scalar_final_k_is_valid(mixed) is False
    assert scalar_final_k_is_valid(normalize_minus_cylinder(-4.0, -2.0, 90)) is True
    assert scalar_final_k_is_valid(normalize_minus_cylinder(+4.0, -2.0, 90)) is True


def test_invalid_refraction_is_incomplete():
    assert normalize_minus_cylinder(None, -1.0, 90) is None
