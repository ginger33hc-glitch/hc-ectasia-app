"""Pure PRK provisional scoring policy for the parallel clean engine.

This mirrors the currently locked PRK-EWSS v1.0 behavior. It is intentionally
kept separate from validated LASIK ERSS terminology and scoring.
"""
from typing import Optional

from .policy import age_points


def prk_morphology_points(morphology: str) -> Optional[int]:
    return {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 5,
        "ABNORMAL_ECTATIC": 5,
    }.get(morphology)


def prk_pachymetry_points(pachy_um: Optional[float]) -> Optional[int]:
    if not isinstance(pachy_um, (int, float)) or isinstance(pachy_um, bool):
        return None
    value = float(pachy_um)
    if value <= 450:
        return 4
    if value <= 480:
        return 3
    if value <= 510:
        return 2
    return 0


def prk_score_total(age_years: Optional[float], pachy_um: Optional[float], morphology: str) -> Optional[int]:
    components = (
        prk_morphology_points(morphology),
        prk_pachymetry_points(pachy_um),
        age_points(age_years),
    )
    if any(value is None for value in components):
        return None
    return int(sum(components))


def prk_score_category(score: Optional[int]) -> Optional[str]:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return None
    if score <= 1:
        return "LOWER_FLAGGED_BURDEN"
    if score <= 3:
        return "CAUTION"
    return "HIGH_CONCERN"


def prk_pta_evidence_gap(pta_percent: Optional[float]) -> bool:
    """Legacy review flag; not an HC hard-stop threshold."""
    return (
        isinstance(pta_percent, (int, float))
        and not isinstance(pta_percent, bool)
        and float(pta_percent) > 35.28
    )
