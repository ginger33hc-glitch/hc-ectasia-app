"""Targeted second-pass transcription for small Pentacam numeric panels.

This module is an extraction-only adapter.  It never changes clinical policy,
calculates a missing Pentacam index, or overwrites a value from the general
extractor.  When a Pentacam image contains still-missing labeled values, the
adapter submits the original plus four overlapping crops and, for missing age,
one focused header crop to a structured reread. It accepts only high-confidence
label/value pairs.
"""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import json
import os
import re
from typing import Any, Callable

from PIL import Image, ImageOps
from nice_policy import POSTERIOR_PUPIL_EXTRACTION_RULE, posterior_candidate_is_acceptable
from pentacam_field_registry import TARGET_FIELDS
from pentacam_source_regions import record_unreadable_region

PENTACAM_SCREEN_FAMILIES = {
    "BAD_DISPLAY",
    "FOUR_MAPS_REFRACTIVE",
    "TOPOMETRIC_KC",
    "PACHYMETRY",
    "OTHER_PENTACAM",
}

SOURCE_TILES = (
    "ORIGINAL", "TOP_HEADER", "UPPER_LEFT", "UPPER_RIGHT", "LOWER_LEFT", "LOWER_RIGHT"
)
MAX_SOURCE_PIXELS = 60_000_000

REREAD_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "screen_family": {
            "type": "string",
            "enum": sorted(PENTACAM_SCREEN_FAMILIES | {"NOT_PENTACAM", "UNCERTAIN"}),
        },
        "readings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
                    "field": {"type": "string", "enum": list(TARGET_FIELDS)},
                    "value": {"type": ["number", "null"]},
                    "status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"],
                    },
                    "printed_label": {"type": ["string", "null"]},
                    "group_label": {"type": ["string", "null"]},
                    "source_tile": {"type": "string", "enum": list(SOURCE_TILES)},
                    "source_box": {
                        "anyOf": [
                            {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0, "maximum": 999},
                                "minItems": 4,
                                "maxItems": 4,
                            },
                            {"type": "null"},
                        ]
                    },
                },
                "required": [
                    "eye", "field", "value", "status", "printed_label", "group_label",
                    "source_tile", "source_box",
                ],
            },
        },
        "patient_age_reading": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "value": {"type": ["integer", "null"]},
                "status": {
                    "type": "string",
                    "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"],
                },
                "printed_label": {"type": ["string", "null"]},
                "source_tile": {"type": "string", "enum": list(SOURCE_TILES)},
                "source_box": {
                    "anyOf": [
                        {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0, "maximum": 999},
                            "minItems": 4,
                            "maxItems": 4,
                        },
                        {"type": "null"},
                    ]
                },
            },
            "required": ["value", "status", "printed_label", "source_tile", "source_box"],
        },
        "pentacam_qs_reading": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "value": {"type": ["string", "null"], "enum": ["OK", "NOT_OK", None]},
                "status": {
                    "type": "string",
                    "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"],
                },
                "printed_label": {"type": ["string", "null"]},
                "source_tile": {"type": "string", "enum": list(SOURCE_TILES)},
                "source_box": {
                    "anyOf": [
                        {
                            "type": "array",
                            "items": {"type": "integer", "minimum": 0, "maximum": 999},
                            "minItems": 4,
                            "maxItems": 4,
                        },
                        {"type": "null"},
                    ]
                },
            },
            "required": ["value", "status", "printed_label", "source_tile", "source_box"],
        },
        "posterior_pupil_readings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
                    "value": {"type": ["number", "null"]},
                    "status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"],
                    },
                    "map_title": {"type": ["string", "null"]},
                    "map_location": {
                        "type": "string", "enum": ["LOWER_RIGHT", "OTHER", "UNREADABLE"]
                    },
                    "posterior_reference": {
                        "type": "string", "enum": ["BFS_FLOAT", "BFTE", "OTHER", "UNREADABLE"]
                    },
                    "bfs_diameter_mm": {"type": ["number", "null"]},
                    "pupil_boundary_visible": {"type": "boolean"},
                    "maximum_rule_applied": {"type": "boolean"},
                    "evidence": {"type": "string"},
                    "source_tile": {"type": "string", "enum": list(SOURCE_TILES)},
                    "source_box": {
                        "anyOf": [
                            {
                                "type": "array",
                                "items": {"type": "integer", "minimum": 0, "maximum": 999},
                                "minItems": 4,
                                "maxItems": 4,
                            },
                            {"type": "null"},
                        ]
                    },
                },
                "required": [
                    "eye", "value", "status", "map_title", "map_location",
                    "posterior_reference", "bfs_diameter_mm", "pupil_boundary_visible",
                    "maximum_rule_applied", "evidence", "source_tile", "source_box",
                ],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "screen_family", "readings", "patient_age_reading", "pentacam_qs_reading",
        "posterior_pupil_readings", "warnings",
    ],
}

