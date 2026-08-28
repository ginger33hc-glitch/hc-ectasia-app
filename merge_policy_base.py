"""Canonical pre-validation merge layer.

This module removes the superseded field-specific duplicate-measurement reconciliation
from bootstrap.py while preserving its EX500 aggregation behavior. Numeric duplicate
reconciliation belongs exclusively to extraction_guard.py, where provenance-aware
<=1% adjudication is applied.
"""
import bootstrap

core = bootstrap.core
_base_merge = bootstrap._original_merge_extractions


def merge_extractions_without_legacy_numeric_reconciliation(results):
    """Merge normally, preserve EX500 plans, and leave numeric conflicts untouched."""
    merged = _base_merge(results)
    laser_plans = []
    ex500_files = set()

    for result in results:
        context = result.get("document_context") or {}
        if context.get("document_type") == "ALCON_EX500_PLANNING" and context.get("source_filename"):
            ex500_files.add(context["source_filename"])
        for item in result.get("laser_plans", []):
            if isinstance(item, dict):
                copied = dict(item)
                copied["source_filename"] = context.get("source_filename")
                laser_plans.append(copied)

    merged["laser_plans"] = laser_plans
    if ex500_files:
        merged["critical_input_issues"] = [
            issue for issue in merged.get("critical_input_issues", [])
            if not (
                str(issue).startswith("Uploaded source yielded no usable eye or treatment data:")
                and any(name in str(issue) for name in ex500_files)
            )
        ]

    return merged


core.merge_extractions = merge_extractions_without_legacy_numeric_reconciliation
core._hc_unified_merge_base_installed = True
