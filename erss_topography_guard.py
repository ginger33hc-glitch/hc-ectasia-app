"""Randleman/ERSS source isolation and dedicated anterior-curvature second pass."""
import json
import extraction_guard
core=extraction_guard.core
_original_merge=core.merge_extractions
_original_extract_one_image=core.extract_one_image
_original_scoring_morphology=core.scoring_morphology

eye_schema=core.SCHEMA["properties"]["eyes"]["items"]
eye_props=eye_schema["properties"]
eye_props["anterior_curvature_map_visible"]={"type":"string","enum":["YES","NO","UNCERTAIN"]}
eye_props["anterior_curvature_map_type"]={"type":"string","enum":["AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE","NONE","UNCERTAIN"]}
eye_props["anterior_curvature_map_location"]={"type":"string","enum":["UPPER_LEFT","OTHER","NONE","UNCERTAIN"]}
for f in ("anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"):
    if f not in eye_schema["required"]: eye_schema["required"].append(f)

core.PROMPT += r"""
RANDLEMAN/ERSS SOURCE RULE: Pentacam BAD and Randleman anterior topography are independent. On a standard
OCULUS PENTACAM 4 Maps Refractive screen the UPPER-LEFT Axial/Sagittal Curvature (Front) panel IS the
anterior curvature/topography source. Upper-right Elevation (Front), lower-left Corneal Thickness and
lower-right Elevation (Back) are not Randleman sources. Never require BAD to recognize or score this map.
"""

QUALIFYING={"AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE"}
ROLE_FIELDS={"anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"}
def _qualifies(e): return e.get("anterior_curvature_map_visible")=="YES" and e.get("anterior_curvature_map_type") in QUALIFYING

ERSS_SCHEMA={
 "type":"object","additionalProperties":False,
 "properties":{
  "display_type":{"type":"string","enum":["PENTACAM_4_MAPS_REFRACTIVE","OTHER_PENTACAM","NOT_PENTACAM","UNCERTAIN"]},
  "eye":{"type":"string","enum":["OD","OS","UNKNOWN"]},
  "anterior_curvature_map_visible":{"type":"string","enum":["YES","NO","UNCERTAIN"]},
  "morphology":{"type":"string","enum":["NORMAL_SYMMETRIC","ASYMMETRIC_BOWTIE","INFERIOR_STEEPENING_SRA","ABNORMAL_ECTATIC","UNCERTAIN"]},
  "asymmetric_bow_tie":{"type":"string","enum":["YES","NO","UNCERTAIN"]},
  "srax":{"type":"string","enum":["YES","NO","UNCERTAIN"]},
  "srax_deg":{"type":["number","null"]},
  "inferior_opposite_steepening_D":{"type":["number","null"]},
  "evidence":{"type":"array","items":{"type":"string"}}
 },
 "required":["display_type","eye","anterior_curvature_map_visible","morphology","asymmetric_bow_tie","srax","srax_deg","inferior_opposite_steepening_D","evidence"]
}
ERSS_PROMPT=r"""You are ONLY the Randleman/ERSS anterior-topography reader. Ignore BAD-D and all Belin/Ambrosio values.
First identify the page. If the header says OCULUS - PENTACAM 4 Maps Refractive, or the standard four-map
layout is unmistakable, set display_type=PENTACAM_4_MAPS_REFRACTIVE. On that page the UPPER-LEFT map is,
by fixed Pentacam layout, Axial/Sagittal Curvature (Front), therefore anterior_curvature_map_visible=YES.
Do not require the small panel title to be perfectly legible once the 4 Maps Refractive page is established.
Upper-right is Elevation Front; lower-left Corneal Thickness; lower-right Elevation Back. They are irrelevant
to Randleman topography.
Then inspect ONLY the upper-left anterior curvature map and classify the Randleman anterior-topography pattern.
NORMAL_SYMMETRIC = round, oval, or symmetric bow-tie. ASYMMETRIC_BOWTIE requires asymmetric steepening >0.5 D
but <1.0 D versus the region 180 degrees opposite, without significant SRA/SRAX. INFERIOR_STEEPENING_SRA
requires support for SRAX >=20 degrees, or >=1.0 D inferior-versus-opposite steepening with printed I-S <1.4 D.
ABNORMAL_ECTATIC is reserved for an unequivocal abnormal ectatic pattern/keratoconus/PMD/FFKC or I-S >=1.4 D.
Report srax_deg or inferior_opposite_steepening_D only when reliably supported; never invent a number. If the
visible pattern is suspicious but the required Randleman category threshold cannot be established, return
morphology=UNCERTAIN. This task never needs a BAD map."""

