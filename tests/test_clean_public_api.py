"""Public API contract for eventual clean-engine migration.

The domain API remains available, while production migration should cross the
explicit reconciled-input application-service boundary rather than importing
internal pipeline modules.
"""
import clean_engine


def test_clean_engine_exposes_stable_assessment_entrypoint():
    assert callable(clean_engine.assess)
    assert clean_engine.EyeInput.__module__ == "clean_engine.models"
    assert clean_engine.AssessmentResult.__module__ == "clean_engine.models"


def test_public_entrypoint_returns_typed_result():
    result = clean_engine.assess(clean_engine.EyeInput(
        age_years=30,
        pachy_thinnest_um=520,
        bad_d=1.0,
        morphology="NORMAL_SYMMETRIC",
        procedure="LASIK",
        prior_refractive_surgery=False,
        ablation_um=60,
        flap_um=100,
        preop_kmean_d=43,
        manifest_mrse_d=-3,
        intended_mrse_d=-3,
        intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0,
        laser_platform="EX500",
    ))
    assert isinstance(result, clean_engine.AssessmentResult)
    assert result.status == "PASS"


def test_clean_engine_exposes_reconciled_service_boundary():
    assert callable(clean_engine.assess_reconciled)
    assert clean_engine.ReconciledEyeInput.__module__ == "clean_engine.input_adapter"
    assert clean_engine.CleanAssessment.__module__ == "clean_engine.service"

    out = clean_engine.assess_reconciled(clean_engine.ReconciledEyeInput(
        age_years=30,
        pachy_thinnest_um=520,
        bad_d=1.0,
        morphology="NORMAL_SYMMETRIC",
        procedure="LASIK",
        prior_refractive_surgery=False,
        ablation_um=60,
        flap_um=100,
        preop_kmean_d=43,
        manifest_mrse_d=-3,
        intended_mrse_d=-3,
        intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0,
        laser_platform="EX500",
    ))
    assert isinstance(out, clean_engine.CleanAssessment)
    assert out.result.status == "PASS"
    assert out.report.status == out.result.status


def test_public_api_is_explicit_and_does_not_export_internal_pipeline_functions():
    assert set(clean_engine.__all__) == {
        "EyeInput", "AssessmentResult", "assess",
        "ReconciledEyeInput", "CleanAssessment", "assess_reconciled",
        "POLICY", "HCPolicy",
    }
    forbidden = {
        "calculate", "calculate_scores", "evaluate_hard_stops", "finalize",
        "decide", "validate_decision_inputs", "combine_status",
        "build_report_model", "to_eye_input",
    }
    assert forbidden.isdisjoint(set(clean_engine.__all__))
