"""Single canonical CER-AI final-disposition owner."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

PASS = "PASS"
CAUTION = "CAUTION"
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
    """Assign final PASS/CAUTION/STOP-DEFER/INCOMPLETE exactly once.

    STOP dominates everything. Missing decision-critical data is never PASS.
    Multiple cautions remain CAUTION and never auto-escalate to STOP. All drivers
    are retained for reporting and archive traceability.
    """
    findings = tuple(findings)
    allowed = {PASS, CAUTION, STOP_DEFER, ASSESSMENT_INCOMPLETE}
    invalid = [finding for finding in findings if finding.status not in allowed]
    if invalid:
        raise ValueError(f"Unknown CER-AI decision status: {invalid[0].status!r}")

    stop_drivers = tuple(f for f in findings if f.status == STOP_DEFER)
    caution_drivers = tuple(f for f in findings if f.status == CAUTION)
    incomplete_drivers = tuple(f for f in findings if f.status == ASSESSMENT_INCOMPLETE)

    if stop_drivers:
        status = STOP_DEFER
    elif incomplete_drivers:
        status = ASSESSMENT_INCOMPLETE
    elif caution_drivers:
        status = CAUTION
    else:
        status = PASS
    return FinalDisposition(status, stop_drivers, caution_drivers, incomplete_drivers)


def presentation_class(status: str) -> str:
    if status == PASS:
        return "pass"
    if status == CAUTION:
        return "caution"
    if status == STOP_DEFER:
        return "fail"
    return "insufficient"
