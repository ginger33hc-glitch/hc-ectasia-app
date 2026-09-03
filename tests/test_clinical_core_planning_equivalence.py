"""Phase 2 equivalence gates for pure LASIK fallback-planning primitives."""

import lasik_planning
from clinical_core.planning import (
    LASIK_PLANS,
    LASIK_PTA_CUTOFF_PERCENT,
    independent_hard_stop,
    plan_payload,
    plan_responsive_failure,
    planning_summary,
    pta_cutoff,
)


def test_plan_sequence_matches_frozen_production():
    assert LASIK_PLANS == lasik_planning.LASIK_PLANS
    assert LASIK_PTA_CUTOFF_PERCENT == lasik_planning.LASIK_PTA_CUTOFF_PERCENT


def test_pta_cutoff_matches_production_boundaries():
    for value in (39.999, 40.0, 40.001):
        result = {"values": {"LASIK_PTA_percent": value}}
        assert pta_cutoff(result) == lasik_planning._pta_cutoff(result)


def test_independent_hard_stop_matches_production_markers():
    samples = [
        "CER-AI operational hard stop: thinnest preoperative cornea <480 µm.",
        "Definite KC/FFKC/PMD",
        "intended sphere <−10.00 D",
        "intended sphere >+6.00 D",
        "postoperative Kmean <36.00 D",
        "postoperative Kmean >48.00 D",
        "unrelated warning",
    ]
    for text in samples:
        result = {"hard_stops": [text]}
        assert independent_hard_stop(result) == lasik_planning._independent_hard_stop(result)


def test_plan_responsive_failure_matches_production():
    cases = [
        {"hard_stops": [], "score": {"category": "LOW"}},
        {"hard_stops": [], "score": {"category": "HIGH"}},
        {"hard_stops": ["plan-specific stop"], "score": {"category": "LOW"}},
    ]
    for result in cases:
        assert plan_responsive_failure(result) == lasik_planning._plan_responsive_failure(result)


def test_plan_payload_matches_production_and_does_not_mutate_base():
    base = {"procedure": "LASIK", "ablation_um": 120, "custom": "keep"}
    for idx, spec in enumerate(LASIK_PLANS):
        actual = plan_payload(base, spec, first=(idx == 0))
        expected = lasik_planning._plan_payload(base, spec, first=(idx == 0))
        assert actual == expected
    assert base == {"procedure": "LASIK", "ablation_um": 120, "custom": "keep"}


def test_planning_summary_matches_production():
    spec = LASIK_PLANS[1]
    result = {
        "status": "CAUTION",
        "values": {"max_ablation_um": 88.0, "LASIK_RSB_um": 312.0, "LASIK_PTA_percent": 38.5},
        "score": {"total": 3, "category": "CAUTION"},
    }
    assert planning_summary(spec, result) == lasik_planning._summary(spec, result)
