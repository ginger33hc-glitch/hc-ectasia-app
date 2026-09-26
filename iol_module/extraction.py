"""Source-locked transcription for IOLMaster 500 and Pentacam reports."""

from __future__ import annotations

import json
import unicodedata
from typing import Any

EYE_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["axial_length_mm", "axial_length_edited_marker", "k1_d", "k1_axis_deg", "k2_d", "k2_axis_deg", "acd_mm", "lens_thickness_mm"],
    "properties": {
        "axial_length_mm": {"type": ["number", "null"]},
        "axial_length_edited_marker": {"type": "boolean"},
        "k1_d": {"type": ["number", "null"]}, "k1_axis_deg": {"type": ["number", "null"]},
        "k2_d": {"type": ["number", "null"]}, "k2_axis_deg": {"type": ["number", "null"]},
        "acd_mm": {"type": ["number", "null"]},
        "lens_thickness_mm": {"type": ["number", "null"]},
    },
}

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["document_type", "eye", "patient_name", "patient_age_years", "pentacam", "cornea_back", "iolmaster500", "unreadable_fields"],
    "properties": {
        "document_type": {"type": "string", "enum": ["PENTACAM_CATARACT_PREOP", "PENTACAM_4_MAPS_REFRACTIVE", "IOLMASTER_500_BIOMETRY", "OTHER"]},
        "eye": {"type": "string", "enum": ["OD", "OS", "BOTH", "UNKNOWN"]},
        "patient_name": {"type": ["string", "null"]},
        "patient_age_years": {"type": ["integer", "null"]},
        "pentacam": {
            "type": "object", "additionalProperties": False,
            "required": ["total_corneal_hoa_4mm_um", "angle_kappa_mm", "angle_alpha_mm", "pupil_dia_3d_mm", "cct_pachy_vertex_um", "hwtw_mm", "acd_internal_mm"],
            "properties": {
                "total_corneal_hoa_4mm_um": {"type": ["number", "null"]},
                "angle_kappa_mm": {"type": ["number", "null"]},
                "angle_alpha_mm": {"type": ["number", "null"]},
                "pupil_dia_3d_mm": {"type": ["number", "null"]},
                "cct_pachy_vertex_um": {"type": ["number", "null"]},
                "hwtw_mm": {"type": ["number", "null"]},
                "acd_internal_mm": {"type": ["number", "null"]},
            },
        },
        "cornea_back": {
            "type": "object", "additionalProperties": False,
            "required": ["k1_d", "k2_d", "k1_axis_deg", "k2_axis_deg", "rh_mm", "rv_mm"],
            "properties": {
                "k1_d": {"type": ["number", "null"]},
                "k2_d": {"type": ["number", "null"]},
                "k1_axis_deg": {"type": ["number", "null"]},
                "k2_axis_deg": {"type": ["number", "null"]},
                "rh_mm": {"type": ["number", "null"]},
                "rv_mm": {"type": ["number", "null"]},
            },
        },
        "iolmaster500": {
            "type": "object", "additionalProperties": False,
            "required": ["device_version", "printed_formula", "printed_target_refraction_d", "OD", "OS"],
            "properties": {
                "device_version": {"type": ["string", "null"]},
                "printed_formula": {"type": ["string", "null"]},
                "printed_target_refraction_d": {"type": ["number", "null"]},
                "OD": EYE_SCHEMA, "OS": EYE_SCHEMA,
            },
        },
        "unreadable_fields": {"type": "array", "items": {"type": "string"}},
    },
}

