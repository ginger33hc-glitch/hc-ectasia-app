"""Production adapter for the independent PS3 policy."""
from dataclasses import asdict
from ps3_policy import DEFER,PS3EyeInput,PS3InterEyeInput,evaluate_ps3
_previous_hc_engine=None; _installed_hc_engine=None; _runtime_core=None

def _finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool)
def _first_number(m,*keys):
    for k in keys:
        v=m.get(k)
        if _finite(v):return float(v)
    return None
def _manifest_axis(p):return _first_number(p,"manifest_axis_deg","manifest_cylinder_axis_deg","entered_axis_deg","cylinder_axis_deg","axis_deg")
def _manifest_astig(p):
    v=_first_number(p,"manifest_cylinder_magnitude_D")
    if v is not None:return abs(v)
    v=_first_number(p,"manifest_cylinder_signed_D"); return abs(v) if v is not None else None
def _refractive_group(p):
    v=str(p.get("ps3_refractive_group") or "").upper(); return v if v in {"MYOPIC_EMMETROPIC","HYPEROPIC_MIXED"} else None
def _inter_eye(s):
    if set(s)!={"OD","OS"}:return None
    o=s["OD"]; x=s["OS"]
    return PS3InterEyeInput(o.get("Kmean_D"),x.get("Kmean_D"),o.get("posterior_Kmean_D"),x.get("posterior_Kmean_D"),o.get("pachy_thinnest_um"),x.get("pachy_thinnest_um"),o.get("F_Ele_Th_um"),x.get("F_Ele_Th_um"),o.get("B_Ele_Th_um"),x.get("B_Ele_Th_um"))
def _eye_input(e,p):
    # SRAX source is deliberately shared with ERSS: dedicated Axial/Sagittal Curvature (Front) read only.
    return PS3EyeInput(anterior_km_d=e.get("Kmean_D"),thinnest_um=e.get("pachy_thinnest_um"),topographic_astig_d=e.get("topographic_astig_D"),topographic_steep_axis_deg=e.get("topographic_steep_axis_deg"),manifest_astig_d=_manifest_astig(p),manifest_axis_deg=_manifest_axis(p),ppi_avg=e.get("PPI_avg"),srax=e.get("srax"),srax_deg=e.get("srax_deg"),refractive_group=_refractive_group(p))
def _selected(r,p):
    p=str(p or "").upper(); return r.disposition.prk if p=="PRK" else r.disposition.smile if p=="SMILE" else r.disposition.lasik if p=="LASIK" else None
def _summary(r):return f"PRK {r.disposition.prk}; SMILE {r.disposition.smile}; LASIK {r.disposition.lasik}"
def hc_engine_with_ps3(extracted,age,eye_plans,patient_modifiers,patient_metadata=None):
    if _previous_hc_engine is None or _runtime_core is None:raise RuntimeError("PS3 runtime adapter was not initialized")
    d=_previous_hc_engine(extracted,age,eye_plans,patient_modifiers,patient_metadata); src={i.get("eye"):i for i in extracted.get("eyes",[]) if i.get("eye") in {"OD","OS"}}; bilateral=_inter_eye(src)
    for er in d.get("eyes",[]):
        n=er.get("eye"); e=src.get(n); p=eye_plans.get(n,{})
        if not e or er.get("status")=="POST-REFRACTIVE PATHWAY REQUIRED" or p.get("prior")!="no":er["ps3"]={"applicable":False,"reason":"PS3 virgin-cornea pathway not applicable."};continue
        r=evaluate_ps3(_eye_input(e,p),bilateral); payload=asdict(r); payload["applicable"]=True; payload["srax_source"]="AXIAL_SAGITTAL_CURVATURE_FRONT_ONLY"; er["ps3"]=payload
        er.setdefault("reasons",[]).append(f"PS3: {r.moderate_count} moderate, {r.high_count} high risk factor(s); {_summary(r)}.")
        er.setdefault("warnings",[]).extend(f"PS3 surgeon review required: {x}" for x in r.review_notes)
        if any(f.key=="srax" and f.status=="NOT_EVALUATED" for f in r.findings):er.setdefault("warnings",[]).append("SRAX surgeon confirmation required: on the Axial/Sagittal Curvature (Front) map, is skewed axis >20°?")
        if _selected(r,p.get("procedure"))==DEFER:
            reason=f"PS3 DEFER for selected {str(p.get('procedure') or '').upper()}: {r.moderate_count} moderate, {r.high_count} high risk factor(s)."; er.setdefault("hard_stops",[]).append(reason);er.setdefault("reasons",[]).append(reason);er["status"]=_runtime_core.combine_status(er["status"],"STOP-DEFER");er["action"]="STOP-DEFER — selected procedure is not allowed by PS3."
        d["status"]=_runtime_core.combine_status(d["status"],er["status"])
    d["ps3_method_note"]="PS3 is independent. SRAX is accepted only from the Axial/Sagittal Curvature (Front) map or explicit surgeon confirmation; inverse-KISA SRAX is prohibited."
    return d
def install(core):
    global _previous_hc_engine,_installed_hc_engine,_runtime_core
    if getattr(core,"_cerai_ps3_runtime_installed",False):return
    _runtime_core=core;_previous_hc_engine=core.hc_engine;_installed_hc_engine=hc_engine_with_ps3;core.hc_engine=hc_engine_with_ps3;core._cerai_ps3_runtime_installed=True
