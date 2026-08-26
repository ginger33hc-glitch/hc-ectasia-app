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


app = FastAPI(title="HC Ectasia App v0.5")
app.mount("/static", StaticFiles(directory="static"), name="static")
client: Optional[OpenAI] = None
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-terra")

EYES = ("OD", "OS")
PRK_EPITHELIUM_UM = 50
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
                    "PPI_min": {"type": ["number", "null"]},
                    "PPI_max": {"type": ["number", "null"]},
                    "ARTmax_um": {"type": ["number", "null"]},
                    "ISV": {"type": ["number", "null"]},
                    "IVA": {"type": ["number", "null"]},
                    "KI": {"type": ["number", "null"]},
                    "CKI": {"type": ["number", "null"]},
                    "IHD": {"type": ["number", "null"]},
                    "I_S": {"type": ["number", "null"]},
                    "KISA": {"type": ["number", "null"]},
                    "IHA": {"type": ["number", "null"]},
                    "Rmin_mm": {"type": ["number", "null"]},
                    "anterior_elevation_thinnest_um": {"type": ["number", "null"]},
                    "posterior_elevation_thinnest_um": {"type": ["number", "null"]},
                    "thinnest_x_mm": {"type": ["number", "null"]},
                    "thinnest_y_mm": {"type": ["number", "null"]},
                    "corneal_volume_mm3": {"type": ["number", "null"]},
                    "RMS_HOA_um": {"type": ["number", "null"]},
                    "vertical_coma_um": {"type": ["number", "null"]},
                    "morphology": {"type": "string", "enum": list(MORPHOLOGY)},
                    "morphology_evidence": {"type": "array", "items": {"type": "string"}},
                    "asymmetric_bow_tie": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "srax": {"type": "string", "enum": ["YES", "NO", "UNCERTAIN"]},
                    "srax_deg": {"type": ["number", "null"]},
                    "inferior_opposite_steepening_D": {"type": ["number", "null"]},
                    "anterior_pattern": {
                        "type": "string",
                        "enum": ["REASSURING", "BORDERLINE", "ABNORMAL", "UNREADABLE"],
                    },
                    "posterior_pattern": {
                        "type": "string",
                        "enum": ["REASSURING", "BORDERLINE", "ABNORMAL", "UNREADABLE"],
                    },
                },
                "required": [
                    "eye", "screen_types", "quality", "missing_or_unreadable", "K1_D", "K2_D",
                    "Kmax_D", "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da",
                    "PPI_avg", "PPI_min", "PPI_max", "ARTmax_um", "ISV", "IVA", "KI", "CKI", "IHD",
                    "I_S", "KISA", "IHA", "Rmin_mm", "anterior_elevation_thinnest_um",
                    "posterior_elevation_thinnest_um", "thinnest_x_mm", "thinnest_y_mm",
                    "corneal_volume_mm3", "RMS_HOA_um", "vertical_coma_um", "morphology",
                    "morphology_evidence", "asymmetric_bow_tie", "srax", "srax_deg",
                    "inferior_opposite_steepening_D",
                    "anterior_pattern", "posterior_pattern",
                ],
            },
        },
        "treatment_corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
                    "source_document": {
                        "type": "string",
                        "enum": ["EXCIMER_LASER_FOLLOW_UP_CARD", "OTHER", "UNKNOWN"],
                    },
                    "source_label": {
                        "type": "string",
                        "enum": ["DUZELTME_MIKTARI", "OTHER", "UNREADABLE"],
                    },
                    "sphere_D": {"type": ["number", "null"]},
                    "cylinder_D": {"type": ["number", "null"]},
                    "axis_deg": {"type": ["number", "null"]},
                    "sphere_cylinder_status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE"],
                    },
                    "axis_status": {
                        "type": "string",
                        "enum": ["CONFIDENT", "UNCERTAIN", "UNREADABLE"],
                    },
                    "raw_text": {"type": ["string", "null"]},
                    "missing_or_unreadable": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "eye", "source_document", "source_label", "sphere_D", "cylinder_D",
                    "axis_deg", "sphere_cylinder_status", "axis_status", "raw_text",
                    "missing_or_unreadable",
                ],
            },
        },
        "global_warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["eyes", "treatment_corrections", "global_warnings"],
}

