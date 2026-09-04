"""Fail-closed Randleman/ERSS readiness for virgin LASIK reports."""
from fastapi import HTTPException

_REQUIRED_ROWS=("topography","RSB","age","pachymetry","MRSE")
_previous_missing_items=None;_previous_request=None;_previous_export_payload=None

def _number(v):return isinstance(v,(int,float)) and not isinstance(v,bool)
def _is_lasik_virgin_eye(eye):
    values=eye.get("values") or {}
    if str(values.get("procedure") or "").upper()!="LASIK":return False
    return str(values.get("prior_refractive_surgery") or "").strip().lower() not in {"yes","true","1"}
def _erss_complete(eye):
    if not _is_lasik_virgin_eye(eye):return True
    erss=eye.get("randleman_erss")
    if not isinstance(erss,dict):return False
    rows=erss.get("rows") or {};return all(_number(rows.get(n)) for n in _REQUIRED_ROWS) and _number(erss.get("total"))
def _component_requests(eye):
    if not _is_lasik_virgin_eye(eye) or _erss_complete(eye):return []
    erss=eye.get("randleman_erss") or {};rows=erss.get("rows") or {};missing=set(erss.get("missing_erss_inputs") or []);missing.update(n for n in _REQUIRED_ROWS if not _number(rows.get(n)));evidence=eye.get("erss_topography_evidence") or {};messages=[]
    if "topography" in missing:
        if evidence.get("needs_surgeon_I_S"):messages.append("Randleman/ERSS requires a usable signed I-S value for numeric topography scoring.")
        if evidence.get("needs_surgeon_SRAX"):messages.append("Randleman/ERSS requires SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map.")
        if not evidence.get("needs_surgeon_I_S") and not evidence.get("needs_surgeon_SRAX"):messages.append("Randleman/ERSS topography is unresolved; confirm signed I-S and Front-map SRAX evidence.")
    if "RSB" in missing:messages.append("Randleman/ERSS RSB is unavailable; complete the LASIK flap thickness and ablation inputs.")
    if "age" in missing:messages.append("Randleman/ERSS age is unavailable; enter the patient age.")
    if "pachymetry" in missing:messages.append("Randleman/ERSS requires preoperative pachy_thinnest_um.")
    if "MRSE" in missing:messages.extend(("Randleman/ERSS requires the preoperative manifest sphere.","Randleman/ERSS requires the preoperative manifest cylinder magnitude."))
    return list(dict.fromkeys(messages or ["Randleman/ERSS score is unavailable; all five LASIK ERSS components must be documented before report generation."]))
def missing_items_with_complete_erss(decision):
    items=list(_previous_missing_items(decision))
    for eye in decision.get("eyes") or []:
        eye_id=eye.get("eye","GLOBAL")
        for message in _component_requests(eye):items.append(("PATIENT","age") if "age is unavailable" in message else (eye_id,message))
    return list(dict.fromkeys(items))
def request_with_randleman(eye,message,extracted):
    if "randleman/erss rsb is unavailable" in str(message).lower():
        return {"eye":eye,"label":"LASIK flap thickness — required to calculate RSB for Randleman/ERSS","kind":"form","key":"flap_um","destination":"source","form_id":f"{str(eye).lower()}_flap","help":"Complete the LASIK flap/ablation plan so residual stromal bed can be calculated."}
    return _previous_request(eye,message,extracted)
def _validate_export_erss(payload):
    decision=payload.get("decision") or {};incomplete=[eye.get("eye","UNKNOWN") for eye in decision.get("eyes") or [] if _is_lasik_virgin_eye(eye) and not _erss_complete(eye)]
    if incomplete:raise HTTPException(409,"Randleman/ERSS is incomplete for "+", ".join(incomplete)+"; complete the missing ERSS inputs before generating a report.")
def export_payload_with_complete_erss(payload):
    exported=_previous_export_payload(payload);_validate_export_erss(exported);return exported
def install(assessment_workflow):
    global _previous_missing_items,_previous_request,_previous_export_payload
    if getattr(assessment_workflow,"_cerai_randleman_report_readiness_installed",False):return
    _previous_missing_items=assessment_workflow.missing_items;_previous_request=assessment_workflow._request;_previous_export_payload=assessment_workflow.export_payload;assessment_workflow.missing_items=missing_items_with_complete_erss;assessment_workflow._request=request_with_randleman;assessment_workflow.export_payload=export_payload_with_complete_erss;assessment_workflow._cerai_randleman_report_readiness_installed=True
