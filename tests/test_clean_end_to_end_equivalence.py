"""End-to-end equivalence matrix for behavior that can be compared safely.

This complements primitive equivalence tests. Intentional CER-AI policy overrides are
kept out of this matrix and remain locked by their dedicated clean tests.
"""
import canonical_engine
import clean_engine
import pytest
from tests.test_hc_engine import MODIFIERS, normal_eye, plan

legacy = canonical_engine.core


def clean_case(**changes):
    values = dict(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK", prior_refractive_surgery=False,
        ablation_um=60, flap_um=100, preop_kmean_d=44,
        manifest_mrse_d=-3, intended_mrse_d=-3,
        intended_sphere_d=-3, intended_cylinder_magnitude_d=0,
        laser_platform="Alcon EX500",
    )
    values.update(changes)
    return clean_engine.assess(clean_engine.EyeInput(**values))


def test_clean_lasik_score_components_match_canonical_primitives_across_matrix():
    cases = ((18,500,"NORMAL_SYMMETRIC",340,-3),(19,505,"ASYMMETRIC_BOWTIE",320,-9),(21,511,"INFERIOR_STEEPENING_SRA",300,-8),(30,520,"NORMAL_SYMMETRIC",360,2))
    for age,pachy,morphology,expected_rsb,mrse in cases:
        flap=100; ablation=pachy-flap-expected_rsb
        out=clean_case(age_years=age,pachy_thinnest_um=pachy,morphology=morphology,flap_um=flap,ablation_um=ablation,manifest_mrse_d=mrse,preop_kmean_d=44)
        expected=(legacy.age_points(age),legacy.lasik_pachy_points(pachy),legacy.lasik_topography_points(morphology),legacy.lasik_rsb_points(expected_rsb),legacy.lasik_mrse_points(mrse))
        actual=(out.scores.age_points,out.scores.pachymetry_points,out.scores.topography_points,out.scores.rsb_points,out.scores.mrse_points)
        assert actual==expected
        assert out.scores.erss_total==sum(expected)


def test_clean_bad_d_classification_matches_canonical_across_final_boundaries():
    for bad_d in (1.0,1.6,1.6001,2.5999,2.6,3.0,4.0):
        out=clean_case(bad_d=bad_d)
        assert out.bad_d_status==legacy.bad_classification(bad_d,final=True)


def test_clean_surgical_outputs_match_locked_canonical_formulas():
    lasik=clean_case(pachy_thinnest_um=520,flap_um=100,ablation_um=60,preop_kmean_d=44,intended_mrse_d=-3)
    assert lasik.calculations.lasik_rsb_um==360
    assert lasik.calculations.lasik_pta_percent==100*(100+60)/520
    assert lasik.calculations.final_kmean_d==44+legacy.CORNEAL_EFFECT_PER_INTENDED_MRSE_D*-3
    prk=clean_case(procedure="PRK",flap_um=None,pachy_thinnest_um=520,ablation_um=60)
    assert prk.calculations.prk_rst_um==520-legacy.PRK_EPITHELIUM_UM-60
    assert prk.calculations.prk_pta_percent==100*(legacy.PRK_EPITHELIUM_UM+60)/520


def test_clean_final_lasik_status_matches_locked_principal_hierarchy_for_comparable_cases():
    expected=(({},"PASS"),({"age_years":18},"CAUTION"),({"bad_d":2.6},"STOP-DEFER"),({"bad_d":None},"DATA INSUFFICIENT"))
    for changes,status in expected:
        assert clean_case(**changes).status==status


def test_same_complete_lasik_cases_match_canonical_end_to_end():
    cases=({"age":30,"pachy":560,"bad_d":1.0},{"age":18,"pachy":560,"bad_d":1.0},{"age":30,"pachy":560,"bad_d":2.6})
    for case in cases:
        eye=normal_eye(pachy=case["pachy"])
        eye["morphology_confidence"]="HIGH"
        eye["erss_source_read"]="DEDICATED_CURVATURE_PASS"
        eye["BAD_D"]=case["bad_d"]
        # Complete ERSS evidence: signed I-S is verified and SRAX is resolved from Front map.
        eye["I_S_status"]="CONFIDENT"
        verified=set(eye.get("table_verified_numeric_fields") or [])
        verified.add("I_S")
        eye["table_verified_numeric_fields"]=sorted(verified)
        eye["data_conflicts"]=eye.get("data_conflicts") or []
        eye["srax_deg"]=0.0
        eye["srax"]="NO"
        canonical=legacy.assess_eye(eye,plan("LASIK",sphere=-3,cylinder=0,ablation=60,flap=100),case["age"],MODIFIERS)
        clean=clean_case(age_years=case["age"],pachy_thinnest_um=case["pachy"],bad_d=case["bad_d"],preop_kmean_d=eye["Kmean_D"],manifest_mrse_d=-3,intended_mrse_d=-3,intended_sphere_d=-3,intended_cylinder_magnitude_d=0)
        assert clean.status==canonical["status"]
        assert bool(clean.hard_stops)==bool(canonical["hard_stops"])
        assert clean.scores.erss_total==canonical["randleman_erss"]["total"]
        assert clean.calculations.lasik_rsb_um==canonical["values"]["LASIK_RSB_um"]
        assert clean.calculations.lasik_pta_percent==pytest.approx(canonical["values"]["LASIK_PTA_percent"])
