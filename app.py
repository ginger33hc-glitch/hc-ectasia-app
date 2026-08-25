import base64
import json
import mimetypes
import os
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

from reports import build_docx, build_pdf


app = FastAPI(title="HC Ectasia App v0.4")
app.mount("/static", StaticFiles(directory="static"), name="static")
client: Optional[OpenAI] = None
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")

EYES = ("OD", "OS")
MORPHOLOGY = (
    "NORMAL_SYMMETRIC",
    "ASYMMETRIC_BOWTIE",
    "INFERIOR_STEEPENING_SRA",
    "ABNORMAL_ECTATIC",
    "UNCERTAIN",
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "eyes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
                    "screen_types": {"type": "array", "items": {"type": "string"}},
                    "quality": {"type": "string", "enum": ["ADEQUATE", "LIMITED", "INADEQUATE"]},
                    "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
                    "K1_D": {"type": ["number", "null"]},
                    "K2_D": {"type": ["number", "null"]},
                    "Kmax_D": {"type": ["number", "null"]},
                    "pachy_thinnest_um": {"type": ["number", "null"]},
                    "BAD_D": {"type": ["number", "null"]},
                    "Df": {"type": ["number", "null"]},
                    "Db": {"type": ["number", "null"]},
                    "Dp": {"type": ["number", "null"]},
                    "Dt": {"type": ["number", "null"]},
                    "Da": {"type": ["number", "null"]},
                    "PPI_avg": {"type": ["number", "null"]},
                    "PPI_max": {"type": ["number", "null"]},
                    "ARTmax_um": {"type": ["number", "null"]},
                    "ISV": {"type": ["number", "null"]},
                    "IVA": {"type": ["number", "null"]},
                    "KI": {"type": ["number", "null"]},
                    "CKI": {"type": ["number", "null"]},
                    "IHD": {"type": ["number", "null"]},
                    "I_S": {"type": ["number", "null"]},
                    "KISA": {"type": ["number", "null"]},
                    "morphology": {"type": "string", "enum": list(MORPHOLOGY)},
                    "morphology_evidence": {"type": "array", "items": {"type": "string"}},
                    "asymmetric_bow_tie": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "srax": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "srax_deg": {"type": ["number", "null"]},
                    "posterior_pattern": {
                        "type": "string",
                        "enum": ["REASSURING", "BORDERLINE", "ABNORMAL", "UNREADABLE"],
                    },
                },
                "required": [
                    "eye", "screen_types", "quality", "missing_or_unreadable", "K1_D", "K2_D",
                    "Kmax_D", "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da",
                    "PPI_avg", "PPI_max", "ARTmax_um", "ISV", "IVA", "KI", "CKI", "IHD",
                    "I_S", "KISA", "morphology", "morphology_evidence", "asymmetric_bow_tie",
                    "srax", "srax_deg", "posterior_pattern",
                ],
            },
        },
        "global_warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["eyes", "global_warnings"],
}

PROMPT = """You are a data-extraction component for Pentacam corneal tomography photographs.
Extract only values visibly supported by the supplied image. Never guess an unreadable or absent
number. Identify OD/OS and screen type. Return null for unreadable/absent numeric values and list
them in missing_or_unreadable. Classify the visible Placido/topographic morphology using exactly
one of: NORMAL_SYMMETRIC, ASYMMETRIC_BOWTIE, INFERIOR_STEEPENING_SRA,
ABNORMAL_ECTATIC, UNCERTAIN. ABNORMAL_ECTATIC is reserved for a clearly visible keratoconus,
forme-fruste keratoconus, pellucid/ectatic pattern; do not infer it from one isolated index.
INFERIOR_STEEPENING_SRA requires visible inferior steepening or skewed radial axis. Record short
visible reasons in morphology_evidence. If the relevant map is not sufficiently visible, use
UNCERTAIN. Do not make a surgical recommendation. Do not calculate or infer missing BAD-D,
component D values, ARTmax, or other indices from related measurements. Treat this as strict
transcription and structured image interpretation, not autonomous diagnosis."""


