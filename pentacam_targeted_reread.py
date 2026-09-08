"""Targeted second-pass transcription for Pentacam labeled fields.

This module is an extraction-only adapter. It never changes clinical policy or
calculates a missing Pentacam index. When a Pentacam image contains still-missing labeled values, the
adapter submits the original plus four overlapping crops and, when needed, one
focused header crop to a structured reread. It accepts only high-confidence
label/value pairs. Conflicting authoritative Four Maps examination dates are
reread here but promoted only by the case-level date policy after both eyes agree.
An existing BAD flat-axis value may be replaced only during the explicit
astigmatic-disparity verification pass; its primary value remains in audit evidence.
F.Ele.Th and B.Ele.Th are always verified from their own labeled BAD central-box
cells before either value can enter a clinical score or report.
"""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import json
import os
import re
from typing import Any

from PIL import Image, ImageOps
from exam_date_reconciliation_policy import possible_calendar_dates
from pentacam_canonical_source_lock import (
    CANONICAL_FIELD_SOURCES, SHOW_2_CORNEA_BACK, SHOW_2_CORNEA_FRONT, SHOW_2_INDICES,
    canonical_source_id, source_family,
)
from pentacam_field_registry import (
    CORNEA_FRONT_KERATOMETRY_FIELDS,
    CORNEA_FRONT_KERATOMETRY_SOURCE,
    TARGET_FIELDS,
)
from pentacam_source_regions import record_unreadable_region

PENTACAM_SCREEN_FAMILIES = {
    "BAD_DISPLAY",
    "FOUR_MAPS_REFRACTIVE",
    "TOPOMETRIC_KC",
    "PACHYMETRY",
    "OTHER_PENTACAM",
    "SHOW_2_EXAMS_TOPOMETRIC",
}

BAD_ELEVATION_FIELDS = ("F_Ele_Th_um", "B_Ele_Th_um")
BAD_ELEVATION_MAX_ATTEMPTS = 5

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
        "exam_date_reading": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "value": {"type": ["string", "null"]},
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
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "screen_family", "readings", "patient_age_reading", "pentacam_qs_reading",
        "exam_date_reading", "warnings",
    ],
}

BAD_ELEVATION_CONFIRMATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "readings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS"]},
                    "field": {"type": "string", "enum": list(BAD_ELEVATION_FIELDS)},
                    "visible_field_label": {"type": ["string", "null"]},
                    "label_value_pair_status": {
                        "type": "string",
                        "enum": ["CONFIRMED_LABEL_ADJACENCY", "WRONG_LABEL", "UNREADABLE"],
                    },
                    "observed_value_text": {"type": ["string", "null"]},
                    "value": {"type": ["integer", "null"]},
                    "status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"],
                    },
                },
                "required": [
                    "eye", "field", "visible_field_label", "label_value_pair_status",
                    "observed_value_text", "value", "status",
                ],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["readings", "warnings"],
}

BAD_ELEVATION_CONFIRMATION_PROMPT = """You are a digit-only verification reader for two
Pentacam BAD Display fields. Each requested field is supplied as an UNTRUSTED crop, followed by an
enlarged grayscale copy. Do not trust the crop caption or a prior claim about its identity.

Use this strict order for each field:
1. First find the literal printed definition: F.Ele.Th for front elevation or B.Ele.Th for back elevation.
2. Then read only the numeric box immediately adjacent to that exact definition.

These definitions are in the central results table's ELEVATION ROW IMMEDIATELY ABOVE THE
PROGRESSION INDEX SECTION, below the upper K1/K2/Axis rows. F.Ele.Th means front/anterior
elevation at the thinnest corneal point; B.Ele.Th means back/posterior elevation at the thinnest
corneal point. Both adjacent values are signed
integers in µm. If the crop instead shows K1, K2, Axis, or another definition, return WRONG_LABEL
with value=null. A plausible number without the requested definition beside it is never acceptable.

Read only the integer printed inside that field's value cell:
- F_Ele_Th_um: the integer immediately attached to the printed F.Ele.Th label.
- B_Ele_Th_um: the integer immediately attached to the printed B.Ele.Th label.

Ignore all prior OCR values. Do not read a neighboring row, map number, label character, unit, box
edge, or separator. In particular, the thin vertical edge of the white value cell is a BORDER, not
the digit 1; never prepend it to the printed number. Preserve a visible minus or plus sign. Put the
exact characters you can see in observed_value_text, then return the same integer in value. Use
CONFIDENT only when the label, sign, and every digit are unambiguous in both crop versions. Do not
calculate, infer, or clinically interpret the value.

REQUESTED CROPS:
{targets}
"""

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
numbers. A map spot or color scale is not a labeled table value. Cornea Diameter/W2W is acceptable
for corneal_diameter_mm only when it is the Pentacam horizontal white-to-white output. I_S is only
the printed IS or I-S field, not ISV, IVA, IHD, IHA, or KISA.

