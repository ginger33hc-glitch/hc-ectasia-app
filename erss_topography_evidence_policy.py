"""Deterministic evidence gate for canonical Randleman/ERSS topography.
Recovery contract: visual morphology retired; signed I-S numeric classifier; direct Front-map SRAX only; SRAX positive strictly >20°; no surrogate SRAX; prior refractive surgery never enters virgin LASIK ERSS.
"""
core=None;_previous_scoring_morphology=None;_previous_required_tomography_missing=None;_previous_assess_eye=None
VALID_I_S_STATUSES={"CONFIDENT","SURGEON_CONFIRMED"};_CATEGORY_RANK={"NORMAL_SYMMETRIC":0,"ASYMMETRIC_BOWTIE":1,"INFERIOR_STEEPENING_SRA":3,"ABNORMAL_ECTATIC":4};_SRAX_COMPLETION="SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map"
def _field_conflict(eye,field):return any(str(x).split(":",1)[0].strip()==field for x in (eye.get("data_conflicts") or []))
def _i_s_status(eye):
    if _field_conflict(eye,"I_S"):return "CONFLICT"
    explicit=eye.get("I_S_status")
    if explicit in {"CONFIDENT","SURGEON_CONFIRMED","CONFLICT","UNREADABLE","NOT_SHOWN"}:return explicit
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("table_verified_numeric_fields") or []):return "CONFIDENT"
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("surgeon_verified_numeric_fields") or []):return "SURGEON_CONFIRMED"
    return "UNREADABLE" if eye.get("I_S") is not None else "NOT_SHOWN"
def _i_s_source(eye):
    if _i_s_status(eye)=="SURGEON_CONFIRMED":return "SURGEON_ENTRY"
    if (eye.get("field_provenance") or {}).get("I_S") or "I_S" in set(eye.get("table_verified_numeric_fields") or []):return "PENTACAM_LABELED_IS_INDEX"
    return None
def _i_s_category(eye):
    v=eye.get("I_S")
    if not(core.is_number(v) and _i_s_status(eye) in VALID_I_S_STATUSES):return None,"Signed I-S is unresolved."
    v=float(v)
    if v>=1.40:return "ABNORMAL_ECTATIC",f"Signed I-S {v:+.2f} D is >= +1.40 D."
    if v>1.00:return "INFERIOR_STEEPENING_SRA",f"Signed I-S {v:+.2f} D is > +1.00 and < +1.40 D."
    if v>0.50:return "ASYMMETRIC_BOWTIE",f"Signed I-S {v:+.2f} D is > +0.50 and <= +1.00 D."
    if v<-.50:return "ASYMMETRIC_BOWTIE",f"Signed I-S {v:+.2f} D is < -0.50 D; negative ABT has no lower limit."
    return "NORMAL_SYMMETRIC",f"Signed I-S {v:+.2f} D is within -0.50 to +0.50 D."
def _surgeon_srax_status(eye):
    s=str(eye.get("srax") or "").upper()
    if s not in {"YES","NO"}:return None
    p=(eye.get("field_provenance") or {}).get("srax") or [];return s if any(isinstance(i,dict) and str(i.get("source") or "").upper()=="SURGEON_CONFIRMED" for i in p) else None
def _front_map_srax(eye):
    if _field_conflict(eye,"srax_deg") or _field_conflict(eye,"srax"):return None,None,None,"Conflicting SRAX observations were not used."
    v=eye.get("srax_deg");src=str(eye.get("srax_source") or "").upper()
    if core.is_number(v) and src in {"AXIAL_SAGITTAL_CURVATURE_FRONT","PENTACAM_AXIAL_SAGITTAL_CURVATURE_FRONT"}:
        d=float(v)
        if 0<=d<=90:return("YES" if d>20 else "NO"),d,"AXIAL_SAGITTAL_CURVATURE_FRONT",f"Direct Front-map SRAX {d:.1f}°; positive criterion is strictly >20°."
        return None,None,None,f"Direct SRAX {d:g}° is outside the accepted 0-90° range."
    c=_surgeon_srax_status(eye)
    if c:return c,None,"SURGEON_CONFIRMED_FRONT_MAP_REVIEW",("Surgeon confirmed SRAX >20° from the Front map." if c=="YES" else "Surgeon confirmed SRAX is not >20° from the Front map.")
    return None,None,None,"SRAX is unresolved on the Axial/Sagittal Curvature (Front) map."