def data_url(raw: bytes, filename: str) -> str:
    mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def openai_client() -> OpenAI:
    global client
    if client is None:
        client = OpenAI()
    return client


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def tri(value: Any) -> str:
    return value if value in ("yes", "no", "unknown") else "unknown"


def combine_status(current: str, new: str) -> str:
    rank = {
        "PASS": 0,
        "POST-REFRACTIVE PATHWAY REQUIRED": 1,
        "DATA INSUFFICIENT": 2,
        "REVIEW — NOT CLEARED": 3,
        "CAUTION — STOP/DEFER": 4,
        "DO NOT PROCEED": 5,
    }
    return new if rank[new] > rank[current] else current


def bad_classification(value: Optional[float], final: bool = False) -> str:
    if not is_number(value):
        return "UNAVAILABLE"
    if final:
        if value <= 1.6:
            return "NORMAL"
        if value < 3.0:
            return "SUSPICIOUS"
        return "ABNORMAL"
    if value < 1.6:
        return "NORMAL"
    if value < 2.6:
        return "SUSPICIOUS"
    return "ABNORMAL"


def lasik_topography_points(morphology: str) -> Optional[int]:
    return {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 1,
        "INFERIOR_STEEPENING_SRA": 3,
        "ABNORMAL_ECTATIC": 4,
    }.get(morphology)


def scoring_morphology(eye: Dict[str, Any]) -> Dict[str, Any]:
    """Apply published ERSS Placido definitions without declaring disease from one index."""
    category = eye.get("morphology", "UNCERTAIN")
    evidence = list(eye.get("morphology_evidence", []))
    i_s = eye.get("I_S")
    srax_deg = eye.get("srax_deg")
    if is_number(i_s) and i_s >= 1.4:
        category = "ABNORMAL_ECTATIC"
        evidence.append("Published Placido-era ERSS abnormal-pattern criterion: I-S >=1.4 D.")
    elif eye.get("srax") == "YES" or (is_number(srax_deg) and srax_deg >= 20):
        category = "INFERIOR_STEEPENING_SRA"
        evidence.append("Published ERSS SRA/SRAX category supported (SRA >=20 degrees or visible SRA).")
    elif eye.get("asymmetric_bow_tie") == "YES" and category == "NORMAL_SYMMETRIC":
        category = "ASYMMETRIC_BOWTIE"
        evidence.append("Visible asymmetric bowtie category reported.")
    return {"category": category, "evidence": list(dict.fromkeys(evidence))}


def lasik_rsb_points(rsb: Optional[float]) -> Optional[int]:
    if not is_number(rsb):
        return None
    if rsb < 240:
        return 4
    if rsb < 260:
        return 3
    if rsb < 280:
        return 2
    if rsb < 300:
        return 1
    return 0


def age_points(age: Optional[int]) -> Optional[int]:
    if not is_number(age) or age < 18:
        return None
    if age <= 21:
        return 3
    if age <= 25:
        return 2
    if age <= 29:
        return 1
    return 0


def lasik_pachy_points(pachy: Optional[float]) -> Optional[int]:
    if not is_number(pachy):
        return None
    # The printed ERSS table leaves 450 µm unstated and places 510 µm on
    # conflicting/overlapping boundaries. Do not silently adjudicate either.
    if pachy in (450, 510):
        return None
    if pachy < 450:
        return 4
    if pachy <= 480:
        return 3
    if pachy <= 510:
        return 2
    return 0


def lasik_mrse_points(mrse: Optional[float]) -> Optional[int]:
    if not is_number(mrse):
        return None
    if mrse < -14:
        return 4
    if mrse < -12:
        return 3
    if mrse < -10:
        return 2
    if mrse < -8:
        return 1
    return 0


