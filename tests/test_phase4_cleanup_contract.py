"""Phase 4 cleanup contract: retired pre-launch tests are quarantined, not skipped."""
from pathlib import Path

import tests.test_hc_engine as current


ROOT = Path(__file__).resolve().parent


def test_no_retired_test_skip_hook_remains():
    text = (ROOT / "conftest.py").read_text(encoding="utf-8")
    assert "_RETIRED_LEGACY_TESTS" not in text
    assert "pytest_collection_modifyitems" not in text
    assert "pytest.mark.skip" not in text


def test_historical_hc_engine_module_is_non_collected():
    legacy = ROOT / "legacy_hc_engine_tests.py"
    assert legacy.exists()
    assert legacy.name != "test_hc_engine.py"
    assert not legacy.name.startswith("test_")


def test_exactly_thirteen_hc_engine_methods_are_retired():
    manifest = current.PHASE4_RETIRED_HC_ENGINE_METHODS
    assert sum(len(methods) for methods in manifest.values()) == 13
    expected = {
        "TestSafetyGates": {
            "test_clinical_eligibility_modifier_blocks_pass_without_score_points",
        },
        "TestBoundaries": {
            "test_prk_cct_480_not_hard_stop_but_scores_caution",
            "test_definite_ectatic_morphology_is_not_downgraded_by_srax_fields",
            "test_minimal_axis_deviation_is_not_scored_as_srax",
            "test_srax_20_degrees_uses_published_erss_sra_category",
            "test_srax_below_20_degrees_is_not_scored",
            "test_unquantified_visual_srax_label_is_not_scored",
        },
        "TestScoringAndCompleteness": {
            "test_reassuring_prk_can_pass",
            "test_extraction_contract_prioritizes_labeled_pentacam_numeric_fields",
            "test_lasik_score_two_has_no_score_escalation",
            "test_local_kmax_is_rejected_but_explicit_local_rmin_remains_permitted",
        },
        "TestApiIntegration": {
            "test_analyze_endpoint_accepts_eye_specific_payload",
            "test_analyze_retry_reuses_same_inflight_or_completed_assessment",
        },
    }
    assert {key: set(value) for key, value in manifest.items()} == expected


def test_representative_active_hc_engine_tests_remain_collected():
    assert hasattr(current.TestSafetyGates, "test_hc_sphere_hard_stops_and_exact_boundaries")
    assert hasattr(current.TestBoundaries, "test_pachymetry_boundaries")
    assert hasattr(current.TestApiIntegration, "test_app_exposes_analyze_and_report_routes")


def test_retired_methods_are_not_exposed_on_collected_classes():
    for class_name, method_names in current.PHASE4_RETIRED_HC_ENGINE_METHODS.items():
        cls = getattr(current, class_name)
        for method_name in method_names:
            assert not hasattr(cls, method_name)
