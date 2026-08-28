"""Equivalence tests for centralized clean status semantics."""
import pytest

from clean_engine.status import STATUS_RANK, combine_status, presentation_class


EXPECTED = {
    "PASS": 0,
    "PASS WITH CAUTION": 1,
    "POST-REFRACTIVE PATHWAY REQUIRED": 2,
    "DATA INSUFFICIENT": 3,
    "REVIEW — NOT CLEARED": 4,
    "CAUTION — DEFER": 5,
    "CAUTION — STOP/DEFER": 5,
    "DO NOT PROCEED": 6,
    "FAIL": 6,
}


def test_status_rank_exactly_matches_locked_runtime_contract():
    assert STATUS_RANK == EXPECTED


def test_combine_returns_more_restrictive_status():
    assert combine_status("PASS", "PASS WITH CAUTION") == "PASS WITH CAUTION"
    assert combine_status("PASS WITH CAUTION", "CAUTION — DEFER") == "CAUTION — DEFER"
    assert combine_status("CAUTION — DEFER", "DO NOT PROCEED") == "DO NOT PROCEED"
    assert combine_status("DO NOT PROCEED", "PASS") == "DO NOT PROCEED"


def test_equal_rank_preserves_current_status():
    assert combine_status("CAUTION — DEFER", "CAUTION — STOP/DEFER") == "CAUTION — DEFER"
    assert combine_status("FAIL", "DO NOT PROCEED") == "FAIL"


def test_unknown_status_fails_closed():
    with pytest.raises(ValueError):
        combine_status("PASS", "UNKNOWN")


def test_pass_with_caution_is_green_semantic_class():
    assert presentation_class("PASS") == "pass"
    assert presentation_class("PASS WITH CAUTION") == "pass"
    assert presentation_class("CAUTION — DEFER") == "caution"
    assert presentation_class("DO NOT PROCEED") == "fail"
    assert presentation_class("REVIEW — NOT CLEARED") == "review"
    assert presentation_class("DATA INSUFFICIENT") == "insufficient"