def prk_morphology_points(morphology: str) -> Optional[int]:
    return {
        "NORMAL_SYMMETRIC": 0,
        "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 5,
        # A numeric Placido abnormal-pattern criterion yields high concern but
        # is not, by itself, relabeled as a definite-disease override.
        "ABNORMAL_ECTATIC": 5,
    }.get(morphology)


def prk_pachy_points(pachy: Optional[float]) -> Optional[int]:
    if not is_number(pachy):
        return None
    if pachy <= 450:
        return 4
    if pachy <= 480:
        return 3
    if pachy <= 510:
        return 2
    return 0


def score_category(procedure: str, score: int) -> str:
    if procedure == "LASIK":
        if score <= 2:
            return "LOW"
        if score == 3:
            return "MODERATE"
        return "HIGH"
    if score <= 1:
        return "LOWER_FLAGGED_BURDEN"
    if score <= 3:
        return "CAUTION"
    return "HIGH_CONCERN"


def tomography_review(eye: Dict[str, Any]) -> Dict[str, Any]:
    bad = {"BAD_D": bad_classification(eye.get("BAD_D"), final=True)}
    for key in ("Df", "Db", "Dp", "Dt", "Da"):
        bad[key] = bad_classification(eye.get(key))

    flags: List[str] = []
    if is_number(eye.get("ARTmax_um")) and eye["ARTmax_um"] <= 424:
        flags.append("ARTmax <=424 µm: cross-sectional subclinical-KC concern flag.")
    if is_number(eye.get("pachy_thinnest_um")) and eye["pachy_thinnest_um"] <= 544:
        flags.append("Thinnest pachymetry <=544 µm: cross-sectional phenotype flag, not an exclusion cutoff.")
    if is_number(eye.get("Dt")) and eye["Dt"] >= -0.165:
        flags.append("BAD-Dt >=-0.165: cross-sectional subclinical-KC concern flag.")
    if is_number(eye.get("Da")) and eye["Da"] >= 0.585:
        flags.append("BAD-Da >=0.585: cross-sectional subclinical-KC concern flag.")

    display_values = list(bad.values())
    if "ABNORMAL" in display_values or eye.get("posterior_pattern") == "ABNORMAL":
        status = "ABNORMAL"
    elif "SUSPICIOUS" in display_values or eye.get("posterior_pattern") == "BORDERLINE":
        status = "SUSPICIOUS"
    elif "UNAVAILABLE" in display_values or eye.get("posterior_pattern") == "UNREADABLE":
        status = "INCOMPLETE"
    else:
        status = "REASSURING"

    return {
        "status": status,
        "BAD_display": bad,
        "cross_sectional_flags": flags,
        "evidence_note": (
            "BAD and ARTmax/TP/Dt/Da thresholds are adjunctive diagnostic/review signals; "
            "they are not independently validated predictors of post-refractive ectasia."
        ),
    }


def estimate_ablation(plan: Dict[str, Any], warnings: List[str]) -> Optional[float]:
    ablation = plan.get("ablation_um")
    if is_number(ablation):
        return float(ablation)
    sphere = plan.get("sphere_D")
    cylinder = plan.get("cylinder_magnitude_D")
    optical_zone = plan.get("optical_zone_mm")
    platform = str(plan.get("laser_platform") or "").lower().replace(" ", "")
    hc_estimate_applicable = "alcon" in platform and "ex500" in platform and optical_zone == 6.0
    if is_number(sphere) and is_number(cylinder) and hc_estimate_applicable:
        warnings.append(
            "Maximum ablation estimated with the HC Alcon EX500, 6.0-mm-zone, 12 µm/D convention; "
            "actual laser-plan maximum is preferred."
        )
        return (abs(float(sphere)) + abs(float(cylinder))) * 12.0
    if is_number(sphere) and is_number(cylinder):
        warnings.append(
            "HC 12 µm/D ablation estimate was not applied because Alcon EX500 and a 6.0-mm optical zone "
            "were not both explicitly documented."
        )
    return None


