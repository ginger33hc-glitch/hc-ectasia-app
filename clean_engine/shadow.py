"""Non-authoritative comparison primitives for controlled clean-engine migration.

This module never selects a clinical result. It compares an authoritative
canonical snapshot with a clean-engine snapshot and records differences for
migration evidence only.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

from .models import AssessmentResult


@dataclass(frozen=True)
class ClinicalSnapshot:
    status: str
    hard_stops: Tuple[str, ...] = ()
    missing: Tuple[str, ...] = ()
    bad_d_status: Optional[str] = None
    lasik_erss_total: Optional[int] = None
    prk_score_total: Optional[int] = None


@dataclass(frozen=True)
class ShadowComparison:
    equivalent: bool
    differences: Tuple[str, ...]
    canonical: ClinicalSnapshot
    clean: ClinicalSnapshot


def snapshot_clean(result: AssessmentResult) -> ClinicalSnapshot:
    return ClinicalSnapshot(
        status=result.status,
        hard_stops=result.hard_stops,
        missing=result.missing,
        bad_d_status=result.bad_d_status,
        lasik_erss_total=result.scores.erss_total,
        prk_score_total=result.prk_scores.total,
    )


def compare_snapshots(canonical: ClinicalSnapshot, clean: ClinicalSnapshot) -> ShadowComparison:
    """Compare outputs without changing, ranking, or overriding either result."""
    differences = []
    for field in (
        "status", "hard_stops", "missing", "bad_d_status",
        "lasik_erss_total", "prk_score_total",
    ):
        if getattr(canonical, field) != getattr(clean, field):
            differences.append(field)
    return ShadowComparison(
        equivalent=not differences,
        differences=tuple(differences),
        canonical=canonical,
        clean=clean,
    )