def _prepared_eye(eye,plan):
    p=dict(eye);p["_erss_i_s_gate_required"]=(plan or {}).get("procedure")=="LASIK";m=(plan or {}).get("surgeon_I_S_D");p["_surgeon_I_S_invalid"]=m is not None and not core.is_number(m)
    if core.is_number(m):p["I_S"]=float(m);p["I_S_status"]="SURGEON_CONFIRMED";p["I_S_source"]="SURGEON_ENTRY"
    return p
def scoring_morphology_with_i_s_evidence_gate(eye):
    if not eye.get("_erss_i_s_gate_required"):return _previous_scoring_morphology(eye)
    cat,ie=_i_s_category(eye);ss,sd,src,se=_front_map_srax(eye);ev=[ie,se]
    if cat is None or ss is None:return {"category":"UNCERTAIN","category_source":"UNRESOLVED_ERSS_TOPOGRAPHY_EVIDENCE","srax_status":ss,"srax_deg":sd,"srax_source":src,"evidence":list(dict.fromkeys(ev))}
    candidates=[(cat,"CANONICAL_SIGNED_I_S")]
    if ss=="YES":candidates.append(("INFERIOR_STEEPENING_SRA","FRONT_MAP_SRAX_GT_20"))
    cat,cs=max(candidates,key=lambda x:_CATEGORY_RANK[x[0]]);ev.append("Highest applicable single topography category selected; I-S and SRAX points are never added.");return {"category":cat,"category_source":cs,"srax_status":ss,"srax_deg":sd,"srax_source":src,"evidence":list(dict.fromkeys(ev))}
def required_tomography_missing_with_i_s(eye):
    missing=list(_previous_required_tomography_missing(eye))
    if not eye.get("_erss_i_s_gate_required"):return missing
    if not(core.is_number(eye.get("I_S")) and _i_s_status(eye) in VALID_I_S_STATUSES):missing.append("usable signed I-S value for Randleman topography")
    if _front_map_srax(eye)[0] is None:missing.append(_SRAX_COMPLETION)
    return list(dict.fromkeys(missing))
def assess_eye_with_i_s_evidence(eye,plan,age,patient_modifiers):
    # Prior refractive surgery must short-circuit before any virgin-cornea ERSS manipulation.
    if str((plan or {}).get("prior") or "").strip().lower() not in {"","no","none","false","0"}:
        return _previous_assess_eye(eye,plan,age,patient_modifiers)
    if (plan or {}).get("procedure")!="LASIK":return _previous_assess_eye(eye,plan,age,patient_modifiers)
    w=_prepared_eye(eye,plan or {});w["morphology"]="UNCERTAIN";w["morphology_confidence"]="UNREADABLE";w["morphology_evidence"]=[];w["asymmetric_bow_tie"]="UNCERTAIN";w["inferior_opposite_steepening_D"]=None
    r=_previous_assess_eye(w,plan,age,patient_modifiers);v=scoring_morphology_with_i_s_evidence_gate(w);s=_i_s_status(w);r["erss_topography_evidence"]={"I_S_D":w.get("I_S") if core.is_number(w.get("I_S")) else None,"I_S_status":s,"I_S_source":_i_s_source(w),"SRAX_deg":v.get("srax_deg"),"SRAX_status":v.get("srax_status") or "UNRESOLVED","SRAX_source":v.get("srax_source"),"validated_category":v.get("category","UNCERTAIN"),"category_source":v.get("category_source","UNRESOLVED"),"single_category_rule":"Highest applicable category from signed I-S and direct Front-map SRAX; never additive.","needs_surgeon_I_S":not(core.is_number(w.get("I_S")) and s in VALID_I_S_STATUSES),"needs_surgeon_SRAX":v.get("srax_status") is None}
    if w.get("_surgeon_I_S_invalid"):r.setdefault("missing",[]).append("valid numeric surgeon-confirmed I-S value")
    r["missing"]=list(dict.fromkeys(r.get("missing") or []));return r
def install(runtime_core):
    global core,_previous_scoring_morphology,_previous_required_tomography_missing,_previous_assess_eye
    if getattr(runtime_core,"_erss_topography_evidence_policy_installed",False):return
    core=runtime_core;_previous_scoring_morphology=runtime_core.scoring_morphology;_previous_required_tomography_missing=runtime_core.required_tomography_missing;_previous_assess_eye=runtime_core.assess_eye;runtime_core.scoring_morphology=scoring_morphology_with_i_s_evidence_gate;runtime_core.required_tomography_missing=required_tomography_missing_with_i_s;runtime_core.assess_eye=assess_eye_with_i_s_evidence;runtime_core._erss_topography_evidence_policy_installed=True
