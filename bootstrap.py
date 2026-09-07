"""Runtime bootstrap for CER-AI extraction extensions.

Clinical scoring is not installed or wrapped here. The authoritative assessment
path is assessment_workflow -> canonical_runtime_service -> clinical_core.
This module temporarily owns only the EX500 extraction schema/prompt and an
extraction merge extension pending the ordered Stage 2-3 extraction cleanup.
"""

import app as core

core.SCHEMA["properties"]["document_context"]["properties"]["document_type"]["enum"].append("ALCON_EX500_PLANNING")
core.SCHEMA["properties"]["laser_plans"] = {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
    "properties": {
        "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
        "platform": {"type": "string", "enum": ["ALCON_WAVELIGHT_EX500", "UNKNOWN"]},
        "max_ablation_um": {"type": ["number", "null"]},
        "max_ablation_status": {"type": "string", "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"]},
        "profile_max_ablation_um": {"type": ["number", "null"]},
        "profile_max_status": {"type": "string", "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"]},
        "optical_zone_mm": {"type": ["number", "null"]},
        "ablation_zone_mm": {"type": ["number", "null"]},
        "flap_thickness_um": {"type": ["number", "null"]},
        "raw_max_ablation_text": {"type": ["string", "null"]},
        "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "eye", "platform", "max_ablation_um", "max_ablation_status",
        "profile_max_ablation_um", "profile_max_status", "optical_zone_mm",
        "ablation_zone_mm", "flap_thickness_um", "raw_max_ablation_text",
        "missing_or_unreadable",
    ],
}}
core.SCHEMA["required"].append("laser_plans")

core.PROMPT += """

ALCON WAVELIGHT EX500 PLANNING-SCREEN RULE:
An uploaded image may be an Alcon WaveLight EX500 treatment-planning screen. When the platform is visibly identifiable as WaveLight/EX500 and the screen shows treatment planning details, set DOCUMENT_TYPE=ALCON_EX500_PLANNING and return one laser_plans entry for the visibly identified eye. Use OD/right and OS/left exactly as displayed; never infer laterality.
The authoritative ablation field is the explicitly printed treatment-details value labeled "Maximal Ablation" or "Max. Ablation". Transcribe that number in micrometres into max_ablation_um only when the label, digits, unit/context, and eye are unambiguous; then set max_ablation_status to CONFIDENT. Preserve the visible label/value in raw_max_ablation_text. Do not calculate this value from sphere/cylinder, optical zone, colour scale, map geometry, residual stroma, or any other field. Do not estimate it visually.
The ablation-profile panel may separately print a value such as "max 109 µm". Transcribe it into profile_max_ablation_um only when unambiguous. This is a cross-check, not a substitute for an unreadable treatment-details Maximal/Max. Ablation field. If both printed values are confident and differ, preserve both values; downstream logic will treat the discrepancy as a conflict rather than choosing either one. The treatment-details Maximal/Max. Ablation value has source priority when the two agree.
Also transcribe explicitly printed Optical Zone, Ablation Zone, and Flap Thickness when readable, but never use them to reconstruct a missing maximum ablation. For an EX500 planning-only image, return an empty eyes array and an empty treatment_corrections array. For a non-EX500 image, return an empty laser_plans array. Pentacam QS is NOT_APPLICABLE on an EX500 planning screen.
"""

# EX500 schema/prompt extension only. Canonical merge ownership remains in app.py.
app = core.app
