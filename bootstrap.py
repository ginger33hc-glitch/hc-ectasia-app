"""Runtime bootstrap for the HC Ectasia App."""
from pathlib import Path

import app as core
from lasik_planning import install

install(core)

# ---------------------------------------------------------------------------
# Alcon WaveLight EX500 treatment-planning image support.
# A directly displayed machine-planned maximum ablation is the preferred
# structural input. If it is absent/unreadable, the existing HC EX500 estimate
# remains the fallback. No ablation value is inferred from the colour map.
# ---------------------------------------------------------------------------
core.SCHEMA["properties"]["document_context"]["properties"]["document_type"]["enum"].append(
    "ALCON_EX500_PLANNING"
)
core.SCHEMA["properties"]["laser_plans"] = {
    "type": "array",
    "items": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
            "platform": {"type": "string", "enum": ["ALCON_WAVELIGHT_EX500", "UNKNOWN"]},
            "max_ablation_um": {"type": ["number", "null"]},
            "max_ablation_status": {
                "type": "string", "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"]
            },
            "profile_max_ablation_um": {"type": ["number", "null"]},
            "profile_max_status": {
                "type": "string", "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE", "NOT_SHOWN"]
            },
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
    },
}
core.SCHEMA["required"].append("laser_plans")

core.PROMPT += """

ALCON WAVELIGHT EX500 PLANNING-SCREEN RULE:
An uploaded image may be an Alcon WaveLight EX500 treatment-planning screen. When the platform is
visibly identifiable as WaveLight/EX500 and the screen shows treatment planning details, set
DOCUMENT_TYPE=ALCON_EX500_PLANNING and return one laser_plans entry for the visibly identified eye.
Use OD/right and OS/left exactly as displayed; never infer laterality.

The authoritative ablation field is the explicitly printed treatment-details value labeled
"Maximal Ablation" or "Max. Ablation". Transcribe that number in micrometres into max_ablation_um
only when the label, digits, unit/context, and eye are unambiguous; then set max_ablation_status to
CONFIDENT. Preserve the visible label/value in raw_max_ablation_text. Do not calculate this value
from sphere/cylinder, optical zone, colour scale, map geometry, residual stroma, or any other field.
Do not estimate it visually.

The ablation-profile panel may separately print a value such as "max 109 µm". Transcribe it into
profile_max_ablation_um only when unambiguous. This is a cross-check, not a substitute for an
unreadable treatment-details Maximal/Max. Ablation field. If both printed values are confident and
differ, preserve both values; downstream logic will treat the discrepancy as a conflict rather than
choosing either one. The treatment-details Maximal/Max. Ablation value has source priority when the
two agree.

Also transcribe explicitly printed Optical Zone, Ablation Zone, and Flap Thickness when readable,
but never use them to reconstruct a missing maximum ablation. For an EX500 planning-only image,
return an empty eyes array and an empty treatment_corrections array. For a non-EX500 image, return an
empty laser_plans array. Pentacam QS is NOT_APPLICABLE on an EX500 planning screen.
"""

_original_merge_extractions = core.merge_extractions


def _conflict_parts(conflict):
    try:
        field, values = str(conflict).split(":", 1)
        left, right = values.split(" vs ", 1)
        return field.strip(), float(left.strip()), float(right.strip())
    except (ValueError, TypeError):
        return None, None, None


def _repeated_measurement_concordant(field, left, right):
    if field == "pachy_thinnest_um":
        return abs(left - right) <= 10.0
    if field == "Rmin_mm":
        scale = max(abs(left), abs(right), 1e-9)
        return abs(left - right) / scale <= 0.01
    return False


def merge_extractions_reconciled(results):
    merged = _original_merge_extractions(results)

    # Preserve EX500 laser-plan data, which the base Pentacam/card merger does not know about.
    laser_plans = []
    ex500_files = set()
    for result in results:
        context = result.get("document_context") or {}
        if context.get("document_type") == "ALCON_EX500_PLANNING":
            if context.get("source_filename"):
                ex500_files.add(context["source_filename"])
        for item in result.get("laser_plans", []):
            if isinstance(item, dict):
                copied = dict(item)
                copied["source_filename"] = context.get("source_filename")
                laser_plans.append(copied)
    merged["laser_plans"] = laser_plans

    # A valid EX500 planning-only image intentionally has no Pentacam eye object or treatment card.
    # Remove the base merger's generic "no usable eye/treatment data" complaint for that source.
    if ex500_files:
        merged["critical_input_issues"] = [
            issue for issue in merged.get("critical_input_issues", [])
            if not (
                str(issue).startswith("Uploaded source yielded no usable eye or treatment data:")
                and any(name in str(issue) for name in ex500_files)
            )
        ]

    for eye in merged.get("eyes", []):
        retained = []
        reconciled = []
        for conflict in eye.get("data_conflicts", []):
            field, left, right = _conflict_parts(conflict)
            if field and _repeated_measurement_concordant(field, left, right):
                if field in ("pachy_thinnest_um", "Rmin_mm"):
                    eye[field] = min(left, right)
                reconciled.append(str(conflict))
            else:
                retained.append(conflict)
        eye["data_conflicts"] = retained
        if reconciled:
            eye.setdefault("reconciled_multi_image_values", []).extend(reconciled)
    return merged


core.merge_extractions = merge_extractions_reconciled

_original_apply_extracted_corrections = core.apply_extracted_corrections


