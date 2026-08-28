"""Single-source decision status semantics for the parallel clean engine."""
from enum import Enum


class DecisionStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_CAUTION = "PASS WITH CAUTION"
    POST_REFRACTIVE_PATHWAY_REQUIRED = "POST-REFRACTIVE PATHWAY REQUIRED"
    DATA_INSUFFICIENT = "DATA INSUFFICIENT"
    REVIEW_NOT_CLEARED = "REVIEW — NOT CLEARED"
    CAUTION_DEFER = "CAUTION — DEFER"
    CAUTION_STOP_DEFER = "CAUTION — STOP/DEFER"
    DO_NOT_PROCEED = "DO NOT PROCEED"
    FAIL = "FAIL"


STATUS_RANK = {
    DecisionStatus.PASS.value: 0,
    DecisionStatus.PASS_WITH_CAUTION.value: 1,
    DecisionStatus.POST_REFRACTIVE_PATHWAY_REQUIRED.value: 2,
    DecisionStatus.DATA_INSUFFICIENT.value: 3,
    DecisionStatus.REVIEW_NOT_CLEARED.value: 4,
    DecisionStatus.CAUTION_DEFER.value: 5,
    DecisionStatus.CAUTION_STOP_DEFER.value: 5,
    DecisionStatus.DO_NOT_PROCEED.value: 6,
    DecisionStatus.FAIL.value: 6,
}


def combine_status(current: str, new: str) -> str:
    current_rank = STATUS_RANK.get(current)
    new_rank = STATUS_RANK.get(new)
    if current_rank is None or new_rank is None:
        raise ValueError(f"Unknown HC decision status: current={current!r}, new={new!r}")
    return new if new_rank > current_rank else current


def presentation_class(status: str) -> str:
    """Return semantic presentation class without embedding CSS or mutating UI files."""
    if status in {DecisionStatus.PASS.value, DecisionStatus.PASS_WITH_CAUTION.value}:
        return "pass"
    if status in {DecisionStatus.DO_NOT_PROCEED.value, DecisionStatus.FAIL.value}:
        return "fail"
    if status.startswith("CAUTION"):
        return "caution"
    if status.startswith("REVIEW"):
        return "review"
    return "insufficient"