def required_tomography_missing(eye: Dict[str, Any]) -> List[str]:
    required = (
        "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da", "ARTmax_um", "PPI_max"
    )
    missing = [key for key in required if not is_number(eye.get(key))]
    derived = scoring_morphology(eye)["category"]
    if derived not in MORPHOLOGY or derived == "UNCERTAIN":
        missing.append("classifiable topographic morphology")
    if eye.get("posterior_pattern") in (None, "UNREADABLE"):
        missing.append("readable posterior pattern")
    if eye.get("quality") == "INADEQUATE":
        missing.append("adequate-quality tomography/topography")
    return missing


def assess_eye(
    eye: Dict[str, Any],
    plan: Dict[str, Any],
    age: Optional[int],
    patient_modifiers: Dict[str, Any],
) -> Dict[str, Any]:
    eye_id = eye.get("eye", "UNKNOWN")
    procedure = plan.get("procedure")
    warnings: List[str] = []
    reasons: List[str] = []
    hard_stops: List[str] = []
    missing: List[str] = []
    modifiers: List[str] = []
    status = "PASS"

    prior = tri(plan.get("prior"))
    stable = tri(plan.get("stable"))
    progression = tri(plan.get("progression"))
    cdva = tri(plan.get("cdva_below_20_20"))
    eye_rubbing = tri(patient_modifiers.get("eye_rubbing"))
    family_history = tri(patient_modifiers.get("family_history"))
    inter_eye = tri(patient_modifiers.get("inter_eye_asymmetry"))

    if eye_id not in EYES:
        missing.append("reliable OD/OS identification")
    if procedure not in ("PRK", "LASIK"):
        missing.append("procedure")
    if prior == "unknown":
        missing.append("prior corneal refractive surgery status")
    if not is_number(age):
        missing.append("age")
    elif age < 18:
        missing.append("age within the published scoring range (>=18 years)")
    if not is_number(plan.get("sphere_D")):
        missing.append("intended sphere")
    if not is_number(plan.get("cylinder_magnitude_D")):
        missing.append("cylinder magnitude")
    if stable == "unknown":
        missing.append("refractive stability")
    if progression == "unknown":
        missing.append("documented progression status")
    if cdva == "unknown":
        missing.append("unexplained CDVA <20/20 status")
    if eye_rubbing == "unknown":
        missing.append("eye-rubbing/ocular-trauma history")
    if family_history == "unknown":
        missing.append("family history of keratoconus")
    if inter_eye == "unknown" and len(patient_modifiers.get("assessed_eyes", [])) > 1:
        missing.append("marked inter-eye asymmetry status")
    if not is_number(plan.get("optical_zone_mm")):
        missing.append("planned optical zone")
    if not str(plan.get("laser_platform") or "").strip():
        missing.append("laser platform")
    if not is_number(plan.get("transition_zone_mm")) and tri(plan.get("transition_zone_not_applicable")) != "yes":
        missing.append("planned transition zone or explicit not-applicable status")
    if tri(plan.get("enhancement_anticipated")) == "unknown":
        missing.append("anticipated enhancement status")
    missing.extend(required_tomography_missing(eye))

    pachy = eye.get("pachy_thinnest_um") if is_number(eye.get("pachy_thinnest_um")) else None
    ablation = estimate_ablation(plan, warnings)
    if ablation is None:
        missing.append("maximum stromal ablation depth or inputs for HC estimate")

    flap = plan.get("flap_um")
    if procedure == "LASIK" and not is_number(flap):
        missing.append("planned LASIK flap thickness")

    rst = pachy - 50 - ablation if procedure == "PRK" and pachy is not None and ablation is not None else None
    rsb = (
        pachy - flap - ablation
        if procedure == "LASIK" and pachy is not None and is_number(flap) and ablation is not None
        else None
    )
    prk_pta = (
        (50 + ablation) / pachy * 100
        if procedure == "PRK" and pachy and ablation is not None
        else None
    )
    lasik_pta = (
        (flap + ablation) / pachy * 100
        if procedure == "LASIK" and pachy and is_number(flap) and ablation is not None
        else None
    )
    surgical_load_flags: List[str] = []
    if procedure == "PRK" and prk_pta is not None and prk_pta > 35.28:
        surgical_load_flags.append(
            "PRK PTA >35.28% lies outside the most reassuring supplied 2-year direct-cohort envelope; "
            "this is an evidence-gap flag, not proof of harm."
        )

    sphere = plan.get("sphere_D")
    cylinder = plan.get("cylinder_magnitude_D")
    mrse = sphere - cylinder / 2 if is_number(sphere) and is_number(cylinder) else None
    visible_morphology = eye.get("morphology", "UNCERTAIN")
    derived_morphology = scoring_morphology(eye)
    morphology = derived_morphology["category"]
    tomo = tomography_review(eye)

    if prior == "yes":
        status = combine_status(status, "POST-REFRACTIVE PATHWAY REQUIRED")
        reasons.append("Prior corneal refractive surgery requires a separate post-refractive pathway.")

    if pachy is not None and pachy < 480:
        hard_stops.append("HC operational hard stop: thinnest preoperative cornea <480 µm.")
    if is_number(sphere) and sphere < -10:
        hard_stops.append("HC operational myopic treatment cutoff: intended sphere <-10.00 D.")
    if is_number(sphere) and sphere > 6:
        hard_stops.append("HC operational hyperopic treatment cutoff: intended sphere >+6.00 D.")
    if procedure == "PRK" and rst is not None and rst < 310:
        hard_stops.append("HC operational PRK RST hard stop: RST <310 µm.")
    if procedure == "LASIK" and rsb is not None and rsb < 300:
        hard_stops.append("HC operational LASIK RSB hard stop: RSB <300 µm.")
    if visible_morphology == "ABNORMAL_ECTATIC":
        hard_stops.append("Definite KC/FFKC/PMD or unequivocal ectatic morphology override.")

    if hard_stops:
        status = "DO NOT PROCEED"
        reasons.extend(hard_stops)

    if stable == "no" or progression == "yes":
        status = combine_status(status, "CAUTION — STOP/DEFER")
        reasons.append("Refractive instability or documented progression: defer and re-evaluate after >=6 months.")
    if cdva == "yes":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append("Unexplained preoperative CDVA <20/20 requires investigation.")
    if eye_rubbing == "yes":
        modifiers.append("Chronic eye rubbing/repetitive ocular trauma present.")
    if family_history == "yes":
        modifiers.append("Family history of keratoconus present.")
    if inter_eye == "yes":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        modifiers.append("Marked inter-eye asymmetry requires escalated review.")

    score_rows: Dict[str, Any] = {}
    score_total: Optional[int] = None
    category: Optional[str] = None

    if procedure == "LASIK":
        score_rows = {
            "topography": lasik_topography_points(morphology),
            "RSB": lasik_rsb_points(rsb),
            "age": age_points(age),
            "pachymetry": lasik_pachy_points(pachy),
            "MRSE": lasik_mrse_points(mrse),
        }
        if pachy in (450, 510):
            missing.append(
                f"LASIK ERSS pachymetry at exactly {int(pachy)} µm requires documented boundary adjudication"
            )
        if all(is_number(value) for value in score_rows.values()):
            score_total = int(sum(score_rows.values()))
            category = score_category("LASIK", score_total)
            if category == "HIGH":
                status = combine_status(status, "DO NOT PROCEED")
                reasons.append("Validated LASIK ERSS high-risk category (score >=4).")
            elif category == "MODERATE":
                status = combine_status(status, "CAUTION — STOP/DEFER")
                reasons.append(
                    "Validated LASIK ERSS moderate-risk category (score 3): defer and re-evaluate after >=6 months."
                )
        if mrse is not None and mrse > 0:
            status = combine_status(status, "REVIEW — NOT CLEARED")
            reasons.append(
                "The supplied LASIK ERSS validation evidence is myopic; hyperopic applicability is not established."
            )
    elif procedure == "PRK":
        score_rows = {
            "morphology": prk_morphology_points(morphology),
            "pachymetry": prk_pachy_points(pachy),
            "age": age_points(age),
        }
        if visible_morphology != "ABNORMAL_ECTATIC" and all(is_number(value) for value in score_rows.values()):
            score_total = int(sum(score_rows.values()))
            category = score_category("PRK", score_total)
            if category == "HIGH_CONCERN":
                status = combine_status(status, "DO NOT PROCEED")
                reasons.append("PRK-EWSS v1.0 provisional high-concern category (score >=4).")
            elif category == "CAUTION":
                status = combine_status(status, "CAUTION — STOP/DEFER")
                reasons.append(
                    "PRK-EWSS v1.0 provisional caution category (score 2-3): defer and re-evaluate after >=6 months."
                )

    if tomo["status"] == "ABNORMAL" and visible_morphology != "ABNORMAL_ECTATIC":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append("Abnormal adjunctive tomography display: morphology/clinical concordance review required.")
    elif tomo["status"] == "SUSPICIOUS":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append("Suspicious adjunctive tomography display: repeat/confirm and review concordance.")

    if missing:
        if not hard_stops:
            status = combine_status(status, "DATA INSUFFICIENT")
        reasons.append("Decision-critical or required clinical data are missing/unresolved; PASS is prohibited.")

    if status == "PASS":
        reasons.append(
            "Override gate negative; procedure-specific score and required tomography/clinical review are reassuring."
        )

    return {
        "eye": eye_id,
        "status": status,
        "action": (
            "STOP/DEFER; repeat relevant ectasia screening and reassess after at least 6 months."
            if status == "CAUTION — STOP/DEFER"
            else "DO NOT PROCEED with elective corneal refractive surgery."
            if status == "DO NOT PROCEED"
            else "No surgical clearance; resolve the stated review/data requirement."
            if status != "PASS"
            else "HC assessment PASS; this is not a guarantee of zero ectasia risk."
        ),
        "reasons": list(dict.fromkeys(reasons)),
        "hard_stops": hard_stops,
        "missing": sorted(set(missing)),
        "warnings": list(dict.fromkeys(warnings)),
        "clinical_modifiers": modifiers,
        "surgical_load_flags": surgical_load_flags,
        "instrument": (
            "LASIK ERSS validated case-control score"
            if procedure == "LASIK"
            else "PRK-EWSS v1.0 provisional evidence-weighted triage score; not validated"
            if procedure == "PRK"
            else None
        ),
        "score": {"rows": score_rows, "total": score_total, "category": category},
        "topography_classification": {
            "image_category": visible_morphology,
            "scoring_category": morphology,
            "evidence": derived_morphology["evidence"],
            "note": "Numeric ERSS category support does not, by itself, constitute a keratoconus diagnosis.",
        },
        "values": {
            "procedure": procedure,
            "age_years": age,
            "sphere_D": sphere,
            "cylinder_magnitude_D": cylinder,
            "MRSE_D": mrse,
            "pachy_thinnest_um": pachy,
            "max_ablation_um": ablation,
            "PRK_RST_um": rst,
            "PRK_PTA_percent": prk_pta,
            "LASIK_RSB_um": rsb,
            "LASIK_PTA_percent": lasik_pta,
            "optical_zone_mm": plan.get("optical_zone_mm"),
            "transition_zone_mm": plan.get("transition_zone_mm"),
            "transition_zone_not_applicable": tri(plan.get("transition_zone_not_applicable")),
            "laser_platform": plan.get("laser_platform"),
            "enhancement_anticipated": tri(plan.get("enhancement_anticipated")),
        },
        "tomography_review": tomo,
        "evidence_boundaries": {
            "HC_policy": [
                "CCT <480 µm is a hard stop; exactly 480 µm is not stopped by that rule alone.",
                "LASIK RSB <300 µm and PRK RST <310 µm are HC operational hard stops.",
                "PRK epithelial thickness is standardized to 50 µm for HC calculations.",
            ],
            "literature_limit": (
                "The supplied evidence does not validate 310 µm as a universal safe PRK cutoff; "
                "it was the minimum observed RST in a 408-eye, 2-year retrospective cohort."
            ),
        },
    }


