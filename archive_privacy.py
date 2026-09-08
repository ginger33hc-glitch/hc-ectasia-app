"""Canonical de-identification boundary for OWNER retrospective archive access.

Doctors may retrieve original material only for cases they created. OWNER archive
routes must pass every catalog entry, assessment, report, and source image through
this module and must never return the immutable original artifact.
"""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw


MASKED = "Masked for owner"
OWNER_SOURCE_MEDIA_TYPE = "image/png"

# All accepted clinical screenshots place patient demographics in the header.
# Mask the complete band so layout/language variations cannot leave an identifier.
OWNER_IDENTITY_HEADER_HEIGHT = 0.16

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


def owner_source_image(raw: bytes) -> bytes:
    """Return a PNG derivative with the complete patient-demographics header masked."""
    with Image.open(BytesIO(raw)) as opened:
        opened.verify()
    with Image.open(BytesIO(raw)) as opened:
        image = opened.convert("RGB")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("invalid source-image dimensions")
    mask_height = max(1, round(height * OWNER_IDENTITY_HEADER_HEIGHT))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, mask_height), fill="white")
    draw.text(
        (max(8, width // 100), max(5, mask_height // 3)),
        "CER-AI OWNER VIEW - PATIENT NAME / ID MASKED",
        fill="black",
    )
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