PROMPT = """
You are transcribing one ophthalmic source image for the independent CER-AI IOL module.
Return only explicitly printed, readable values. Never estimate, calculate, average, copy
from the fellow eye, or substitute a similar field. Nonmatching document objects use nulls.

Classify as PENTACAM_CATARACT_PREOP, PENTACAM_4_MAPS_REFRACTIVE,
IOLMASTER_500_BIOMETRY, or OTHER. Preserve
OD/right or OS/left; use BOTH for a bilateral IOLMaster page.

Pentacam Cataract Pre-Op source locks:
- Total Corneal HOA (4mm), Chord µ (approved kappa mapping), Chord α, Pupil Dia (3D).
- cct_pachy_vertex_um is Pachy Vertex, never Thinnest.
- hwtw_mm is HWTW.
- acd_internal_mm is ACD (Int.), the true internal ACD excluding corneal thickness.
  Never substitute ACD (Ext.).
TCRP, SimK and Diff. are not authoritative and must not be extracted.

Pentacam 4 Maps Refractive: transcribe the left numeric panel's "Cornea Back"
K1, K2 (preserve printed negative signs), their explicitly printed axes, and
Rh/Rv radii in mm. Do not use Cornea Front, color maps, or infer missing axes.
Rh/Rv are horizontal and vertical radii, not principal radii. Set missing
printed values to null. These measurements belong only to the indicated eye.

IOLMaster 500 source locks: use only the upper biometry block, never lower IOL tables.
Transcribe AL, K1 and axis, K2 and axis, and ACD separately for OD and OS. Set the AL
edited marker only when an asterisk is printed. Transcribe lens thickness only if explicitly
printed. Preserve device version, printed formula and target when readable. IOLMaster K1/K2
and axes are the sole source for the toric trigger.

For unreadable recognized-document fields return null and add the fully qualified key to
unreadable_fields.
"""


def validate_source_bundle(sources: list[dict[str, Any]]) -> dict[str, str]:
    """Fail closed before values from different IOL reports can be combined."""
    expected = {
        "PENTACAM_CATARACT_PREOP", "PENTACAM_4_MAPS_REFRACTIVE",
        "IOLMASTER_500_BIOMETRY",
    }
    documents = [item.get("extraction") or {} for item in sources]
    types = [item.get("document_type") for item in documents]
    if len(types) != 3 or set(types) != expected or len(set(types)) != 3:
        raise ValueError("Upload exactly one Cataract Pre-Op, one same-eye 4 Maps Refractive, and one IOLMaster 500 report.")

    names = [" ".join(str(item.get("patient_name") or "").split()) for item in documents]
    if any(not name for name in names):
        raise ValueError("Patient name must be readable on all three reports before combining their measurements.")
    normalized = {unicodedata.normalize("NFKC", name).casefold() for name in names}
    if len(normalized) != 1:
        raise ValueError("Patient names differ across the three reports. Check the source images.")

    by_type = dict(zip(types, documents))
    eye = by_type["PENTACAM_CATARACT_PREOP"].get("eye")
    if eye not in {"OD", "OS"}:
        raise ValueError("The operative eye must be readable on the Pentacam Cataract Pre-Op report.")
    if by_type["PENTACAM_4_MAPS_REFRACTIVE"].get("eye") != eye:
        raise ValueError("The 4 Maps Refractive report must show the same operative eye.")
    iolmaster = by_type["IOLMASTER_500_BIOMETRY"]
    if iolmaster.get("eye") not in {"BOTH", eye} or not isinstance((iolmaster.get("iolmaster500") or {}).get(eye), dict):
        raise ValueError("The IOLMaster report must include biometry for the operative eye.")
    return {"patient_name": names[types.index("PENTACAM_CATARACT_PREOP")], "eye": eye}


def extract_image(core: Any, raw: bytes, filename: str) -> dict[str, Any]:
    response = core.openai_client().responses.create(
        model=core.MODEL, store=False, reasoning={"effort": "low"},
        input=[{"role": "user", "content": [
            {"type": "input_text", "text": PROMPT},
            {"type": "input_image", "image_url": core.data_url(raw, filename), "detail": "original"},
        ]}],
        text={"verbosity": "low", "format": {"type": "json_schema", "name": "cerai_iol_source_extraction", "strict": True, "schema": EXTRACTION_SCHEMA}},
    )
    if not response.output_text or not response.output_text.strip():
        raise RuntimeError("IOL source extraction returned empty output")
    return json.loads(response.output_text)
