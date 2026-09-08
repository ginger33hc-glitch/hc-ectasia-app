"""Semantic reconciliation for Pentacam examination dates.

The extractor preserves the printed date string. This policy only decides whether
the authoritative Pentacam sources refer to the same calendar date; it never
rewrites the source strings or invents a date.

Binding CER-AI rule: ONLY Four Maps Refractive pages are authoritative for the
exam date. Dates printed on BAD Display, Show 2 Exams Topometric, or any other
uploaded Pentacam source are excluded entirely from exam-date reconciliation.
"""
from datetime import date
import re


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


def _normalized_printed_date(value):
    """Normalize separators only; retain the printed value in extraction evidence."""
    text = " ".join(str(value or "").strip().split())
    return re.sub(r"[.-]", "/", text)


def _dates_have_one_calendar_interpretation(values):
    if len(values) < 2:
        return False
    possibilities = [possible_calendar_dates(value) for value in values]
    if any(not item for item in possibilities):
        return False
    # Two Four Maps pages from the same Pentacam can print the same ambiguous
    # day/month string. Equal printed numeric components establish consistency
    # even though the calendar locale cannot be inferred from the string alone.
    normalized = {_normalized_printed_date(value) for value in values}
    if len(normalized) == 1:
        return True
    return len(set.intersection(*possibilities)) == 1


def _authoritative_date_values(extractions, *, targeted=False):
    values = []
    for extraction in extractions or []:
        context = (extraction or {}).get("document_context") or {}
        if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
            continue
        if not _is_four_maps_refractive(extraction):
            continue
        if targeted:
            evidence = context.get("targeted_exam_date_reread_evidence") or {}
            raw = evidence.get("value")
        else:
            raw = context.get("exam_date")
        if raw not in (None, ""):
            values.append(raw)
    return values


def dates_are_semantically_consistent(extractions):
    values = _authoritative_date_values(extractions)
    return _dates_have_one_calendar_interpretation(values)


def authoritative_exam_date_conflict(extractions) -> bool:
    """Return whether two or more authoritative Four Maps dates conflict."""
    values = _authoritative_date_values(extractions)
    if len(values) < 2:
        return False
    if any(not possible_calendar_dates(value) for value in values):
        return True
    return not _dates_have_one_calendar_interpretation(values)


def promote_consistent_targeted_exam_dates(extractions) -> bool:
    """Promote focused Four Maps header rereads only when both pages agree.

    Primary OCR strings remain attached as evidence. No targeted value is used
    unless every authoritative Four Maps page produced a valid, mutually
    consistent date reread.
    """
    authoritative = [
        extraction for extraction in extractions or []
        if ((extraction or {}).get("document_context") or {}).get("document_type")
        == "PENTACAM_TOPOGRAPHY"
        and _is_four_maps_refractive(extraction)
    ]
    if len(authoritative) < 2:
        return False
    values = _authoritative_date_values(authoritative, targeted=True)
    if len(values) != len(authoritative) or not _dates_have_one_calendar_interpretation(values):
        return False
    for extraction in authoritative:
        context = extraction["document_context"]
        evidence = context["targeted_exam_date_reread_evidence"]
        context["primary_exam_date_reading"] = context.get("exam_date")
        context["exam_date"] = evidence["value"]
        evidence["promoted"] = True
    return True
