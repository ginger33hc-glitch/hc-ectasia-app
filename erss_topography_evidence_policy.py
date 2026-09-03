"""Evidence gate for canonical Randleman/ERSS topography scoring.

ERSS topography uses two independent evidence channels:
1) the signed Topometric I-S value; and
2) SRAX measured only from the Axial/Sagittal Curvature (Front) map.

SRAX is never reconstructed from KISA, Kmax, I-S, astigmatism, BAD-D, or any
other surrogate. If the Front-map SRAX cannot be determined, explicit surgeon
confirmation of whether SRAX is >20 degrees is required.
"""

core=None; _previous_scoring_morphology=None; _previous_required_tomography_missing=None; _previous_assess_eye=None; _prior_assess_eye=None
VALID_I_S_STATUSES={"CONFIDENT","SURGEON_CONFIRMED"}
_CATEGORY_RANK={"NORMAL_SYMMETRIC":0,"ASYMMETRIC_BOWTIE":1,"INFERIOR_STEEPENING_SRA":3,"ABNORMAL_ECTATIC":4}
_RANDLEMAN_ROWS=("topography","RSB","age","pachymetry","MRSE")
_RETIRED_TOPOGRAPHY_REQUEST_TERMS=("morphology","topography category","asymmetric bow","inferior steep")
_SRAX_COMPLETION_TEXT="SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map"

def _field_conflict(eye,field):return any(str(item).split(":",1)[0].strip()==field for item in (eye.get("data_conflicts") or []))
def _i_s_status(eye):
    if _field_conflict(eye,"I_S"):return "CONFLICT"
    explicit=eye.get("I_S_status")
    if explicit in {"CONFIDENT","SURGEON_CONFIRMED","CONFLICT","UNREADABLE","NOT_SHOWN"}:return explicit
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("table_verified_numeric_fields") or []):return "CONFIDENT"
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("surgeon_verified_numeric_fields") or []):return "SURGEON_CONFIRMED"
    return "UNREADABLE" if eye.get("I_S") is not None else "NOT_SHOWN"
def _i_s_source(eye):
    if _i_s_status(eye)=="SURGEON_CONFIRMED":return "SURGEON_ENTRY"
    p=(eye.get("field_provenance") or {}).get("I_S") or []
    return "PENTACAM_LABELED_IS_INDEX" if p or "I_S" in set(eye.get("table_verified_numeric_fields") or []) else None
def _prepared_eye(eye,plan):
    p=dict(eye);p["_erss_i_s_gate_required"]=(plan or {}).get("procedure")=="LASIK";manual=(plan or {}).get("surgeon_I_S_D");p["_surgeon_I_S_invalid"]=manual is not None and not core.is_number(manual)
    if core.is_number(manual):p["I_S"]=float(manual);p["I_S_status"]="SURGEON_CONFIRMED";p["I_S_source"]="SURGEON_ENTRY"
    return p
def _i_s_category(eye):
    v=eye.get("I_S")
    if not(core.is_number(v) and _i_s_status(eye) in VALID_I_S_STATUSES):return None,None
    v=float(v)
    if v>=1.40:return "ABNORMAL_ECTATIC",f"Canonical signed I-S {v:+.2f} D is >= +1.40 D."
    if 1.00<v<1.40:return "INFERIOR_STEEPENING_SRA",f"Canonical signed I-S {v:+.2f} D is > +1.00 and < +1.40 D."
    if .50<v<=1.00:return "ASYMMETRIC_BOWTIE",f"Canonical signed I-S {v:+.2f} D is > +0.50 and <= +1.00 D."
    if v<-.50:return "ASYMMETRIC_BOWTIE",f"Canonical signed I-S {v:+.2f} D is < -0.50 D; negative ABT has no lower limit."
    if -.50<=v<=.50:return "NORMAL_SYMMETRIC",f"Canonical signed I-S {v:+.2f} D is within -0.50 to +0.50 D."
    return None,f"Canonical signed I-S {v:+.2f} D lies outside the currently defined CER-AI I-S bands."
def _surgeon_confirmed_srax(eye):
    v=str(eye.get("srax") or "").upper()
    if v not in {"YES","NO"}:return None
    p=(eye.get("field_provenance") or {}).get("srax") or []
    return v if any(str(i.get("source") or "").upper()=="SURGEON_CONFIRMED" for i in p if isinstance(i,dict)) else None
