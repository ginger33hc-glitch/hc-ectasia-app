import pytest

from astigmatic_disparity_policy import (
    NORMAL,
    NOT_EVALUATED,
    VALIDATION_REQUIRED,
    axis_difference_deg,
    axis_requires_targeted_verification,
    evaluate_astigmatic_disparity,
)


def evaluate(**overrides):
    values = {
        "tomographic_astig_d": 3.1,
        "tomographic_flat_axis_deg": 1.1,
        "manifest_astig_d": 3.1,
        "manifest_axis_deg": 2.0,
    }
    values.update(overrides)
    return evaluate_astigmatic_disparity(**values)


def test_meridional_axis_difference_wraps_at_180_degrees():
    assert axis_difference_deg(175, 5) == 10


def test_ten_degree_axis_difference_requests_validation_but_never_scores_ps3():
    result = evaluate(tomographic_flat_axis_deg=0, manifest_axis_deg=10)
    assert result.status == VALIDATION_REQUIRED
    assert result.axis_difference_deg == 10
    assert result.affects_ps3 is False
    assert result.affects_procedure_eligibility is False
    assert axis_requires_targeted_verification(result)


def test_one_diopter_magnitude_difference_requests_validation_only():
    result = evaluate(tomographic_astig_d=3.0, manifest_astig_d=4.0)
    assert result.status == VALIDATION_REQUIRED
    assert result.magnitude_difference_d == 1.0
    assert result.affects_ps3 is False
    assert result.affects_procedure_eligibility is False


def test_values_below_both_thresholds_are_normal():
    result = evaluate(tomographic_flat_axis_deg=1.1, manifest_axis_deg=2.0)
    assert result.status == NORMAL
    assert result.axis_difference_deg == pytest.approx(0.9)


def test_zero_cylinder_omits_meaningless_axis_but_keeps_magnitude_check():
    result = evaluate(
        tomographic_astig_d=3.1,
        manifest_astig_d=0,
        manifest_axis_deg=None,
    )
    assert result.status == VALIDATION_REQUIRED
    assert result.axis_difference_deg is None


def test_missing_magnitude_is_passive_and_does_not_block_ps3():
    result = evaluate(manifest_astig_d=None)
    assert result.status == NOT_EVALUATED
    assert result.affects_ps3 is False
    assert result.affects_procedure_eligibility is False