PROMPT = """You are a strict data-extraction component for preoperative corneal-refractive-surgery images.
The image may be a Pentacam/topography screen, an Excimer Laser Follow-up Card (Excimer Laser Takip
Karti), or another clinical document. Extract only values visibly supported by the supplied image.
Never guess an unreadable or absent
number. Identify OD/OS and screen type. Return null for unreadable/absent numeric values and list
them in missing_or_unreadable. Classify the visible Placido/topographic morphology using exactly
one of: NORMAL_SYMMETRIC, ASYMMETRIC_BOWTIE, INFERIOR_STEEPENING_SRA,
ABNORMAL_ECTATIC, UNCERTAIN. Transcribe visible anterior/posterior elevation-at-thinnest-point,
thinnest-point location, pachymetric-progression, topometric, corneal-volume, and HOA/coma values
when they are printed; otherwise return null. Classify both visible anterior and posterior maps as
REASSURING, BORDERLINE, ABNORMAL, or UNREADABLE. ABNORMAL_ECTATIC is reserved for a clearly visible keratoconus,
forme-fruste keratoconus, pellucid/ectatic pattern; do not infer it from one isolated index.
Extract K1_D, K2_D, and Kmax_D only from explicitly labeled K1, K2, and Kmax summary-table fields.
Never use a numeric spot label printed inside a curvature map as K1, K2, or Kmax. If the labeled
summary field is not visible, return null for that field. Classify morphology only when an axial,
sagittal, tangential, or Placido curvature/topography map is actually visible. A BAD display without
such a curvature map does not support a morphology classification; use UNCERTAIN for morphology,
asymmetric_bow_tie, and srax on that image rather than inferring them from elevation or pachymetry.
Apply the published Placido-era ERSS morphology definitions strictly. A small or merely nonzero axis
deviation is not SRAX/SRA. Set srax=YES and use INFERIOR_STEEPENING_SRA only when the image
supports a skewed radial axis of at least 20 degrees. srax_deg is the angular separation of the two
principal hemi-meridians; it is not the cylinder axis and not deviation from the horizontal or vertical
meridian. Alternatively, INFERIOR_STEEPENING_SRA may be used when there is at least 1.0 D of
inferior steepening versus the region 180 degrees opposite the steepest region and the printed I-S is
less than 1.4 D. Record that regional difference only in inferior_opposite_steepening_D. Do not infer
either numeric criterion from a slight visual asymmetry or from map colors alone. If the 20-degree or
1.0-D criterion cannot be verified, set srax=UNCERTAIN, srax_deg=null, and use UNCERTAIN rather than
INFERIOR_STEEPENING_SRA. Asymmetric bowtie requires greater than 0.5 D but less than 1.0 D of
asymmetric steepening versus the region 180 degrees opposite, without SRA. Normal/symmetrical
includes round, oval, and symmetric bowtie patterns. Record short visible reasons in
morphology_evidence. If the relevant map is not sufficiently visible, use UNCERTAIN. Do not make a
surgical recommendation. Do not calculate or infer missing BAD-D,
component D values, ARTmax, or other indices from related measurements. Treat this as strict
transcription and structured image interpretation, not autonomous diagnosis.

For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled
"Duzeltme Miktari" (including Turkish characters). Do not substitute values from "Subjektif
Refraksiyon" or any other row. Map SAG/right to OD and SOL/left to OS. Transcribe sphere, signed
cylinder, and axis exactly as written. sphere_cylinder_status may be CONFIDENT only when the sphere
and cylinder digits and signs are unambiguous. If either is ambiguous, set both numeric fields to
null and use UNCERTAIN or UNREADABLE while preserving visible characters in raw_text. Axis ambiguity
does not require discarding an otherwise confident sphere/cylinder pair; report it separately in
axis_status and set axis_deg to null when uncertain. Never transpose cylinder notation and never
infer the laser platform, optical zone, procedure, or ablation depth from the card. For a card-only
image with no corneal tomography/topography data, return an empty eyes array. For a tomography-only
image with no treatment card, return an empty treatment_corrections array."""


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
    reported_category = eye.get("morphology", "UNCERTAIN")
    category = reported_category
    evidence = list(eye.get("morphology_evidence", []))
    i_s = eye.get("I_S")
    srax_deg = eye.get("srax_deg")
    inferior_opposite = eye.get("inferior_opposite_steepening_D")
    srax_supported = is_number(srax_deg) and srax_deg >= 20
    inferior_supported = (
        is_number(inferior_opposite)
        and inferior_opposite >= 1.0
        and is_number(i_s)
        and i_s < 1.4
    )
    asymmetric_supported = (
        is_number(inferior_opposite)
        and 0.5 < inferior_opposite < 1.0
        and not srax_supported
    )
    if reported_category == "ABNORMAL_ECTATIC":
        category = "ABNORMAL_ECTATIC"
    elif is_number(i_s) and i_s >= 1.4:
        category = "ABNORMAL_ECTATIC"
        evidence.append("Published Placido-era ERSS abnormal-pattern criterion: I-S >=1.4 D.")
    elif srax_supported or inferior_supported:
        category = "INFERIOR_STEEPENING_SRA"
        if srax_supported:
            evidence.append("Published ERSS SRA/SRAX category supported: SRA/SRAX >=20 degrees.")
        if inferior_supported:
            evidence.append(
                "Published ERSS inferior-steepening category supported: >=1.0 D versus the opposite "
                "region with I-S <1.4 D."
            )
    elif reported_category == "INFERIOR_STEEPENING_SRA" or eye.get("srax") == "YES":
        category = "UNCERTAIN"
        evidence.append(
            "SRAX/inferior-steepening label not scored: neither SRA/SRAX >=20 degrees nor the "
            ">=1.0 D inferior-opposite criterion with I-S <1.4 D was documented."
        )
    elif reported_category == "ASYMMETRIC_BOWTIE" or eye.get("asymmetric_bow_tie") == "YES":
        if asymmetric_supported:
            category = "ASYMMETRIC_BOWTIE"
            evidence.append(
                "Published ERSS asymmetric-bowtie category supported: >0.5 D and <1.0 D "
                "versus the region 180 degrees opposite, without SRA."
            )
        else:
            category = "UNCERTAIN"
            evidence.append(
                "Asymmetric-bowtie label not scored: the required >0.5 D and <1.0 D "
                "opposite-region difference without SRA was not documented."
            )
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
    map_patterns = (eye.get("anterior_pattern"), eye.get("posterior_pattern"))
    if "ABNORMAL" in display_values or "ABNORMAL" in map_patterns:
        status = "ABNORMAL"
    elif "SUSPICIOUS" in display_values or "BORDERLINE" in map_patterns:
        status = "SUSPICIOUS"
    elif "UNAVAILABLE" in display_values or "UNREADABLE" in map_patterns:
        status = "INCOMPLETE"
    elif flags:
        status = "CONCERN FLAGS"
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
    is_ex500 = "alcon" in platform and "ex500" in platform
    ablation_rate = {6.0: 12.0, 6.5: 15.0, 7.0: 16.33}.get(optical_zone) if is_ex500 else None
    if is_number(sphere) and sphere > 0:
        warnings.append(
            "The HC linear EX500 ablation estimate is not applied to a hyperopic or mixed-meridian plan; "
            "enter the actual laser-plan maximum ablation."
        )
        return None
    if is_number(sphere) and is_number(cylinder) and ablation_rate is not None:
        warnings.append(
            f"Maximum ablation estimated with the HC Alcon EX500, {optical_zone:.1f}-mm-zone, "
            f"{ablation_rate:g} µm/D convention; "
            "actual laser-plan maximum is preferred."
        )
        return (abs(float(sphere)) + abs(float(cylinder))) * ablation_rate
    if is_number(sphere) and is_number(cylinder):
        warnings.append(
            "The HC ablation estimate was not applied because an Alcon EX500 with a 6.0-mm, "
            "6.5-mm, or 7.0-mm optical zone was not explicitly documented."
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
    if eye.get("anterior_pattern") in (None, "UNREADABLE"):
        missing.append("readable anterior pattern")
    if eye.get("quality") in ("LIMITED", "INADEQUATE"):
        missing.append("adequate-quality tomography/topography")
    for conflict in eye.get("data_conflicts", []):
        missing.append(f"unresolved multi-image conflict: {conflict}")
    return missing


def assess_eye(
    eye: Dict[str, Any],
    plan: Dict[str, Any],
    age: Optional[int],
    patient_modifiers: Dict[str, Any],
) -> Dict[str, Any]:
    eye_id = eye.get("eye", "UNKNOWN")
    procedure = plan.get("procedure")
    warnings: List[str] = list(plan.get("correction_warnings", []))
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
    pregnancy_nursing = tri(patient_modifiers.get("pregnancy_nursing"))
    collagen_tissue_disease = tri(patient_modifiers.get("collagen_tissue_disease"))
    drug_usage = tri(patient_modifiers.get("drug_usage"))

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

    rst = (
        pachy - PRK_EPITHELIUM_UM - ablation
        if procedure == "PRK" and pachy is not None and ablation is not None
        else None
    )
    rsb = (
        pachy - flap - ablation
        if procedure == "LASIK" and pachy is not None and is_number(flap) and ablation is not None
        else None
    )
    prk_pta = (
        (PRK_EPITHELIUM_UM + ablation) / pachy * 100
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
    if pregnancy_nursing == "yes":
        modifiers.append("Pregnancy or nursing reported; separate refractive-surgery eligibility review required.")
    if collagen_tissue_disease == "yes":
        modifiers.append("Collagen/connective-tissue disease reported; separate clinical eligibility review required.")
    if drug_usage == "yes":
        modifiers.append("Relevant medication/drug usage reported; medication-specific clinical review required.")

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

    if is_number(sphere) and sphere > 0:
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append(
            "The supplied procedure-specific scoring evidence is predominantly myopic; "
            "hyperopic or mixed-meridian applicability is not established."
        )

    if tomo["status"] == "ABNORMAL" and visible_morphology != "ABNORMAL_ECTATIC":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append("Abnormal adjunctive tomography display: morphology/clinical concordance review required.")
    elif tomo["status"] == "SUSPICIOUS":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append("Suspicious adjunctive tomography display: repeat/confirm and review concordance.")
    elif tomo["status"] == "CONCERN FLAGS":
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append(
            "One or more supplied cross-sectional tomography concern thresholds are positive; "
            "confirm repeatability and clinical/map concordance before any clearance."
        )

    if procedure == "PRK" and surgical_load_flags:
        status = combine_status(status, "REVIEW — NOT CLEARED")
        reasons.append(
            "The PRK plan lies outside the supplied reassuring 2-year direct-cohort PTA envelope; "
            "the evidence gap requires documented review and cannot receive automatic PASS."
        )

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
            "correction_axis_deg": plan.get("correction_axis_deg"),
            "correction_source": plan.get("correction_source"),
            "MRSE_D": mrse,
            "pachy_thinnest_um": pachy,
            "max_ablation_um": ablation,
            "PRK_epithelium_um": PRK_EPITHELIUM_UM if procedure == "PRK" else None,
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


def apply_extracted_corrections(
    extracted: Dict[str, Any], eye_plans: Dict[str, Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Auto-fill an empty eye plan from an unambiguous Duzeltme Miktari entry.

    Manual sphere/cylinder values always take priority. A partial manual pair is never mixed with
    an extracted value, and conflicting cards never produce an automatic treatment plan.
    """
    effective = {
        eye: dict(eye_plans.get(eye, {})) if isinstance(eye_plans.get(eye, {}), dict) else {}
        for eye in EYES
    }
    grouped: Dict[str, List[Dict[str, Any]]] = {eye: [] for eye in EYES}
    for correction in extracted.get("treatment_corrections", []):
        if not isinstance(correction, dict):
            continue
        eye = correction.get("eye")
        if (
            eye in EYES
            and correction.get("source_document") == "EXCIMER_LASER_FOLLOW_UP_CARD"
            and correction.get("source_label") == "DUZELTME_MIKTARI"
        ):
            grouped[eye].append(correction)

    for eye, candidates in grouped.items():
        if not candidates:
            continue
        plan = effective[eye]
        plan.setdefault("correction_warnings", [])
        confident = [
            item for item in candidates
            if item.get("sphere_cylinder_status") == "CONFIDENT"
            and is_number(item.get("sphere_D"))
            and is_number(item.get("cylinder_D"))
        ]
        pairs = {
            (float(item["sphere_D"]), float(item["cylinder_D"])) for item in confident
        }
        if not pairs:
            plan["correction_warnings"].append(
                f"{eye} Duzeltme Miktari was present but not confidently readable; no treatment correction was auto-filled."
            )
            continue
        if len(pairs) > 1:
            plan["correction_warnings"].append(
                f"Conflicting {eye} Duzeltme Miktari readings were extracted; no treatment correction was auto-filled."
            )
            continue

        sphere, signed_cylinder = next(iter(pairs))
        if signed_cylinder > 0:
            plan["correction_warnings"].append(
                f"{eye} card uses plus-cylinder notation; automatic transposition is prohibited. Enter the intended minus-cylinder plan manually."
            )
            continue

        manual_sphere = is_number(plan.get("sphere_D"))
        manual_cylinder = is_number(plan.get("cylinder_magnitude_D"))
        if manual_sphere != manual_cylinder:
            plan["correction_warnings"].append(
                f"{eye} has a partial manual correction; extracted card values were not mixed with manual input."
            )
            continue
        if manual_sphere and manual_cylinder:
            if (
                abs(float(plan["sphere_D"]) - sphere) > 1e-6
                or abs(float(plan["cylinder_magnitude_D"]) - abs(signed_cylinder)) > 1e-6
            ):
                plan["correction_warnings"].append(
                    f"{eye} manual correction differs from the extracted Duzeltme Miktari; manual values retained."
                )
            continue

        plan["sphere_D"] = sphere
        plan["cylinder_magnitude_D"] = abs(signed_cylinder)
        plan["correction_source"] = "Excimer Laser Takip Karti — Duzeltme Miktari"
        axes = {
            float(item["axis_deg"])
            for item in confident
            if item.get("axis_status") == "CONFIDENT"
            and is_number(item.get("axis_deg"))
            and 0 <= float(item["axis_deg"]) <= 180
        }
        if len(axes) == 1:
            plan["correction_axis_deg"] = next(iter(axes))
        elif len(axes) > 1:
            plan["correction_warnings"].append(
                f"Conflicting {eye} cylinder axes were extracted; sphere/cylinder were transferred but the axis was not."
            )
        else:
            plan["correction_warnings"].append(
                f"{eye} cylinder axis was not confidently readable; sphere/cylinder were transferred without an axis."
            )

    return effective


def hc_engine(
    extracted: Dict[str, Any],
    age: Optional[int],
    eye_plans: Dict[str, Dict[str, Any]],
    patient_modifiers: Dict[str, Any],
) -> Dict[str, Any]:
    extracted_eyes = [
        eye for eye in extracted.get("eyes", [])
        if isinstance(eye, dict) and eye.get("eye") in EYES
    ]
    assessed_ids = [eye.get("eye") for eye in extracted_eyes]
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
        "version": "software v0.5.1 / source set 2026-08-25 plus binding HC amendments",
    }


def merge_extractions(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {"eyes": [], "treatment_corrections": [], "global_warnings": []}
    by_eye: Dict[str, Dict[str, Any]] = {}
    conservative = {
        "pachy_thinnest_um": "min", "BAD_D": "max", "Df": "max", "Db": "max",
        "Dp": "max", "Dt": "max", "Da": "max", "ARTmax_um": "min", "PPI_max": "max",
        "PPI_avg": "max", "PPI_min": "max", "Kmax_D": "max", "ISV": "max", "IVA": "max",
        "KI": "max", "CKI": "max", "IHD": "max", "I_S": "max", "KISA": "max",
        "IHA": "max", "anterior_elevation_thinnest_um": "max",
        "posterior_elevation_thinnest_um": "max", "RMS_HOA_um": "max", "vertical_coma_um": "max",
        "srax_deg": "max", "inferior_opposite_steepening_D": "max",
    }
    morphology_rank = {
        "UNCERTAIN": 0, "NORMAL_SYMMETRIC": 1, "ASYMMETRIC_BOWTIE": 2,
        "INFERIOR_STEEPENING_SRA": 3, "ABNORMAL_ECTATIC": 4,
    }
    quality_rank = {"INADEQUATE": 0, "LIMITED": 1, "ADEQUATE": 2}
    posterior_rank = {"UNREADABLE": 0, "REASSURING": 1, "BORDERLINE": 2, "ABNORMAL": 3}
    numeric_tolerance = {
        # These fields are not HC score inputs. Small differences commonly represent OCR of a
        # nearby map label or display rounding, not a clinically meaningful multi-image conflict.
        "K1_D": 0.25,
        "K2_D": 0.25,
        "Kmax_D": 0.25,
    }

    def normalized_eye(raw_eye: Dict[str, Any]) -> Dict[str, Any]:
        eye = dict(raw_eye)
        derived = scoring_morphology(eye)["category"]
        eye["morphology"] = derived
        if eye.get("asymmetric_bow_tie") == "YES" and derived != "ASYMMETRIC_BOWTIE":
            eye["asymmetric_bow_tie"] = "UNCERTAIN"
        if eye.get("srax") == "YES" and derived != "INFERIOR_STEEPENING_SRA":
            eye["srax"] = "UNCERTAIN"
        return eye

    for result in results:
        merged["global_warnings"].extend(result.get("global_warnings", []))
        merged["treatment_corrections"].extend(
            item for item in result.get("treatment_corrections", []) if isinstance(item, dict)
        )
        for raw_eye in result.get("eyes", []):
            eye = normalized_eye(raw_eye)
            eye_id = eye.get("eye", "UNKNOWN")
            if eye_id not in by_eye:
                by_eye[eye_id] = dict(eye)
                continue
            target = by_eye[eye_id]
            target.setdefault("data_conflicts", [])
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

                # Missing/uncertain information on a page that lacks the relevant map is not
                # contradictory evidence against a readable observation on another page.
                if key == "morphology":
                    if old == "UNCERTAIN" and value != "UNCERTAIN":
                        target[key] = value
                        continue
                    if value == "UNCERTAIN":
                        continue
                elif key in ("anterior_pattern", "posterior_pattern"):
                    if old == "UNREADABLE" and value != "UNREADABLE":
                        target[key] = value
                        continue
                    if value == "UNREADABLE":
                        continue
                elif key in ("asymmetric_bow_tie", "srax"):
                    if old == "UNCERTAIN" and value != "UNCERTAIN":
                        target[key] = value
                        continue
                    if value == "UNCERTAIN":
                        continue

                if (
                    key in numeric_tolerance
                    and is_number(old)
                    and is_number(value)
                    and abs(float(old) - float(value)) <= numeric_tolerance[key]
                ):
                    continue

                target["data_conflicts"].append(f"{key}: {old} vs {value}")
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
                elif key == "anterior_pattern":
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
        eye["data_conflicts"] = sorted(set(eye.get("data_conflicts", [])))
        eye["missing_or_unreadable"] = sorted(
            set(key for key in eye.get("missing_or_unreadable", []) if eye.get(key) is None)
        )

    merged["eyes"] = list(by_eye.values())
    unique_corrections: List[Dict[str, Any]] = []
    seen_corrections = set()
    for correction in merged["treatment_corrections"]:
        key = json.dumps(correction, sort_keys=True, ensure_ascii=False)
        if key not in seen_corrections:
            seen_corrections.add(key)
            unique_corrections.append(correction)
    merged["treatment_corrections"] = unique_corrections
    merged["global_warnings"] = sorted(set(merged["global_warnings"]))
    return merged


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    return FileResponse(
        "static/sw.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/",
        },
    )


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
                    "type": "json_schema", "name": "hc_preoperative_image_extraction",
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
    effective_plans = apply_extracted_corrections(extracted, plans)
    return {
        "extracted": extracted,
        "effective_eye_plans": effective_plans,
        "decision": hc_engine(extracted, age, effective_plans, modifiers),
    }
