"""Pure numeric reconciliation primitives for the parallel clean engine.

The clean engine accepts duplicate numeric observations only when all adjudicated
observations belong to the same accepted provenance class and their full relative
spread is <=1%. The higher value is retained. Labeled-table evidence has priority
over permitted map fallback evidence.
"""
from dataclasses import dataclass
from typing import Iterable, Optional


LABELED_TABLE = "LABELED_TABLE"
PERMITTED_MAP_FALLBACK = "PERMITTED_MAP_FALLBACK"
UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class NumericObservation:
    value: float
    source_class: str


def within_one_percent(values: Iterable[float]) -> bool:
    values = [float(v) for v in values]
    if len(values) < 2:
        return False
    low, high = min(values), max(values)
    denominator = max(abs(v) for v in values)
    if denominator == 0:
        return low == high
    return abs(high - low) / denominator <= 0.01 + 1e-12


def reconcile_numeric(observations: Iterable[NumericObservation]) -> Optional[float]:
    observations = list(observations)
    labeled = [o for o in observations if o.source_class == LABELED_TABLE]
    fallback = [o for o in observations if o.source_class == PERMITTED_MAP_FALLBACK]
    chosen = labeled if labeled else fallback
    if not chosen:
        return None
    values = [float(o.value) for o in chosen]
    if len(values) == 1:
        return values[0]
    if not within_one_percent(values):
        return None
    return max(values)
