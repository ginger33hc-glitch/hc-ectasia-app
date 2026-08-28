"""Contract tests for aggregate shadow migration evidence."""
from dataclasses import FrozenInstanceError
import pytest

from clean_engine.shadow_evidence import ShadowEvidence
from clean_engine.shadow_summary import summarize_shadow_evidence


def record(equivalent, differences=()):
    return ShadowEvidence(equivalent, differences, "CANONICAL", "CLEAN")


def test_empty_summary_is_zeroed():
    summary = summarize_shadow_evidence([])
    assert summary.total == 0
    assert summary.equivalent == 0
    assert summary.divergent == 0
    assert summary.difference_counts == ()


def test_summary_counts_equivalence_and_each_difference_field():
    summary = summarize_shadow_evidence([
        record(True),
        record(False, ("status",)),
        record(False, ("status", "hard_stops")),
    ])
    assert summary.total == 3
    assert summary.equivalent == 1
    assert summary.divergent == 2
    assert summary.difference_counts == (("hard_stops", 1), ("status", 2))


def test_summary_is_order_independent_and_deterministic():
    a = record(False, ("missing", "status"))
    b = record(False, ("status",))
    assert summarize_shadow_evidence([a, b]) == summarize_shadow_evidence([b, a])


def test_summary_is_immutable():
    summary = summarize_shadow_evidence([record(True)])
    with pytest.raises(FrozenInstanceError):
        summary.total = 2


def test_summary_has_no_cutover_or_clinical_decision_field():
    names = set(summarize_shadow_evidence([]).__dataclass_fields__)
    assert names == {"total", "equivalent", "divergent", "difference_counts"}
    assert names.isdisjoint({"approved", "ready", "cutover", "decision", "authoritative"})
