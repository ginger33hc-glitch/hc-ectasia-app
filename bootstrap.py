"""Runtime bootstrap for the HC Ectasia App."""
from pathlib import Path

import app as core
from lasik_planning import install

install(core)

# Reconcile small numeric differences when the same Pentacam examination is represented on
# overlapping screenshots. These are ingestion/merge tolerances, not clinical progression
# thresholds. Materially discordant values remain unresolved conflicts.
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
        # Pentacam pachymetry has finite test-retest variability. A <=10 µm difference between
        # overlapping screenshots is reconciled conservatively rather than treated as missing data.
        return abs(left - right) <= 10.0
    if field == "Rmin_mm":
        # Radius is displayed with rounding and can vary slightly across repeated representations.
        # Permit <=1% relative disagreement (e.g. 7.09 vs 7.03 mm); retain the lower Rmin.
        scale = max(abs(left), abs(right), 1e-9)
        return abs(left - right) / scale <= 0.01
    return False


def merge_extractions_reconciled(results):
    merged = _original_merge_extractions(results)
    for eye in merged.get("eyes", []):
        retained = []
        reconciled = []
        for conflict in eye.get("data_conflicts", []):
            field, left, right = _conflict_parts(conflict)
            if field and _repeated_measurement_concordant(field, left, right):
                # Keep the safety-limiting value, matching the HC engine's conservative direction.
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

# Keep the browser defaults and LASIK plan visibility synchronized with HC policy.
# The server-side engine enforces Plan A -> B -> C. The browser patch makes the selected
# plan unmistakable at the top of each LASIK PASS result so a surgeon cannot overlook
# that the engine may have fallen back from Plan A.
index_path = Path(__file__).parent / "static" / "index.html"
try:
    html = index_path.read_text(encoding="utf-8")
    replacements = {
        "HC Ectasia App v0.7.4": "HC Ectasia App v0.7.7",
        "HC Ectasia App v0.7.5": "HC Ectasia App v0.7.7",
        "HC Ectasia App v0.7.6": "HC Ectasia App v0.7.7",
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
    # Failure to patch display defaults must not prevent startup; server-side enforcement remains active.
    pass

core.app.title = "HC Ectasia App v0.7.7"
app = core.app
