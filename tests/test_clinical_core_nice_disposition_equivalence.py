"""Phase 2 equivalence tests for pure NICE and disposition rules."""

import pytest

import canonical_engine
import clinical_disposition as production_disposition
from clinical_core.disposition import combine_status, presentation_class
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
def test_pure_nice_matches_production(k2, central, pe, i_s):
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
        (4, "PASS"),
        (5, "CAUTION"),
        (8, "CAUTION"),
        (9, "STOP-DEFER"),
        (12, "STOP-DEFER"),
        (None, "DATA INSUFFICIENT"),
    ],
)
def test_nice_specific_disposition_is_launch_frozen(total, expected):
    assert nice_disposition(total) == expected


def test_pure_status_rank_matches_production():
    statuses = tuple(production_disposition.STATUS_RANK)
    for current in statuses:
        for new in statuses:
            assert combine_status(current, new) == production_disposition.combine_status(current, new)


@pytest.mark.parametrize(
    "status",
    ["PASS", "CAUTION", "STOP-DEFER", "DATA INSUFFICIENT", "POST-REFRACTIVE PATHWAY REQUIRED"],
)
def test_presentation_class_matches_production(status):
    assert presentation_class(status) == production_disposition.presentation_class(status)


def test_importing_pure_core_does_not_mutate_runtime():
    core = canonical_engine.core
    before = (core.assess_eye, core.hc_engine, core.merge_extractions)
    import clinical_core  # noqa: F401
    after = (core.assess_eye, core.hc_engine, core.merge_extractions)
    assert after == before
