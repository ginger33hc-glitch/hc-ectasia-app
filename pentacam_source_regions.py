"""Canonical unread Pentacam/topography source-region policy.

Extraction adapters may record an exact unread label/value box.  Readiness uses
this module to resolve that box—or a source-role-specific map panel—without
duplicating clinical rules or exposing a region from the wrong eye.
"""

from __future__ import annotations

from typing import Any


REQUEST_SOURCE_KEYS = {
    "surgeon_nice_central_um": "central_pachy_um",
    "surgeon_nice_pe_um": "B_Ele_Th_um",
    "surgeon_I_S_D": "I_S",
    "surgeon_topography_category": "erss_topography",
}

# Normalized ORIGINAL-image boxes are intentionally broad enough to contain the
# complete map. Exact extractor-supplied boxes always take precedence.
CANONICAL_MAP_REGIONS = {
    "source_quality": {
        "tile": "ORIGINAL",
        "source_box": None,
        "printed_label": "Complete source image requiring replacement",
    },
    "erss_topography": {
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    },
    "morphology": {
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    },
    "asymmetric_bow_tie": {
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    },
    "srax": {
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    },
    "srax_deg": {
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    },
    "inferior_opposite_steepening_D": {
        "tile": "ORIGINAL",
        "source_box": [300, 60, 700, 560],
        "printed_label": "Axial/Sagittal Curvature (Front) — upper-left map",
    },
    "anterior_pattern": {
        "tile": "ORIGINAL",
        "source_box": [610, 60, 995, 560],
        "printed_label": "Elevation (Front) — upper-right map",
    },
    "posterior_pattern": {
        "tile": "ORIGINAL",
        "source_box": [610, 430, 995, 995],
        "printed_label": "Elevation (Back) — lower-right map",
    },
}


def source_key(request_key: Any) -> str:
    key = str(request_key or "")
    return REQUEST_SOURCE_KEYS.get(key, key)


def record_unreadable_region(
    eye: dict[str, Any],
    key: str,
    *,
    filename: Any,
    tile: Any,
    source_box: Any = None,
    printed_label: Any = None,
) -> None:
    """Record one exact, eye-scoped unread region from an extraction adapter."""
    if not filename or not tile:
        return
    eye.setdefault("unreadable_source_regions", {})[key] = {
        "file": str(filename),
        "tile": str(tile),
        "source_box": source_box,
        "printed_label": printed_label,
    }


def _patient_age_region(extracted: dict[str, Any]) -> dict[str, Any] | None:
    direct = (extracted.get("document_context") or {}).get("targeted_unreadable_age_region")
    if direct:
        return direct
    hints = [
        context.get("targeted_unreadable_age_region")
        for context in extracted.get("document_contexts") or []
        if context.get("targeted_unreadable_age_region")
    ]
    return hints[0] if len(hints) == 1 else None


def _eye(extracted: dict[str, Any], eye_id: str) -> dict[str, Any] | None:
    return next(
        (candidate for candidate in extracted.get("eyes") or [] if candidate.get("eye") == eye_id),
        None,
    )


def _provenance_files(eye: dict[str, Any], key: str) -> list[str]:
    records = (eye.get("field_provenance") or {}).get(key) or []
    files = {
        str(record.get("file"))
        for record in records
        if isinstance(record, dict) and record.get("file")
    }
    return sorted(files)


def _erss_file(eye: dict[str, Any]) -> str | None:
    sources = [
        source for source in eye.get("erss_topography_sources") or []
        if isinstance(source, dict)
        and source.get("file")
        and source.get("map_type") == "AXIAL_SAGITTAL_FRONT"
        and source.get("map_location") == "UPPER_LEFT"
    ]
    dedicated = [source for source in sources if source.get("reader") == "DEDICATED_CURVATURE_PASS"]
    candidates = dedicated or sources
    if not candidates:
        return None
    # Prefer the unresolved/lowest-confidence dedicated read that caused surgeon completion.
    rank = {"UNREADABLE": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}
    selected = min(candidates, key=lambda source: rank.get(source.get("morphology_confidence"), 4))
    return str(selected["file"])


def region_hints(
    extracted: dict[str, Any], eye_id: str, request_key: Any
) -> list[dict[str, Any]]:
    """Resolve exact unread boxes first, then safe same-eye canonical panels."""
    key = source_key(request_key)
    if eye_id == "PATIENT" and key == "age":
        hint = _patient_age_region(extracted)
        return [hint] if hint else []
    eye = _eye(extracted, eye_id)
    if eye is None:
        return []

    exact = (eye.get("unreadable_source_regions") or {}).get(key)
    if exact:
        return [exact]
    # Backward compatibility for snapshots created before the generic region contract.
    legacy = (eye.get("targeted_unreadable_regions") or {}).get(key)
    if legacy:
        return [legacy]

    panel = CANONICAL_MAP_REGIONS.get(key)
    if panel is None:
        return []
    if key == "source_quality":
        filenames = sorted(
            str(filename) for filename, quality in (eye.get("quality_by_source") or {}).items()
            if filename and quality in {"LIMITED", "INADEQUATE"}
        )
    elif key in {
        "erss_topography", "morphology", "asymmetric_bow_tie", "srax",
        "srax_deg", "inferior_opposite_steepening_D",
    }:
        filenames = [_erss_file(eye)]
    else:
        filenames = _provenance_files(eye, key)
    return [{"file": filename, **panel} for filename in filenames if filename]


def region_hint(
    extracted: dict[str, Any], eye_id: str, request_key: Any
) -> dict[str, Any] | None:
    """Backward-compatible single-region accessor."""
    hints = region_hints(extracted, eye_id, request_key)
    return hints[0] if hints else None
