from clinical_core import ClinicalCoreInput, PS3EyeInput, PS3InterEyeInput, evaluate_normalized_case
from clinical_core.disposition import ASSESSMENT_INCOMPLETE, CAUTION, STOP_DEFER
from clinical_eligibility import evaluate_eligibility


def _core_input():
    return ClinicalCoreInput(
        procedure="LASIK",
        age_years=35,
        thinnest_um=560,
        i_s_d=0.0,
        derived_srax_deg=0.0,
        manifest_mrse_d=-3.0,
        intended_sphere_d=-3.0,
        intended_cylinder_d=0.0,
        intended_axis_deg=0.0,
        flap_um=100,
        ablation_um=60,
        preop_kmean_d=42.5,
        intended_mrse_d=-3.0,
        final_bad_d=1.0,
        nice_k2_d=43.0,
        nice_central_pachy_um=565,
        nice_b_ele_th_um=8,
        ps3_eye=PS3EyeInput(
            anterior_km_d=43.0,
            thinnest_um=560.0,
            ppi_avg=1.0,
            f_ele_th_um=8.0,
            b_ele_th_um=10.0,
            srax_deg=10.0,
        ),
        ps3_inter_eye=PS3InterEyeInput(
            od_anterior_km_d=43.0,
            os_anterior_km_d=43.1,
            od_posterior_km_d=-6.0,
            os_posterior_km_d=-6.05,
            od_thinnest_um=560.0,
            os_thinnest_um=565.0,
            od_front_elevation_thinnest_um=2.0,
            os_front_elevation_thinnest_um=3.0,
            od_back_elevation_thinnest_um=5.0,
            os_back_elevation_thinnest_um=8.0,
        ),
    )


def _plan(**overrides):
    values = {"stable": "yes", "progression": "no", "cdva_below_20_20": "no"}
    values.update(overrides)
    return values


def _modifiers(**overrides):
    values = {
        "eye_rubbing": "no",
        "family_history": "no",
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no",
        "drug_usage": "no",
        "dry_eye": "no",
        "systemic_disease": "no",
    }
    values.update(overrides)
    return values


def test_reassuring_eligibility_keeps_reassuring_core_pass():
    eligibility = evaluate_eligibility(_plan(), _modifiers())
    result = evaluate_normalized_case(_core_input(), external_findings=eligibility.findings)
    assert result["status"] == "PASS"
    assert result["external_findings"] == eligibility.findings


def test_eligibility_stop_is_retained_by_same_finalizer():
    eligibility = evaluate_eligibility(_plan(stable="no"), _modifiers())
    result = evaluate_normalized_case(_core_input(), external_findings=eligibility.findings)
    assert result["status"] == STOP_DEFER
    assert "refractive_stability" in {item.key for item in result["final_disposition"].stop_drivers}


def test_eligibility_caution_does_not_auto_escalate_to_stop():
    eligibility = evaluate_eligibility(
        _plan(cdva_below_20_20="yes"),
        _modifiers(dry_eye="yes"),
    )
    result = evaluate_normalized_case(_core_input(), external_findings=eligibility.findings)
    assert result["status"] == CAUTION
    assert {item.key for item in result["final_disposition"].caution_drivers} >= {"unexplained_cdva", "dry_eye"}


def test_missing_eligibility_documentation_is_incomplete_not_pass():
    eligibility = evaluate_eligibility(_plan(), _modifiers(dry_eye="unknown"))
    result = evaluate_normalized_case(_core_input(), external_findings=eligibility.findings)
    assert result["status"] == ASSESSMENT_INCOMPLETE
    assert "clinical_eligibility" in {item.key for item in result["final_disposition"].incomplete_drivers}


def test_collagen_stop_is_retained_by_same_finalizer():
    eligibility = evaluate_eligibility(
        _plan(), _modifiers(collagen_tissue_disease="yes")
    )
    result = evaluate_normalized_case(_core_input(), external_findings=eligibility.findings)
    assert result["status"] == STOP_DEFER
    assert "collagen_tissue_disease" in {
        item.key for item in result["final_disposition"].stop_drivers
    }


def test_external_findings_must_be_canonical_decision_findings():
    try:
        evaluate_normalized_case(_core_input(), external_findings=({"status": "STOP-DEFER"},))
    except TypeError as exc:
        assert "DecisionFinding" in str(exc)
    else:
        raise AssertionError("Non-canonical external finding must be rejected")