def hc_engine(
    extracted: Dict[str, Any],
    age: Optional[int],
    eye_plans: Dict[str, Dict[str, Any]],
    patient_modifiers: Dict[str, Any],
) -> Dict[str, Any]:
    extracted_eyes = [eye for eye in extracted.get("eyes", []) if isinstance(eye, dict)]
    assessed_ids = [eye.get("eye") for eye in extracted_eyes if eye.get("eye") in EYES]
    patient_modifiers = dict(patient_modifiers)
    patient_modifiers["assessed_eyes"] = assessed_ids

    results = []
    for eye in extracted_eyes:
        eye_id = eye.get("eye", "UNKNOWN")
        results.append(assess_eye(eye, eye_plans.get(eye_id, {}), age, patient_modifiers))

    if not results:
        return {
            "status": "DATA INSUFFICIENT",
            "action": "No eye-specific assessment could be completed.",
            "eyes": [],
            "warnings": extracted.get("global_warnings", []),
        }

    overall = "PASS"
    for result in results:
        overall = combine_status(overall, result["status"])

    return {
        "status": overall,
        "action": "Overall result reflects the least favorable eye. Each eye remains independently scored; values are never averaged.",
        "eyes": results,
        "warnings": extracted.get("global_warnings", []),
        "protocol": "HC Preoperative Ectasia Risk Assessment for Corneal Refractive Surgery",
        "version": "software v0.4 / source set 2026-08-24 plus binding HC amendments",
    }