REREAD_PROMPT = """You are ONLY a targeted Pentacam labeled-numeric-field transcriber.
The first image is the complete original screen. The remaining images are overlapping crops from
that exact same screen, supplied only to make small printed text easier to read.

Read only the requested fields listed below. Return a reading only when the field's own printed
label and its attached numeric value are both visible. Preserve decimal point, sign, and eye
laterality exactly. Use CONFIDENT only when label, digits, sign, and OD/OS are unambiguous. If two
tiles appear to disagree, return one UNCERTAIN reading with value=null rather than choosing.

Never calculate or reconstruct a missing value. In particular, do not calculate ARTmax from
pachymetry/PPImax, do not back-calculate PPImax from ARTmax, and do not derive BAD components,
topometric indices, K values, axes, HWTW, elevation, or pachymetry from colors or neighboring
numbers. Except for the dedicated posterior_pupil_max_um instruction below, a map spot or color
scale is not a labeled table value. Cornea Diameter/W2W is acceptable
for corneal_diameter_mm only when it is the Pentacam horizontal white-to-white output. I_S is only
the printed IS or I-S field, not ISV, IVA, IHD, IHA, or KISA.

PENTACAM LANDMARK LABELS:
- Kmax_D is only the value in its explicitly printed KMax/Kmax row.
- ARTmax_um is only the value in its explicitly printed ARTmax row beneath Progression Index.
- pachy_thinnest_um is the pachymetry number identified by the CIRCULAR marker beside the printed
  "Thinnest Locat." label. Do not return Pachy Vertex N., Pupil Center, a corneal-thickness-map
  number, or the adjacent X/Y location coordinates as thinnest pachymetry.
- central_pachy_um is the pachymetry number identified as "Pupil Center" by the PLUS-SHAPED (+)
  marker beside it. Pachy Vertex N., the circle-marked Thinnest Locat. value, and map numbers are
  not central_pachy_um.
- corneal_diameter_mm is only the explicitly printed HWTW/horizontal white-to-white value.

The printed_label response must contain the visible row/field label associated with the value. If
that label is only Min, Avg/Ave, Max, X, or Y beneath a shared heading, copy the visible shared
heading into group_label; otherwise use group_label=null. source_tile must identify the clearest
image containing the heading/label and digits. When the requested label is visible, source_box must
tightly enclose that label and its attached value area within source_tile, using
[x_min,y_min,x_max,y_max] coordinates normalized to 0..999 from the tile's top-left corner. This
applies even when the digits are unreadable. Use source_box=null only when the field is not shown or
cannot be localized. Do not include unrequested fields. Do not make any clinical interpretation or
recommendation.

PATIENT-LEVEL AGE RULE:
{age_target}
Age belongs to the patient, never to OD or OS. When requested, transcribe it exactly once only from
an explicitly printed Age/Patient Age field in the Pentacam demographic header. Accept a value only
when the age label and completed-year integer are both visible. Do not use date of birth, birth year,
exam date, another unlabeled number, or arithmetic. Never estimate or calculate age. If the printed
age label or digits are unclear, return value=null with the appropriate status.

PENTACAM QUALITY SPECIFICATION (QS) RULE:
{qs_target}
When requested, inspect the literal device field labeled QS/Quality Specification. Return OK only
when the printed label and an explicitly acceptable/OK value are both unambiguous. Return NOT_OK
for a visibly non-OK device status. Never infer QS from apparent image clarity or from another
quality label. When the QS label is visible but its value is unclear, return value=null and localize
the label/value box so it can be shown to the surgeon.

REQUESTED FIELDS BY EYE:
{targets}

DEDICATED NICE POSTERIOR MAP TARGETS:
{posterior_targets}
{posterior_rule}
Only perform this map reading for the requested eyes. Confirm the map title, lower-right location,
BFS/Float reference, Dia 8.00 mm and visible central dashed boundary independently. Compare all
printed signed measurement labels whose points are inside that boundary; do not stop at the first
positive number. Set maximum_rule_applied=true only after comparing the complete bounded field.
source_tile must be LOWER_RIGHT. source_box must enclose the dashed assessment field and its printed
measurements so an unreadable result can be shown beside the surgeon correction input. If any
required landmark, sign or digit is ambiguous, return value=null and UNREADABLE/UNCERTAIN. Return
an empty posterior_pupil_readings array when no posterior target is requested or the map is absent.
"""


