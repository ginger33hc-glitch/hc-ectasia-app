"""Runtime bootstrap for the HC Ectasia App."""
from pathlib import Path

import app as core
from lasik_planning import install

install(core)

# Keep the browser defaults and LASIK plan visibility synchronized with HC policy.
# The server-side engine enforces Plan A -> B -> C. The browser patch makes the selected
# plan unmistakable at the top of each LASIK PASS result so a surgeon cannot overlook
# that the engine may have fallen back from Plan A.
index_path = Path(__file__).parent / "static" / "index.html"
try:
    html = index_path.read_text(encoding="utf-8")
    replacements = {
        "HC Ectasia App v0.7.4": "HC Ectasia App v0.7.6",
        "HC Ectasia App v0.7.5": "HC Ectasia App v0.7.6",
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

core.app.title = "HC Ectasia App v0.7.6"
app = core.app