def merge_extractions(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {"eyes": [], "global_warnings": []}
    by_eye: Dict[str, Dict[str, Any]] = {}
    conservative = {
        "pachy_thinnest_um": "min", "BAD_D": "max", "Df": "max", "Db": "max",
        "Dp": "max", "Dt": "max", "Da": "max", "ARTmax_um": "min", "PPI_max": "max",
    }
    morphology_rank = {
        "UNCERTAIN": 0, "NORMAL_SYMMETRIC": 1, "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 3, "ABNORMAL_ECTATIC": 4,
    }
    quality_rank = {"INADEQUATE": 0, "LIMITED": 1, "ADEQUATE": 2}
    posterior_rank = {"UNREADABLE": 0, "REASSURING": 1, "BORDERLINE": 2, "ABNORMAL": 3}

    for result in results:
        merged["global_warnings"].extend(result.get("global_warnings", []))
        for eye in result.get("eyes", []):
            eye_id = eye.get("eye", "UNKNOWN")
            if eye_id not in by_eye:
                by_eye[eye_id] = dict(eye)
                continue
            target = by_eye[eye_id]
            target["screen_types"] = sorted(set(target.get("screen_types", []) + eye.get("screen_types", [])))
            target["morphology_evidence"] = list(
                dict.fromkeys(target.get("morphology_evidence", []) + eye.get("morphology_evidence", []))
            )
            if quality_rank.get(eye.get("quality"), 0) > quality_rank.get(target.get("quality"), 0):
                target["quality"] = eye.get("quality")

            for key, value in eye.items():
                if key in ("eye", "screen_types", "quality", "missing_or_unreadable", "morphology_evidence"):
                    continue
                old = target.get(key)
                if old is None and value is not None:
                    target[key] = value
                    continue
                if value is None or old == value:
                    continue
                if key in conservative and is_number(old) and is_number(value):
                    target[key] = min(old, value) if conservative[key] == "min" else max(old, value)
                    merged["global_warnings"].append(
                        f"Conflicting {key} values for {eye_id}; conservative limiting value retained."
                    )
                elif key == "morphology":
                    target[key] = max((old, value), key=lambda item: morphology_rank.get(item, 0))
                    merged["global_warnings"].append(
                        f"Conflicting morphology classifications for {eye_id}; more concerning visible category retained."
                    )
                elif key == "posterior_pattern":
                    target[key] = max((old, value), key=lambda item: posterior_rank.get(item, 0))
                elif key in ("asymmetric_bow_tie", "srax"):
                    if "YES" in (old, value):
                        target[key] = "YES"
                    elif "UNCERTAIN" in (old, value):
                        target[key] = "UNCERTAIN"
                    else:
                        target[key] = "NO"
                elif old != value:
                    merged["global_warnings"].append(
                        f"Conflicting {key} values for {eye_id}: {old} vs {value}; first value retained."
                    )

    for eye in by_eye.values():
        eye["missing_or_unreadable"] = sorted(
            set(key for key in eye.get("missing_or_unreadable", []) if eye.get(key) is None)
        )

    merged["eyes"] = list(by_eye.values())
    merged["global_warnings"] = sorted(set(merged["global_warnings"]))
    return merged


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.post("/report/pdf")
def report_pdf(payload: Dict[str, Any] = Body(...)) -> StreamingResponse:
    content = build_pdf(payload)
    return StreamingResponse(
        BytesIO(content), media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="HC_Ectasia_Report.pdf"'},
    )


@app.post("/report/word")
def report_word(payload: Dict[str, Any] = Body(...)) -> StreamingResponse:
    content = build_docx(payload)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="HC_Ectasia_Report.docx"'},
    )


