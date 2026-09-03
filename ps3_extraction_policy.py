"""Narrow extraction-schema extension for PS3/new Pentacam fields.

PS3 and ERSS consume existing canonical CER-AI measurements read-only. This
module adds only the new PS3 fields required by the current runtime and
preserves them through the legacy merge seam.

Elevation source ownership is strict:
- F_Ele_Th_um comes only from the printed F. Ele.Th box on the BAD/Belin-Ambrosio Display.
- B_Ele_Th_um is not re-read by PS3; it is consumed only from the dedicated
  BAD-display B. Ele.Th reading already owned by the NICE extraction pathway.
Generic anterior/posterior elevation-at-thinnest values and map spots must never
substitute for these labeled BAD-display boxes.
"""

from math import isfinite

import exam_date_reconciliation_policy


PS3_EXTRA_FIELDS = {
    "topographic_astig_D": {"type": ["number", "null"]},
    "topographic_steep_axis_deg": {"type": ["number", "null"]},
    "posterior_Kmean_D": {"type": ["number", "null"]},
    "F_Ele_Th_um": {"type": ["number", "null"]},
}

PS3_SOURCE_PROMPT = r"""
PS3 ADDITIONAL LABELED-BOX READINGS (transcription only; do not score):
Read ONLY the four new fields below from their stated source. Existing canonical
CER-AI fields, including B_Ele_Th_um, must be left to their existing dedicated
extraction/reconciliation pathways and must not be re-read for PS3.

SHOW 2 EXAMS -> TOPOMETRIC:
- topographic_astig_D: upper Cornea Front section, printed 'Astig.' box.
- topographic_steep_axis_deg: same Cornea Front section, printed 'Axis: (steep)' box.
- posterior_Kmean_D: middle/upper Cornea Back section, printed 'Km:' box.

BAD / BELIN-AMBROSIO DISPLAY ONLY:
- F_Ele_Th_um: printed 'F. Ele.Th' box in the central labeled area.

For F. Ele.Th, never use an Elevation Front map value, BFS, Float, BFTE, colour
scale, generic anterior elevation-at-thinnest field, or another Pentacam screen.
If the F. Ele.Th label or attached digits are unreadable/not shown on the BAD
Display, return null. Do not interpret PTI/CTSP morphology, Corneal Thickness
Map morphology, or Relative Thickness Map morphology in this extraction pass.
"""


_previous_merge_extractions = None


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
        a = left % 180.0
        b = right % 180.0
        diff = abs(a - b)
        return min(diff, 180.0 - diff) <= 1e-6
    return abs(left - right) <= 1e-6


def _bad_display_result(result):
    """True only when the extraction itself identifies a BAD/Belin-Ambrosio page."""
    context = result.get("document_context") or {}
    tokens = [
        context.get("document_type"),
        context.get("display_type"),
        context.get("screen_type"),
    ]
    for eye in result.get("eyes") or []:
        tokens.extend(eye.get("screen_types") or [])
    normalized = [str(token or "").upper().replace("/", "_").replace(" ", "_") for token in tokens]
    if any(
        token in {
            "BAD_DISPLAY",
            "BELIN_AMBROSIO_DISPLAY",
            "BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY",
        }
        or ("BELIN" in token and "AMBROSIO" in token)
        or ("ENHANCED" in token and "ECTASIA" in token and "DISPLAY" in token)
        for token in normalized
    ):
        return True
    return any(
        reading.get("b_ele_th_page") == "BAD_DISPLAY"
        for reading in result.get("nice_readings") or []
    )


def _bad_b_ele_th_candidates(results, eye_name):
    """Reuse the canonical NICE-owned B. Ele.Th reading; never re-read it for PS3."""
    values = []
    for result in results:
        for reading in result.get("nice_readings") or []:
            if reading.get("eye") != eye_name:
                continue
            if (
                reading.get("b_ele_th_status") == "CONFIDENT"
                and reading.get("b_ele_th_landmark") == "B_ELE_TH_LABELED_BOX"
                and reading.get("b_ele_th_page") == "BAD_DISPLAY"
                and _number(reading.get("B_Ele_Th_um"))
            ):
                values.append(float(reading["B_Ele_Th_um"]))
    return values


def merge_extractions_with_new_fields(results):
    """Preserve PS3 fields, strict BAD elevation ownership, and exam-date reconciliation."""
    if _previous_merge_extractions is None:
        raise RuntimeError("PS3/new-field merge adapter was not initialized")

    merged = _previous_merge_extractions(results)
    merged = exam_date_reconciliation_policy.reconcile_merged_exam_date_conflict(merged, results)
    merged_by_eye = {
        item.get("eye"): item
        for item in merged.get("eyes", [])
        if item.get("eye") in {"OD", "OS"}
    }

    for eye_name, target in merged_by_eye.items():
        verified_target = list(target.get("table_verified_numeric_fields") or [])
        conflicts = [
            item for item in (target.get("data_conflicts") or [])
            if str(item).split(":", 1)[0].strip() not in {
                "F_Ele_Th_um",
                "B_Ele_Th_um",
                "anterior_elevation_thinnest_um",
                "posterior_elevation_thinnest_um",
            }
        ]

        for field in PS3_EXTRA_FIELDS:
            candidates = []
            for result in results:
                if field == "F_Ele_Th_um" and not _bad_display_result(result):
                    continue
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
                if field == "F_Ele_Th_um":
                    target.setdefault("field_provenance", {})[field] = [
                        {"source": "BAD_DISPLAY_F_ELE_TH_LABELED_BOX"}
                    ]
            elif len(unique) > 1:
                target[field] = None
                verified_target = [name for name in verified_target if name != field]
                conflict = f"{field}: " + " vs ".join(f"{value:g}" for value in unique)
                if conflict not in conflicts:
                    conflicts.append(conflict)
            elif field == "F_Ele_Th_um":
                target[field] = None
                verified_target = [name for name in verified_target if name != field]
            elif field not in target:
                target[field] = None

        b_values = []
        for value in _bad_b_ele_th_candidates(results, eye_name):
            if not any(abs(value - seen) <= 1e-6 for seen in b_values):
                b_values.append(value)
        if b_values:
            # The NICE extractor owns this reading. PS3 merely consumes the
            # source-locked value for its agreed inter-eye comparison.
            target["B_Ele_Th_um"] = b_values[0]
            target.setdefault("field_provenance", {})["B_Ele_Th_um"] = [
                {"source": "BAD_DISPLAY_B_ELE_TH_LABELED_BOX"}
            ]
        else:
            target["B_Ele_Th_um"] = None

        target["table_verified_numeric_fields"] = verified_target
        target["data_conflicts"] = conflicts

    return merged


def _install_new_field_merge(core):
    global _previous_merge_extractions

    if not hasattr(core, "merge_extractions") or getattr(core, "_cerai_ps3_merge_installed", False):
        return

    _previous_merge_extractions = core.merge_extractions
    core.merge_extractions = merge_extractions_with_new_fields
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

    table_enum = properties["table_verified_numeric_fields"]["items"]["enum"]
    for name in PS3_EXTRA_FIELDS:
        if name not in table_enum:
            table_enum.append(name)

    if "PS3 ADDITIONAL LABELED-BOX READINGS" not in core.PROMPT:
        core.PROMPT += "\n" + PS3_SOURCE_PROMPT

    _install_new_field_merge(core)
    core._cerai_ps3_extraction_installed = True
