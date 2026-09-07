"""Pure NICE and single-final-disposition tests."""

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
from nice_scoring import score_nice as production_score_nice


@pytest.mark.parametrize(
    "k2,central,pe,i_s",
    [
        (44.0, 530, 10.0, 0.5),
        (45.0, 520, 15.5, 1.0),
        (47.0, 500, 17.9, 1.4),
        (47.1, 499, 18.0, 1.41),
        (48.5, 480, 22.0, -0.5),
        (None, 520, 15, 1.0),
        (44.0, None, 15, 1.0),
        (44.0, 520, None, 1.0),
        (44.0, 520, 15, None),
        (19.9, 520, 15, 1.0),
        (80.1, 520, 15, 1.0),
        (44.0, 299, 15, 1.0),
        (44.0, 801, 15, 1.0),
        (44.0, 520, 301, 1.0),
    ],
)
def test_pure_nice_matches_numeric_scoring_reference(k2, central, pe, i_s):
    expected = production_score_nice(k2, central, pe, i_s)
    actual = score_nice(k2, central, pe, i_s)
    assert actual["total"] == expected["total"]
    assert actual["category"] == expected["category"]
    assert actual["rows"] == expected["rows"]
    assert actual["values"] == expected["values"]
    assert actual["missing"] == expected["missing"]


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
    before = (core.assess_eye, core.hc_engine, core.merge_extractions)
    import clinical_core  # noqa: F401
    after = (core.assess_eye, core.hc_engine, core.merge_extractions)
    assert after == before
