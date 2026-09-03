"""PHI-free aggregate diagnostics for CER-AI Phase 3 shadow evaluation.

This module never stores patient identifiers, eye measurements, plans, full
clinical results, reports, or archive payloads.  It records only aggregate
counts and parity mismatch channel names.  Shadow diagnostics are disabled by
default and never influence the authoritative clinical decision.
"""
from __future__ import annotations

import os
from collections import Counter
from threading import RLock
from typing import Any, Mapping

from phase3_shadow_service import evaluate_shadow

ENV_FLAG = "CERAI_LINEAR_SHADOW_DIAGNOSTICS_ENABLED"

_lock = RLock()
_total = 0
_matches = 0
_mismatches = 0
_channel_mismatches: Counter[str] = Counter()


def shadow_diagnostics_enabled(env: Mapping[str, str] | None = None) -> bool:
    source = os.environ if env is None else env
    return str(source.get(ENV_FLAG, "0")).strip().lower() in {"1", "true", "yes", "on"}


def observe_shadow_parity(
    production_eye_result: Mapping[str, Any],
    normalized_input: Any,
    *,
    procedure: str,
    enabled: bool | None = None,
) -> dict[str, Any]:
    """Run one shadow comparison and retain aggregate diagnostics only."""
    use_shadow = shadow_diagnostics_enabled() if enabled is None else bool(enabled)
    if not use_shadow:
        return {"observed": False, "reason": "SHADOW_DIAGNOSTICS_DISABLED"}

    shadow = evaluate_shadow(
        production_eye_result,
        normalized_input,
        procedure=procedure,
    )
    mismatches = tuple(str(x) for x in shadow.get("parity", {}).get("mismatches", ()))

    global _total, _matches, _mismatches
    with _lock:
        _total += 1
        if mismatches:
            _mismatches += 1
            _channel_mismatches.update(mismatches)
        else:
            _matches += 1

    return {
        "observed": True,
        "cutover_allowed": not mismatches,
        "mismatch_channels": list(mismatches),
    }


def diagnostics_snapshot() -> dict[str, Any]:
    """Return aggregate, non-clinical diagnostics only."""
    with _lock:
        return {
            "total_observations": _total,
            "parity_matches": _matches,
            "parity_mismatches": _mismatches,
            "mismatch_channels": dict(sorted(_channel_mismatches.items())),
        }


def _reset_diagnostics_for_tests() -> None:
    global _total, _matches, _mismatches
    with _lock:
        _total = 0
        _matches = 0
        _mismatches = 0
        _channel_mismatches.clear()
