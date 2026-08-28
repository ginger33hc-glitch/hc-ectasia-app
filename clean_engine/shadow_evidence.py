"""Typed, non-clinical evidence records for clean-engine shadow migration.

These records summarize comparison outcomes only. They never alter, rank, or
select a clinical decision and deliberately contain no patient identifiers.
"""
from dataclasses import dataclass
from typing import Tuple

from .shadow import ShadowComparison


@dataclass(frozen=True)
class ShadowEvidence:
    equivalent: bool
    differences: Tuple[str, ...]
    canonical_status: str
    clean_status: str


def build_shadow_evidence(comparison: ShadowComparison) -> ShadowEvidence:
    """Reduce a comparison to immutable, identifier-free migration evidence."""
    return ShadowEvidence(
        equivalent=comparison.equivalent,
        differences=comparison.differences,
        canonical_status=comparison.canonical.status,
        clean_status=comparison.clean.status,
    )
