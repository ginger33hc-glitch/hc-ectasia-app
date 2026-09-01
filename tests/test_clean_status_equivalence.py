"""Equivalence tests for centralized clean status semantics."""
import pytest

from clean_engine.status import STATUS_RANK, combine_status, presentation_class
from clinical_disposition import CLINICAL_STATUSES


EXPECTED = {
    "PASS": 0,
    "CAUTION": 1,
    "POST-REFRACTIVE PATHWAY REQUIRED": 2,
    "DATA INSUFFICIENT": 3,
    "STOP-DEFER": 4,
}


def test_status_rank_exactly_matches_locked_runtime_contract():
    assert STATUS_RANK == EXPECTED


def test_clinical_result_contract_has_exactly_three_categories():
    assert CLINICAL_STATUSES == frozenset({"PASS", "CAUTION", "STOP-DEFER"})


def test_combine_returns_more_restrictive_status():
    assert combine_status("PASS", "PASS") == "PASS"
    assert combine_status("PASS", "STOP-DEFER") == "STOP-DEFER"
    assert combine_status("STOP-DEFER", "STOP-DEFER") == "STOP-DEFER"
    assert combine_status("STOP-DEFER", "PASS") == "STOP-DEFER"


def test_equal_rank_preserves_current_status():
    assert combine_status("STOP-DEFER", "STOP-DEFER") == "STOP-DEFER"


def test_unknown_status_fails_closed():
    with pytest.raises(ValueError):
        combine_status("PASS", "UNKNOWN")


def test_three_dispositions_have_distinct_semantic_classes():
    assert presentation_class("PASS") == "pass"
    assert presentation_class("CAUTION") == "caution"
    assert presentation_class("STOP-DEFER") == "fail"
    assert presentation_class("DATA INSUFFICIENT") == "insufficient"
