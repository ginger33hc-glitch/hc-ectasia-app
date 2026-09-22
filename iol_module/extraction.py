"""Source-locked image transcription for Pentacam Cataract Pre-Op documents."""

from __future__ import annotations

import json
from typing import Any


EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "document_type", "eye", "patient_name", "patient_age_years",
        "pentacam", "unreadable_fields",
    ],
    "properties": {
        "document_type": {
            "type": "string",
            "enum": ["PENTACAM_CATARACT_PREOP", "OTHER"],
        },
        "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
        "patient_name": {"type": ["string", "null"]},
        "patient_age_years": {"type": ["integer", "null"]},
        "pentacam": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "total_corneal_hoa_4mm_um", "q_value", "angle_kappa_mm",
                "angle_alpha_mm", "pupil_dia_3d_mm", "tcrp_astigmatism_d",
                "tcrp_k2_axis_deg",
            ],
            "properties": {
                "total_corneal_hoa_4mm_um": {"type": ["number", "null"]},
                "q_value": {"type": ["number", "null"]},
                "angle_kappa_mm": {"type": ["number", "null"]},
                "angle_alpha_mm": {"type": ["number", "null"]},
                "pupil_dia_3d_mm": {"type": ["number", "null"]},
                "tcrp_astigmatism_d": {"type": ["number", "null"]},
                "tcrp_k2_axis_deg": {"type": ["number", "null"]},
            },
        },
        "unreadable_fields": {"type": "array", "items": {"type": "string"}},
    },
}


PROMPT = """
You are transcribing one ophthalmic source image for the independent CER-AI IOL module.
Return only values explicitly printed and readable in this image. Never estimate, calculate,
average, copy from the fellow eye, or substitute a visually similar field.

Classify the image as PENTACAM_CATARACT_PREOP or OTHER. Preserve explicit OD/right
or OS/left laterality; otherwise return UNKNOWN.

For a Pentacam Cataract Pre-Op image, use these source locks only:
- total_corneal_hoa_4mm_um: lower-right field exactly labeled “Total Corneal HOA (4mm)”.
- angle_kappa_mm: lower-right Chord mu/kappa field used by the approved screen mapping.
- angle_alpha_mm: lower-right Chord alpha field.
- pupil_dia_3d_mm: lower-right “Pupil Dia (3D)” only. Ignore “Pupil Dia (virt)” completely.
- tcrp_astigmatism_d: “Astig” in the “TCRP 3.0mm, zone, pupil” column only.
- tcrp_k2_axis_deg: axis printed with K2 in that same TCRP column only.
Do not use SimK or Diff. as a candidate, cross-check, fallback, or substitute.
- q_value: transcribe only an explicitly labeled corneal Q/asphericity value. If the approved
  Q field is not shown or unreadable, return null.

For every required field that belongs to the recognized document but cannot be read with high
confidence, return null and add its canonical key to unreadable_fields.
"""


def extract_image(core: Any, raw: bytes, filename: str) -> dict[str, Any]:
    response = core.openai_client().responses.create(
        model=core.MODEL,
        store=False,
        reasoning={"effort": "low"},
        input=[{
            "role": "user",
            "content": [
                {"type": "input_text", "text": PROMPT},
                {
                    "type": "input_image",
                    "image_url": core.data_url(raw, filename),
                    "detail": "original",
                },
            ],
        }],
        text={
            "verbosity": "low",
            "format": {
                "type": "json_schema",
                "name": "cerai_iol_source_extraction",
                "strict": True,
                "schema": EXTRACTION_SCHEMA,
            },
        },
    )
    if not response.output_text or not response.output_text.strip():
        raise RuntimeError("IOL source extraction returned empty output")
    return json.loads(response.output_text)
