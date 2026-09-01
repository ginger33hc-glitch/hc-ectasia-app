"""Targeted second-pass transcription for small Pentacam numeric panels.

This module is an extraction-only adapter.  It never changes clinical policy,
calculates a missing Pentacam index, or overwrites a value from the general
extractor.  When a Pentacam image contains still-missing labeled numeric
fields, the adapter submits the original plus four overlapping crops to one
focused, structured reread and accepts only high-confidence label/value pairs.
"""

from __future__ import annotations

from collections import defaultdict
from io import BytesIO
import json
import os
import re
from typing import Any, Callable

from PIL import Image, ImageOps


TARGET_FIELDS = (
    "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmax_D",
    "corneal_diameter_mm", "pachy_thinnest_um", "BAD_D", "Df", "Db",
    "Dp", "Dt", "Da", "PPI_avg", "PPI_min", "PPI_max", "ARTmax_um",
    "ISV", "IVA", "KI", "CKI", "IHD", "I_S", "KISA", "IHA",
    "Rmin_mm", "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um", "thinnest_x_mm", "thinnest_y_mm",
    "corneal_volume_mm3", "RMS_HOA_um", "vertical_coma_um", "Kmean_D",
    "total_RMS_um", "spherical_aberration_um",
)

PENTACAM_SCREEN_FAMILIES = {
    "BAD_DISPLAY",
    "FOUR_MAPS_REFRACTIVE",
    "TOPOMETRIC_KC",
    "PACHYMETRY",
    "OTHER_PENTACAM",
}

SOURCE_TILES = ("ORIGINAL", "UPPER_LEFT", "UPPER_RIGHT", "LOWER_LEFT", "LOWER_RIGHT")
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
                },
                "required": [
                    "eye", "field", "value", "status", "printed_label", "group_label",
                    "source_tile",
                ],
            },
        },
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["screen_family", "readings", "warnings"],
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
numbers. A map spot or color scale is not a labeled table value. Cornea Diameter/W2W is acceptable
for corneal_diameter_mm only when it is the Pentacam horizontal white-to-white output. I_S is only
the printed IS or I-S field, not ISV, IVA, IHD, IHA, or KISA.

The printed_label response must contain the visible row/field label associated with the value. If
that label is only Min, Avg/Ave, Max, X, or Y beneath a shared heading, copy the visible shared
heading into group_label; otherwise use group_label=null. source_tile must identify the clearest
image containing the heading/label and digits. Do not include unrequested fields. Do not make any
clinical interpretation or recommendation.

REQUESTED FIELDS BY EYE:
{targets}
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
        missing = [field for field in TARGET_FIELDS if eye.get(field) is None]
        if missing:
            targets[eye_id] = missing
    return targets


def build_overlapping_tiles(raw: bytes) -> list[tuple[str, bytes]]:
    """Decode safely and return four overlapping PNG regions without altering the source."""
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
    boxes = (
        ("UPPER_LEFT", (0, 0, left_end, top_end)),
        ("UPPER_RIGHT", (right_start, 0, width, top_end)),
        ("LOWER_LEFT", (0, bottom_start, left_end, height)),
        ("LOWER_RIGHT", (right_start, bottom_start, width, height)),
    )
    tiles = []
    for name, box in boxes:
        crop = image.crop(box)
        output = BytesIO()
        crop.save(output, format="PNG", optimize=True)
        tiles.append((name, output.getvalue()))
    return tiles


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
        "pachy_thinnest_um": (("thinnest", "pachythin", "thinnestpachy", "thinnestlocation"),),
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


def _same_number(values: list[float]) -> bool:
    return max(values) - min(values) <= 1e-9


def apply_targeted_readings(
    core: Any,
    result: dict[str, Any],
    reread: dict[str, Any],
    requested: dict[str, list[str]],
    filename: str,
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
        if reading.get("status") != "CONFIDENT" or not core.is_number(reading.get("value")):
            continue
        if not label_supports_field(field, reading.get("printed_label"), reading.get("group_label")):
            result.setdefault("global_warnings", []).append(
                f"Targeted Pentacam reread rejected {eye_id} {field} in {filename}: "
                "the returned printed label did not identify that field unambiguously."
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
        verified = set(eye.get("table_verified_numeric_fields") or [])
        verified.add(field)
        eye["table_verified_numeric_fields"] = sorted(verified)
        eye["missing_or_unreadable"] = [
            item for item in eye.get("missing_or_unreadable") or [] if item != field
        ]
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
    return result


def _target_summary(requested: dict[str, list[str]]) -> str:
    return "\n".join(f"{eye}: {', '.join(fields)}" for eye, fields in sorted(requested.items()))


def targeted_reread(core: Any, raw: bytes, filename: str, requested: dict[str, list[str]]) -> dict[str, Any]:
    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": REREAD_PROMPT.format(targets=_target_summary(requested))},
        {"type": "input_text", "text": "ORIGINAL complete screen:"},
        {"type": "input_image", "image_url": core.data_url(raw, filename), "detail": "original"},
    ]
    for tile_name, tile_raw in build_overlapping_tiles(raw):
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
        if not _enabled() or not requested:
            return result
        try:
            reread = targeted_reread(core, raw, filename, requested)
            return apply_targeted_readings(core, result, reread, requested, filename)
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
