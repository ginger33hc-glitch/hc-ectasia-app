"""Randleman/ERSS source guard: anterior curvature wins across multi-image Pentacam sets."""
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

MANDATORY RANDLEMAN SOURCE RECOGNITION:
The Randleman/ERSS topography variable is ANTERIOR CORNEAL CURVATURE/TOPOGRAPHY, not elevation and not BAD-D.
On an OCULUS Pentacam 4 Maps Refractive page, the UPPER-LEFT colored map labelled
"Axial / Sagittal Curvature (Front)" is the anterior curvature map. Whenever that panel is visible,
you MUST return anterior_curvature_map_visible=YES, anterior_curvature_map_type=AXIAL_SAGITTAL_FRONT,
anterior_curvature_map_location=UPPER_LEFT and assess morphology/SRA-SRAX from THAT UPPER-LEFT MAP.
Do not call it OTHER. Do not call it NONE. Do not say no anterior curvature map is visible.

The UPPER-RIGHT "Elevation (Front)" is anterior ELEVATION and is NOT the Randleman map.
The LOWER-LEFT "Corneal Thickness" is pachymetry and is NOT the Randleman map.
The LOWER-RIGHT "Elevation (Back)" is posterior elevation and is NOT the Randleman map.
A Belin/Ambrosio or Topometric image in the same upload set may legitimately have no anterior curvature
panel. That NO/NONE describes only that image and MUST NOT negate a YES curvature source found on a
separate 4 Maps Refractive image.

If the upper-left Axial/Sagittal Curvature (Front) map is visible, inspect its bow-tie axes directly.
Use the published Randleman morphology categories only when their criteria can be supported from that
map; otherwise preserve the verified curvature source and return morphology UNCERTAIN rather than
pretending the map is absent.
"""

QUALIFYING={"AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE"}
ROLE_FIELDS={"anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"}
def _qualifies(e): return e.get("anterior_curvature_map_visible")=="YES" and e.get("anterior_curvature_map_type") in QUALIFYING

def merge_extractions_with_erss_source_guard(results):
    # First preserve per-image truth. A BAD/Topometric page saying NO must never erase a separate 4-Maps YES.
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

    # Remove map-role fields before generic merge: YES vs NO across different screen types is NOT a data conflict.
    merge_input=[]
    for result in guarded:
        r=dict(result); eyes=[]
        for src in result.get("eyes",[]):
            e=dict(src)
            for f in ROLE_FIELDS: e.pop(f,None)
            eyes.append(e)
        r["eyes"]=eyes; merge_input.append(r)
    merged=_original_merge(merge_input)

    for eye in merged.get("eyes",[]):
        eye_id=eye.get("eye"); sources=[]; source_eyes=[]
        for result in guarded:
            filename=(result.get("document_context") or {}).get("source_filename")
            for src in result.get("eyes",[]):
                if src.get("eye")==eye_id and _qualifies(src):
                    sources.append({"file":filename,"map_type":src.get("anterior_curvature_map_type"),"map_location":src.get("anterior_curvature_map_location"),"morphology":src.get("morphology")})
                    source_eyes.append(src)
        eye["erss_topography_sources"]=sources
        eye.setdefault("field_provenance",{})["erss_topography"]=sources
        if sources:
            # Presence is existential across the upload set: any verified qualifying source wins.
            eye["anterior_curvature_map_visible"]="YES"
            best=source_eyes[0]
            eye["anterior_curvature_map_type"]=best.get("anterior_curvature_map_type")
            eye["anterior_curvature_map_location"]=best.get("anterior_curvature_map_location")
            # Critically, restore morphology evidence from the qualifying curvature image after generic merge.
            eye["morphology"]=best.get("morphology","UNCERTAIN")
            eye["asymmetric_bow_tie"]=best.get("asymmetric_bow_tie","UNCERTAIN")
            eye["srax"]=best.get("srax","UNCERTAIN")
            eye["srax_deg"]=best.get("srax_deg")
            eye["inferior_opposite_steepening_D"]=best.get("inferior_opposite_steepening_D")
            eye["morphology_evidence"]=list(dict.fromkeys((best.get("morphology_evidence") or [])+["Randleman/ERSS source verified: anterior curvature map present; non-curvature images do not override it."]))
            # Purge obsolete role-field conflicts left by older payload logic if present.
            eye["data_conflicts"]=[c for c in eye.get("data_conflicts",[]) if str(c).split(":",1)[0].strip() not in ROLE_FIELDS]
        else:
            eye["anterior_curvature_map_visible"]="NO"; eye["anterior_curvature_map_type"]="NONE"; eye["anterior_curvature_map_location"]="NONE"
            eye["morphology"]="UNCERTAIN"; eye["asymmetric_bow_tie"]="UNCERTAIN"; eye["srax"]="UNCERTAIN"; eye["srax_deg"]=None; eye["inferior_opposite_steepening_D"]=None
            eye.setdefault("morphology_evidence",[]).append("Randleman/ERSS topography unavailable: no verified anterior curvature source in the uploaded image set.")
        eye["morphology_evidence"]=list(dict.fromkeys(eye.get("morphology_evidence",[])))
    return merged
core.merge_extractions=merge_extractions_with_erss_source_guard