def _enabled() -> bool:
    return os.getenv("CERAI_TARGETED_REREAD_ENABLED", "1").strip() == "1"


def _looks_like_pentacam(result: dict[str, Any]) -> bool:
    context = result.get("document_context") or {}
    if context.get("document_type") == "PENTACAM_TOPOGRAPHY":
        return True
    for eye in result.get("eyes") or []:
        for screen_type in eye.get("screen_types") or []:
            text = str(screen_type).upper()
            if any(token in text for token in ("PENTACAM", "BELIN", "AMBROSIO", "4 MAP", "TOPO/KC")):
                return True
    return False


def missing_targets_by_eye(result: dict[str, Any]) -> dict[str, list[str]]:
    """Return only still-empty table fields for explicitly identified OD/OS eyes."""
    if not _looks_like_pentacam(result):
        return {}
    targets: dict[str, list[str]] = {}
    for eye in result.get("eyes") or []:
        eye_id = eye.get("eye")
        if eye_id not in {"OD", "OS"}:
            continue
        central_present = any(
            reading.get("eye") == eye_id
            and reading.get("central_status") == "CONFIDENT"
            and reading.get("central_landmark") == "PUPIL_CENTER_PLUS"
            and reading.get("central_pachy_um") is not None
            for reading in result.get("nice_readings") or []
            if isinstance(reading, dict)
        )
        missing = [
            field for field in TARGET_FIELDS
            if not (field == "central_pachy_um" and central_present)
            and eye.get(field) is None
        ]
        if missing:
            targets[eye_id] = missing
    return targets


def patient_age_is_missing(result: dict[str, Any]) -> bool:
    """True only for a Pentacam source whose patient-level printed age remains empty."""
    if not _looks_like_pentacam(result):
        return False
    context = result.get("document_context") or {}
    return context.get("patient_age_years") is None


def pentacam_qs_is_missing(result: dict[str, Any]) -> bool:
    """True only when literal Pentacam QS has not already been read as OK/NOT_OK."""
    if not _looks_like_pentacam(result):
        return False
    context = result.get("document_context") or {}
    return context.get("pentacam_qs") not in {"OK", "NOT_OK"}


def missing_posterior_targets(result: dict[str, Any]) -> list[str]:
    """Return eyes still lacking a canonically acceptable NICE posterior-map reading."""
    if not _looks_like_pentacam(result):
        return []
    targets = []
    for eye in result.get("eyes") or []:
        eye_id = eye.get("eye")
        if eye_id not in {"OD", "OS"}:
            continue
        present = any(
            reading.get("eye") == eye_id and posterior_candidate_is_acceptable(reading)
            for reading in result.get("nice_readings") or []
            if isinstance(reading, dict)
        )
        if not present:
            targets.append(eye_id)
    return targets