PENTACAM LANDMARK LABELS:
- K1_D, K1_axis_deg, K2_D, K2_axis_deg, and Kmean_D are accepted only when the complete original
  visibly says "Show 2 Exams Topometric" and the value is inside the corresponding eye's upper
  parameter panel visibly headed "Cornea Front". For these readings, screen_family must be
  SHOW_2_EXAMS_TOPOMETRIC and group_label must be "Cornea Front". Kmean_D is the printed Km row,
  never a calculation. Reject every similarly named value from Cornea Back, True Net Power, Total
  Corneal Refractive Power, another screen/panel, a map, or Kmax.
- Kmax_D is only the value in its explicitly printed KMax/Kmax row.
- ARTmax_um is only the value in its explicitly printed ARTmax row beneath Progression Index.
- pachy_thinnest_um is the pachymetry number identified by the CIRCULAR marker beside the printed
  "Thinnest Locat." label. Do not return Pachy Vertex N., Pupil Center, a corneal-thickness-map
  number, or the adjacent X/Y location coordinates as thinnest pachymetry.
- central_pachy_um is the pachymetry number identified as "Pupil Center" by the PLUS-SHAPED (+)
  marker beside it. Pachy Vertex N., the circle-marked Thinnest Locat. value, and map numbers are
  not central_pachy_um.
- F_Ele_Th_um is only the signed value attached to the explicitly printed "F. Ele.Th" label in
  the BAD Display central results table's elevation row immediately above Progression Index.
  B_Ele_Th_um is only the signed value in the explicitly printed "B. Ele.Th" box in that same row.
  First locate the literal
  F.Ele.Th or B.Ele.Th definition in the central results table's elevation row immediately above
  the Progression Index section and below the upper K1/K2/Axis rows; then localize only that
  definition and its immediately adjacent signed µm value box. F.Ele.Th is front/anterior elevation
  at the thinnest point. B.Ele.Th is back/posterior
  elevation at the thinnest point. A K1/K2/Axis crop is invalid even if its number looks plausible.
  Read each label/value pair independently;
  never swap the front and back values or copy one into the other. Never use an Elevation (Back) map
  or Elevation (Front) map, pupil boundary, BFS/Float or BFTE value, another elevation field, neighboring
  number, or a calculated value. If either label, sign, or number is unclear, return that field as
  UNCERTAIN or UNREADABLE with value=null.
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

FOUR MAPS EXAMINATION-DATE RULE:
{exam_date_target}
When requested, read only the explicitly labeled examination Date field in the patient/header area
of this Four Maps Refractive page. Transcribe the complete printed date string exactly, including
leading zeroes and separators. Do not use Date of Birth, examination time, image filename, another
page, or arithmetic. Check every digit at original resolution and in the TOP_HEADER crop. Use
CONFIDENT only when the Date label and every printed date digit are unambiguous. This focused result
is case-reconciled with the other Four Maps page; never copy or assume the other eye's date.

REQUESTED FIELDS BY EYE:
{targets}

