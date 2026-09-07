"""Step-1 cleanup contract for physically retired legacy clinical paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent


def test_no_retired_test_skip_hook_remains():
    text = (ROOT / "conftest.py").read_text(encoding="utf-8")
    assert "_RETIRED_LEGACY_TESTS" not in text
    assert "pytest_collection_modifyitems" not in text
    assert "pytest.mark.skip" not in text


def test_monolithic_legacy_hc_engine_tests_are_physically_retired():
    assert not (ROOT / "test_hc_engine.py").exists()
    assert not (ROOT / "legacy_hc_engine_tests.py").exists()


def test_parallel_clean_engine_is_physically_retired():
    assert not (REPO / "clean_engine").exists()
    assert not any(ROOT.glob("test_clean_*.py"))


def test_deleted_runtime_wrappers_are_not_present():
    retired = (
        "hc_age_policy.py",
        "hc_bad_final_policy.py",
        "pachymetry_policy.py",
        "randleman_bad_independence.py",
        "hc_final_decision_policy.py",
        "inter_eye_tomography_policy.py",
        "ps3_runtime_policy.py",
        "erss_auto_read_policy.py",
        "erss_topography_evidence_policy.py",
        "erss_topography_guard.py",
        "erss_visual_morphology_policy.py",
        "microkeratome_planning_policy.py",
        "lasik_planning.py",
        "nice_policy.py",
        "nice_scoring.py",
    )
    for path in retired:
        assert not (REPO / path).exists(), path


def test_retirement_record_exists_and_names_canonical_authority():
    record = (REPO / "docs" / "CERAI_STEP1_TEST_RETIREMENTS.md").read_text(encoding="utf-8")
    assert "clinical_core" in record
    assert "canonical_runtime_service" in record
    assert "assessment_workflow" in record
    assert "Monolithic legacy HC-engine regression suite" in record
