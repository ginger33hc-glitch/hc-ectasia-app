"""Pure Practical Subjective Scoring System (PS3) policy for CER-AI.

PS3 is independent of Randleman, BAD-D and NICE. Automated PS3 findings have
an explicit completeness state. Manual morphology review items are never counted
as automated Moderate/High findings and do not determine automated completeness.
"""
from dataclasses import dataclass, field
from math import isfinite
from typing import Optional, Tuple

NORMAL = "NORMAL"
MODERATE = "MODERATE"
HIGH = "HIGH"
NOT_EVALUATED = "NOT_EVALUATED"
NOT_REQUIRED = "NOT_REQUIRED"
ALLOWED = "ALLOWED"
DEFER = "DEFER"
INCOMPLETE = "INCOMPLETE"
ASTIGMATIC_COMPARISON_ACTIVATION_D = 3.0

AUTOMATED_KEYS = (
    "anterior_km",
    "thinnest",
    "astigmatic_study",
    "elevation",
    "ppi_average",
    "inter_eye_asymmetry",
    "srax",
)

MANUAL_REVIEW_KEYS = (
    "corneal_thickness_map_morphology",
    "relative_thickness_map",
    "pti_ctsp_morphology",
)


@dataclass(frozen=True)
class PS3EyeInput:
    anterior_km_d: Optional[float] = None
    thinnest_um: Optional[float] = None
    topographic_astig_d: Optional[float] = None
    bad_flat_axis_deg: Optional[float] = None
    manifest_astig_d: Optional[float] = None
    manifest_axis_deg: Optional[float] = None
    ppi_avg: Optional[float] = None
    f_ele_th_um: Optional[float] = None
    b_ele_th_um: Optional[float] = None
    srax: Optional[str] = None
    srax_deg: Optional[float] = None


@dataclass(frozen=True)
class PS3InterEyeInput:
    od_anterior_km_d: Optional[float] = None
    os_anterior_km_d: Optional[float] = None
    od_posterior_km_d: Optional[float] = None
    os_posterior_km_d: Optional[float] = None
    od_thinnest_um: Optional[float] = None
    os_thinnest_um: Optional[float] = None
    od_front_elevation_thinnest_um: Optional[float] = None
    os_front_elevation_thinnest_um: Optional[float] = None
    od_back_elevation_thinnest_um: Optional[float] = None
    os_back_elevation_thinnest_um: Optional[float] = None


@dataclass(frozen=True)
class PS3Finding:
    key: str
    status: str
    detail: str


@dataclass(frozen=True)
class PS3ProcedureDisposition:
    prk: str
    smile: str
    lasik: str


@dataclass(frozen=True)
class PS3Result:
    findings: Tuple[PS3Finding, ...]
    moderate_count: int
    high_count: int
    disposition: PS3ProcedureDisposition
    srax_deg: Optional[float] = None
    inter_eye_score: Optional[int] = None
    review_notes: Tuple[str, ...] = field(default_factory=tuple)
    complete: bool = False
    missing_keys: Tuple[str, ...] = field(default_factory=tuple)


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) else None


def _axis_difference_deg(a, b):
    a = _num(a)
    b = _num(b)
    if a is None or b is None:
        return None
    difference = abs((a % 180) - (b % 180))
    return min(difference, 180 - difference)


def _inter_eye_score(inp):
    if inp is None:
        return None, PS3Finding(
            "inter_eye_asymmetry", NOT_EVALUATED,
            "Bilateral PS3 inter-eye values unavailable.",
        )
    pairs = (
        ("anterior Km", inp.od_anterior_km_d, inp.os_anterior_km_d, 0.3),
        ("posterior Km", inp.od_posterior_km_d, inp.os_posterior_km_d, 0.1),
        ("thinnest pachymetry", inp.od_thinnest_um, inp.os_thinnest_um, 12),
        ("front elevation at thinnest", inp.od_front_elevation_thinnest_um, inp.os_front_elevation_thinnest_um, 2),
        ("back elevation at thinnest", inp.od_back_elevation_thinnest_um, inp.os_back_elevation_thinnest_um, 5),
    )
    if any(_num(a) is None or _num(b) is None for _, a, b, _ in pairs):
        return None, PS3Finding(
            "inter_eye_asymmetry", NOT_EVALUATED,
            "One or more bilateral PS3 inter-eye values are unavailable.",
        )
    exceeded = [label for label, a, b, threshold in pairs if abs(float(a) - float(b)) >= threshold]
    score = len(exceeded)
    status = HIGH if score == 5 else MODERATE if score == 4 else NORMAL
    detail = f"Inter-eye score {score}/5"
    detail += f"; exceeded: {', '.join(exceeded)}." if exceeded else "."
    return score, PS3Finding("inter_eye_asymmetry", status, detail)