"""


_REREAD_CANONICAL_SOURCE_LINES = "\n".join(
    f"- {field}: {source_id} -> {label}"
    for field, (source_id, label) in CANONICAL_FIELD_SOURCES.items()
)
REREAD_PROMPT += (
    "\nCANONICAL EXACT-SOURCE REGISTRY:\n"
    "A requested locked field is acceptable only from the exact source below. "
    "Use the visible group heading to distinguish Cornea Front, Cornea Back, and the 8-mm Indices panel.\n"
    + _REREAD_CANONICAL_SOURCE_LINES + "\n"
)


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
        missing = [
            field for field in TARGET_FIELDS
            if not (
                field in CORNEA_FRONT_KERATOMETRY_FIELDS
                and eye.get("keratometry_source") != CORNEA_FRONT_KERATOMETRY_SOURCE
            )
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


def bad_elevation_targets_by_eye(result: dict[str, Any]) -> dict[str, list[str]]:
    """Require focused F/B labeled-cell evidence for every identified BAD page."""
    if not _looks_like_pentacam(result):
        return {}
    targets: dict[str, list[str]] = {}
    for eye in result.get("eyes") or []:
        eye_id = eye.get("eye")
        if eye_id not in {"OD", "OS"}:
            continue
        screen_tokens = {
            _normalize_label(item) for item in eye.get("screen_types") or []
        }
        source_ids = eye.get("canonical_source_ids") or {}
        is_bad_page = any(
            "baddisplay" in token or ("belin" in token and "ambrosio" in token)
            for token in screen_tokens
        ) or any(
            source_ids.get(field) == canonical_source_id(field)
            for field in BAD_ELEVATION_FIELDS
        )
        if is_bad_page:
            targets[eye_id] = list(BAD_ELEVATION_FIELDS)
    return targets


def _prepare_bad_elevation_verification(
    result: dict[str, Any], requested: dict[str, list[str]], filename: str,
) -> dict[tuple[str, str], Any]:
    """Quarantine primary F/B OCR values while retaining them only as audit evidence."""
    originals: dict[tuple[str, str], Any] = {}
    for eye in result.get("eyes") or []:
        eye_id = eye.get("eye")
        fields = requested.get(eye_id, [])
        if not fields:
            continue
        verified = set(eye.get("table_verified_numeric_fields") or [])
        source_ids = eye.setdefault("canonical_source_ids", {})
        missing = list(eye.get("missing_or_unreadable") or [])
        evidence = eye.setdefault("bad_elevation_verification_evidence", {})
        targeted_evidence = eye.setdefault("targeted_reread_evidence", {})
        for field in fields:
            primary_value = eye.get(field)
            originals[(eye_id, field)] = primary_value
            evidence[field] = {
                "file": filename,
                "primary_value": primary_value,
                "verified_value": None,
                "status": "PENDING",
            }
            eye[field] = None
            verified.discard(field)
            source_ids.pop(field, None)
            targeted_evidence.pop(field, None)
            if field not in missing:
                missing.append(field)
        eye["table_verified_numeric_fields"] = sorted(verified)
        eye["missing_or_unreadable"] = missing
    return originals


def _enhance_numeric_crop(raw: bytes) -> bytes:
    """Enlarge a localized value cell without inventing or removing digit strokes."""
    with Image.open(BytesIO(raw)) as opened:
        image = ImageOps.exif_transpose(opened).convert("L")
        scale = max(2, min(6, 1200 // max(1, image.width)))
        image = image.resize(
            (image.width * scale, image.height * scale), Image.Resampling.LANCZOS,
        )
        image = ImageOps.autocontrast(image, cutoff=1)
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def confirm_bad_elevation_crops(
    core: Any,
    crops: dict[tuple[str, str], bytes],
) -> dict[tuple[str, str], int]:
    """Transcribe only already-localized F/B value cells in one independent pass."""
    target_text = "\n".join(f"{eye}: {field}" for eye, field in sorted(crops))
    content: list[dict[str, Any]] = [{
        "type": "input_text",
        "text": BAD_ELEVATION_CONFIRMATION_PROMPT.format(targets=target_text),
    }]
    for (eye_id, field), crop in sorted(crops.items()):
        content.extend((
            {"type": "input_text", "text": f"{eye_id} {field} tight original crop:"},
            {
                "type": "input_image",
                "image_url": core.data_url(crop, f"{eye_id}-{field}.png"),
                "detail": "original",
            },
            {"type": "input_text", "text": f"{eye_id} {field} enlarged grayscale crop:"},
            {
                "type": "input_image",
                "image_url": core.data_url(
                    _enhance_numeric_crop(crop), f"{eye_id}-{field}-enlarged.png",
                ),
                "detail": "original",
            },
        ))
    response = core.openai_client().responses.create(
        model=core.MODEL,
        store=False,
        reasoning={"effort": "medium"},
        input=[{"role": "user", "content": content}],
        text={
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "cerai_bad_elevation_digit_confirmation",
                "strict": True,
                "schema": BAD_ELEVATION_CONFIRMATION_SCHEMA,
            },
        },
    )
    if not response.output_text or not response.output_text.strip():
        raise RuntimeError("BAD elevation digit confirmation returned empty output")
    payload = json.loads(response.output_text)
    candidates: dict[tuple[str, str], list[int]] = defaultdict(list)
    for reading in payload.get("readings") or []:
        key = (reading.get("eye"), reading.get("field"))
        value = reading.get("value")
        observed = str(reading.get("observed_value_text") or "").strip()
        if (
            key in crops
            and reading.get("label_value_pair_status") == "CONFIRMED_LABEL_ADJACENCY"
            and label_supports_field(key[1], reading.get("visible_field_label"))
            and reading.get("status") == "CONFIDENT"
            and isinstance(value, int) and not isinstance(value, bool)
            and re.fullmatch(r"[+-]?\d+", observed)
            and int(observed) == value
        ):
            candidates[key].append(value)
    return {
        key: values[0] for key, values in candidates.items()
        if values and all(value == values[0] for value in values)
    }


def _finish_bad_elevation_verification(
    core: Any,
    result: dict[str, Any],
    requested: dict[str, list[str]],
    originals: dict[tuple[str, str], Any],
    filename: str,
    localized: dict[tuple[str, str], dict[str, Any]],
    confirmation_runs: list[dict[tuple[str, str], int]],
    attempt_counts: dict[tuple[str, str], int] | None = None,
    attempt_errors: dict[tuple[str, str], list[str]] | None = None,
) -> None:
    eyes = {
        eye.get("eye"): eye for eye in result.get("eyes") or []
        if eye.get("eye") in requested
    }
    for key, primary_value in originals.items():
        eye_id, field = key
        eye = eyes[eye_id]
        localized_reading = localized.get(key) or {}
        localized_value = localized_reading.get("value")
        votes = [localized_value] + [run.get(key) for run in confirmation_runs]
        numeric_votes = [int(value) for value in votes if core.is_number(value) and int(value) == value]
        accepted = next(
            (value for value in numeric_votes if numeric_votes.count(value) >= 2), None,
        )
        verified = set(eye.get("table_verified_numeric_fields") or [])
        source_ids = eye.setdefault("canonical_source_ids", {})
        missing = list(eye.get("missing_or_unreadable") or [])
        eye[field] = accepted
        if accepted is not None:
            verified.add(field)
            source_ids[field] = canonical_source_id(field)
            missing = [item for item in missing if item != field]
            eye.get("unreadable_source_regions", {}).pop(field, None)
            eye.setdefault("targeted_reread_evidence", {})[field] = [{
                "file": filename,
                "source": "DEDICATED_BAD_ELEVATION_DIGIT_CONSENSUS",
                "tile": localized_reading.get("source_tile"),
                "printed_label": localized_reading.get("printed_label"),
                "group_label": localized_reading.get("group_label"),
                "value": accepted,
                "confirmation_values": [run.get(key) for run in confirmation_runs],
            }]
            if (
                core.is_number(primary_value)
                and abs(float(primary_value) - float(accepted)) > 1e-9
            ):
                result.setdefault("global_warnings", []).append(
                    f"{eye_id} {field} corrected by dedicated BAD value-cell consensus "
                    f"from {float(primary_value):g} to {accepted:g} µm."
                )
        else:
            verified.discard(field)
            source_ids.pop(field, None)
            if field not in missing:
                missing.append(field)
            result.setdefault("global_warnings", []).append(
                f"{eye_id} {field} remained unresolved after "
                f"{(attempt_counts or {}).get(key, 0)} automated BAD elevation attempts; "
                "surgeon entry is required."
            )
        eye["table_verified_numeric_fields"] = sorted(verified)
        eye["missing_or_unreadable"] = missing
        eye.setdefault("bad_elevation_verification_evidence", {})[field] = {
            "file": filename,
            "primary_value": primary_value,
            "localized_value": localized_value,
            "confirmation_values": [run.get(key) for run in confirmation_runs],
            "automated_attempts": (attempt_counts or {}).get(key, 0),
            "attempt_errors": list((attempt_errors or {}).get(key, [])),
            "verified_value": accepted,
            "status": "VERIFIED" if accepted is not None else "UNRESOLVED",
        }


def verify_bad_elevation_fields(
    core: Any,
    result: dict[str, Any],
    raw: bytes,
    filename: str,
    requested: dict[str, list[str]],
    originals: dict[tuple[str, str], Any],
) -> None:
    """Find each literal F/B definition, then verify only its adjacent value box."""
    localized: dict[tuple[str, str], dict[str, Any]] = {}
    confirmation_runs: list[dict[tuple[str, str], int]] = []
    attempt_counts: dict[tuple[str, str], int] = defaultdict(int)
    attempt_errors: dict[tuple[str, str], list[str]] = defaultdict(list)
    unresolved = {
        (eye_id, field) for eye_id, fields in requested.items() for field in fields
    }
    for _attempt in range(BAD_ELEVATION_MAX_ATTEMPTS):
        if not unresolved:
            break
        active_keys = set(unresolved)
        for key in active_keys:
            attempt_counts[key] += 1
        retry_request: dict[str, list[str]] = defaultdict(list)
        for eye_id, field in active_keys:
            retry_request[eye_id].append(field)
        try:
            reread = targeted_reread(core, raw, filename, dict(retry_request))
        except Exception as exc:
            for key in active_keys:
                attempt_errors[key].append(type(exc).__name__)
            confirmation_runs.append({})
            continue
        candidates: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for reading in reread.get("readings") or []:
            key = (reading.get("eye"), reading.get("field"))
            if (
                key in unresolved
                and reading.get("status") == "CONFIDENT"
                and core.is_number(reading.get("value"))
                and source_supports_field(
                    reread.get("screen_family"), key[1], reading.get("group_label")
                )
                and label_supports_field(
                    key[1], reading.get("printed_label"), reading.get("group_label")
                )
                and reading.get("source_box") is not None
            ):
                candidates[key].append(reading)
        attempt_localized = {
            key: readings[0]
            for key, readings in candidates.items()
            if all(
                abs(float(reading["value"]) - float(readings[0]["value"])) <= 1e-9
                for reading in readings
            )
        }
        attempt_crops = {}
        for key, reading in attempt_localized.items():
            try:
                attempt_crops[key] = render_source_region(
                    raw, reading.get("source_tile"), reading.get("source_box"),
                )
            except Exception as exc:
                attempt_errors[key].append(type(exc).__name__)
        try:
            confirmation = confirm_bad_elevation_crops(core, attempt_crops) if attempt_crops else {}
        except Exception as exc:
            for key in active_keys:
                attempt_errors[key].append(type(exc).__name__)
            confirmation = {}
        confirmation_runs.append(confirmation)
        for key in set(confirmation) & set(attempt_localized):
            localized[key] = attempt_localized[key]
            confirmed_value = confirmation[key]
            independent_values = [
                run.get(key) for run in confirmation_runs if run.get(key) is not None
            ]
            localizer_agrees = confirmed_value == int(attempt_localized[key]["value"])
            independent_consensus = independent_values.count(confirmed_value) >= 2
            if localizer_agrees or independent_consensus:
                unresolved.discard(key)
    _finish_bad_elevation_verification(
        core, result, requested, originals, filename, localized, confirmation_runs,
        attempt_counts, attempt_errors,
    )


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


def source_supports_field(screen_family: Any, field: str, group_label: Any = None) -> bool:
    required_family = source_family(field)
    if required_family is not None and str(screen_family or "") != required_family:
        return False
    source_id = canonical_source_id(field)
    group = _normalize_label(group_label)
    if source_id == SHOW_2_CORNEA_FRONT:
        return group == "corneafront"
    if source_id == SHOW_2_CORNEA_BACK:
        return group == "corneaback"
    if source_id == SHOW_2_INDICES:
        return any(token in group for token in ("indicesin8mmzone", "indices8mm", "indices"))
    return True


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
        "Kmax_D": {"kmax", "kmaxd"}, "Kmean_D": {"km", "kmean", "kmeand"},
        "Rmin_mm": {"rmin", "rminmm"}, "topometric_RMin": {"rmin", "rminmm"},
        "TKC": {"tkc"}, "F_Ele_Th_um": {"feleth", "felethum", "fronteleth"},
        "posterior_Kmean_D": {"km", "kmean", "kmeand"},
        "topographic_astig_D": {"astig", "astigd"},
        "ml7_bad_k1_d": {"k1", "k1d"},
        "ml7_bad_k2_d": {"k2", "k2d"},
        "bad_flat_axis_deg": {"axis"},
        "topographic_steep_axis_deg": {"axis", "axissteep", "steepaxis"},
        "B_Ele_Th_um": {"beleth", "belethum", "backeleth"},
    }
    if field in exact:
        return label in exact[field]
    requirements = {
        "corneal_diameter_mm": (("hwtw", "horizontalwhitetowhite", "horizontalwtw", "corneadiameter", "w2w"),),
        "pachy_thinnest_um": (("thinnestlocat", "thinnestlocation"),),
        "central_pachy_um": (("pupilcenter",),),
        "ARTmax_um": (("artmax", "ambrosiorelationalthicknessmax"),),
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
    pentacam_qs_requested: bool = False,
    exam_date_requested: bool = False,
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
        if not source_supports_field(
            reread.get("screen_family"), field, reading.get("group_label")
        ):
            if reading.get("status") == "CONFIDENT" and core.is_number(reading.get("value")):
                result.setdefault("global_warnings", []).append(
                    f"Targeted Pentacam reread rejected {eye_id} {field} in {filename}: "
                    "the returned screen/panel was not the field's canonical source."
                )
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
        if eye is None or eye.get(field) is not None:
            continue
        values = [float(item["value"]) for item in readings]
        if not _same_number(values):
            result.setdefault("global_warnings", []).append(
                f"Targeted Pentacam reread conflict for {eye_id} {field} in {filename}; "
                "no reread value was used."
            )
            continue
        retained = values[0]
        eye[field] = retained
        if field in CORNEA_FRONT_KERATOMETRY_FIELDS:
            eye["keratometry_source"] = CORNEA_FRONT_KERATOMETRY_SOURCE
        verified = set(eye.get("table_verified_numeric_fields") or [])
        verified.add(field)
        eye["table_verified_numeric_fields"] = sorted(verified)
        source_id = canonical_source_id(field)
        if source_id:
            eye.setdefault("canonical_source_ids", {})[field] = source_id
        eye["missing_or_unreadable"] = [
            item for item in eye.get("missing_or_unreadable") or [] if item != field
        ]
        eye.get("unreadable_source_regions", {}).pop(field, None)
        evidence = eye.setdefault("targeted_reread_evidence", {}).setdefault(field, [])
        best = readings[0]
        evidence_record = {
            "file": filename,
            "source": "TARGETED_LABELED_TILE_REREAD",
            "tile": best.get("source_tile"),
            "printed_label": best.get("printed_label"),
            "group_label": best.get("group_label"),
            "value": retained,
        }
        if best.get("source_box") is not None:
            evidence_record["source_box"] = best.get("source_box")
        evidence.append(evidence_record)

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
    if exam_date_requested:
        context = result.setdefault("document_context", {})
        reading = reread.get("exam_date_reading") or {}
        value = reading.get("value")
        label = _normalize_label(reading.get("printed_label"))
        valid_label = label in {"date", "examdate", "examinationdate"}
        valid_date = isinstance(value, str) and bool(possible_calendar_dates(value))
        valid_source = reread.get("screen_family") == "FOUR_MAPS_REFRACTIVE"
        if (
            reading.get("status") == "CONFIDENT"
            and valid_source and valid_label and valid_date
        ):
            context["targeted_exam_date_reread_evidence"] = {
                "file": filename,
                "source": "TARGETED_FOUR_MAPS_HEADER_REREAD",
                "tile": reading.get("source_tile"),
                "printed_label": reading.get("printed_label"),
                "value": value,
                "promoted": False,
            }
        elif reading.get("status") == "CONFIDENT" and value is not None:
            result.setdefault("global_warnings", []).append(
                f"Targeted Four Maps examination-date reread rejected in {filename}: "
                "the page, printed Date label, or complete date value was not unambiguous."
            )
        elif reading.get("status") in {"UNCERTAIN", "UNREADABLE"} and valid_label:
            context["targeted_unreadable_exam_date_region"] = {
                "file": filename,
                "tile": reading.get("source_tile"),
                "source_box": reading.get("source_box"),
                "printed_label": reading.get("printed_label"),
            }
    return result


def _target_summary(requested: dict[str, list[str]]) -> str:
    return "\n".join(f"{eye}: {', '.join(fields)}" for eye, fields in sorted(requested.items()))


def targeted_reread(
    core: Any,
    raw: bytes,
    filename: str,
    requested: dict[str, list[str]],
    patient_age_requested: bool = False,
    pentacam_qs_requested: bool = False,
    exam_date_requested: bool = False,
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
    exam_date_target = (
        "PATIENT: the Four Maps examination Date is requested."
        if exam_date_requested
        else "PATIENT: the examination Date is not requested; return null/NOT_SHOWN."
    )
    content: list[dict[str, Any]] = [
        {
            "type": "input_text",
            "text": REREAD_PROMPT.format(
                targets=_target_summary(requested) or "No eye-level numeric fields requested.",
                age_target=age_target,
                qs_target=qs_target,
                exam_date_target=exam_date_target,
            ),
        },
        {"type": "input_text", "text": "ORIGINAL complete screen:"},
        {"type": "input_image", "image_url": core.data_url(raw, filename), "detail": "original"},
    ]
    for tile_name, tile_raw in build_overlapping_tiles(
        raw, include_top_header=(
            patient_age_requested or pentacam_qs_requested or exam_date_requested
        )
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



def enrich_extraction(
    core: Any, result: dict[str, Any], raw: bytes, filename: str,
    *, exam_date_requested: bool = False,
) -> dict[str, Any]:
    """Run the targeted second pass explicitly after primary extraction."""
    elevation_requested = bad_elevation_targets_by_eye(result)
    elevation_originals = _prepare_bad_elevation_verification(
        result, elevation_requested, filename,
    )
    requested = missing_targets_by_eye(result)
    for eye_id, fields in list(requested.items()):
        elevation_fields = set(elevation_requested.get(eye_id, []))
        requested[eye_id] = [field for field in fields if field not in elevation_fields]
        if not requested[eye_id]:
            requested.pop(eye_id)
    patient_age_requested = patient_age_is_missing(result)
    pentacam_qs_requested = pentacam_qs_is_missing(result)
    if not _enabled():
        _finish_bad_elevation_verification(
            core, result, elevation_requested, elevation_originals, filename, {}, [],
        )
        return result
    if requested or patient_age_requested or pentacam_qs_requested or exam_date_requested:
        try:
            reread = targeted_reread(
                core, raw, filename, requested, patient_age_requested, pentacam_qs_requested,
                exam_date_requested,
            )
            apply_targeted_readings(
                core, result, reread, requested, filename, patient_age_requested,
                pentacam_qs_requested, exam_date_requested,
            )
        except Exception as exc:
            result.setdefault("global_warnings", []).append(
                f"Targeted Pentacam numeric reread failed for {filename}: "
                f"{type(exc).__name__}; unresolved fields require surgeon entry."
            )
    if elevation_requested:
        try:
            verify_bad_elevation_fields(
                core, result, raw, filename, elevation_requested, elevation_originals,
            )
        except Exception as exc:
            result.setdefault("global_warnings", []).append(
                f"Dedicated BAD elevation verification failed for {filename}: "
                f"{type(exc).__name__}; surgeon entry is required."
            )
            _finish_bad_elevation_verification(
                core, result, elevation_requested, elevation_originals, filename, {}, [],
            )
    return result


def verify_astigmatic_disparity_bad_flat_axes(
    core: Any,
    result: dict[str, Any],
    raw: bytes,
    filename: str,
    eye_ids: set[str],
) -> dict[str, Any]:
    """Focused-reread threshold-level BAD axes before disparity reporting.

    Only the canonical BAD flat-axis field is eligible. If the focused reading
    is not confident and source-valid, the value is left unresolved rather than
    retaining an unverified validation warning. This path cannot affect PS3.
    """
    requested: dict[str, list[str]] = {}
    originals: dict[str, float] = {}
    source_id = canonical_source_id("bad_flat_axis_deg")
    for eye in result.get("eyes") or []:
        eye_id = eye.get("eye")
        if eye_id not in eye_ids or not core.is_number(eye.get("bad_flat_axis_deg")):
            continue
        if (eye.get("canonical_source_ids") or {}).get("bad_flat_axis_deg") != source_id:
            continue
        originals[eye_id] = float(eye["bad_flat_axis_deg"])
        eye["bad_flat_axis_deg"] = None
        missing = list(eye.get("missing_or_unreadable") or [])
        if "bad_flat_axis_deg" not in missing:
            missing.append("bad_flat_axis_deg")
        eye["missing_or_unreadable"] = missing
        requested[eye_id] = ["bad_flat_axis_deg"]
    if not requested:
        return result

    try:
        reread = targeted_reread(core, raw, filename, requested)
        apply_targeted_readings(core, result, reread, requested, filename)
    except Exception as exc:
        result.setdefault("global_warnings", []).append(
            f"Astigmatic-disparity BAD flat-axis verification failed for {filename}: "
            f"{type(exc).__name__}; surgeon confirmation is required."
        )

    eyes = {
        eye.get("eye"): eye for eye in result.get("eyes") or []
        if eye.get("eye") in requested
    }
    for eye_id, primary_value in originals.items():
        eye = eyes[eye_id]
        verified_value = eye.get("bad_flat_axis_deg")
        eye.setdefault("astigmatic_disparity_verification_evidence", {})["bad_flat_axis_deg"] = {
            "file": filename,
            "primary_value": primary_value,
            "verified_value": verified_value,
            "status": "VERIFIED" if core.is_number(verified_value) else "UNRESOLVED",
        }
        if core.is_number(verified_value):
            if abs(float(verified_value) - primary_value) > 1e-9:
                result.setdefault("global_warnings", []).append(
                    f"{eye_id} BAD flat axis corrected by focused canonical-box reread "
                    f"from {primary_value:g}° to {float(verified_value):g}°."
                )
        else:
            result.setdefault("global_warnings", []).append(
                f"{eye_id} BAD flat axis associated with an astigmatic-disparity warning "
                "could not be verified; surgeon confirmation is recommended."
            )
    return result
