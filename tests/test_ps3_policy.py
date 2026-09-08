import pytest

from ps3_policy import (
    ALLOWED,
    DEFER,
    HIGH,
    INCOMPLETE,
    MANUAL_REVIEW_KEYS,
    MODERATE,
    NORMAL,
    NOT_EVALUATED,
    PS3EyeInput,
    PS3InterEyeInput,
    evaluate_ps3,
)


def finding(result, key):
    return next(item for item in result.findings if item.key == key)


def normal_eye(**overrides):
    values = dict(
        anterior_km_d=47.0,
        thinnest_um=520.0,
        ppi_avg=1.1,
        f_ele_th_um=8.0,
        b_ele_th_um=10.0,
        srax="NO",
        srax_deg=10.0,
    )
    values.update(overrides)
    return PS3EyeInput(**values)


def normal_inter_eye(**overrides):
    values = dict(
        od_anterior_km_d=43.0,
        os_anterior_km_d=43.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.05,
        od_thinnest_um=520.0,
        os_thinnest_um=525.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0,
        os_back_elevation_thinnest_um=8.0,
    )
    values.update(overrides)
    return PS3InterEyeInput(**values)


@pytest.mark.parametrize("km,status", [(47.99, NORMAL), (48.0, MODERATE), (50.0, MODERATE), (50.01, HIGH)])
def test_anterior_km_boundaries(km, status):
    assert finding(evaluate_ps3(normal_eye(anterior_km_d=km), normal_inter_eye()), "anterior_km").status == status


@pytest.mark.parametrize("thinnest,status", [(500.01, NORMAL), (500.0, MODERATE), (470.0, MODERATE), (469.99, HIGH)])
def test_thinnest_boundaries(thinnest, status):
    assert finding(evaluate_ps3(normal_eye(thinnest_um=thinnest), normal_inter_eye()), "thinnest").status == status


def test_ppi_average_boundary():
    assert finding(evaluate_ps3(normal_eye(ppi_avg=1.2), normal_inter_eye()), "ppi_average").status == NORMAL
    assert finding(evaluate_ps3(normal_eye(ppi_avg=1.2001), normal_inter_eye()), "ppi_average").status == MODERATE


def test_canonical_f_b_ele_th_thresholds_are_strictly_greater_than_12_and_15():
    boundary = evaluate_ps3(normal_eye(f_ele_th_um=12.0, b_ele_th_um=15.0), normal_inter_eye())
    assert finding(boundary, "elevation").status == NORMAL
    front_high = evaluate_ps3(normal_eye(f_ele_th_um=12.01, b_ele_th_um=15.0), normal_inter_eye())
    assert finding(front_high, "elevation").status == HIGH
    back_high = evaluate_ps3(normal_eye(f_ele_th_um=12.0, b_ele_th_um=15.01), normal_inter_eye())
    assert finding(back_high, "elevation").status == HIGH


def test_missing_canonical_f_or_b_ele_th_makes_ps3_incomplete():
    result = evaluate_ps3(normal_eye(f_ele_th_um=None), normal_inter_eye())
    assert finding(result, "elevation").status == NOT_EVALUATED
    assert result.complete is False
    assert "elevation" in result.missing_keys


def test_inter_eye_score_four_is_moderate_and_five_is_high():
    score4 = normal_inter_eye(
        os_anterior_km_d=43.31, os_posterior_km_d=-6.11, os_thinnest_um=532.0,
        os_front_elevation_thinnest_um=4.0,
    )
    result4 = evaluate_ps3(normal_eye(), score4)
    assert result4.inter_eye_score == 4
    assert finding(result4, "inter_eye_asymmetry").status == MODERATE
    score5 = PS3InterEyeInput(**{**score4.__dict__, "os_back_elevation_thinnest_um": 10.0})
    result5 = evaluate_ps3(normal_eye(), score5)
    assert result5.inter_eye_score == 5
    assert finding(result5, "inter_eye_asymmetry").status == HIGH


def test_inter_eye_equal_to_limit_counts_as_exceeded():
    assert evaluate_ps3(normal_eye(), normal_inter_eye(os_thinnest_um=532.0)).inter_eye_score == 1


def test_complete_normal_ps3_is_explicitly_complete_and_allowed():
    result = evaluate_ps3(normal_eye(), normal_inter_eye())
    assert result.complete is True
    assert result.missing_keys == ()
    assert result.disposition.prk == ALLOWED
    assert result.disposition.smile == ALLOWED
    assert result.disposition.lasik == ALLOWED


