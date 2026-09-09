"""Acceptance tests for the CER-AI-modified PS3 thinness-only LASIK rule."""
import pytest

from clinical_core import ClinicalCoreInput, PS3EyeInput, PS3InterEyeInput
from clinical_core.pipeline import evaluate_normalized_case


def _ps3_eye(**overrides):
    values = dict(
        anterior_km_d=43.0,
        thinnest_um=495.0,
        ppi_avg=1.0,
        f_ele_th_um=8.0,
        b_ele_th_um=10.0,
        i_s_d=0.0,
        srax="NO",
        srax_deg=10.0,
    )
    values.update(overrides)
    return PS3EyeInput(**values)


def _inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=43.0,
        os_anterior_km_d=43.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.05,
        od_thinnest_um=495.0,
        os_thinnest_um=500.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0,
        os_back_elevation_thinnest_um=8.0,
    )


def _case(**overrides):
    thickness = overrides.pop("thinnest_um", 495.0)
    ps3_eye = overrides.pop("ps3_eye", _ps3_eye(thinnest_um=thickness))
    values = dict(
        procedure="LASIK",
        age_years=35,
        thinnest_um=thickness,
        i_s_d=0.0,
        derived_srax_deg=10.0,
        srax_gt20_confirmed=False,
        manifest_mrse_d=-2.0,
        intended_sphere_d=-2.0,
        intended_cylinder_d=0.0,
        intended_axis_deg=0.0,
        flap_um=90.0,
        ablation_um=30.0,
        preop_kmean_d=43.0,
        intended_mrse_d=-2.0,
        final_bad_d=1.0,
        nice_k2_d=44.0,
        nice_central_pachy_um=525.0,
        nice_b_ele_th_um=10.0,
        ps3_eye=ps3_eye,
        ps3_inter_eye=_inter_eye(),
    )
    values.update(overrides)
    return ClinicalCoreInput(**values)


@pytest.mark.parametrize("thickness", (490.0, 495.0, 500.0))
def test_thickness_only_ps3_defer_becomes_lasik_pass_with_caution(thickness):
    result = evaluate_normalized_case(_case(thinnest_um=thickness))
    assert result["erss_status"] == "PASS"
    assert result["nice_status"] == "PASS"
    assert result["bad_d"]["status"] == "PASS"
    assert result["ps3"].moderate_count == 1
    assert result["ps3"].disposition.lasik == "DEFER"
    assert result["ps3"].disposition.prk == "ALLOWED"
    assert result["ps3"].disposition.smile == "ALLOWED"
    assert result["ps3_status"] == "PASS WITH CAUTION"
    assert result["ps3_decision"].modification_applied is True
    assert result["status"] == "PASS WITH CAUTION"


@pytest.mark.parametrize("thickness", (489.99, 500.01))
def test_exception_does_not_change_ps3_outside_490_to_500(thickness):
    result = evaluate_normalized_case(_case(thinnest_um=thickness))
    if thickness < 490:
        assert result["ps3"].disposition.lasik == "DEFER"
        assert result["ps3_status"] == "STOP-DEFER"
        assert result["status"] == "STOP-DEFER"
    else:
        assert result["ps3"].disposition.lasik == "ALLOWED"
        assert result["ps3_status"] == "PASS"
        assert result["status"] == "PASS"
    assert result["ps3_decision"].modification_applied is False


@pytest.mark.parametrize(
    "overrides,system_key",
    (
        ({"manifest_mrse_d": -8.5}, "erss_status"),
        ({"nice_k2_d": 45.0}, "nice_status"),
        ({"final_bad_d": 2.0}, "bad_d"),
    ),
)
def test_any_other_scoring_system_caution_preserves_lasik_defer(overrides, system_key):
    result = evaluate_normalized_case(_case(**overrides))
    if system_key == "bad_d":
        assert result["bad_d"]["status"] == "CAUTION"
    else:
        assert result[system_key] == "CAUTION"
    assert result["ps3_status"] == "STOP-DEFER"
    assert result["ps3_decision"].modification_applied is False
    assert result["status"] == "STOP-DEFER"


def test_second_ps3_moderate_cancels_all_procedures_and_cannot_use_exception():
    result = evaluate_normalized_case(_case(ps3_eye=_ps3_eye(ppi_avg=1.21)))
    assert result["ps3"].moderate_count == 2
    assert result["ps3"].disposition.lasik == "DEFER"
    assert result["ps3"].disposition.prk == "DEFER"
    assert result["ps3"].disposition.smile == "DEFER"
    assert result["ps3_status"] == "STOP-DEFER"
    assert result["ps3_decision"].modification_applied is False


def test_one_high_cancels_all_procedures_and_cannot_use_exception():
    result = evaluate_normalized_case(_case(ps3_eye=_ps3_eye(anterior_km_d=51.0)))
    assert result["ps3"].high_count == 1
    assert result["ps3"].disposition.lasik == "DEFER"
    assert result["ps3"].disposition.prk == "DEFER"
    assert result["ps3"].disposition.smile == "DEFER"
    assert result["ps3_status"] == "STOP-DEFER"
    assert result["ps3_decision"].modification_applied is False


def test_exception_is_lasik_only_and_does_not_modify_raw_prk_or_smile_rules():
    for procedure in ("PRK", "SMILE"):
        result = evaluate_normalized_case(_case(procedure=procedure, flap_um=None))
        assert result["ps3_status"] == "PASS"
        assert result["ps3_decision"].modification_applied is False