def _erss_second_pass(raw,filename):
    response=core.openai_client().responses.create(
        model=core.MODEL,store=False,reasoning={"effort":"medium"},
        input=[{"role":"user","content":[{"type":"input_text","text":ERSS_PROMPT},{"type":"input_image","image_url":core.data_url(raw,filename),"detail":"original"}]}],
        text={"format":{"type":"json_schema","name":"erss_curvature_read","strict":True,"schema":ERSS_SCHEMA}}
    )
    return json.loads(response.output_text)

def extract_one_image_with_erss(raw,filename):
    result=_original_extract_one_image(raw,filename)
    # Run the dedicated source reader for every upload. It independently decides whether
    # the image is a Pentacam 4 Maps Refractive page, so a generic document-type
    # misclassification cannot suppress Randleman/ERSS source recognition.
    try:
        er=_erss_second_pass(raw,filename)
    except Exception as exc:
        result.setdefault("global_warnings",[]).append(f"Dedicated ERSS curvature-map read failed for {filename}: {type(exc).__name__}; general extraction retained.")
        return result
    if er.get("display_type")!="PENTACAM_4_MAPS_REFRACTIVE":
        return result
    er["anterior_curvature_map_visible"]="YES"
    target_eye=er.get("eye")
    candidates=[e for e in result.get("eyes",[]) if target_eye=="UNKNOWN" or e.get("eye")==target_eye]
    if len(candidates)==1:
        e=candidates[0]
        e["anterior_curvature_map_visible"]="YES";e["anterior_curvature_map_type"]="AXIAL_SAGITTAL_FRONT";e["anterior_curvature_map_location"]="UPPER_LEFT"
        for f in ("morphology","asymmetric_bow_tie","srax","srax_deg","inferior_opposite_steepening_D"): e[f]=er.get(f)
        e["morphology_evidence"]=list(dict.fromkeys((er.get("evidence") or [])+["Dedicated ERSS pass: Pentacam 4 Maps upper-left Axial/Sagittal Curvature (Front) recognized as anterior topography."]))
        e["erss_source_read"]="DEDICATED_CURVATURE_PASS"
    else:
        result.setdefault("global_warnings",[]).append(
            f"Dedicated ERSS reader recognized Pentacam 4 Maps Refractive in {filename}, but eye laterality could not be mapped unambiguously; no morphology was assigned."
        )
    return result
core.extract_one_image=extract_one_image_with_erss