def _elevation_finding(inp):
    """Use only canonical BAD Display F.Ele.Th/B.Ele.Th values."""
    front = _num(inp.f_ele_th_um)
    back = _num(inp.b_ele_th_um)
    if front is None or back is None:
        return PS3Finding(
            "elevation", NOT_EVALUATED,
            "Canonical BAD F.Ele.Th and/or B.Ele.Th is unavailable.",
        )
    reasons = []
    if front > 12:
        reasons.append(f"F.Ele.Th {front:g} µm > 12")
    if back > 15:
        reasons.append(f"B.Ele.Th {back:g} µm > 15")
    if reasons:
        return PS3Finding("elevation", HIGH, "; ".join(reasons) + ".")
    return PS3Finding(
        "elevation", NORMAL,
        f"F.Ele.Th {front:g} µm <=12 and B.Ele.Th {back:g} µm <=15.",
    )


def _count(findings):
    moderate = sum(item.status == MODERATE for item in findings)
    high = sum(item.status == HIGH for item in findings)
    return moderate, high


def _automated_completeness(findings):
    by_key = {item.key: item for item in findings}
    missing = tuple(
        key for key in AUTOMATED_KEYS
        if key not in by_key or by_key[key].status == NOT_EVALUATED
    )
    return not missing, missing


def _disposition(moderate_count: int, high_count: int, complete: bool):
    if high_count >= 1 or moderate_count >= 2:
        return PS3ProcedureDisposition(DEFER, DEFER, DEFER)
    if moderate_count == 1:
        if complete:
            return PS3ProcedureDisposition(ALLOWED, ALLOWED, DEFER)
        return PS3ProcedureDisposition(INCOMPLETE, INCOMPLETE, DEFER)
    if complete:
        return PS3ProcedureDisposition(ALLOWED, ALLOWED, ALLOWED)
    return PS3ProcedureDisposition(INCOMPLETE, INCOMPLETE, INCOMPLETE)


