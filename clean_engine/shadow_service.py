"""Non-authoritative service for canonical-vs-clean migration evidence.

This boundary accepts an already-produced canonical result and a reconciled clean
input. It never chooses, ranks, or replaces the authoritative clinical result.
"""
from typing import Any, Mapping

from .canonical_adapter import snapshot_canonical
from .input_adapter import ReconciledEyeInput
from .migration import run_clean_assessment
from .shadow import ShadowComparison, compare_snapshots, snapshot_clean


def compare_canonical_with_clean(
    canonical_result: Mapping[str, Any],
    clean_input: ReconciledEyeInput,
) -> ShadowComparison:
    """Run clean assessment and return read-only comparison evidence."""
    canonical = snapshot_canonical(canonical_result)
    clean = snapshot_clean(run_clean_assessment(clean_input).result)
    return compare_snapshots(canonical, clean)
