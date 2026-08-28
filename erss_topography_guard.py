"""Randleman/ERSS source guard: deterministic Pentacam 4 Maps anterior-curvature recognition."""
import extraction_guard
core=extraction_guard.core
_original_merge=core.merge_extractions

eye_schema=core.SCHEMA["properties"]["eyes"]["items"]
eye_props=eye_schema["properties"]
eye_props["anterior_curvature_map_visible"]={"type":"string","enum":["YES","NO","UNCERTAIN"]}
eye_props["anterior_curvature_map_type"]={"type":"string","enum":["AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE","NONE","UNCERTAIN"]}
eye_props["anterior_curvature_map_location"]={"type":"string","enum":["UPPER_LEFT","OTHER","NONE","UNCERTAIN"]}
for f in ("anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"):
    if f not in eye_schema["required"]: eye_schema["required"].append(f)

core.PROMPT += r"""

DETERMINISTIC PENTACAM 4 MAPS RECOGNITION — DO THIS BEFORE ANY RANDLEMAN SCORING:
First classify the SCREEN/PAGE itself.
If the image title/header says "OCULUS - PENTACAM 4 Maps Refractive" or clearly shows the standard Pentacam
4 Maps Refractive four-panel layout, then identify the four panels by FIXED POSITION:
  UPPER LEFT  = Axial / Sagittal Curvature (Front) = ANTERIOR CURVATURE / ANTERIOR TOPOGRAPHY.
  UPPER RIGHT = Elevation (Front)                  = anterior elevation, NOT curvature.
  LOWER LEFT  = Corneal Thickness                  = pachymetry, NOT curvature.
  LOWER RIGHT = Elevation (Back)                   = posterior elevation, NOT curvature.
For a recognized Pentacam 4 Maps Refractive page, the upper-left panel MUST be treated as a present
anterior-curvature source even if small text is partially unreadable, provided the standard four-panel
layout and upper-left curvature color scale/map are visible. Set:
  anterior_curvature_map_visible = YES
  anterior_curvature_map_type = AXIAL_SAGITTAL_FRONT
  anterior_curvature_map_location = UPPER_LEFT
Do NOT require a BAD/Belin-Ambrosio display. Do NOT use BAD-D to confirm this identity. Do NOT return
NONE/OTHER merely because another uploaded image is a BAD, Topometric, elevation, or pachymetry display.

RANDLEMAN/ERSS IS A SEPARATE PATHWAY FROM BAD. Once the upper-left anterior curvature panel is recognized,
inspect THAT PANEL for the published anterior-topography morphology criteria, including asymmetric bow-tie,
inferior steepening, and SRA/SRAX. Specifically inspect whether the superior and inferior steep radial axes
are non-collinear/skewed; if a reliable SRAX angle can be measured, report srax_deg. Do not invent an angle.
"""

QUALIFYING={"AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE"}
ROLE_FIELDS={"anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"}
def _qualifies(e):
    return e.get("anterior_curvature_map_visible")=="YES" and e.get("anterior_curvature_map_type") in QUALIFYING

def merge_extractions_with_erss_source_guard(results):
    guarded=[]
    for result in results:
        copied=dict(result); copied_eyes=[]
        for raw in result.get("eyes",[]):
            e=dict(raw)
            if not _qualifies(e):
                e["morphology"]="UNCERTAIN"; e["asymmetric_bow_tie"]="UNCERTAIN"; e["srax"]="UNCERTAIN"
                e["srax_deg"]=None; e["inferior_opposite_steepening_D"]=None
            copied_eyes.append(e)
        copied["eyes"]=copied_eyes; guarded.append(copied)
    merge_input=[]
    for result in guarded:
        r=dict(result); eyes=[]
        for src in result.get("eyes",[]):
            e=dict(src)
            for f in ROLE_FIELDS:e.pop(f,None)
            eyes.append(e)
        r["eyes"]=eyes;merge_input.append(r)
    merged=_original_merge(merge_input)
    for eye in merged.get("eyes",[]):
        eye_id=eye.get("eye");sources=[];source_eyes=[]
        for result in guarded:
            filename=(result.get("document_context") or {}).get("source_filename")
            for src in result.get("eyes",[]):
                if src.get("eye")==eye_id and _qualifies(src):
                    sources.append({"file":filename,"map_type":src.get("anterior_curvature_map_type"),"map_location":src.get("anterior_curvature_map_location"),"morphology":src.get("morphology"),"srax_deg":src.get("srax_deg")})
                    source_eyes.append(src)
        eye["erss_topography_sources"]=sources;eye.setdefault("field_provenance",{})["erss_topography"]=sources;eye["erss_bad_dependency"]=False
        if sources:
            eye["anterior_curvature_map_visible"]="YES"
            best=next((s for s in source_eyes if s.get("morphology") not in (None,"UNCERTAIN")),source_eyes[0])
            eye["anterior_curvature_map_type"]=best.get("anterior_curvature_map_type");eye["anterior_curvature_map_location"]=best.get("anterior_curvature_map_location")
            for f in ("morphology","asymmetric_bow_tie","srax","srax_deg","inferior_opposite_steepening_D"):eye[f]=best.get(f)
            evidence=[x for x in (best.get("morphology_evidence") or []) if "BAD" not in str(x).upper() and "BELIN" not in str(x).upper()]
            evidence.append("Anterior curvature source verified independently from Pentacam 4 Maps/topography; BAD is not required for Randleman/ERSS.")
            eye["morphology_evidence"]=list(dict.fromkeys(evidence));eye["data_conflicts"]=[c for c in eye.get("data_conflicts",[]) if str(c).split(":",1)[0].strip() not in ROLE_FIELDS]
        else:
            eye["anterior_curvature_map_visible"]="NO";eye["anterior_curvature_map_type"]="NONE";eye["anterior_curvature_map_location"]="NONE"
            eye["morphology"]="UNCERTAIN";eye["asymmetric_bow_tie"]="UNCERTAIN";eye["srax"]="UNCERTAIN";eye["srax_deg"]=None;eye["inferior_opposite_steepening_D"]=None
            eye["morphology_evidence"]=["Randleman/ERSS topography unavailable only because no anterior curvature/topography source was recognized; BAD data are irrelevant."]
    return merged
core.merge_extractions=merge_extractions_with_erss_source_guard
