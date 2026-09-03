"""Phase 2 equivalence gates for PS3 and procedural safety core."""

from dataclasses import asdict

import canonical_engine
import lasik_planning
import ps3_policy
from clinical_core.ps3 import PS3EyeInput, PS3InterEyeInput, evaluate_ps3
from clinical_core.safety import (
    CORNEAL_EFFECT_PER_INTENDED_MRSE_D,
    FINAL_KMEAN_MAX_D,
    FINAL_KMEAN_MIN_D,
    LASIK_PTA_CUTOFF_PERCENT,
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

core = canonical_engine.core


def test_safety_constants_match_frozen_production_constants():
    assert PRK_EPITHELIUM_UM == core.PRK_EPITHELIUM_UM
    assert CORNEAL_EFFECT_PER_INTENDED_MRSE_D == core.CORNEAL_EFFECT_PER_INTENDED_MRSE_D
    assert FINAL_KMEAN_MIN_D == core.FINAL_KMEAN_MIN_D
    assert FINAL_KMEAN_MAX_D == core.FINAL_KMEAN_MAX_D
    assert LASIK_PTA_CUTOFF_PERCENT == lasik_planning.LASIK_PTA_CUTOFF_PERCENT


def test_structural_calculations_match_launch_contract_examples():
    assert lasik_rsb_um(520, 100, 120) == 300
    assert lasik_rsb_um(520, 100, 121) == 299
    assert prk_rst_um(520, 160) == 310
    assert prk_rst_um(520, 161) == 309
    assert lasik_pta_percent(500, 100, 100) == 40.0
    assert estimated_final_kmean_d(44.0, -10.0) == 36.0
    assert estimated_final_kmean_d(43.2, 6.0) == 48.0


def test_procedural_hard_stop_boundaries_are_exact():
    assert not preop_thickness_hard_stop(480)
    assert preop_thickness_hard_stop(479.999)
    assert not lasik_rsb_hard_stop(300)
    assert lasik_rsb_hard_stop(299.999)
    assert not prk_rst_hard_stop(310)
    assert prk_rst_hard_stop(309.999)
    assert not lasik_pta_hard_stop(39.999)
    assert lasik_pta_hard_stop(40.0)
    assert not final_kmean_hard_stop(36.0)
    assert not final_kmean_hard_stop(48.0)
    assert final_kmean_hard_stop(35.999)
    assert final_kmean_hard_stop(48.001)
    assert not sphere_magnitude_hard_stop(-10.0)
    assert sphere_magnitude_hard_stop(-10.001)
    assert not sphere_magnitude_hard_stop(6.0)
    assert sphere_magnitude_hard_stop(6.001)


def test_ps3_clinical_core_facade_matches_existing_pure_policy():
    eye = PS3EyeInput(
        anterior_km_d=49.0,
        thinnest_um=490.0,
        topographic_astig_d=2.0,
        topographic_steep_axis_deg=90.0,
        manifest_astig_d=2.0,
        manifest_axis_deg=90.0,
        ppi_avg=1.0,
        srax="NO",
        srax_deg=0.0,
        bfte_front_um=10.0,
        bfte_back_um=12.0,
        refractive_group="MYOPIC_EMMETROPIC",
    )
    inter_eye = PS3InterEyeInput(
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
    via_core = evaluate_ps3(eye, inter_eye)
    via_existing_policy = ps3_policy.evaluate_ps3(eye, inter_eye)
    assert asdict(via_core) == asdict(via_existing_policy)


def test_ps3_one_moderate_and_two_moderate_dispositions_remain_separate():
    one = evaluate_ps3(PS3EyeInput(anterior_km_d=49.0, thinnest_um=520.0, srax="NO", srax_deg=0.0))
    assert one.moderate_count == 1
    assert one.disposition.lasik == ps3_policy.DEFER
    assert one.disposition.prk == ps3_policy.ALLOWED

    two = evaluate_ps3(PS3EyeInput(anterior_km_d=49.0, thinnest_um=490.0, srax="NO", srax_deg=0.0))
    assert two.moderate_count >= 2
    assert two.disposition.lasik == ps3_policy.DEFER
    assert two.disposition.prk == ps3_policy.DEFER
