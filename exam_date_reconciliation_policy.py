"""Semantic reconciliation for Pentacam examination dates.

The extractor preserves the printed date string. This policy only decides whether
multiple Pentacam sources refer to the same calendar date; it never rewrites the
source strings or invents a date.
"""
from copy import deepcopy
from datetime import date
import re

_CONFLICT = "Conflicting Pentacam examination dates across uploaded sources."
_previous_merge_extractions = None


def _valid_iso(year, month, day):
    try:
        return date(int(year), int(month), int(day)).isoformat()
    except (TypeError, ValueError):
        return None


def possible_calendar_dates(value):
    """Return all calendar dates compatible with a printed date string.

    Ambiguous numeric day/month strings deliberately return both valid
    interpretations. A conflict is suppressed only when every Pentacam source
    shares exactly one possible calendar date.
    """
    if value is None:
        return set()
    text = " ".join(str(value).strip().split())
    if not text:
        return set()

    match = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        parsed = _valid_iso(*match.groups())
        return {parsed} if parsed else set()

    match = re.fullmatch(r"(\d{1,2})([./-])(\d{1,2})\2(\d{4})", text)
    if not match:
        return set()
    first, separator, second, year = match.groups()
    if separator == ".":
        parsed = _valid_iso(year, second, first)
        return {parsed} if parsed else set()

    return {
        parsed
        for parsed in (
            _valid_iso(year, first, second),
            _valid_iso(year, second, first),
        )
        if parsed
    }


def _pentacam_date_possibilities(extractions):
    values = []
    for extraction in extractions or []:
        context = (extraction or {}).get("document_context") or {}
        if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
            continue
        raw = context.get("exam_date")
        if raw in (None, ""):
            continue
        possibilities = possible_calendar_dates(raw)
        if not possibilities:
            return None
        values.append(possibilities)
    return values


def dates_are_semantically_consistent(extractions):
    possibilities = _pentacam_date_possibilities(extractions)
    if not possibilities or len(possibilities) < 2:
        return False
    common = set.intersection(*possibilities)
    return len(common) == 1


def reconcile_merged_exam_date_conflict(merged, extractions):
    """Remove only a false raw-string date conflict from an already merged result."""
    if not dates_are_semantically_consistent(extractions):
        return merged
    reconciled = deepcopy(merged)
    reconciled["critical_input_issues"] = [
        issue for issue in reconciled.get("critical_input_issues") or []
        if str(issue) != _CONFLICT
    ]
    return reconciled


def merge_extractions_with_exam_date_reconciliation(extractions):
    """Compatibility wrapper for isolated tests; production composes this inside PS3 merge."""
    if _previous_merge_extractions is None:
        raise RuntimeError("Exam-date reconciliation wrapper was not initialized")
    return reconcile_merged_exam_date_conflict(_previous_merge_extractions(extractions), extractions)


def install(runtime_core):
    """Compatibility installer only; production must not stack this outside the canonical merge adapter."""
    global _previous_merge_extractions
    if getattr(runtime_core, "_exam_date_reconciliation_policy_installed", False):
        return
    _previous_merge_extractions = runtime_core.merge_extractions
    runtime_core.merge_extractions = merge_extractions_with_exam_date_reconciliation
    runtime_core._exam_date_reconciliation_policy_installed = True
