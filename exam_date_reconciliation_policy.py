"""Semantic reconciliation for Pentacam examination dates.

The extractor preserves the printed date string. This policy only decides whether
the authoritative Pentacam sources refer to the same calendar date; it never
rewrites the source strings or invents a date.

Binding CER-AI rule: ONLY Four Maps Refractive pages are authoritative for the
exam date. Dates printed on BAD Display, Show 2 Exams Topometric, or any other
uploaded Pentacam source are excluded entirely from exam-date reconciliation.
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
    """Return all calendar dates compatible with a printed date string."""
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


def _is_four_maps_refractive(extraction):
    """True only for the authoritative Four Maps Refractive source page."""
    for eye in (extraction or {}).get("eyes") or []:
        for screen_type in eye.get("screen_types") or []:
            normalized = re.sub(r"[^A-Z0-9]+", "_", str(screen_type).upper()).strip("_")
            if "FOUR_MAPS_REFRACTIVE" in normalized:
                return True
            if "FOUR_MAPS" in normalized and "REFRACTIVE" in normalized:
                return True
    return False


def _pentacam_date_possibilities(extractions):
    values = []
    for extraction in extractions or []:
        context = (extraction or {}).get("document_context") or {}
        if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
            continue
        if not _is_four_maps_refractive(extraction):
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
    """Remove a date conflict unless authoritative Four Maps pages disagree."""
    authoritative = _pentacam_date_possibilities(extractions)
    if authoritative is None or not authoritative:
        return merged
    if len(authoritative) == 1:
        consistent = True
    else:
        common = set.intersection(*authoritative)
        consistent = len(common) == 1
    if not consistent:
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
