"""Single canonical CER-AI final-disposition owner."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PASS = "PASS"
CAUTION = "CAUTION"
PASS_WITH_CAUTION = "PASS WITH CAUTION"
STOP_DEFER = "STOP-DEFER"
ASSESSMENT_INCOMPLETE = "ASSESSMENT INCOMPLETE"
POST_REFRACTIVE = "POST-REFRACTIVE PATHWAY REQUIRED"

# Compatibility name for callers being migrated; same status, not a second rule.
DATA_INSUFFICIENT = ASSESSMENT_INCOMPLETE


@dataclass(frozen=True)
class DecisionFinding:
    key: str
    status: str
    detail: str = ""


@dataclass(frozen=True)
class FinalDisposition:
    status: str
    stop_drivers: tuple[DecisionFinding, ...]
    caution_drivers: tuple[DecisionFinding, ...]
    incomplete_drivers: tuple[DecisionFinding, ...]


def finalize_disposition(findings: Iterable[DecisionFinding]) -> FinalDisposition:
    """Combine ERSS/NICE/PS3/Final BAD-D once, preserving independent gates and eye results.

    STOP dominates everything. Missing decision-critical data is never PASS.
    Zero or one caution among four completed systems yields PASS; two yield
    PASS WITH CAUTION; three or four yield CAUTION. Independent caution findings retain
    CAUTION. Already-combined eye results propagate without counting eyes as
    scoring systems. All drivers remain available for report/archive tracing.
    """
    findings = tuple(findings)
    allowed = {PASS, PASS_WITH_CAUTION, CAUTION, STOP_DEFER, ASSESSMENT_INCOMPLETE}
    invalid = [finding for finding in findings if finding.status not in allowed]
    if invalid:
        raise ValueError(f"Unknown CER-AI decision status: {invalid[0].status!r}")

    stop_drivers = tuple(f for f in findings if f.status == STOP_DEFER)
    caution_drivers = tuple(f for f in findings if f.status in {CAUTION, PASS_WITH_CAUTION})
    incomplete_drivers = tuple(f for f in findings if f.status == ASSESSMENT_INCOMPLETE)
    scoring_keys = {"randleman_erss", "nice", "ps3", "bad_d"}
    completed_scoring_keys = {f.key for f in findings if f.key in scoring_keys and f.status in {PASS, CAUTION}}
    caution_scoring_keys = {f.key for f in findings if f.key in scoring_keys and f.status == CAUTION}
    independent_caution = any(f.status == CAUTION and f.key not in scoring_keys for f in findings)

    if stop_drivers:
        status = STOP_DEFER
    elif incomplete_drivers:
        status = ASSESSMENT_INCOMPLETE
    elif caution_drivers:
        if independent_caution or len(caution_scoring_keys) >= 3:
            status = CAUTION
        elif caution_scoring_keys:
            if completed_scoring_keys != scoring_keys:
                status = CAUTION
            else:
                status = PASS if len(caution_scoring_keys) == 1 else PASS_WITH_CAUTION
        else:
            status = PASS_WITH_CAUTION
    else:
        status = PASS
    return FinalDisposition(status, stop_drivers, caution_drivers, incomplete_drivers)


def presentation_class(status: str) -> str:
    if status == PASS:
        return "pass"
    if status in {CAUTION, PASS_WITH_CAUTION}:
        return "caution"
    if status == STOP_DEFER:
        return "fail"
    return "insufficient"
