"""Randleman/ERSS source guard: anterior curvature only, with explicit SRA/SRAX detection."""
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

MANDATORY RANDLEMAN / ERSS ANTERIOR-TOPOGRAPHY ANALYSIS:
Randleman/ERSS anterior-topography scoring is COMPLETELY INDEPENDENT of Pentacam BAD analysis. Never require or use BAD/Belin-Ambrosio, BAD-D, Df/Db/Dp/Dt/Da, ARTmax, PPI, elevation, or pachymetry to assign this topography score.

On OCULUS Pentacam 4 Maps Refractive, the UPPER-LEFT panel labelled "Axial / Sagittal Curvature (Front)" is the qualifying ANTERIOR CURVATURE map. If visible, set anterior_curvature_map_visible=YES, type=AXIAL_SAGITTAL_FRONT, location=UPPER_LEFT. Upper-right Elevation (Front), lower-left Corneal Thickness, lower-right Elevation (Back), and BAD displays are not Randleman sources.

CRITICAL: DO NOT reduce every non-normal bow-tie to ASYMMETRIC_BOWTIE. Explicitly inspect the two principal steep hemimeridian/radial axes of the bow-tie on the anterior axial/sagittal map. Determine whether the superior and inferior lobes are aligned on one straight meridian or are SKEWED relative to each other. This is the SRA/SRAX question.
- If the two steep radial axes are visibly non-collinear/skewed, set srax=YES and estimate srax_deg from the angular separation when the image permits a defensible measurement.
- If the axes are clearly collinear, set srax=NO.
- If image quality does not permit the axis relationship to be judged, set srax=UNCERTAIN; do not silently set NO.
- A clearly visible skewed-axis pattern must be recorded in morphology_evidence even when an exact degree cannot be measured.

PUBLISHED ERSS TOPOGRAPHY CATEGORIES:
NORMAL_SYMMETRIC = 0 points.
ASYMMETRIC_BOWTIE = 1 point only when asymmetry is present WITHOUT qualifying SRA/SRAX or inferior-steepening criteria.
INFERIOR_STEEPENING_SRA = 3 points when significant SRA/SRAX is present (published threshold SRAX >=20 degrees), with or without inferior steepening, OR when the published qualifying inferior-steepening criterion is met.
ABNORMAL_ECTATIC = 4 points for an abnormal ectatic topographic pattern.
Therefore, if srax_deg is measured >=20 degrees, morphology MUST be INFERIOR_STEEPENING_SRA, not ASYMMETRIC_BOWTIE. If skew is visually present but the exact angle cannot be measured, do not falsely award 1 point as though SRA were absent: mark the topography category UNCERTAIN and explicitly state that SRAX requires quantification.

Across multiple images, one qualifying anterior-curvature map is sufficient. NO/NONE from BAD/elevation/pachymetry/topometric screens cannot override it.
"""

QUALIFYING={"AXIAL_SAGITTAL_FRONT","AXIAL","SAGITTAL","TANGENTIAL","PLACIDO","OTHER_CURVATURE"}
ROLE_FIELDS={"anterior_curvature_map_visible","anterior_curvature_map_type","anterior_curvature_map_location"}
def _qualifies(e): return e.get("anterior_curvature_map_visible")=="YES" and e.get("anterior_curvature_map_type") in QUALIFYING

def _enforce_srax(e):
    """Prevent a 1-point ABT classification from swallowing measured significant SRAX."""
    x=dict(e); deg=x.get("srax_deg"); srax=x.get("srax")
    try: d=float(deg) if deg is not None else None
    except (TypeError,ValueError): d=None
    if d is not None and d>=20.0:
        x["srax"]="YES"; x["morphology"]="INFERIOR_STEEPENING_SRA"
        ev=list(x.get("morphology_evidence") or []);ev.append(f"Significant skewed radial axes quantified on anterior curvature map: SRAX {d:g} degrees (>=20 degrees).")
        x["morphology_evidence"]=list(dict.fromkeys(ev))
    elif srax=="YES" and d is None and x.get("morphology")=="ASYMMETRIC_BOWTIE":
        # Visible skew cannot safely be demoted to the 1-point ABT bucket without quantification.
        x["morphology"]="UNCERTAIN"
        ev=list(x.get("morphology_evidence") or []);ev.append("Skewed radial axes are visible on anterior curvature map, but SRAX angle is not reliably quantified; do not assign the 1-point ABT category until SRAX is quantified.")
        x["morphology_evidence"]=list(dict.fromkeys(ev))
    return x

def merge_extractions_with_erss_source_guard(results):
    guarded=[]
    for result in results:
        copied=dict(result); copied_eyes=[]
        for raw in result.get("eyes",[]):
            e=_enforce_srax(raw)
            if not _qualifies(e):
                e["morphology"]="UNCERTAIN";e["asymmetric_bow_tie"]="UNCERTAIN";e["srax"]="UNCERTAIN";e["srax_deg"]=None;e["inferior_opposite_steepening_D"]=None
            copied_eyes.append(e)
        copied["eyes"]=copied_eyes;guarded.append(copied)
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
        eye_id=eye.get("eye");sources=[];source_eyes=[]
        for result in guarded:
            filename=(result.get("document_context") or {}).get("source_filename")
            for src in result.get("eyes",[]):
                if src.get("eye")==eye_id and _qualifies(src):
                    src=_enforce_srax(src);sources.append({"file":filename,"map_type":src.get("anterior_curvature_map_type"),"map_location":src.get("anterior_curvature_map_location"),"morphology":src.get("morphology"),"srax":src.get("srax"),"srax_deg":src.get("srax_deg")});source_eyes.append(src)
        eye["erss_topography_sources"]=sources;eye.setdefault("field_provenance",{})["erss_topography"]=sources;eye["erss_bad_dependency"]=False
        if sources:
            eye["anterior_curvature_map_visible"]="YES"
            # Prefer quantified significant SRAX, then another supported morphology, never a generic ABT over stronger evidence.
            best=next((s for s in source_eyes if s.get("srax_deg") is not None and float(s.get("srax_deg"))>=20),None) or next((s for s in source_eyes if s.get("morphology") not in (None,"UNCERTAIN")),source_eyes[0])
            best=_enforce_srax(best)
            for f in ("anterior_curvature_map_type","anterior_curvature_map_location","morphology","asymmetric_bow_tie","srax","srax_deg","inferior_opposite_steepening_D"):eye[f]=best.get(f)
            evidence=[x for x in (best.get("morphology_evidence") or []) if "BAD" not in str(x).upper() and "BELIN" not in str(x).upper()];evidence.append("Randleman/ERSS topography assessed from anterior curvature map only; BAD data are not part of this score.");eye["morphology_evidence"]=list(dict.fromkeys(evidence))
            eye["data_conflicts"]=[c for c in eye.get("data_conflicts",[]) if str(c).split(":",1)[0].strip() not in ROLE_FIELDS]
        else:
            eye["anterior_curvature_map_visible"]="NO";eye["anterior_curvature_map_type"]="NONE";eye["anterior_curvature_map_location"]="NONE";eye["morphology"]="UNCERTAIN";eye["asymmetric_bow_tie"]="UNCERTAIN";eye["srax"]="UNCERTAIN";eye["srax_deg"]=None;eye["inferior_opposite_steepening_D"]=None;eye["morphology_evidence"]=["Randleman/ERSS topography unavailable: no verified anterior curvature/topography source in the uploaded image set; BAD data are irrelevant."]
    return merged
core.merge_extractions=merge_extractions_with_erss_source_guard
