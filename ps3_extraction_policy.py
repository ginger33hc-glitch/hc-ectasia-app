"""Narrow extraction-schema extension for PS3/new Pentacam fields.

PS3 and ERSS consume existing canonical CER-AI measurements read-only. This
module adds only four measurements that did not previously exist in the
canonical schema and preserves those four through the legacy merge seam. It
must not change ownership or reconciliation of existing Kmax, Kmean, thinnest
pachymetry, I-S, KISA, B.Ele.Th, PPI, or ARTmax fields.
"""

from math import isfinite


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


def _number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def _equivalent(field, left, right):
    left = float(left)
    right = float(right)
    if field == "topographic_steep_axis_deg":
        # Astigmatism axes are circular modulo 180 degrees.
        a = left % 180.0
        b = right % 180.0
        diff = abs(a - b)
        return min(diff, 180.0 - diff) <= 1e-6
    return abs(left - right) <= 1e-6


def _install_new_field_merge(core):
    """Preserve only the four new labeled-box fields through legacy merge.

    The legacy merge iterates core.TABLE_NUMERIC_FIELDS. We intentionally do
    not expand that behavior-locked tuple. Instead, this narrow adapter carries
    the four new fields after the legacy merge and fails closed on conflicts.
    """
    if not hasattr(core, "merge_extractions") or getattr(core, "_cerai_ps3_merge_installed", False):
        return

    previous_merge = core.merge_extractions

    def merge_with_new_fields(results):
        merged = previous_merge(results)
        merged_by_eye = {
            item.get("eye"): item
            for item in merged.get("eyes", [])
            if item.get("eye") in {"OD", "OS"}
        }

        for eye_name, target in merged_by_eye.items():
            verified_target = list(target.get("table_verified_numeric_fields") or [])
            conflicts = list(target.get("data_conflicts") or [])

            for field in PS3_EXTRA_FIELDS:
                candidates = []
                for result in results:
                    for source_eye in result.get("eyes", []) or []:
                        if source_eye.get("eye") != eye_name:
                            continue
                        value = source_eye.get(field)
                        verified = field in set(source_eye.get("table_verified_numeric_fields") or [])
                        if verified and _number(value):
                            candidates.append(float(value))

                unique = []
                for value in candidates:
                    if not any(_equivalent(field, value, seen) for seen in unique):
                        unique.append(value)

                if len(unique) == 1:
                    target[field] = unique[0]
                    if field not in verified_target:
                        verified_target.append(field)
                elif len(unique) > 1:
                    target[field] = None
                    verified_target = [name for name in verified_target if name != field]
                    conflict = f"{field}: " + " vs ".join(f"{value:g}" for value in unique)
                    if conflict not in conflicts:
                        conflicts.append(conflict)
                elif field not in target:
                    target[field] = None

            target["table_verified_numeric_fields"] = verified_target
            target["data_conflicts"] = conflicts

        return merged

    core.merge_extractions = merge_with_new_fields
    core._cerai_ps3_merge_installed = True


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

    _install_new_field_merge(core)
    core._cerai_ps3_extraction_installed = True