def merge_extractions_with_erss_source_guard(results):
    guarded=[]
    for result in results:
        copied=dict(result); eyes=[]
        for raw in result.get("eyes",[]):
            e=dict(raw)
            if not _qualifies(e):
                e.update({"morphology":"UNCERTAIN","asymmetric_bow_tie":"UNCERTAIN","srax":"UNCERTAIN","srax_deg":None,"inferior_opposite_steepening_D":None})
            eyes.append(e)
        copied["eyes"]=eyes;guarded.append(copied)
    merge_input=[]
    for result in guarded:
        r=dict(result);eyes=[]
        for src in result.get("eyes",[]):
            e=dict(src)
            for f in ROLE_FIELDS:e.pop(f,None)
            eyes.append(e)
        r["eyes"]=eyes;merge_input.append(r)
    merged=_original_merge(merge_input)
    for eye in merged.get("eyes",[]):
        eye_id=eye.get("eye");source_eyes=[];sources=[]
        for result in guarded:
            filename=(result.get("document_context") or {}).get("source_filename")
            for src in result.get("eyes",[]):
                if src.get("eye")==eye_id and _qualifies(src):
                    source_eyes.append(src);sources.append({"file":filename,"map_type":src.get("anterior_curvature_map_type"),"map_location":src.get("anterior_curvature_map_location"),"morphology":src.get("morphology"),"srax_deg":src.get("srax_deg"),"reader":src.get("erss_source_read")})
        eye["erss_topography_sources"]=sources;eye.setdefault("field_provenance",{})["erss_topography"]=sources;eye["erss_bad_dependency"]=False
        if source_eyes:
            dedicated=[s for s in source_eyes if s.get("erss_source_read")=="DEDICATED_CURVATURE_PASS"]
            categories={s.get("morphology") for s in dedicated if s.get("morphology") not in (None,"UNCERTAIN")}
            if len(categories)>1:
                best=dedicated[0]
                best=dict(best);best.update({"morphology":"UNCERTAIN","asymmetric_bow_tie":"UNCERTAIN","srax":"UNCERTAIN","srax_deg":None,"inferior_opposite_steepening_D":None})
                best["morphology_evidence"]=["Conflicting dedicated anterior-curvature morphology reads; Randleman topography left UNCERTAIN for surgeon review."]
            else:
                best=next((s for s in dedicated if s.get("morphology") not in (None,"UNCERTAIN")),None) or (dedicated[0] if dedicated else source_eyes[0])
            eye["anterior_curvature_map_visible"]="YES";eye["anterior_curvature_map_type"]=best.get("anterior_curvature_map_type");eye["anterior_curvature_map_location"]=best.get("anterior_curvature_map_location")
            for f in ("morphology","asymmetric_bow_tie","srax","srax_deg","inferior_opposite_steepening_D"):eye[f]=best.get(f)
            eye["morphology_evidence"]=list(dict.fromkeys(best.get("morphology_evidence") or []));eye["erss_source_read"]=best.get("erss_source_read")
        else:
            eye.update({"anterior_curvature_map_visible":"NO","anterior_curvature_map_type":"NONE","anterior_curvature_map_location":"NONE","morphology":"UNCERTAIN","asymmetric_bow_tie":"UNCERTAIN","srax":"UNCERTAIN","srax_deg":None,"inferior_opposite_steepening_D":None,"erss_source_read":None})
        eye["data_conflicts"]=[c for c in eye.get("data_conflicts",[]) if str(c).split(":",1)[0].strip() not in ROLE_FIELDS]
    qualifying_eyes={e.get("eye") for e in merged.get("eyes",[]) if _qualifies(e)}
    if qualifying_eyes:
        def keep_warning(w):
            text=str(w).upper()
            source_specific=("NO ANTERIOR" in text or "MORPHOLOGY" in text or "SRAX" in text) and ("BELIN" in text or "BAD" in text or "TOPOMETRIC" in text)
            return not source_specific
        merged["global_warnings"]=[w for w in merged.get("global_warnings",[]) if keep_warning(w)]
    return merged
core.merge_extractions=merge_extractions_with_erss_source_guard

def scoring_morphology_with_dedicated_source(eye):
    """Do not discard a threshold-constrained classification produced by the dedicated ERSS pass."""
    if eye.get("erss_source_read")=="DEDICATED_CURVATURE_PASS" and _qualifies(eye):
        category=eye.get("morphology","UNCERTAIN")
        evidence=list(eye.get("morphology_evidence") or [])
        if category in {"NORMAL_SYMMETRIC","ASYMMETRIC_BOWTIE","INFERIOR_STEEPENING_SRA","ABNORMAL_ECTATIC"}:
            evidence.append("Randleman category accepted from the dedicated threshold-constrained anterior-curvature read; BAD/BAD-D was not used.")
            return {"category":category,"evidence":list(dict.fromkeys(evidence))}
    return _original_scoring_morphology(eye)
core.scoring_morphology=scoring_morphology_with_dedicated_source
