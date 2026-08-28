"""Aggregate identifier-free shadow evidence for migration review.

The summary is observational only. It does not define a cutover threshold and
cannot authorize or alter a clinical decision.
"""
from dataclasses import dataclass
from typing import Iterable, Tuple

from .shadow_evidence import ShadowEvidence


@dataclass(frozen=True)
class ShadowSummary:
    total: int
    equivalent: int
    divergent: int
    difference_counts: Tuple[Tuple[str, int], ...]


def summarize_shadow_evidence(records: Iterable[ShadowEvidence]) -> ShadowSummary:
    items = tuple(records)
    counts = {}
    for record in items:
        for difference in record.differences:
            counts[difference] = counts.get(difference, 0) + 1
    equivalent = sum(1 for record in items if record.equivalent)
    return ShadowSummary(
        total=len(items),
        equivalent=equivalent,
        divergent=len(items) - equivalent,
        difference_counts=tuple(sorted(counts.items())),
    )
