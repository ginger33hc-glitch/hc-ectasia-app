import os

import pytest


# Unit and equivalence tests exercise clinical endpoints directly. Production
# access control has dedicated tests and is enabled by default outside pytest.
os.environ.setdefault("CERAI_REQUIRE_ACCESS_KEY", "0")


# Phase 1 freezes the launch contract in tests/test_launch_behavior_contract.py.
# The exact legacy tests below encode behavior that was explicitly retired before
# launch (visual ERSS morphology authority, PRK-EWSS numeric scoring, permissive
# Rmin map fallback, and one-image /analyze acceptance). They are kept in source
# for historical traceability but must not be treated as current requirements.
_RETIRED_LEGACY_TESTS = {
    "tests/test_hc_engine.py::TestSafetyGates::test_clinical_eligibility_modifier_blocks_pass_without_score_points": "PRK-EWSS numeric score was removed; the clinical STOP-DEFER modifier remains authoritative.",
    "tests/test_hc_engine.py::TestBoundaries::test_prk_cct_480_not_hard_stop_but_scores_caution": "PRK-EWSS numeric scoring was removed; 480 um remains governed by tissue safety and independent pathways.",
    "tests/test_hc_engine.py::TestScoringAndCompleteness::test_reassuring_prk_can_pass": "PRK-EWSS numeric score was removed; PRK disposition is now produced by independent CER-AI pathways.",
    "tests/test_hc_engine.py::TestBoundaries::test_definite_ectatic_morphology_is_not_downgraded_by_srax_fields": "Visual ERSS morphology authority was explicitly removed; signed I-S and derived SRAX are authoritative.",
    "tests/test_hc_engine.py::TestBoundaries::test_minimal_axis_deviation_is_not_scored_as_srax": "Legacy visual srax_deg is no longer an ERSS input; SRAX is derived from numeric inputs.",
    "tests/test_hc_engine.py::TestBoundaries::test_srax_20_degrees_uses_published_erss_sra_category": "Legacy visual srax_deg is no longer authoritative; the launch contract tests derived SRAX >=20 degrees.",
    "tests/test_hc_engine.py::TestBoundaries::test_srax_below_20_degrees_is_not_scored": "Legacy visual srax_deg is no longer authoritative; the launch contract tests derived SRAX boundaries.",
    "tests/test_hc_engine.py::TestBoundaries::test_unquantified_visual_srax_label_is_not_scored": "Visual morphology/SRAX labels were removed from the ERSS workflow.",
    "tests/test_hc_engine.py::TestScoringAndCompleteness::test_extraction_contract_prioritizes_labeled_pentacam_numeric_fields": "The old prompt assertion expected visual categorical-map instructions that were deliberately removed.",
    "tests/test_hc_engine.py::TestScoringAndCompleteness::test_lasik_score_two_has_no_score_escalation": "This fixture depended on visual asymmetric-bow-tie scoring; numeric I-S/SRAX now determine the topography component.",
    "tests/test_hc_engine.py::TestScoringAndCompleteness::test_local_kmax_is_rejected_but_explicit_local_rmin_remains_permitted": "Rmin map fallback was explicitly removed; Rmin is source-locked to Four Maps Refractive > Cornea Front.",
    "tests/test_hc_engine.py::TestApiIntegration::test_analyze_endpoint_accepts_eye_specific_payload": "Production /analyze now requires the complete five-image mandatory Pentacam source set.",
    "tests/test_hc_engine.py::TestApiIntegration::test_analyze_retry_reuses_same_inflight_or_completed_assessment": "The legacy fixture supplies one image; retry behavior is tested separately from the mandatory five-image gate.",
}


def pytest_collection_modifyitems(config, items):
    """Mark only explicitly retired pre-launch expectations as skipped.

    This is intentionally node-id exact: no file-wide or pattern-based skipping is
    allowed. New tests and all current clinical behavior locks continue to run.
    """
    for item in items:
        reason = _RETIRED_LEGACY_TESTS.get(item.nodeid)
        if reason:
            item.add_marker(pytest.mark.skip(reason=f"Retired pre-launch expectation: {reason}"))
