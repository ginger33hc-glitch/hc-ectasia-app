"""Read-only adapter from canonical result dictionaries to shadow snapshots.

The adapter does not execute, rank, or modify clinical decisions. It only copies
already-produced canonical output into the neutral migration comparison model.
"""
from typing import Any, Mapping, Optional, Tuple

from .shadow import ClinicalSnapshot


def _tuple_strings(value: Any) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item) for item in value)


def _score_total(result: Mapping[str, Any]) -> Optional[int]:
    score = result.get("score")
    if not isinstance(score, Mapping):
        return None
    total = score.get("total")
    if isinstance(total, bool) or not isinstance(total, (int, float)):
        return None
    return int(total)


def snapshot_canonical(result: Mapping[str, Any]) -> ClinicalSnapshot:
    """Copy decision-critical fields from an authoritative canonical result."""
    values = result.get("values")
    procedure = str(values.get("procedure") or "").upper() if isinstance(values, Mapping) else ""
    total = _score_total(result)
    return ClinicalSnapshot(
        status=str(result.get("status") or ""),
        hard_stops=_tuple_strings(result.get("hard_stops")),
        missing=_tuple_strings(result.get("missing")),
        bad_d_status=(
            str(result["bad_d_status"])
            if result.get("bad_d_status") is not None
            else None
        ),
        lasik_erss_total=total if procedure == "LASIK" else None,
        prk_score_total=total if procedure == "PRK" else None,
    )