def build_overlapping_tiles(raw: bytes, *, include_top_header: bool = False) -> list[tuple[str, bytes]]:
    """Decode safely and return overlapping PNG regions without altering the source."""
    with Image.open(BytesIO(raw)) as opened:
        width, height = opened.size
        if width <= 0 or height <= 0 or width * height > MAX_SOURCE_PIXELS:
            raise ValueError("image dimensions are outside the targeted-reread safety limit")
        image = ImageOps.exif_transpose(opened)
        image.load()
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")

    width, height = image.size
    left_end = max(1, round(width * 0.58))
    right_start = min(width - 1, round(width * 0.42))
    top_end = max(1, round(height * 0.58))
    bottom_start = min(height - 1, round(height * 0.42))
    boxes = [
        ("UPPER_LEFT", (0, 0, left_end, top_end)),
        ("UPPER_RIGHT", (right_start, 0, width, top_end)),
        ("LOWER_LEFT", (0, bottom_start, left_end, height)),
        ("LOWER_RIGHT", (right_start, bottom_start, width, height)),
    ]
    if include_top_header:
        boxes.insert(0, ("TOP_HEADER", (0, 0, width, max(1, round(height * 0.36)))))
    tiles = []
    for name, box in boxes:
        crop = image.crop(box)
        output = BytesIO()
        crop.save(output, format="PNG", optimize=True)
        tiles.append((name, output.getvalue()))
    return tiles


def render_source_region(raw: bytes, tile_name: str, source_box: Any = None) -> bytes:
    """Return a temporary display crop for one unresolved labeled field."""
    if tile_name not in SOURCE_TILES:
        raise ValueError("unknown Pentacam source tile")
    with Image.open(BytesIO(raw)) as opened:
        width, height = opened.size
        if width <= 0 or height <= 0 or width * height > MAX_SOURCE_PIXELS:
            raise ValueError("image dimensions are outside the source-region safety limit")
        image = ImageOps.exif_transpose(opened)
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
    width, height = image.size
    boxes = {
        "ORIGINAL": (0, 0, width, height),
        "TOP_HEADER": (0, 0, width, max(1, round(height * 0.36))),
        "UPPER_LEFT": (0, 0, max(1, round(width * 0.58)), max(1, round(height * 0.58))),
        "UPPER_RIGHT": (min(width - 1, round(width * 0.42)), 0, width, max(1, round(height * 0.58))),
        "LOWER_LEFT": (0, min(height - 1, round(height * 0.42)), max(1, round(width * 0.58)), height),
        "LOWER_RIGHT": (min(width - 1, round(width * 0.42)), min(height - 1, round(height * 0.42)), width, height),
    }
    tile = image.crop(boxes[tile_name])
    if isinstance(source_box, (list, tuple)) and len(source_box) == 4:
        try:
            x1, y1, x2, y2 = (int(value) for value in source_box)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid normalized source box") from exc
        if not (0 <= x1 < x2 <= 999 and 0 <= y1 < y2 <= 999):
            raise ValueError("invalid normalized source box")
        tile_width, tile_height = tile.size
        left = round(tile_width * x1 / 999)
        top = round(tile_height * y1 / 999)
        right = max(left + 1, round(tile_width * x2 / 999))
        bottom = max(top + 1, round(tile_height * y2 / 999))
        pad_x = max(12, round((right - left) * 0.18))
        pad_y = max(8, round((bottom - top) * 0.35))
        tile = tile.crop((
            max(0, left - pad_x), max(0, top - pad_y),
            min(tile_width, right + pad_x), min(tile_height, bottom + pad_y),
        ))
    output = BytesIO()
    tile.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _normalize_label(value: Any) -> str:
    text = str(value or "").casefold()
    text = text.replace("ı", "i")
    return re.sub(r"[^a-z0-9]+", "", text)


