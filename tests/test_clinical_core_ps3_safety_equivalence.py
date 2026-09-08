"""Monday acceptance gates for PS3 facade and procedural safety core."""

from dataclasses import asdict

import ps3_policy
from clinical_core.ps3 import PS3EyeInput, PS3InterEyeInput, evaluate_ps3
from clinical_core.safety import (
    CORNEAL_EFFECT_PER_INTENDED_MRSE_D,
    FINAL_KMEAN_MAX_D,
    FINAL_KMEAN_MIN_D,
    PRK_EPITHELIUM_UM,
    estimated_final_kmean_d,
    final_kmean_hard_stop,
    lasik_pta_hard_stop,
    lasik_pta_percent,
    lasik_rsb_hard_stop,
    lasik_rsb_um,
    preop_thickness_hard_stop,
    prk_rst_hard_stop,
    prk_rst_um,
    sphere_magnitude_hard_stop,
)


def complete_eye(**overrides):
    values = dict(
        anterior_km_d=43.0,
        thinnest_um=520.0,
        topographic_astig_d=1.0,
        bad_flat_axis_deg=90.0,
        manifest_astig_d=1.0,
        manifest_axis_deg=90.0,
        ppi_avg=1.0,
        f_ele_th_um=10.0,
        b_ele_th_um=12.0,
        srax="NO",
        srax_deg=0.0,
    )
    values.update(overrides)
    return PS3EyeInput(**values)


def complete_inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=44.0,
        os_anterior_km_d=44.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.0,
        od_thinnest_um=520.0,
        os_thinnest_um=518.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=2.0,
        od_back_elevation_thinnest_um=4.0,
        os_back_elevation_thinnest_um=4.0,
    )


def test_safety_constants_match_accepted_values():
    assert PRK_EPITHELIUM_UM == 50.0
    assert CORNEAL_EFFECT_PER_INTENDED_MRSE_D == 0.8
    assert FINAL_KMEAN_MIN_D == 36.0
    assert FINAL_KMEAN_MAX_D == 48.0


def test_structural_calculations_match_matrix_examples():
    assert lasik_rsb_um(520, 100, 120) == 300
    assert lasik_rsb_um(520, 100, 121) == 299
    assert prk_rst_um(520, 160) == 310
    assert prk_rst_um(520, 161) == 309
    assert lasik_pta_percent(500, 100, 100) == 40.0
    assert estimated_final_kmean_d(44.0, -10.0) == 36.0
    assert estimated_final_kmean_d(43.2, 6.0) == 48.0


def test_procedural_hard_stop_boundaries_are_exact():
    assert not preop_thickness_hard_stop(480)
    assert preop_thickness_hard_stop(479)
    assert not lasik_rsb_hard_stop(300)
    assert lasik_rsb_hard_stop(299)
    assert not prk_rst_hard_stop(310)
    assert prk_rst_hard_stop(309)
    assert not final_kmean_hard_stop(36.0)
    assert not final_kmean_hard_stop(48.0)
    assert final_kmean_hard_stop(35.99)
    assert final_kmean_hard_stop(48.01)
    assert not sphere_magnitude_hard_stop(-10.0)
    assert sphere_magnitude_hard_stop(-10.01)
    assert not sphere_magnitude_hard_stop(6.0)
    assert sphere_magnitude_hard_stop(6.01)


def test_pta_40_percent_boundary_is_a_canonical_lasik_hard_stop():
    assert lasik_pta_percent(500, 100, 100) == 40.0
    assert not lasik_pta_hard_stop(39.99)
    assert lasik_pta_hard_stop(40.0)
    assert lasik_pta_hard_stop(40.01)


def test_ps3_clinical_core_facade_is_the_same_pure_policy():
    eye = complete_eye(anterior_km_d=49.0, thinnest_um=490.0)
    inter_eye = complete_inter_eye()
    via_core = evaluate_ps3(eye, inter_eye)
    via_existing_policy = ps3_policy.evaluate_ps3(eye, inter_eye)
    assert asdict(via_core) == asdict(via_existing_policy)


def test_ps3_one_moderate_and_two_moderate_dispositions_remain_separate_when_complete():
    one = evaluate_ps3(complete_eye(anterior_km_d=49.0), complete_inter_eye())
    assert one.complete is True
    assert one.moderate_count == 1
    assert one.disposition.lasik == ps3_policy.DEFER
    assert one.disposition.prk == ps3_policy.ALLOWED

    two = evaluate_ps3(complete_eye(anterior_km_d=49.0, thinnest_um=490.0), complete_inter_eye())
    assert two.moderate_count >= 2
    assert two.disposition.lasik == ps3_policy.DEFER
    assert two.disposition.prk == ps3_policy.DEFER