@app.post("/analyze")
async def analyze(
    images: List[UploadFile] = File(...),
    age: Optional[int] = Form(None),
    eye_plans: str = Form("{}"),
    patient_modifiers: str = Form("{}"),
):
    if not images:
        raise HTTPException(400, "No images supplied.")
    try:
        plans = json.loads(eye_plans)
        modifiers = json.loads(patient_modifiers)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid structured clinical input: {exc}") from exc
    if not isinstance(plans, dict) or not isinstance(modifiers, dict):
        raise HTTPException(400, "eye_plans and patient_modifiers must be JSON objects.")

    extraction_results = []
    for image in images:
        raw = await image.read()
        if not raw:
            continue
        content = [
            {"type": "input_text", "text": PROMPT},
            {
                "type": "input_image",
                "image_url": data_url(raw, image.filename or "image.jpg"),
                "detail": "original",
            },
        ]
        response = openai_client().responses.create(
            model=MODEL,
            store=False,
            reasoning={"effort": "low"},
            input=[{"role": "user", "content": content}],
            text={
                "format": {
                    "type": "json_schema", "name": "pentacam_extraction",
                    "strict": True, "schema": SCHEMA,
                }
            },
        )
        output_text = response.output_text
        print(
            "OPENAI DEBUG:", "status=", getattr(response, "status", None),
            "incomplete_details=", getattr(response, "incomplete_details", None),
            "output_length=", len(output_text or ""),
            "output_preview=", repr((output_text or "")[:300]), flush=True,
        )
        if not output_text or not output_text.strip():
            raise RuntimeError(
                "OpenAI returned empty output_text. "
                f"status={getattr(response, 'status', None)}, "
                f"incomplete_details={getattr(response, 'incomplete_details', None)}"
            )
        try:
            extraction_results.append(json.loads(output_text))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"OpenAI output was not valid JSON: {exc}; preview={output_text[:300]!r}"
            ) from exc

    if not extraction_results:
        raise HTTPException(400, "No readable images supplied.")
    extracted = merge_extractions(extraction_results)
    return {
        "extracted": extracted,
        "decision": hc_engine(extracted, age, plans, modifiers),
    }