def label_supports_field(field: str, printed_label: Any, group_label: Any = None) -> bool:
    """Reject neighboring-number assignments before they enter the clinical audit."""
    raw_label = str(printed_label or "")
    label = _normalize_label(raw_label)
    group = _normalize_label(group_label)
    if not label:
        return False
    if field in {"K1_axis_deg", "K2_axis_deg"}:
        row = "k1" if field.startswith("K1") else "k2"
        return label.startswith(row) and ("axis" in label or "ax" in label or "@" in raw_label)
    if field in {"PPI_min", "PPI_avg", "PPI_max"}:
        suffixes = {
            "PPI_min": {"min", "minimum"},
            "PPI_avg": {"avg", "ave", "average"},
            "PPI_max": {"max", "maximum"},
        }
        combined_labels = {
            "PPI_min": ("ppimin", "progressionindexmin", "pachymetricprogressionmin"),
            "PPI_avg": ("ppiavg", "ppiave", "ppiaverage", "progressionindexavg", "progressionindexaverage"),
            "PPI_max": ("ppimax", "progressionindexmax", "pachymetricprogressionmax"),
        }
        if any(token in label for token in combined_labels[field]):
            return True
        progression_group = any(token in group for token in ("ppi", "progressionindex", "pachymetricprogression"))
        return progression_group and label in suffixes[field]
    exact = {
        "BAD_D": {"d", "finald", "dfinal", "badd", "finalbadd"},
        "Df": {"df", "baddf"}, "Db": {"db", "baddb"},
        "Dp": {"dp", "baddp"}, "Dt": {"dt", "baddt"}, "Da": {"da", "badda"},
        "ISV": {"isv"}, "IVA": {"iva"}, "KI": {"ki"}, "CKI": {"cki"},
        "IHD": {"ihd"}, "I_S": {"is", "isindex"}, "KISA": {"kisa", "kisaindex"},
        "IHA": {"iha"}, "K1_D": {"k1", "k1d"},
        "K2_D": {"k2", "k2d"},
        "Kmax_D": {"kmax", "kmaxd"}, "Kmean_D": {"kmean", "kmeand"},
        "Rmin_mm": {"rmin", "rminmm"},
    }
    if field in exact:
        return label in exact[field]
    requirements = {
        "corneal_diameter_mm": (("hwtw", "horizontalwhitetowhite", "horizontalwtw", "corneadiameter", "w2w"),),
        "pachy_thinnest_um": (("thinnestlocat", "thinnestlocation"),),
        "central_pachy_um": (("pupilcenter",),),
        "ARTmax_um": (("artmax", "ambrosiorelationalthicknessmax"),),
        "anterior_elevation_thinnest_um": (("anteriorelevation", "frontelevation"), ("thin", "thinnest")),
        "posterior_elevation_thinnest_um": (("posteriorelevation", "backelevation"), ("thin", "thinnest")),
        "thinnest_x_mm": (("thinnestx", "thinlocationx", "pachythinx"),),
        "thinnest_y_mm": (("thinnesty", "thinlocationy", "pachythiny"),),
        "corneal_volume_mm3": (("cornealvolume", "corneavolume"),),
        "RMS_HOA_um": (("rmshoa", "higherorderaberrationrms", "hoarms"),),
        "vertical_coma_um": (("verticalcoma", "comavertical"),),
        "total_RMS_um": (("totalrms", "rmstotal"),),
        "spherical_aberration_um": (("sphericalaberration",),),
    }
    groups = requirements.get(field)
    return bool(groups) and all(any(token in label for token in alternatives) for alternatives in groups)


def label_supports_patient_age(printed_label: Any) -> bool:
    label = _normalize_label(printed_label)
    return label in {
        "age", "agey", "ageyr", "ageyrs", "ageyear", "ageyears", "patientage", "alter"
    }


def _same_number(values: list[float]) -> bool:
    return max(values) - min(values) <= 1e-9


