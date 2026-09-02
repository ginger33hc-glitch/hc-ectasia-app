"""Procedure-aware status composition and final-decision stage."""
from dataclasses import dataclass
from typing import Optional, Tuple

from .decision import DecisionInput, DecisionOutput, decide
from .models import PrkScoreValues
from .status import combine_status
from clinical_disposition import CAUTION, PASS, STOP_DEFER


@dataclass(frozen=True)
class FinalizationInput:
    procedure: str
    bad_d_status: str
    lasik_erss_total: Optional[float]
    prk_scores: PrkScoreValues
    hard_stops: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FinalizationOutput:
    status: str
    rule: str
    upstream_status: str


def finalize(inp: FinalizationInput) -> FinalizationOutput:
    """Compose procedure-specific upstream status, then apply principal hierarchy."""
    procedure = (inp.procedure or "").upper()
    upstream = STOP_DEFER if inp.hard_stops else ("DATA INSUFFICIENT" if inp.missing else PASS)

    if procedure == "PRK" and not inp.hard_stops and not inp.missing:
        if inp.prk_scores.category == "HIGH_CONCERN":
            upstream = combine_status(upstream, STOP_DEFER)
        elif inp.prk_scores.category == "CAUTION":
            upstream = combine_status(upstream, STOP_DEFER)
        if inp.prk_scores.pta_evidence_gap:
            upstream = combine_status(upstream, CAUTION)
    elif procedure == "LASIK" and not inp.hard_stops and not inp.missing:
        if inp.lasik_erss_total == 3:
            upstream = combine_status(upstream, CAUTION)

    decision: DecisionOutput = decide(DecisionInput(
        upstream_status=upstream,
        bad_d_status=inp.bad_d_status,
        erss_total=inp.lasik_erss_total,
        has_hard_stop=bool(inp.hard_stops),
        decision_critical_incomplete=bool(inp.missing),
    ))
    return FinalizationOutput(decision.status, decision.rule, upstream)