def apply_extracted_corrections_with_ex500(extracted, eye_plans):
    effective = _original_apply_extracted_corrections(extracted, eye_plans)
    grouped = {eye: [] for eye in core.EYES}
    for item in extracted.get("laser_plans", []):
        eye = item.get("eye")
        if eye in core.EYES and item.get("platform") == "ALCON_WAVELIGHT_EX500":
            grouped[eye].append(item)

    for eye, candidates in grouped.items():
        if not candidates:
            continue
        plan = effective.setdefault(eye, {})
        warnings = plan.setdefault("correction_warnings", [])
        usable = []
        for item in candidates:
            max_value = item.get("max_ablation_um")
            profile_value = item.get("profile_max_ablation_um")
            if item.get("max_ablation_status") != "CONFIDENT" or not core.is_number(max_value):
                continue
            if not 0 <= float(max_value) <= 400:
                warnings.append(f"{eye} EX500 Maximal Ablation is outside the accepted 0-400 µm input range; it was not used.")
                continue
            if (
                item.get("profile_max_status") == "CONFIDENT"
                and core.is_number(profile_value)
                and abs(float(max_value) - float(profile_value)) > 0.5
            ):
                warnings.append(
                    f"{eye} EX500 DATA CONFLICT: treatment-details Maximal Ablation "
                    f"{float(max_value):g} µm differs from ablation-profile max {float(profile_value):g} µm; "
                    "neither value was used."
                )
                continue
            usable.append(float(max_value))

        distinct = sorted({round(value, 3) for value in usable})
        if len(distinct) > 1:
            warnings.append(
                f"{eye} EX500 DATA CONFLICT: multiple confident Maximal Ablation values were extracted "
                f"({', '.join(f'{value:g}' for value in distinct)} µm); no machine value was used."
            )
            continue
        if len(distinct) == 1:
            actual = distinct[0]
            previous = plan.get("ablation_um")
            if core.is_number(previous) and abs(float(previous) - actual) > 0.5:
                warnings.append(
                    f"{eye} entered/calculated ablation {float(previous):g} µm was replaced by the "
                    f"directly displayed EX500 Maximal Ablation {actual:g} µm."
                )
            plan["ablation_um"] = actual
            plan["ablation_source"] = "ALCON_WAVELIGHT_EX500_DISPLAYED_MAXIMAL_ABLATION"
            plan["laser_platform"] = "Alcon WaveLight EX500"
            warnings.append(
                f"{eye} maximum ablation uses the directly displayed Alcon WaveLight EX500 "
                f"Maximal Ablation value ({actual:g} µm); HC calculated estimate was not used."
            )
        elif candidates:
            warnings.append(
                f"{eye} EX500 planning image did not provide one conflict-free confident Maximal Ablation value; "
                "the HC calculation fallback will be used when its required inputs are available."
            )

        plan["correction_warnings"] = list(dict.fromkeys(warnings))
    return effective


core.apply_extracted_corrections = apply_extracted_corrections_with_ex500

# Expose ablation provenance in the decision payload/report data.
_original_assess_eye = core.assess_eye


def assess_eye_with_ablation_source(eye, plan, age, patient_modifiers):
    result = _original_assess_eye(eye, plan, age, patient_modifiers)
    result.setdefault("values", {})["max_ablation_source"] = (
        plan.get("ablation_source")
        if plan.get("ablation_source")
        else "HC_CALCULATED_ESTIMATE" if result.get("values", {}).get("max_ablation_um") is not None else None
    )
    return result


core.assess_eye = assess_eye_with_ablation_source

# Keep the browser defaults and LASIK plan visibility synchronized with HC policy.
index_path = Path(__file__).parent / "static" / "index.html"
try:
    html = index_path.read_text(encoding="utf-8")
    replacements = {
        "HC Ectasia App v0.7.4": "HC Ectasia App v0.7.8",
        "HC Ectasia App v0.7.5": "HC Ectasia App v0.7.8",
        "HC Ectasia App v0.7.6": "HC Ectasia App v0.7.8",
        "HC Ectasia App v0.7.7": "HC Ectasia App v0.7.8",
        '<option value="100">100 µm</option>': '<option value="100" selected>100 µm</option>',
        '<option value="6.5">6.5 mm</option>': '<option value="6.5" selected>6.5 mm</option>',
        '<option value="9.0">9.0 mm</option>': '<option value="9.0" selected>9.0 mm</option>',
        'function renderEye(r, extracted){': '''function lasikPlanHeadline(r){
  const v=r.values||{};
  if(r.status!=="PASS"||v.procedure!=="LASIK")return "";
  const plan=r.lasik_selected_plan||v.LASIK_selected_plan;
  if(!plan)return "";
  const flap=v.LASIK_flap_um;
  const optical=v.optical_zone_mm;
  const transition=v.transition_zone_mm;
  const parts=[plan];
  if(flap!==null&&flap!==undefined)parts.push(`FLAP ${fmt(flap,0)} µm`);
  if(optical!==null&&optical!==undefined)parts.push(`OPTICAL ZONE ${fmt(optical,1)} mm`);
  if(transition!==null&&transition!==undefined)parts.push(`TRANSITION ZONE ${fmt(transition,1)} mm`);
  return parts.join(" • ");
}
function statusHeadline(r){
  const plan=lasikPlanHeadline(r);
  return plan?`${r.status} — ${plan}`:r.status;
}
function renderEye(r, extracted){''',
        '<span class="status ${statusClass(r.status)}">${safe(r.status)}</span>': '<span class="status ${statusClass(r.status)}">${safe(statusHeadline(r))}</span>',
    }
    patched = html
    for old, new in replacements.items():
        patched = patched.replace(old, new)
    if patched != html:
        index_path.write_text(patched, encoding="utf-8")
except OSError:
    pass

core.app.title = "HC Ectasia App v0.7.8"
app = core.app