def apply_targeted_readings(
    core: Any,
    result: dict[str, Any],
    reread: dict[str, Any],
    requested: dict[str, list[str]],
    filename: str,
    patient_age_requested: bool = False,
    posterior_requested: list[str] | None = None,
    pentacam_qs_requested: bool = False,
) -> dict[str, Any]:
    """Fill only null requested fields from one conflict-free confident reread."""
    if reread.get("screen_family") not in PENTACAM_SCREEN_FAMILIES:
        return result
    eyes = {eye.get("eye"): eye for eye in result.get("eyes") or [] if eye.get("eye") in {"OD", "OS"}}
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for reading in reread.get("readings") or []:
        if not isinstance(reading, dict):
            continue
        eye_id, field = reading.get("eye"), reading.get("field")
        if eye_id not in requested or field not in requested.get(eye_id, []):
            continue
        if not label_supports_field(field, reading.get("printed_label"), reading.get("group_label")):
            if reading.get("status") == "CONFIDENT" and core.is_number(reading.get("value")):
                result.setdefault("global_warnings", []).append(
                    f"Targeted Pentacam reread rejected {eye_id} {field} in {filename}: "
                    "the returned printed label did not identify that field unambiguously."
                )
            continue
        if reading.get("status") != "CONFIDENT" or not core.is_number(reading.get("value")):
            if reading.get("status") in {"UNCERTAIN", "UNREADABLE"}:
                eye = eyes.get(eye_id)
                if eye is not None:
                    record_unreadable_region(
                        eye, field, filename=filename,
                        tile=reading.get("source_tile"),
                        source_box=reading.get("source_box"),
                        printed_label=reading.get("printed_label"),
                    )
            continue
        candidates[(eye_id, field)].append(reading)

    for (eye_id, field), readings in candidates.items():
        eye = eyes.get(eye_id)
        if eye is None or (field != "central_pachy_um" and eye.get(field) is not None):
            continue
        values = [float(item["value"]) for item in readings]
        if not _same_number(values):
            result.setdefault("global_warnings", []).append(
                f"Targeted Pentacam reread conflict for {eye_id} {field} in {filename}; "
                "no reread value was used."
            )
            continue
        retained = values[0]
        if field == "central_pachy_um":
            result.setdefault("nice_readings", []).append({
                "eye": eye_id,
                "central_pachy_um": retained,
                "central_status": "CONFIDENT",
                "central_landmark": "PUPIL_CENTER_PLUS",
                "posterior_pupil_max_um": None,
                "posterior_status": "NOT_SHOWN",
                "posterior_reference": "UNREADABLE",
                "bfs_diameter_mm": None,
                "pupil_boundary_visible": False,
                "evidence": (
                    f"Targeted Pupil Center plus-marker reread: {readings[0].get('printed_label')}"
                ),
            })
        else:
            eye[field] = retained
            verified = set(eye.get("table_verified_numeric_fields") or [])
            verified.add(field)
            eye["table_verified_numeric_fields"] = sorted(verified)
        eye["missing_or_unreadable"] = [
            item for item in eye.get("missing_or_unreadable") or [] if item != field
        ]
        eye.get("unreadable_source_regions", {}).pop(field, None)
        evidence = eye.setdefault("targeted_reread_evidence", {}).setdefault(field, [])
        best = readings[0]
        evidence.append({
            "file": filename,
            "source": "TARGETED_LABELED_TILE_REREAD",
            "tile": best.get("source_tile"),
            "printed_label": best.get("printed_label"),
            "group_label": best.get("group_label"),
            "value": retained,
        })

    posterior_requested = posterior_requested or []
    posterior_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reading in reread.get("posterior_pupil_readings") or []:
        if not isinstance(reading, dict) or reading.get("eye") not in posterior_requested:
            continue
        eye_id = reading["eye"]
        localized = (
            reading.get("source_tile") == "LOWER_RIGHT"
            and reading.get("source_box") is not None
        )
        valid = (
            reread.get("screen_family") == "FOUR_MAPS_REFRACTIVE"
            and reading.get("status") == "CONFIDENT"
            and core.is_number(reading.get("value"))
            and 0 < float(reading["value"]) <= 300
            and _normalize_label(reading.get("map_title")) == "elevationback"
            and reading.get("map_location") == "LOWER_RIGHT"
            and reading.get("posterior_reference") == "BFS_FLOAT"
            and reading.get("bfs_diameter_mm") == 8
            and reading.get("pupil_boundary_visible") is True
            and reading.get("maximum_rule_applied") is True
            and reading.get("source_tile") == "LOWER_RIGHT"
        )
        if valid:
            posterior_candidates[eye_id].append(reading)
            continue
        if localized and reading.get("status") in {"CONFIDENT", "UNCERTAIN", "UNREADABLE"}:
            eye = eyes.get(eye_id)
            if eye is not None:
                record_unreadable_region(
                    eye, "posterior_pupil_max_um", filename=filename,
                    tile="LOWER_RIGHT", source_box=reading.get("source_box"),
                    printed_label=reading.get("map_title") or "Elevation (Back)",
                )
        if reading.get("status") == "CONFIDENT" and reading.get("value") is not None:
            result.setdefault("global_warnings", []).append(
                f"Targeted NICE posterior reread rejected {eye_id} in {filename}: "
                "the lower-right Elevation (Back), dashed boundary, BFS Float Dia 8.00, "
                "or complete maximum rule was not verified."
            )

    for eye_id, readings in posterior_candidates.items():
        values = [float(reading["value"]) for reading in readings]
        if not _same_number(values):
            result.setdefault("global_warnings", []).append(
                f"Targeted NICE posterior reread conflict for {eye_id} in {filename}; "
                "no posterior_pupil_max_um value was used."
            )
            continue
        best = readings[0]
        retained = values[0]
        result.setdefault("nice_readings", []).append({
            "eye": eye_id,
            "central_pachy_um": None,
            "central_status": "NOT_SHOWN",
            "central_landmark": "UNREADABLE",
            "posterior_pupil_max_um": retained,
            "posterior_status": "CONFIDENT",
            "posterior_reference": "BFS_FLOAT",
            "bfs_diameter_mm": 8,
            "pupil_boundary_visible": True,
            "evidence": (
                "Targeted lower-right Elevation (Back) reread: highest positive printed "
                f"value inside the central dashed boundary = {retained:g} µm. "
                f"{best.get('evidence') or ''}"
            ).strip(),
        })
        eye = eyes.get(eye_id)
        if eye is not None:
            eye.setdefault("targeted_reread_evidence", {}).setdefault(
                "posterior_pupil_max_um", []
            ).append({
                "file": filename,
                "source": "TARGETED_NICE_POSTERIOR_MAP_REREAD",
                "tile": "LOWER_RIGHT",
                "printed_label": best.get("map_title"),
                "group_label": "central dashed pupil boundary",
                "value": retained,
            })
            eye.get("unreadable_source_regions", {}).pop("posterior_pupil_max_um", None)

    if patient_age_requested:
        context = result.setdefault("document_context", {})
        age_reading = reread.get("patient_age_reading") or {}
        value = age_reading.get("value")
        valid_value = (
            core.is_number(value)
            and int(value) == value
            and 18 <= int(value) <= 120
        )
        if (
            context.get("patient_age_years") is None
            and age_reading.get("status") == "CONFIDENT"
            and valid_value
            and label_supports_patient_age(age_reading.get("printed_label"))
        ):
            context["patient_age_years"] = int(value)
            context["targeted_age_reread_evidence"] = {
                "file": filename,
                "source": "TARGETED_PENTACAM_DEMOGRAPHIC_REREAD",
                "tile": age_reading.get("source_tile"),
                "printed_label": age_reading.get("printed_label"),
                "value": int(value),
            }
            context["missing_or_unreadable"] = [
                item for item in context.get("missing_or_unreadable") or []
                if _normalize_label(item) not in {"age", "patientage", "patientageyears"}
            ]
        elif age_reading.get("status") == "CONFIDENT" and value is not None:
            result.setdefault("global_warnings", []).append(
                f"Targeted Pentacam age reread rejected in {filename}: "
                "the printed age label or adult completed-year value was not unambiguous."
            )
        elif (
            age_reading.get("status") in {"UNCERTAIN", "UNREADABLE"}
            and label_supports_patient_age(age_reading.get("printed_label"))
        ):
            context["targeted_unreadable_age_region"] = {
                "file": filename,
                "tile": age_reading.get("source_tile"),
                "source_box": age_reading.get("source_box"),
                "printed_label": age_reading.get("printed_label"),
            }
    if pentacam_qs_requested:
        context = result.setdefault("document_context", {})
        qs_reading = reread.get("pentacam_qs_reading") or {}
        label = _normalize_label(qs_reading.get("printed_label"))
        value = qs_reading.get("value")
        label_valid = label in {"qs", "qualityspecification", "qualityspec", "qualitystatus"}
        if qs_reading.get("status") == "CONFIDENT" and value in {"OK", "NOT_OK"} and label_valid:
            context["pentacam_qs"] = value
            context["targeted_qs_reread_evidence"] = {
                "file": filename,
                "source": "TARGETED_PENTACAM_QS_REREAD",
                "tile": qs_reading.get("source_tile"),
                "printed_label": qs_reading.get("printed_label"),
                "value": value,
            }
            for eye in eyes.values():
                eye["_pentacam_qs"] = value
                eye["pentacam_qs"] = value
                eye.get("unreadable_source_regions", {}).pop("pentacam_qs", None)
        elif (
            qs_reading.get("status") in {"UNCERTAIN", "UNREADABLE"}
            and label_valid
            and qs_reading.get("source_box") is not None
        ):
            for eye in eyes.values():
                record_unreadable_region(
                    eye, "pentacam_qs", filename=filename,
                    tile=qs_reading.get("source_tile"),
                    source_box=qs_reading.get("source_box"),
                    printed_label=qs_reading.get("printed_label"),
                )
    return result


