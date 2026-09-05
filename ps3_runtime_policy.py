"""Runtime adapter for independent PS3 on the approved recovery architecture."""
from dataclasses import asdict
from ps3_policy import DEFER, PS3EyeInput, PS3InterEyeInput, evaluate_ps3

_previous_hc_engine=None; _runtime_core=None

def _finite(v):return isinstance(v,(int,float)) and not isinstance(v,bool)
def _first_number(m,*keys):
    for k in keys:
        v=m.get(k)
        if _finite(v):return float(v)
    return None
def _manifest_axis(plan):return _first_number(plan,"manifest_axis_deg","manifest_cylinder_axis_deg","entered_axis_deg","cylinder_axis_deg","axis_deg")
def _manifest_astig(plan):
    v=_first_number(plan,"manifest_cylinder_magnitude_D")
    if v is not None:return abs(v)
    v=_first_number(plan,"manifest_cylinder_signed_D");return abs(v) if v is not None else None
def _refractive_group(plan):
    v=str(plan.get("ps3_refractive_group") or "").upper();return v if v in {"MYOPIC_EMMETROPIC","HYPEROPIC_MIXED"} else None

def _inter_eye(source):
    if set(source)!={"OD","OS"}:return None
    od,os=source["OD"],source["OS"]
    return PS3InterEyeInput(od.get("Kmean_D"),os.get("Kmean_D"),od.get("posterior_Kmean_D"),os.get("posterior_Kmean_D"),od.get("pachy_thinnest_um"),os.get("pachy_thinnest_um"),od.get("F_Ele_Th_um"),os.get("F_Ele_Th_um"),od.get("B_Ele_Th_um"),os.get("B_Ele_Th_um"))

def _authoritative_srax(eye):
    """Consume, never derive, the same source-locked SRAX state used by ERSS."""
    evidence=eye.get("erss_topography_evidence") or {}
    status=str(evidence.get("SRAX_status") or "").upper();deg=evidence.get("SRAX_deg");source=evidence.get("SRAX_source")
    if status in {"YES","NO"} or _finite(deg):return status or "UNRESOLVED",float(deg) if _finite(deg) else None,source
    # Extraction may carry the authoritative observation before ERSS publishes its evidence record.
    source=str(eye.get("srax_source") or "").upper();deg=eye.get("srax_deg")
    if source in {"AXIAL_SAGITTAL_CURVATURE_FRONT","PENTACAM_AXIAL_SAGITTAL_CURVATURE_FRONT"} and _finite(deg):
        d=float(deg);return "YES" if d>20 else "NO",d,"AXIAL_SAGITTAL_CURVATURE_FRONT"
    provenance=(eye.get("field_provenance") or {}).get("srax") or []
    confirmed=any(isinstance(i,dict) and str(i.get("source") or "").upper()=="SURGEON_CONFIRMED" for i in provenance)
    categorical=str(eye.get("srax") or "").upper()
    if confirmed and categorical in {"YES","NO"}:return categorical,None,"SURGEON_CONFIRMED_FRONT_MAP_REVIEW"
    return "UNRESOLVED",None,None

def _eye_input(eye,plan):
    ss,sd,src=_authoritative_srax(eye)
    return PS3EyeInput(anterior_km_d=eye.get("Kmean_D"),thinnest_um=eye.get("pachy_thinnest_um"),topographic_astig_d=eye.get("topographic_astig_D"),topographic_steep_axis_deg=eye.get("topographic_steep_axis_deg"),manifest_astig_d=_manifest_astig(plan),manifest_axis_deg=_manifest_axis(plan),ppi_avg=eye.get("PPI_avg"),srax_status=ss,srax_deg=sd,srax_source=src,refractive_group=_refractive_group(plan))
def _selected(result,procedure):
    p=str(procedure or "").upper();return result.disposition.prk if p=="PRK" else result.disposition.smile if p=="SMILE" else result.disposition.lasik if p=="LASIK" else None
def _summary(r):return f"PRK {r.disposition.prk}; SMILE {r.disposition.smile}; LASIK {r.disposition.lasik}"

def hc_engine_with_ps3(extracted,age,eye_plans,patient_modifiers,patient_metadata=None):
    if _previous_hc_engine is None or _runtime_core is None:raise RuntimeError("PS3 runtime adapter not initialized")
    decision=_previous_hc_engine(extracted,age,eye_plans,patient_modifiers,patient_metadata)
    source={x.get("eye"):x for x in extracted.get("eyes",[]) if x.get("eye") in {"OD","OS"}};bilateral=_inter_eye(source)
    for eye_result in decision.get("eyes",[]):
        name=eye_result.get("eye");eye=source.get(name);plan=eye_plans.get(name,{})
        if not eye or eye_result.get("status")=="POST-REFRACTIVE PATHWAY REQUIRED" or plan.get("prior")!="no":
            eye_result["ps3"]={"applicable":False,"reason":"PS3 virgin-cornea pathway not applicable."};continue
        result=evaluate_ps3(_eye_input(eye,plan),bilateral);payload=asdict(result);payload["applicable"]=True;payload["independent_channel"]=True;eye_result["ps3"]=payload
        eye_result.setdefault("reasons",[]).append(f"PS3: {result.moderate_count} moderate, {result.high_count} high risk factor(s); {_summary(result)}.")
        eye_result.setdefault("warnings",[]).extend(f"PS3 surgeon review required: {n}" for n in result.review_notes)
        if any(f.key=="srax" and f.status=="NOT_EVALUATED" for f in result.findings):eye_result.setdefault("warnings",[]).append("SRAX surgeon confirmation required: on the Axial/Sagittal Curvature (Front) map, is skewed axis >20°?")
        if _selected(result,plan.get("procedure"))==DEFER:
            reason=f"PS3 DEFER for selected {str(plan.get('procedure') or '').upper()}: {result.moderate_count} moderate, {result.high_count} high risk factor(s).";eye_result.setdefault("hard_stops",[]).append(reason);eye_result.setdefault("reasons",[]).append(reason);eye_result["status"]=_runtime_core.combine_status(eye_result["status"],"STOP-DEFER");eye_result["action"]="STOP-DEFER — selected procedure is not allowed by PS3."
        decision["status"]=_runtime_core.combine_status(decision["status"],eye_result["status"])
    decision["ps3_method_note"]="PS3 is independent. It consumes the authoritative Front-map SRAX state shared with ERSS; it never derives SRAX from KISA or other surrogate values."
    return decision

def install(core):
    global _previous_hc_engine,_runtime_core
    if getattr(core,"_cerai_ps3_runtime_installed",False):return
    _runtime_core=core;_previous_hc_engine=core.hc_engine;core.hc_engine=hc_engine_with_ps3;core._cerai_ps3_runtime_installed=True