def test_single_moderate_allows_prk_and_smile_but_defers_lasik():
    result = evaluate_ps3(normal_eye(anterior_km_d=48.0), normal_inter_eye())
    assert result.complete is True
    assert result.moderate_count == 1
    assert result.high_count == 0
    assert result.disposition.prk == ALLOWED
    assert result.disposition.smile == ALLOWED
    assert result.disposition.lasik == DEFER


def test_two_moderates_defer_all_procedures():
    result = evaluate_ps3(normal_eye(anterior_km_d=48.0, ppi_avg=1.21), normal_inter_eye())
    assert result.moderate_count == 2
    assert result.disposition.prk == DEFER
    assert result.disposition.smile == DEFER
    assert result.disposition.lasik == DEFER


def test_one_high_defers_all_procedures():
    result = evaluate_ps3(normal_eye(thinnest_um=469.0), normal_inter_eye())
    assert result.high_count >= 1
    assert result.disposition.prk == DEFER
    assert result.disposition.smile == DEFER
    assert result.disposition.lasik == DEFER


def test_incomplete_ps3_never_returns_reassuring_allowed():
    result = evaluate_ps3(normal_eye(ppi_avg=None), normal_inter_eye())
    assert result.complete is False
    assert "ppi_average" in result.missing_keys
    assert result.disposition.prk == INCOMPLETE
    assert result.disposition.smile == INCOMPLETE
    assert result.disposition.lasik == INCOMPLETE


def test_single_moderate_plus_incomplete_keeps_lasik_defer_and_other_procedures_incomplete():
    result = evaluate_ps3(normal_eye(anterior_km_d=48.0, ppi_avg=None), normal_inter_eye())
    assert result.complete is False
    assert result.disposition.lasik == DEFER
    assert result.disposition.prk == INCOMPLETE
    assert result.disposition.smile == INCOMPLETE


def test_manual_morphology_items_are_not_evaluated_without_becoming_automated_missing_inputs():
    result = evaluate_ps3(normal_eye(), normal_inter_eye())
    assert finding(result, "corneal_thickness_map_morphology").status == NOT_EVALUATED
    assert finding(result, "relative_thickness_map").status == NOT_EVALUATED
    assert finding(result, "pti_ctsp_morphology").status == NOT_EVALUATED
    assert all("not evaluated" in finding(result, key).detail.lower() for key in MANUAL_REVIEW_KEYS)
    assert len(result.review_notes) == 3
    assert result.complete is True
    assert result.missing_keys == ()


def test_srax_exactly_20_is_not_high_but_more_than_20_is_high():
    boundary = evaluate_ps3(normal_eye(srax="NO", srax_deg=20.0), normal_inter_eye())
    assert finding(boundary, "srax").status == NORMAL
    high = evaluate_ps3(normal_eye(srax="YES", srax_deg=20.01), normal_inter_eye())
    assert finding(high, "srax").status == HIGH


def test_srax_unavailable_is_incomplete_and_requests_surgeon_review():
    result = evaluate_ps3(normal_eye(srax="UNCERTAIN", srax_deg=None), normal_inter_eye())
    item = finding(result, "srax")
    assert item.status == NOT_EVALUATED
    assert result.complete is False
    assert "srax" in result.missing_keys
    assert "Axial/Sagittal Curvature (Front)" in item.detail
    assert "ask surgeon" in item.detail.lower()


def test_binary_front_map_or_surgeon_confirmation_is_supported_without_numeric_srax():
    assert finding(evaluate_ps3(normal_eye(srax="YES", srax_deg=None), normal_inter_eye()), "srax").status == HIGH
    assert finding(evaluate_ps3(normal_eye(srax="NO", srax_deg=None), normal_inter_eye()), "srax").status == NORMAL


def test_irrevocable_defer_still_requires_srax_for_complete_ps3():
    result = evaluate_ps3(normal_eye(thinnest_um=469.0, srax="UNCERTAIN", srax_deg=None), normal_inter_eye())
    assert finding(result, "srax").status == NOT_EVALUATED
    assert "srax" in result.missing_keys
    assert result.complete is False
    assert result.disposition.lasik == DEFER
    assert result.disposition.prk == DEFER
    assert result.disposition.smile == DEFER


def test_existing_high_factor_does_not_discard_shared_numeric_srax():
    result = evaluate_ps3(normal_eye(thinnest_um=469, srax_deg=20.01), normal_inter_eye())
    assert result.srax_deg == 20.01
    assert finding(result, "srax").status == HIGH
    assert result.high_count == 2