def evaluate_ps3(eye, inter_eye=None):
    findings = []

    km = _num(eye.anterior_km_d)
    if km is None:
        findings.append(PS3Finding("anterior_km", NOT_EVALUATED, "Anterior Km unavailable."))
    elif km > 50:
        findings.append(PS3Finding("anterior_km", HIGH, f"Anterior Km {km:g} D > 50 D."))
    elif km >= 48:
        findings.append(PS3Finding("anterior_km", MODERATE, f"Anterior Km {km:g} D is 48-50 D."))
    else:
        findings.append(PS3Finding("anterior_km", NORMAL, f"Anterior Km {km:g} D < 48 D."))

    thinnest = _num(eye.thinnest_um)
    if thinnest is None:
        findings.append(PS3Finding("thinnest", NOT_EVALUATED, "Thinnest pachymetry unavailable."))
    elif thinnest < 470:
        findings.append(PS3Finding("thinnest", HIGH, f"Thinnest {thinnest:g} µm < 470 µm."))
    elif thinnest <= 500:
        findings.append(PS3Finding("thinnest", MODERATE, f"Thinnest {thinnest:g} µm is 470-500 µm."))
    else:
        findings.append(PS3Finding("thinnest", NORMAL, f"Thinnest {thinnest:g} µm > 500 µm."))

    topo_astig = _num(eye.topographic_astig_d)
    manifest_astig = _num(eye.manifest_astig_d)
    comparison_inactive = (
        topo_astig is not None
        and manifest_astig is not None
        and max(abs(topo_astig), abs(manifest_astig)) <= ASTIGMATIC_COMPARISON_ACTIVATION_D
    )
    axis_is_meaningful = (
        not comparison_inactive
        and topo_astig is not None
        and manifest_astig is not None
        and abs(topo_astig) > 1e-12
        and abs(manifest_astig) > 1e-12
    )
    axis_difference = (
        _axis_difference_deg(eye.bad_flat_axis_deg, eye.manifest_axis_deg)
        if axis_is_meaningful
        else None
    )
    if comparison_inactive:
        findings.append(PS3Finding(
            "astigmatic_study", NOT_REQUIRED,
            f"Manifest astigmatism {abs(manifest_astig):g} D and topographic astigmatism "
            f"{abs(topo_astig):g} D are both <={ASTIGMATIC_COMPARISON_ACTIVATION_D:.2f} D; "
            "comparison inactive, no PS3 risk factor.",
        ))
    elif (
        topo_astig is None
        or manifest_astig is None
        or (axis_is_meaningful and axis_difference is None)
    ):
        findings.append(PS3Finding(
            "astigmatic_study", NOT_EVALUATED,
            "Manifest/topographic astigmatism magnitude or axis unavailable.",
        ))
    else:
        magnitude_difference = abs(abs(manifest_astig) - abs(topo_astig))
        axis_abnormal = axis_difference is not None and axis_difference > 10
        status = MODERATE if magnitude_difference > 1 or axis_abnormal else NORMAL
        axis_detail = (
            f"BAD flat-axis versus minus-cylinder manifest axis difference {axis_difference:.1f}°"
            if axis_difference is not None
            else "axis comparison not applicable because an astigmatic magnitude is zero"
        )
        findings.append(PS3Finding(
            "astigmatic_study", status,
            f"Astigmatism difference {magnitude_difference:.2f} D; {axis_detail}.",
        ))

    findings.append(_elevation_finding(eye))

    ppi_avg = _num(eye.ppi_avg)
    if ppi_avg is None:
        findings.append(PS3Finding("ppi_average", NOT_EVALUATED, "PPI Average unavailable."))
    elif ppi_avg > 1.2:
        findings.append(PS3Finding("ppi_average", MODERATE, f"PPI Average {ppi_avg:g} > 1.20."))
    else:
        findings.append(PS3Finding("ppi_average", NORMAL, f"PPI Average {ppi_avg:g} <= 1.20."))

    inter_eye_score, inter_eye_finding = _inter_eye_score(inter_eye)
    findings.append(inter_eye_finding)

    srax_deg = _num(eye.srax_deg)
    srax_state = str(eye.srax or "UNCERTAIN").upper()
    if srax_deg is not None:
        status = HIGH if srax_deg > 20 else NORMAL
        relation = ">" if srax_deg > 20 else "<="
        findings.append(PS3Finding(
            "srax", status,
            f"Front-map SRAX {srax_deg:.1f}° {relation} 20°. Source: Axial/Sagittal Curvature (Front).",
        ))
    elif srax_state == "YES":
        findings.append(PS3Finding(
            "srax", HIGH,
            "Surgeon/front-map confirmation: SRAX >20°.",
        ))
    elif srax_state == "NO":
        findings.append(PS3Finding(
            "srax", NORMAL,
            "Surgeon/front-map confirmation: SRAX is not >20°.",
        ))
    else:
        findings.append(PS3Finding(
            "srax", NOT_EVALUATED,
            "SRAX cannot be determined from the Axial/Sagittal Curvature (Front) map; ask surgeon whether skewed axis is >20°.",
        ))

    review_notes = (
        "Corneal Thickness Map morphology: manual surgeon review only; not counted in automated PS3.",
        "Relative Thickness Map: manual surgeon review only; not counted in automated PS3.",
        "PTI/CTSP thickness-profile morphology: manual surgeon review only; not counted in automated PS3.",
    )
    for key, note in zip(MANUAL_REVIEW_KEYS, review_notes):
        findings.append(PS3Finding(key, NOT_REQUIRED, note))

    moderate_count, high_count = _count(findings)
    complete, missing_keys = _automated_completeness(findings)
    disposition = _disposition(moderate_count, high_count, complete)
    return PS3Result(
        tuple(findings),
        moderate_count,
        high_count,
        disposition,
        srax_deg,
        inter_eye_score,
        review_notes,
        complete,
        missing_keys,
    )
