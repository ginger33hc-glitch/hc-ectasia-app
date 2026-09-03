"""Fail-closed Phase 3 parity checks."""
from copy import deepcopy

from phase3_parity_service import compare_eye_results


def _production():
    return {
        "status": "PASS",
        "score": {"total": 1},
        "bad_summary": {"category": "NORMAL"},
        "nice": {"total": 4},
        "ps3": {"disposition": {"lasik": "ALLOWED", "prk": "ALLOWED", "smile": "ALLOWED"}},
        "values": {
            "LASIK_RSB_um": 350.0,
            "LASIK_PTA_percent": 33.0,
            "estimated_final_Kmean_D": 42.0,
        },
    }


def _linear():
    return {
        "status": "PASS",
        "erss": {"total": 1},
        "bad_d": {"classification": "NORMAL"},
        "nice": {"total": 4},
        "ps3_status": "PASS",
        "procedural_safety": {
            "LASIK_RSB_um": 350.0,
            "LASIK_PTA_percent": 33.0,
            "estimated_final_Kmean_D": 42.0,
        },
    }


def test_exact_channel_parity_allows_cutover():
    result = compare_eye_results(_production(), _linear(), procedure="LASIK")
    assert result["cutover_allowed"] is True
    assert result["mismatches"] == []


def test_single_clinical_mismatch_blocks_cutover():
    production = _production()
    linear = _linear()
    linear["bad_d"]["classification"] = "SUSPICIOUS"
    result = compare_eye_results(production, linear, procedure="LASIK")
    assert result["cutover_allowed"] is False
    assert "bad_d_classification" in result["mismatches"]


def test_structural_mismatch_blocks_cutover():
    linear = _linear()
    linear["procedural_safety"]["LASIK_PTA_percent"] = 40.0
    result = compare_eye_results(_production(), linear, procedure="LASIK")
    assert result["cutover_allowed"] is False
    assert "LASIK_PTA_percent" in result["mismatches"]


def test_final_status_mismatch_blocks_cutover_by_default():
    linear = _linear()
    linear["status"] = "CAUTION"
    result = compare_eye_results(_production(), linear, procedure="LASIK")
    assert result["cutover_allowed"] is False
    assert "final_status" in result["mismatches"]


def test_comparison_is_read_only():
    production = _production()
    linear = _linear()
    before = deepcopy((production, linear))
    compare_eye_results(production, linear, procedure="LASIK")
    assert (production, linear) == before