def _target_summary(requested: dict[str, list[str]]) -> str:
    return "\n".join(f"{eye}: {', '.join(fields)}" for eye, fields in sorted(requested.items()))


def targeted_reread(
    core: Any,
    raw: bytes,
    filename: str,
    requested: dict[str, list[str]],
    patient_age_requested: bool = False,
    posterior_requested: list[str] | None = None,
    pentacam_qs_requested: bool = False,
) -> dict[str, Any]:
    age_target = (
        "PATIENT: patient_age_years is requested."
        if patient_age_requested
        else "PATIENT: patient_age_years is not requested; return null/NOT_SHOWN."
    )
    qs_target = (
        "Pentacam QS is requested."
        if pentacam_qs_requested
        else "Pentacam QS is not requested; return null/NOT_SHOWN."
    )
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": REREAD_PROMPT.format(
                targets=_target_summary(requested) or "No eye-level numeric fields requested.",
                age_target=age_target,
                qs_target=qs_target,
                posterior_targets=(
                    ", ".join(posterior_requested or [])
                    or "No posterior_pupil_max_um map reading requested."
                ),
                posterior_rule=POSTERIOR_PUPIL_EXTRACTION_RULE,
            ),
        },
        {"type": "input_text", "text": "ORIGINAL complete screen:"},
        {"type": "input_image", "image_url": core.data_url(raw, filename), "detail": "original"},
    ]
    for tile_name, tile_raw in build_overlapping_tiles(
        raw, include_top_header=patient_age_requested or pentacam_qs_requested
    ):
        content.extend((
            {"type": "input_text", "text": f"{tile_name} crop of the same screen:"},
            {"type": "input_image", "image_url": core.data_url(tile_raw, f"{tile_name}.png"), "detail": "original"},
        ))
    response = core.openai_client().responses.create(
        model=core.MODEL,
        store=False,
        reasoning={"effort": "medium"},
        input=[{"role": "user", "content": content}],
        text={
            "verbosity": "high",
            "format": {
                "type": "json_schema",
                "name": "cerai_pentacam_targeted_reread",
                "strict": True,
                "schema": REREAD_SCHEMA,
            },
        },
    )
    if not response.output_text or not response.output_text.strip():
        raise RuntimeError("targeted Pentacam reread returned empty output")
    return json.loads(response.output_text)


