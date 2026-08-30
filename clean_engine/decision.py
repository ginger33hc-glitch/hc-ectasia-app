"""Pure final-decision hierarchy for the parallel clean engine.

No production wiring. This mirrors the locked principal hierarchy while using
the shared CER-AI score disposition policy.
"""
from dataclasses import dataclass

from .policy import score_decision_band


@dataclass(frozen=True)
class DecisionInput:
    upstream_status: str
    bad_d_status: str
    erss_total: float | None
    has_hard_stop: bool = False
    decision_critical_incomplete: bool = False


@dataclass(frozen=True)
class DecisionOutput:
    status: str
    rule: str


def decide(inp: DecisionInput) -> DecisionOutput:
    status_upper = (inp.upstream_status or "").upper()
    if inp.has_hard_stop or status_upper in {"DO NOT PROCEED", "FAIL"}:
        return DecisionOutput(inp.upstream_status, "PRESERVE_HARD_STOP")
    if inp.decision_critical_incomplete or "DATA INSUFFICIENT" in status_upper or "NOT ASSESSED" in status_upper:
        return DecisionOutput(inp.upstream_status, "PRESERVE_INCOMPLETE")
    if inp.bad_d_status in {"UNAVAILABLE", "UNREADABLE", ""} or inp.erss_total is None:
        return DecisionOutput(inp.upstream_status, "PRESERVE_UNAVAILABLE_PRINCIPAL_INPUT")
    if inp.bad_d_status == "ABNORMAL":
        return DecisionOutput("DO NOT PROCEED", "FINAL_BAD_D_ABNORMAL")
    score_band = score_decision_band(inp.erss_total)
    if score_band in {"DEFER", "STOP"}:
        if status_upper in {"PASS", "PASS WITH CAUTION"}:
            return DecisionOutput("CAUTION — DEFER", "ERSS_GE_3")
        return DecisionOutput(inp.upstream_status, "ERSS_GE_3_PRESERVE_MORE_ADVERSE_UPSTREAM")
    return DecisionOutput("PASS WITH CAUTION", "FINAL_BAD_D_NOT_ABNORMAL_AND_ERSS_LT_3")
