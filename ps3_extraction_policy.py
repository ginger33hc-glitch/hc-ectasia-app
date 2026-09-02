"""Narrow extraction-schema extension for PS3-only Pentacam fields.

PS3 is a consumer of existing canonical CER-AI measurements. This module adds
only the four measurements that did not previously exist in the canonical
schema. It must not re-read, rename, reconcile, or otherwise change existing
Kmax, Kmean, thinnest pachymetry, I-S, KISA, B.Ele.Th, PPI, or ARTmax fields.
"""

PS3_EXTRA_FIELDS = {
    "topographic_astig_D": {"type": ["number", "null"]},
    "topographic_steep_axis_deg": {"type": ["number", "null"]},
    "posterior_Kmean_D": {"type": ["number", "null"]},
    "F_Ele_Th_um": {"type": ["number", "null"]},
}

PS3_SOURCE_PROMPT = r"""
PS3 ADDITIONAL LABELED-BOX READINGS (transcription only; do not score):
Read ONLY the four new fields below. Existing canonical CER-AI fields must be
left to their existing extraction/reconciliation pathways and must not be
re-read or reinterpreted for PS3.

SHOW 2 EXAMS -> TOPOMETRIC:
- topographic_astig_D: upper Cornea Front section, printed 'Astig.' box.
- topographic_steep_axis_deg: same Cornea Front section, printed 'Axis: (steep)' box.
- posterior_Kmean_D: middle/upper Cornea Back section, printed 'Km:' box.

BAD DISPLAY:
- F_Ele_Th_um: printed 'F. Ele.Th' box in the central area.

If any stated label or attached digits are unreadable/not shown, return null.
Never reconstruct a missing value from a map, neighboring number, K1/K2
arithmetic, colour scale, or another screen. Do not interpret PTI/CTSP
morphology, Corneal Thickness Map morphology, or Relative Thickness Map
morphology in this extraction pass.
"""


def install(core):
    if getattr(core, "_cerai_ps3_extraction_installed", False):
        return

    eye_schema = core.SCHEMA["properties"]["eyes"]["items"]
    properties = eye_schema["properties"]
    required = eye_schema["required"]
    for name, schema in PS3_EXTRA_FIELDS.items():
        properties.setdefault(name, schema)
        if name not in required:
            required.append(name)

    # Allow the extractor to identify only these four as explicitly read new
    # values without expanding core.TABLE_NUMERIC_FIELDS (behavior-locked).
    table_enum = properties["table_verified_numeric_fields"]["items"]["enum"]
    for name in PS3_EXTRA_FIELDS:
        if name not in table_enum:
            table_enum.append(name)

    if "PS3 ADDITIONAL LABELED-BOX READINGS" not in core.PROMPT:
        core.PROMPT += "\n" + PS3_SOURCE_PROMPT

    core._cerai_ps3_extraction_installed = True
