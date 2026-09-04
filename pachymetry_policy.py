"""CER-AI pachymetry policy patch.

CER-AI policy:
- thinnest pachymetry <=480 µm: hard stop
- 481-499 µm: 2 points
- 500-509 µm: 1 point
- >=510 µm: 0 points

The 480 µm boundary is inclusive and is an operational CER-AI hard stop.
"""
import bootstrap

core = bootstrap.core

def hc_lasik_pachy_points(pachy):
    if not core.is_number(pachy): return None
    value=float(pachy)
    if value <= 480: return None
    if value < 500: return 2
    if value < 510: return 1
    return 0

core.lasik_pachy_points=hc_lasik_pachy_points
_previous_assess_eye=core.assess_eye

def assess_eye_with_hc_pachymetry(eye,plan,age,patient_modifiers):
    original_pachy=eye.get("pachy_thinnest_um");working_eye=eye
    if core.is_number(original_pachy) and float(original_pachy)==510.0:
        working_eye=dict(eye);working_eye["pachy_thinnest_um"]=510.000001
    result=_previous_assess_eye(working_eye,plan,age,patient_modifiers)
    if result.get("status")=="POST-REFRACTIVE PATHWAY REQUIRED": return result
    if core.is_number(original_pachy):
        value=float(original_pachy);result.setdefault("values",{})["pachy_thinnest_um"]=original_pachy
        if value <= 480:
            stop="CER-AI operational hard stop: thinnest preoperative cornea <=480 µm."
            hard=[x for x in list(result.get("hard_stops") or []) if "thinnest preoperative cornea" not in str(x)]
            if stop not in hard: hard.append(stop)
            result["hard_stops"]=hard
            reasons=[x for x in list(result.get("reasons") or []) if "thinnest preoperative cornea" not in str(x)]
            if stop not in reasons: reasons.insert(0,stop)
            result["reasons"]=list(dict.fromkeys(reasons));result["status"]="STOP-DEFER";result["action"]="STOP-DEFER; do not proceed with elective corneal refractive surgery."
        if result.get("values",{}).get("procedure")=="LASIK":
            score=result.get("score") or {}
            if value <= 480: score.setdefault("rows",{})["pachymetry"]=None
            result["score"]=score;warnings=list(result.get("warnings") or []);warnings.append("CER-AI-MODIFIED LASIK PACHYMETRY POLICY: <=480 µm = hard stop; 481-499 µm = +2; 500-509 µm = +1; >=510 µm = +0.");result["warnings"]=list(dict.fromkeys(warnings))
    return result

core.assess_eye=assess_eye_with_hc_pachymetry
app=bootstrap.app
