"""Narrow extraction-schema extension for PS3 labeled Pentacam fields.

This module only declares where PS3 inputs are read. It contains no clinical
thresholds and does not alter Randleman/BAD-D/NICE scoring or the legacy
TABLE_NUMERIC_FIELDS contract.
"""

PS3_EXTRA_FIELDS = {
    "topographic_astig_D": {"type": ["number", "null"]},
    "topographic_steep_axis_deg": {"type": ["number", "null"]},
    "posterior_Kmean_D": {"type": ["number", "null"]},
    "F_Ele_Th_um": {"type": ["number", "null"]},
}

PS3_SOURCE_PROMPT = r"""
PS3 ADDITIONAL LABELED-BOX READINGS (transcription only; do not score):
Use only explicitly printed values from the stated Pentacam locations. Never
reconstruct a missing value from a map, neighboring number, K1/K2 arithmetic,
colour scale, or another screen.

SHOW 2 EXAMS -> TOPOMETRIC:
- topographic_astig_D: upper Cornea Front section, printed 'Astig.' box.
- topographic_steep_axis_deg: same Cornea Front section, printed 'Axis: (steep)' box.
- posterior_Kmean_D: middle/upper Cornea Back section, printed 'Km:' box.
- Kmax_D: lower area immediately below the 'Thinnest Locat.' row with the small
  circle marker; use the dedicated printed Kmax box only.
- I_S and KISA: middle/lower Topometric index area, printed 'I-S' and 'KISA' boxes.
- pachy_thinnest_um: printed 'Thinnest Locat.' row next to the small circle marker.

BAD DISPLAY:
- F_Ele_Th_um: printed 'F. Ele.Th' box in the central area.
- B_Ele_Th_um: printed 'B. Ele.Th' box immediately adjacent to F. Ele.Th.
- PPI_avg: Progression Index section, printed 'Avg.' box below the elevation boxes.
- ARTmax_um: dedicated ARTmax box adjacent to the Progression Index section.

If any stated label or attached digits are unreadable/not shown, return null.
Do not interpret PTI/CTSP morphology, Corneal Thickness Map morphology, or
Relative Thickness Map morphology in this extraction pass.
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

    # Allow the extractor to identify these as explicitly read labeled values,
    # without expanding core.TABLE_NUMERIC_FIELDS (a behavior-locked legacy tuple).
    table_enum = properties["table_verified_numeric_fields"]["items"]["enum"]
    for name in PS3_EXTRA_FIELDS:
        if name not in table_enum:
            table_enum.append(name)

    if "PS3 ADDITIONAL LABELED-BOX READINGS" not in core.PROMPT:
        core.PROMPT += "\n" + PS3_SOURCE_PROMPT

    core._cerai_ps3_extraction_installed = True