def make_targeted_extractor(core: Any, previous: Callable[[bytes, str], dict[str, Any]]):
    def extract_one_image_with_targeted_reread(raw: bytes, filename: str) -> dict[str, Any]:
        result = previous(raw, filename)
        requested = missing_targets_by_eye(result)
        patient_age_requested = patient_age_is_missing(result)
        posterior_requested = missing_posterior_targets(result)
        pentacam_qs_requested = pentacam_qs_is_missing(result)
        if not _enabled() or (
            not requested and not patient_age_requested
            and not posterior_requested and not pentacam_qs_requested
        ):
            return result
        try:
            reread = targeted_reread(
                core, raw, filename, requested, patient_age_requested, posterior_requested,
                pentacam_qs_requested,
            )
            return apply_targeted_readings(
                core, result, reread, requested, filename, patient_age_requested,
                posterior_requested, pentacam_qs_requested,
            )
        except Exception as exc:
            result.setdefault("global_warnings", []).append(
                f"Targeted Pentacam numeric reread failed for {filename}: "
                f"{type(exc).__name__}; original extraction retained."
            )
            return result

    return extract_one_image_with_targeted_reread


_previous_extract_one_image = None
extract_one_image_with_targeted_reread = None


def install(core: Any) -> None:
    global _previous_extract_one_image, extract_one_image_with_targeted_reread
    if getattr(core, "_cerai_targeted_pentacam_reread_installed", False):
        return
    _previous_extract_one_image = core.extract_one_image
    extract_one_image_with_targeted_reread = make_targeted_extractor(core, _previous_extract_one_image)
    core.extract_one_image = extract_one_image_with_targeted_reread
    core._cerai_targeted_pentacam_reread_installed = True