def _front_map_srax(eye):
    if _field_conflict(eye,"srax_deg") or _field_conflict(eye,"srax"):return None,None,None,"Conflicting SRAX readings were not used."
    v=eye.get("srax_deg")
    if core.is_number(v):
        d=float(v)
        if 0<=d<=90:return ("YES" if d>20 else "NO",d,"AXIAL_SAGITTAL_CURVATURE_FRONT",f"Front-map SRAX {d:.1f}°; criterion is strictly >20°.")
        return None,None,None,f"SRAX {d:g}° is outside the accepted 0-90° skew range and was not used."
    c=_surgeon_confirmed_srax(eye)
    if c:return c,None,"SURGEON_CONFIRMED_FRONT_MAP_REVIEW",f"Surgeon confirmed SRAX {'>20°' if c=='YES' else 'is not >20°'} from the Axial/Sagittal Curvature (Front) map."
    return None,None,None,"SRAX could not be determined from the Axial/Sagittal Curvature (Front) map."
def scoring_morphology_with_i_s_evidence_gate(eye):
    if not eye.get("_erss_i_s_gate_required"):return _previous_scoring_morphology(eye)
    evidence=[];candidates=[];ic,ie=_i_s_category(eye)
    if ie:evidence.append(ie)
    if ic:candidates.append((ic,"CANONICAL_SIGNED_I_S"))
    ss,sd,src,se=_front_map_srax(eye);evidence.append(se)
    if ss=="YES":candidates.append(("INFERIOR_STEEPENING_SRA","FRONT_MAP_SRAX_GT_20"));evidence.append("Randleman SRAX criterion met: Front-map skew is >20°.")
    elif ss=="NO":evidence.append("Randleman SRAX >20° criterion is not met.")
    if ic is None or ss is None:
        if _i_s_status(eye)=="CONFLICT":evidence.append("Conflicting same-eye I-S readings were not used.")
        evidence.append("Randleman topography remains unscored until both signed I-S and Front-map SRAX status are resolved.")
        return {"category":"UNCERTAIN","category_source":"UNRESOLVED_ERSS_TOPOGRAPHY_EVIDENCE","srax_deg":sd,"srax_status":ss,"srax_source":src,"evidence":list(dict.fromkeys(evidence))}
    category,source=max(candidates,key=lambda item:_CATEGORY_RANK[item[0]]);evidence.append("Highest applicable single Randleman topography category selected from signed I-S and Front-map SRAX; categories are never added together.")
    return {"category":category,"category_source":source,"srax_deg":sd,"srax_status":ss,"srax_source":src,"evidence":list(dict.fromkeys(evidence))}
def _is_retired_topography_request(item):return any(t in str(item).lower() for t in _RETIRED_TOPOGRAPHY_REQUEST_TERMS)
def required_tomography_missing_with_i_s(eye):
    missing=[i for i in _previous_required_tomography_missing(eye) if not _is_retired_topography_request(i)]
    if not eye.get("_erss_i_s_gate_required"):return missing
    if not(core.is_number(eye.get("I_S")) and _i_s_status(eye) in VALID_I_S_STATUSES):missing.append("usable signed I-S value for numeric Randleman topography scoring")
    ss,_,_,_=_front_map_srax(eye)
    if ss is None:missing.append(_SRAX_COMPLETION_TEXT)
    return list(dict.fromkeys(missing))
def _publish_validated_erss_topography(result,validated):
    category=validated.get("category")
    if category=="UNCERTAIN":return
    points=core.lasik_topography_points(category)
    if points is None:return
    topo=result.setdefault("topography_classification",{});topo["scoring_category"]=category;topo["evidence"]=validated.get("evidence") or []
    erss=result.get("randleman_erss")
    if isinstance(erss,dict):
        rows=dict(erss.get("rows") or {});rows["topography"]=points;erss["rows"]=rows;missing=[n for n in _RANDLEMAN_ROWS if rows.get(n) is None];erss["missing_erss_inputs"]=missing;total=None if missing else sum(int(rows[n]) for n in _RANDLEMAN_ROWS);erss["total"]=total;erss["category"]=core.score_category("LASIK",total) if total is not None else None;erss["topography_category"]=category;erss["topography_evidence"]=validated.get("evidence") or [];result["randleman_erss"]=erss
    score=result.get("score")
    if isinstance(score,dict):
        rows=dict(score.get("rows") or {});rows["topography"]=points;score["rows"]=rows
        if all(core.is_number(rows.get(n)) for n in _RANDLEMAN_ROWS):total=sum(int(rows[n]) for n in _RANDLEMAN_ROWS);score["total"]=total;score["category"]=core.score_category("LASIK",total)
        result["score"]=score
