"""Public API contract for eventual clean-engine migration.

Callers should need only clean_engine.EyeInput / assess / AssessmentResult,
not internal policy or pipeline modules.
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
        ablation_um=60,
        flap_um=100,
        preop_kmean_d=43,
        intended_mrse_d=-3,
        intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0,
        laser_platform="EX500",
    ))
    assert isinstance(result, clean_engine.AssessmentResult)
    assert result.status == "PASS WITH CAUTION"


def test_public_api_does_not_export_internal_pipeline_functions():
    forbidden = {
        "calculate", "calculate_scores", "evaluate_hard_stops", "finalize",
        "decide", "validate_decision_inputs", "combine_status",
    }
    assert forbidden.isdisjoint(set(clean_engine.__all__))
