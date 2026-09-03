"""Non-authoritative Phase 3 shadow evaluator for CER-AI.

The production result remains authoritative. This service evaluates the same
already-normalized clinical input through the linear core, compares the two via
the fail-closed parity service, and returns shadow data separately. It never
mutates or decorates the production clinical result.
"""
from __future__ import annotations

from typing import Any, Mapping

from clinical_core.pipeline import evaluate_normalized_case
from phase3_parity_service import compare_eye_results


def evaluate_shadow(
    production_eye_result: Mapping[str, Any],
    normalized_input: Any,
    *,
    procedure: str,
) -> dict[str, Any]:
    """Evaluate linear core in shadow mode while keeping legacy authoritative."""
    linear_result = evaluate_normalized_case(normalized_input)
    parity = compare_eye_results(
        production_eye_result,
        linear_result,
        procedure=procedure,
    )
    return {
        "mode": "SHADOW_ONLY",
        "authoritative_engine": "LEGACY_COMPOSED_RUNTIME",
        "authoritative_result": production_eye_result,
        "linear_shadow_result": linear_result,
        "parity": parity,
        "cutover_allowed": bool(parity.get("cutover_allowed")),
    }
