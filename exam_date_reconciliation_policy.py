"""Semantic reconciliation for Pentacam examination dates.

The extractor preserves the printed date string. This policy only decides whether
the authoritative Pentacam sources refer to the same calendar date; it never
rewrites the source strings or invents a date.

Binding CER-AI rule: ONLY Four Maps Refractive pages are authoritative for the
exam date. Dates printed on BAD Display, Show 2 Exams Topometric, or any other
uploaded Pentacam source are excluded entirely from exam-date reconciliation.
"""
from datetime import date
from copy import deepcopy
import re


EXAM_DATE_CONFLICT_ISSUE = "Conflicting Pentacam examination dates across uploaded sources."
EXAM_DATE_CONFIRMATION_KEY = "pentacam_exam_date_conflict"
EXAM_DATE_APPROVAL = "APPROVE_CONTINUE"
EXAM_DATE_APPROVAL_WARNING = (
    "PENTACAM EXAMINATION DATE CONFLICT: automated readings could not be reconciled; "
    "the surgeon reviewed the uploaded Four Maps headers and approved continuation."
)


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


def merged_exam_date_evidence(extracted):
    """Return display-only evidence from authoritative merged Four Maps contexts."""
    evidence = []
    for context in (extracted or {}).get("document_contexts") or []:
        if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
            continue
        eyes = [eye for eye in context.get("four_maps_eyes") or [] if eye in {"OD", "OS"}]
        if not eyes:
            continue
        targeted = context.get("targeted_exam_date_reread_evidence") or {}
        primary = context.get("primary_exam_date_reading", context.get("exam_date"))
        evidence.append({
            "source_filename": context.get("source_filename"),
            "eyes": eyes,
            "primary_reading": primary,
            "targeted_reread": targeted.get("value"),
            "effective_reading": context.get("exam_date"),
        })
    return evidence


def apply_surgeon_exam_date_approval(extracted, source_confirmations):
    """Resolve only this policy's blocker after explicit surgeon approval.

    The source date readings are preserved. This records an approval rather than
    rewriting either source date or declaring the automated readings consistent.
    """
    working = deepcopy(extracted)
    if not isinstance(source_confirmations, dict):
        raise ValueError("Source confirmations must be an object.")
    if set(source_confirmations) - {EXAM_DATE_CONFIRMATION_KEY}:
        raise ValueError("Unsupported source confirmation.")
    decision = source_confirmations.get(EXAM_DATE_CONFIRMATION_KEY)
    if decision is None:
        return working
    if decision != EXAM_DATE_APPROVAL:
        raise ValueError("Invalid Pentacam examination-date confirmation.")
    issues = list(working.get("critical_input_issues") or [])
    if EXAM_DATE_CONFLICT_ISSUE not in issues:
        already_approved = any(
            item.get("key") == EXAM_DATE_CONFIRMATION_KEY
            and item.get("decision") == EXAM_DATE_APPROVAL
            for item in working.get("surgeon_source_confirmations") or []
        )
        if already_approved:
            return working
        raise ValueError("No unresolved Pentacam examination-date conflict is available for approval.")
    working["critical_input_issues"] = [
        issue for issue in issues if issue != EXAM_DATE_CONFLICT_ISSUE
    ]
    confirmation = {
        "key": EXAM_DATE_CONFIRMATION_KEY,
        "decision": EXAM_DATE_APPROVAL,
        "evidence": merged_exam_date_evidence(working),
    }
    existing = [
        item for item in working.get("surgeon_source_confirmations") or []
        if item.get("key") != EXAM_DATE_CONFIRMATION_KEY
    ]
    working["surgeon_source_confirmations"] = existing + [confirmation]
    working["identity_warnings"] = list(dict.fromkeys(
        list(working.get("identity_warnings") or []) + [EXAM_DATE_APPROVAL_WARNING]
    ))
    return working
