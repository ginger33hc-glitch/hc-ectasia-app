"""Acceptance tests for strict PS3 procedure-specific disposition."""
import pytest

from clinical_core import ClinicalCoreInput, PS3EyeInput, PS3InterEyeInput
from clinical_core.pipeline import evaluate_normalized_case


def _ps3_eye(**overrides):
    values = dict(
        anterior_km_d=43.0, thinnest_um=495.0, ppi_avg=1.0,
        f_ele_th_um=8.0, b_ele_th_um=10.0, i_s_d=0.0,
        srax="NO", srax_deg=10.0,
    )
    values.update(overrides)
    return PS3EyeInput(**values)


def _inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=43.0, os_anterior_km_d=43.1,
        od_posterior_km_d=-6.0, os_posterior_km_d=-6.05,
        od_thinnest_um=495.0, os_thinnest_um=500.0,
        od_front_elevation_thinnest_um=2.0, os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0, os_back_elevation_thinnest_um=8.0,
    )


def _case(procedure="LASIK", ps3_eye=None):
    return ClinicalCoreInput(
        procedure=procedure, age_years=35, thinnest_um=495.0, i_s_d=0.0,
        derived_srax_deg=10.0, srax_gt20_confirmed=False,
        manifest_mrse_d=-2.0, intended_sphere_d=-2.0,
        intended_cylinder_d=0.0, intended_axis_deg=0.0,
        flap_um=90.0 if procedure == "LASIK" else None, ablation_um=30.0,
        preop_kmean_d=43.0, intended_mrse_d=-2.0, final_bad_d=1.0,
        nice_k2_d=44.0, nice_central_pachy_um=525.0, nice_b_ele_th_um=10.0,
        ps3_eye=ps3_eye or _ps3_eye(), ps3_inter_eye=_inter_eye(),
    )


@pytest.mark.parametrize("thickness", (490.0, 495.0, 500.0))
def test_one_thinness_moderate_strictly_defers_lasik(thickness):
    eye = _ps3_eye(thinnest_um=thickness)
    case = _case(ps3_eye=eye)
    case = ClinicalCoreInput(**{**case.__dict__, "thinnest_um": thickness})
    result = evaluate_normalized_case(case)
    assert result["ps3"].moderate_count == 1
    assert result["ps3"].disposition.lasik == "DEFER"
    assert result["ps3"].disposition.prk == "ALLOWED"
    assert result["ps3"].disposition.smile == "ALLOWED"
    assert result["ps3_status"] == "STOP-DEFER"
    assert result["status"] == "STOP-DEFER"


@pytest.mark.parametrize("procedure", ("PRK", "SMILE"))
def test_one_moderate_allows_prk_and_smile_when_other_systems_pass(procedure):
    result = evaluate_normalized_case(_case(procedure=procedure))
    assert result["ps3_status"] == "PASS"
    assert result["status"] == "PASS"


@pytest.mark.parametrize(
    "eye",
    (_ps3_eye(ppi_avg=1.21), _ps3_eye(anterior_km_d=51.0)),
)
def test_two_moderates_or_one_high_defer_every_procedure(eye):
    for procedure in ("LASIK", "PRK", "SMILE"):
        result = evaluate_normalized_case(_case(procedure=procedure, ps3_eye=eye))
        assert result["ps3_status"] == "STOP-DEFER"
        assert result["status"] == "STOP-DEFER"
