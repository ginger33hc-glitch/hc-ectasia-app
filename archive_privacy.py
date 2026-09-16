"""Canonical de-identification boundary for OWNER retrospective archive access.

Doctors may retrieve original material only for cases they created. OWNER archive
routes must pass every catalog entry, assessment, and report through this module.
OWNER accounts must never receive source-image bytes or immutable original reports.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MASKED = "Masked for owner"

_IDENTITY_KEYS = {
    "patient_id", "patient_name", "patient_first_name", "patient_last_name",
    "patient_date_of_birth", "date_of_birth", "birth_date",
}
_FILENAME_KEYS = {
    "file", "filename", "source_filename", "name_source_file", "original_filename",
}


def _identity_literals(value: Any) -> list[str]:
    literals: set[str] = set()

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).casefold() in _IDENTITY_KEYS and child is not None and child != "":
                    literals.add(str(child))
                visit(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                visit(child)

    visit(value)
    return sorted(literals, key=len, reverse=True)


def _scrub(value: Any, literals: list[str]) -> Any:
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            normalized = str(key).casefold()
            if normalized in _IDENTITY_KEYS:
                cleaned[key] = MASKED
            elif normalized in _FILENAME_KEYS:
                cleaned[key] = "De-identified source image"
            else:
                cleaned[key] = _scrub(child, literals)
        return cleaned
    if isinstance(value, list):
        return [_scrub(item, literals) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub(item, literals) for item in value)
    if isinstance(value, str):
        cleaned = value
        for literal in literals:
            if len(literal.strip()) >= 2:
                cleaned = cleaned.replace(literal, MASKED)
        return cleaned
    return value


def owner_catalog(entry: dict[str, Any]) -> dict[str, Any]:
    """Return an OWNER-safe catalog entry while retaining clinical indexing."""
    cleaned = deepcopy(entry)
    cleaned["patient"] = dict(cleaned.get("patient") or {})
    cleaned["patient"]["name"] = MASKED
    cleaned["patient"]["id"] = MASKED
    cleaned["owner_deidentified"] = True
    return cleaned


def owner_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    """Remove direct identity and filename evidence from an archived snapshot."""
    cleaned = _scrub(deepcopy(assessment), _identity_literals(assessment))
    patient = cleaned.setdefault("patient", {})
    patient["name"] = MASKED
    patient["id"] = MASKED
    cleaned["owner_deidentified"] = True
    return cleaned