def _recover_status_after_topography_resolution(result):
    """Remove only the stale DATA INSUFFICIENT state created by retired generic morphology/SRAX placeholders."""
    if result.get("status")!="DATA INSUFFICIENT" or result.get("missing"):return
    hard=list(result.get("hard_stops") or [])
    reasons=[r for r in (result.get("reasons") or []) if "Decision-critical or required clinical data are missing/unresolved" not in str(r)]
    if hard:status="STOP-DEFER"
    else:
        erss=(result.get("randleman_erss") or {}).get("category")
        if erss=="HIGH":status="STOP-DEFER"
        elif erss=="MODERATE":status="CAUTION"
        elif reasons:status="CAUTION"
        else:status="PASS"
    result["status"]=status;result["reasons"]=list(dict.fromkeys(reasons))
    result["action"]=("STOP-DEFER; do not proceed unless the stated stop/defer condition is resolved." if status=="STOP-DEFER" else "CAUTION — surgeon review required; this category does not automatically defer surgery." if status=="CAUTION" else "CER-AI assessment PASS; this is not a guarantee of zero ectasia risk.")
def assess_eye_with_i_s_evidence(eye,plan,age,patient_modifiers):
    if core.tri((plan or {}).get("prior"))=="yes":return (_prior_assess_eye or _previous_assess_eye)(eye,plan,age,patient_modifiers)
    if (plan or {}).get("procedure")!="LASIK":return _previous_assess_eye(eye,plan,age,patient_modifiers)
    working=_prepared_eye(eye,plan or {});working["morphology"]="UNCERTAIN";working["morphology_confidence"]="UNREADABLE";working["morphology_evidence"]=[];working["asymmetric_bow_tie"]="UNCERTAIN";working["inferior_opposite_steepening_D"]=None
    result=_previous_assess_eye(working,plan,age,patient_modifiers);validated=scoring_morphology_with_i_s_evidence_gate(working);_publish_validated_erss_topography(result,validated);ist=_i_s_status(working);ss=validated.get("srax_status")
    rec={"I_S_D":working.get("I_S") if core.is_number(working.get("I_S")) else None,"I_S_status":ist,"I_S_source":_i_s_source(working),"SRAX_deg":validated.get("srax_deg"),"SRAX_status":ss or "UNRESOLVED","SRAX_source":validated.get("srax_source"),"validated_category":validated.get("category","UNCERTAIN"),"category_source":validated.get("category_source","UNRESOLVED_ERSS_TOPOGRAPHY_EVIDENCE"),"single_category_rule":"Highest applicable category from signed I-S and Front-map SRAX; categories are never added.","needs_surgeon_I_S":not(core.is_number(working.get("I_S")) and ist in VALID_I_S_STATUSES),"needs_surgeon_SRAX":ss is None}
    result["erss_topography_evidence"]=rec;result.setdefault("values",{}).update({"I_S_D":rec["I_S_D"],"I_S_status":rec["I_S_status"],"I_S_source":rec["I_S_source"],"SRAX_deg":rec["SRAX_deg"],"SRAX_status":rec["SRAX_status"],"SRAX_source":rec["SRAX_source"]})
    if working.get("_surgeon_I_S_invalid"):result.setdefault("missing",[]).append("valid numeric surgeon-confirmed I-S value")
    result["missing"]=[i for i in dict.fromkeys(result.get("missing") or []) if not _is_retired_topography_request(i) and not (ss is not None and str(i)==_SRAX_COMPLETION_TEXT)]
    if validated.get("category")!="UNCERTAIN":_recover_status_after_topography_resolution(result)
    return result
def install(runtime_core,prior_assess_eye=None):
    global core,_previous_scoring_morphology,_previous_required_tomography_missing,_previous_assess_eye,_prior_assess_eye
    if getattr(runtime_core,"_erss_topography_evidence_policy_installed",False):return
    core=runtime_core;_previous_scoring_morphology=runtime_core.scoring_morphology;_previous_required_tomography_missing=runtime_core.required_tomography_missing;_previous_assess_eye=runtime_core.assess_eye;_prior_assess_eye=prior_assess_eye;runtime_core.scoring_morphology=scoring_morphology_with_i_s_evidence_gate;runtime_core.required_tomography_missing=required_tomography_missing_with_i_s;runtime_core.assess_eye=assess_eye_with_i_s_evidence;runtime_core._erss_topography_evidence_policy_installed=True
