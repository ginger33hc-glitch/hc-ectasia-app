import pytest

from ps3_policy import (
    ALLOWED,
    DEFER,
    HIGH,
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
        topographic_astig_d=1.0,
        topographic_steep_axis_deg=175.0,
        manifest_astig_d=1.0,
        manifest_axis_deg=5.0,
        ppi_avg=1.1,
        srax="NO",
        srax_deg=10.0,
        bfte_front_um=8.0,
        bfte_back_um=10.0,
        refractive_group="MYOPIC_EMMETROPIC",
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


@pytest.mark.parametrize(
    "km,status",
    [(47.99, NORMAL), (48.0, MODERATE), (50.0, MODERATE), (50.01, HIGH)],
)
def test_anterior_km_boundaries(km, status):
    result = evaluate_ps3(normal_eye(anterior_km_d=km), normal_inter_eye())
    assert finding(result, "anterior_km").status == status


@pytest.mark.parametrize(
    "thinnest,status",
    [(500.01, NORMAL), (500.0, MODERATE), (470.0, MODERATE), (469.99, HIGH)],
)
def test_thinnest_boundaries(thinnest, status):
    result = evaluate_ps3(normal_eye(thinnest_um=thinnest), normal_inter_eye())
    assert finding(result, "thinnest").status == status


def test_axis_difference_wraps_at_180_degrees():
    result = evaluate_ps3(normal_eye(topographic_steep_axis_deg=175, manifest_axis_deg=5), normal_inter_eye())
    assert finding(result, "astigmatic_study").status == NORMAL


def test_astigmatic_study_moderate_if_magnitude_difference_exceeds_one_diopter():
    result = evaluate_ps3(normal_eye(manifest_astig_d=2.01), normal_inter_eye())
    assert finding(result, "astigmatic_study").status == MODERATE


def test_astigmatic_study_moderate_if_axis_difference_exceeds_ten_degrees():
    result = evaluate_ps3(normal_eye(topographic_steep_axis_deg=0, manifest_axis_deg=10.1), normal_inter_eye())
    assert finding(result, "astigmatic_study").status == MODERATE


def test_ppi_average_boundary():
    assert finding(evaluate_ps3(normal_eye(ppi_avg=1.2), normal_inter_eye()), "ppi_average").status == NORMAL
    assert finding(evaluate_ps3(normal_eye(ppi_avg=1.2001), normal_inter_eye()), "ppi_average").status == MODERATE


def test_bfte_high_risk_thresholds_are_strictly_greater_than_12_and_15():
    result = evaluate_ps3(normal_eye(bfte_front_um=12.0, bfte_back_um=15.0), normal_inter_eye())
    assert finding(result, "elevation").status == NORMAL
    result = evaluate_ps3(normal_eye(bfte_front_um=12.01, bfte_back_um=15.0), normal_inter_eye())
    assert finding(result, "elevation").status == HIGH


def test_bfs_myopic_emmetropic_thresholds_are_inclusive():
    result = evaluate_ps3(normal_eye(bfte_front_um=None, bfte_back_um=None, bfs_front_um=8.0, bfs_back_um=17.0), normal_inter_eye())
    assert finding(result, "elevation").status == HIGH


def test_bfs_hyperopic_mixed_thresholds_are_inclusive():
    result = evaluate_ps3(normal_eye(
        bfte_front_um=None,
        bfte_back_um=None,
        bfs_front_um=6.0,
        bfs_back_um=28.0,
        refractive_group="HYPEROPIC_MIXED",
    ), normal_inter_eye())
    assert finding(result, "elevation").status == HIGH


def test_inter_eye_score_four_is_moderate_and_five_is_high():
    score4 = normal_inter_eye(
        os_anterior_km_d=43.31,
        os_posterior_km_d=-6.11,
        os_thinnest_um=532.0,
        os_front_elevation_thinnest_um=4.0,
    )
    result4 = evaluate_ps3(normal_eye(), score4)
    assert result4.inter_eye_score == 4
    assert finding(result4, "inter_eye_asymmetry").status == MODERATE

    score5 = PS3InterEyeInput(
        **{**score4.__dict__, "os_back_elevation_thinnest_um": 10.0}
    )
    result5 = evaluate_ps3(normal_eye(), score5)
    assert result5.inter_eye_score == 5
    assert finding(result5, "inter_eye_asymmetry").status == HIGH


def test_inter_eye_equal_to_limit_counts_as_exceeded_because_normal_requires_less_than_limit():
    result = evaluate_ps3(normal_eye(), normal_inter_eye(os_thinnest_um=532.0))
    assert result.inter_eye_score == 1


def test_single_moderate_allows_prk_and_smile_but_defers_lasik():
    result = evaluate_ps3(normal_eye(anterior_km_d=48.0), normal_inter_eye())
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


def test_unread_morphologies_are_explicitly_not_evaluated_and_do_not_count_as_normal():
    result = evaluate_ps3(normal_eye(), normal_inter_eye())
    assert finding(result, "corneal_thickness_map_morphology").status == NOT_EVALUATED
    assert finding(result, "relative_thickness_map").status == NOT_EVALUATED
    assert finding(result, "pti_ctsp_morphology").status == NOT_EVALUATED
    assert len(result.review_notes) == 3


def test_srax_exactly_20_is_not_high_but_more_than_20_is_high():
    boundary = evaluate_ps3(normal_eye(srax="NO", srax_deg=20.0), normal_inter_eye())
    assert finding(boundary, "srax").status == NORMAL
    assert boundary.srax_deg == pytest.approx(20.0)

    high = evaluate_ps3(normal_eye(srax="YES", srax_deg=20.01), normal_inter_eye())
    assert finding(high, "srax").status == HIGH
    assert high.srax_deg == pytest.approx(20.01)


def test_srax_unavailable_is_not_evaluated_and_requests_surgeon_review():
    result = evaluate_ps3(normal_eye(srax="UNCERTAIN", srax_deg=None), normal_inter_eye())
    item = finding(result, "srax")
    assert item.status == NOT_EVALUATED
    assert "Axial/Sagittal Curvature (Front)" in item.detail
    assert "ask surgeon" in item.detail.lower()


def test_binary_front_map_or_surgeon_confirmation_is_supported_without_numeric_srax():
    high = evaluate_ps3(normal_eye(srax="YES", srax_deg=None), normal_inter_eye())
    normal = evaluate_ps3(normal_eye(srax="NO", srax_deg=None), normal_inter_eye())
    assert finding(high, "srax").status == HIGH
    assert finding(normal, "srax").status == NORMAL
