"""Strict source ownership for additional PS3 Pentacam fields.

This module augments the output of the canonical ERSS source-aware merge. It never
replaces core.merge_extractions, never scores PS3, and never calculates SRAX.
"""
from math import isfinite

PS3_EXTRA_FIELDS={"topographic_astig_D":{"type":["number","null"]},"topographic_steep_axis_deg":{"type":["number","null"]},"posterior_Kmean_D":{"type":["number","null"]},"F_Ele_Th_um":{"type":["number","null"]}}
PS3_SOURCE_PROMPT=r"""
PS3 ADDITIONAL LABELED-BOX READINGS — TRANSCRIPTION ONLY; DO NOT SCORE OR DERIVE SRAX.
SHOW 2 EXAMS -> TOPOMETRIC:
- topographic_astig_D: Cornea Front, printed Astig. value.
- topographic_steep_axis_deg: Cornea Front, printed Axis (steep) value.
- posterior_Kmean_D: Cornea Back, printed Km value.
BAD / BELIN-AMBROSIO DISPLAY ONLY:
- F_Ele_Th_um: printed F. Ele.Th labeled box.
B_Ele_Th_um is not re-read here; use only the existing NICE-owned BAD Display B. Ele.Th reading.
If the exact approved label/source is not shown or is unreadable, return null. Never substitute a map value or calculated value.
"""

def _number(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(float(v))
def _equivalent(field,a,b):
    a=float(a);b=float(b)
    if field=="topographic_steep_axis_deg":
        d=abs((a%180)-(b%180));return min(d,180-d)<=1e-6
    return abs(a-b)<=1e-6
def _normalized_token(v):return str(v or "").upper().replace("/","_").replace(" ","_")
def _screen_tokens(result,eye):
    context=result.get("document_context") or {};tokens=[context.get("document_type"),context.get("display_type"),context.get("screen_type")];tokens.extend(eye.get("screen_types") or []);return [_normalized_token(x) for x in tokens]
def _is_bad_display(result,eye):return any(t in {"BAD_DISPLAY","BELIN_AMBROSIO_DISPLAY","BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY"} or ("BELIN" in t and "AMBROSIO" in t) for t in _screen_tokens(result,eye))
def _is_show2_topometric(result,eye):
    tokens=_screen_tokens(result,eye);return any("SHOW_2_EXAMS" in t or "SHOW2" in t for t in tokens) and any("TOPOMETRIC" in t for t in tokens)
def _provenance_source(eye,field):
    items=(eye.get("field_provenance") or {}).get(field) or [];return {_normalized_token(i.get("source")) for i in items if isinstance(i,dict)}
def _source_ok(result,eye,field):
    sources=_provenance_source(eye,field)
    if field=="F_Ele_Th_um":return _is_bad_display(result,eye) and (not sources or "BAD_DISPLAY_F_ELE_TH_LABELED_BOX" in sources)
    if not _is_show2_topometric(result,eye):return False
    allowed={"topographic_astig_D":{"SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT_ASTIG","PENTACAM_SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT_ASTIG"},"topographic_steep_axis_deg":{"SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT_AXIS_STEEP","PENTACAM_SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT_AXIS_STEEP"},"posterior_Kmean_D":{"SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK_KM","PENTACAM_SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK_KM"}}[field]
    return not sources or bool(sources & allowed)
def _bad_b_ele_th_candidates(results,eye_name):
    values=[]
    for result in results:
        for reading in result.get("nice_readings") or []:
            if reading.get("eye")==eye_name and reading.get("b_ele_th_status")=="CONFIDENT" and reading.get("b_ele_th_landmark")=="B_ELE_TH_LABELED_BOX" and reading.get("b_ele_th_page")=="BAD_DISPLAY" and _number(reading.get("B_Ele_Th_um")):values.append(float(reading["B_Ele_Th_um"]))
    return values

def augment_merged_extraction(results,merged):
    """Add only source-locked PS3 fields to an already canonical ERSS merge result."""
    by_eye={x.get("eye"):x for x in merged.get("eyes",[]) if x.get("eye") in {"OD","OS"}}
    for eye_name,target in by_eye.items():
        verified=list(target.get("table_verified_numeric_fields") or []);conflicts=list(target.get("data_conflicts") or [])
        for field in PS3_EXTRA_FIELDS:
            candidates=[]
            for result in results:
                for source_eye in result.get("eyes") or []:
                    if source_eye.get("eye")!=eye_name or not _source_ok(result,source_eye,field):continue
                    value=source_eye.get(field)
                    if field in set(source_eye.get("table_verified_numeric_fields") or []) and _number(value):candidates.append(float(value))
            unique=[]
            for value in candidates:
                if not any(_equivalent(field,value,x) for x in unique):unique.append(value)
            if len(unique)==1:
                target[field]=unique[0]
                if field not in verified:verified.append(field)
                source={"topographic_astig_D":"SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT_ASTIG","topographic_steep_axis_deg":"SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT_AXIS_STEEP","posterior_Kmean_D":"SHOW_2_EXAMS_TOPOMETRIC_CORNEA_BACK_KM","F_Ele_Th_um":"BAD_DISPLAY_F_ELE_TH_LABELED_BOX"}[field]
                target.setdefault("field_provenance",{})[field]=[{"source":source}]
            else:
                target[field]=None;verified=[x for x in verified if x!=field]
                if len(unique)>1:
                    msg=f"{field}: "+" vs ".join(f"{x:g}" for x in unique)
                    if msg not in conflicts:conflicts.append(msg)
        b=[]
        for value in _bad_b_ele_th_candidates(results,eye_name):
            if not any(abs(value-x)<=1e-6 for x in b):b.append(value)
        target["B_Ele_Th_um"]=b[0] if len(b)==1 else None
        if len(b)==1:target.setdefault("field_provenance",{})["B_Ele_Th_um"]=[{"source":"BAD_DISPLAY_B_ELE_TH_LABELED_BOX"}]
        elif len(b)>1:
            msg="B_Ele_Th_um: "+" vs ".join(f"{x:g}" for x in b)
            if msg not in conflicts:conflicts.append(msg)
        target["table_verified_numeric_fields"]=verified;target["data_conflicts"]=conflicts
    return merged

def install(core):
    if getattr(core,"_cerai_ps3_extraction_installed",False):return
    eye_schema=core.SCHEMA["properties"]["eyes"]["items"];properties=eye_schema["properties"];required=eye_schema["required"]
    for name,schema in PS3_EXTRA_FIELDS.items():
        properties.setdefault(name,schema)
        if name not in required:required.append(name)
    enum=properties["table_verified_numeric_fields"]["items"]["enum"]
    for name in PS3_EXTRA_FIELDS:
        if name not in enum:enum.append(name)
    if "PS3 ADDITIONAL LABELED-BOX READINGS" not in core.PROMPT:core.PROMPT+="\n"+PS3_SOURCE_PROMPT
    # Deliberately do not replace core.merge_extractions. The canonical ERSS merge remains outermost.
    core._cerai_ps3_extraction_installed=True
