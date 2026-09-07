"""Pure NICE and single-final-disposition tests.

Step-1 authority note: the duplicate ``nice_scoring.py`` implementation was
retired. These tests now lock the approved NICE thresholds directly at the sole
canonical owner, ``clinical_core.nice``.
"""

import pytest

import canonical_engine
from clinical_core.disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
    presentation_class,
)
from clinical_core.nice import nice_disposition, score_nice


@pytest.mark.parametrize(
    "inputs,expected_rows,expected_total,expected_category",
    [
        ((44.99, 521, 15.5, 0.99), {"K2": 1, "central_pachymetry": 1, "B_Ele_Th": 1, "I_S": 1}, 4, "NO_NICE_ESCALATION"),
        ((45.0, 520, 15.5001, 1.0), {"K2": 2, "central_pachymetry": 2, "B_Ele_Th": 2, "I_S": 2}, 8, "CAUTION"),
        ((47.0, 500, 17.9999, 1.4), {"K2": 2, "central_pachymetry": 2, "B_Ele_Th": 2, "I_S": 2}, 8, "CAUTION"),
        ((47.0001, 499.999, 18.0, 1.4001), {"K2": 3, "central_pachymetry": 3, "B_Ele_Th": 3, "I_S": 3}, 12, "HARD_STOP"),
        ((48.5, 530, 10.0, -0.5), {"K2": 3, "central_pachymetry": 1, "B_Ele_Th": 1, "I_S": 1}, 6, "CAUTION"),
    ],
)
def test_canonical_nice_boundary_rows(inputs, expected_rows, expected_total, expected_category):
    actual = score_nice(*inputs)
    assert actual["rows"] == expected_rows
    assert actual["total"] == expected_total
    assert actual["category"] == expected_category
    assert actual["missing"] == []


@pytest.mark.parametrize(
    "inputs,expected_missing",
    [
        ((None, 520, 15, 1.0), ["K2_D"]),
        ((44.0, None, 15, 1.0), ["central_pachy_um"]),
        ((44.0, 520, None, 1.0), ["B_Ele_Th_um"]),
        ((44.0, 520, 15, None), ["I_S_D"]),
        ((19.9, 520, 15, 1.0), ["K2_D"]),
        ((80.1, 520, 15, 1.0), ["K2_D"]),
        ((44.0, 299, 15, 1.0), ["central_pachy_um"]),
        ((44.0, 801, 15, 1.0), ["central_pachy_um"]),
        ((44.0, 520, 301, 1.0), ["B_Ele_Th_um"]),
    ],
)
def test_canonical_nice_incomplete_inputs_fail_closed(inputs, expected_missing):
    actual = score_nice(*inputs)
    assert actual["total"] is None
    assert actual["category"] == "INCOMPLETE"
    assert actual["rows"] == {}
    assert actual["missing"] == expected_missing


@pytest.mark.parametrize(
    "total,expected",
    [
        (4, PASS),
        (5, CAUTION),
        (8, CAUTION),
        (9, STOP_DEFER),
        (12, STOP_DEFER),
        (None, ASSESSMENT_INCOMPLETE),
    ],
)
def test_nice_specific_disposition(total, expected):
    assert nice_disposition(total) == expected


def test_single_finalizer_stop_dominates_and_retains_all_stop_drivers():
    final = finalize_disposition((
        DecisionFinding("bad_d", STOP_DEFER),
        DecisionFinding("safety", STOP_DEFER),
        DecisionFinding("nice", CAUTION),
    ))
    assert final.status == STOP_DEFER
    assert {item.key for item in final.stop_drivers} == {"bad_d", "safety"}


def test_single_finalizer_multiple_cautions_remain_caution():
    final = finalize_disposition((
        DecisionFinding("bad_d", CAUTION),
        DecisionFinding("nice", CAUTION),
    ))
    assert final.status == CAUTION


def test_single_finalizer_incomplete_is_never_pass():
    final = finalize_disposition((
        DecisionFinding("nice", ASSESSMENT_INCOMPLETE),
        DecisionFinding("bad_d", PASS),
    ))
    assert final.status == ASSESSMENT_INCOMPLETE


@pytest.mark.parametrize(
    "status,expected",
    [
        (PASS, "pass"),
        (CAUTION, "caution"),
        (STOP_DEFER, "fail"),
        (ASSESSMENT_INCOMPLETE, "insufficient"),
    ],
)
def test_presentation_class_uses_clean_core_statuses(status, expected):
    assert presentation_class(status) == expected


def test_importing_pure_core_does_not_mutate_runtime():
    core = canonical_engine.core
    before_merge = core.merge_extractions
    assert not hasattr(core, "assess_eye")
    assert not hasattr(core, "hc_engine")
    import clinical_core  # noqa: F401
    assert core.merge_extractions is before_merge
    assert not hasattr(core, "assess_eye")
    assert not hasattr(core, "hc_engine")
