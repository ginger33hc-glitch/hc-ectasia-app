"""Practical Subjective Scoring System (PS3) policy for CER-AI.

This module is intentionally pure and independent of the canonical Randleman,
BAD-D, NICE, and clean-engine pipelines. It consumes already-read clinical
values and returns PS3-specific findings and procedure permissions only.

Source of thresholds: the current PS3 examination form supplied for the CER-AI
project, with explicitly agreed operational mappings. Morphologic items that
cannot be read reliably are reported as NOT_EVALUATED and are never silently
counted as normal.
"""
from dataclasses import dataclass, field
from math import isfinite
from typing import Optional, Tuple

from derived_srax import derive_srax_deg


NORMAL = "NORMAL"
MODERATE = "MODERATE"
HIGH = "HIGH"
NOT_EVALUATED = "NOT_EVALUATED"
ALLOWED = "ALLOWED"
DEFER = "DEFER"


@dataclass(frozen=True)
class PS3EyeInput:
    anterior_km_d: Optional[float] = None
    thinnest_um: Optional[float] = None
    topographic_astig_d: Optional[float] = None
    topographic_steep_axis_deg: Optional[float] = None
    manifest_astig_d: Optional[float] = None
    manifest_axis_deg: Optional[float] = None
    ppi_avg: Optional[float] = None
    kmax_d: Optional[float] = None
    i_s_d: Optional[float] = None
    kisa_percent: Optional[float] = None
    # 8-mm BFS elevation at thinnest location, when available.
    bfs_front_um: Optional[float] = None
    bfs_back_um: Optional[float] = None
    # BFTE elevation values, when available.
    bfte_front_um: Optional[float] = None
    bfte_back_um: Optional[float] = None
    refractive_group: Optional[str] = None  # MYOPIC_EMMETROPIC or HYPEROPIC_MIXED


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
    derived_srax_deg: Optional[float] = None
    inter_eye_score: Optional[int] = None
    review_notes: Tuple[str, ...] = field(default_factory=tuple)


def _num(value) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) else None


def _axis_difference_deg(a, b) -> Optional[float]:
    """Smallest difference between astigmatism axes on a 180-degree circle."""
    a = _num(a)
    b = _num(b)
    if a is None or b is None:
        return None
    a %= 180.0
    b %= 180.0
    diff = abs(a - b)
    return min(diff, 180.0 - diff)


def _inter_eye_score(inp: Optional[PS3InterEyeInput]) -> Tuple[Optional[int], PS3Finding]:
    if inp is None:
        return None, PS3Finding("inter_eye_asymmetry", NOT_EVALUATED, "Bilateral PS3 inter-eye values unavailable.")
    pairs = (
        ("anterior Km", inp.od_anterior_km_d, inp.os_anterior_km_d, 0.3),
        ("posterior Km", inp.od_posterior_km_d, inp.os_posterior_km_d, 0.1),
        ("thinnest pachymetry", inp.od_thinnest_um, inp.os_thinnest_um, 12.0),
        ("front elevation at thinnest", inp.od_front_elevation_thinnest_um, inp.os_front_elevation_thinnest_um, 2.0),
        ("back elevation at thinnest", inp.od_back_elevation_thinnest_um, inp.os_back_elevation_thinnest_um, 5.0),
    )
    if any(_num(a) is None or _num(b) is None for _, a, b, _ in pairs):
        return None, PS3Finding("inter_eye_asymmetry", NOT_EVALUATED, "One or more bilateral PS3 inter-eye values are unavailable.")
    exceeded = [label for label, a, b, limit in pairs if abs(float(a) - float(b)) >= limit]
    score = len(exceeded)
    if score == 5:
        status = HIGH
    elif score == 4:
        status = MODERATE
    else:
        status = NORMAL
    detail = f"Inter-eye score {score}/5" + (f"; exceeded: {', '.join(exceeded)}." if exceeded else ".")
    return score, PS3Finding("inter_eye_asymmetry", status, detail)


def _elevation_finding(inp: PS3EyeInput) -> PS3Finding:
    bfs_front = _num(inp.bfs_front_um)
    bfs_back = _num(inp.bfs_back_um)
    bfte_front = _num(inp.bfte_front_um)
    bfte_back = _num(inp.bfte_back_um)
    group = str(inp.refractive_group or "").upper()

    high_reasons = []
    if bfs_front is not None or bfs_back is not None:
        if group == "MYOPIC_EMMETROPIC":
            if bfs_front is not None and bfs_front >= 8.0:
                high_reasons.append(f"BFS front {bfs_front:g} µm >= 8")
            if bfs_back is not None and bfs_back >= 18.0:
                high_reasons.append(f"BFS back {bfs_back:g} µm >= 18")
        elif group == "HYPEROPIC_MIXED":
            if bfs_front is not None and bfs_front >= 7.0:
                high_reasons.append(f"BFS front {bfs_front:g} µm >= 7")
            if bfs_back is not None and bfs_back >= 28.0:
                high_reasons.append(f"BFS back {bfs_back:g} µm >= 28")

    if bfte_front is not None and bfte_front > 12.0:
        high_reasons.append(f"BFTE front {bfte_front:g} µm > 12")
    if bfte_back is not None and bfte_back > 15.0:
        high_reasons.append(f"BFTE back {bfte_back:g} µm > 15")

    if high_reasons:
        return PS3Finding("elevation", HIGH, "; ".join(high_reasons) + ".")
    if None not in (bfte_front, bfte_back):
        return PS3Finding("elevation", NORMAL, "Available BFTE elevation criteria are below PS3 high-risk thresholds.")
    if group in {"MYOPIC_EMMETROPIC", "HYPEROPIC_MIXED"} and None not in (bfs_front, bfs_back):
        return PS3Finding("elevation", NORMAL, "Available BFS elevation criteria are below PS3 high-risk thresholds.")
    return PS3Finding("elevation", NOT_EVALUATED, "Required PS3 elevation values are incomplete.")


def evaluate_ps3(eye: PS3EyeInput, inter_eye: Optional[PS3InterEyeInput] = None) -> PS3Result:
    findings = []

    km = _num(eye.anterior_km_d)
    if km is None:
        findings.append(PS3Finding("anterior_km", NOT_EVALUATED, "Anterior Km unavailable."))
    elif km > 50.0:
        findings.append(PS3Finding("anterior_km", HIGH, f"Anterior Km {km:g} D > 50 D."))
    elif km >= 48.0:
        findings.append(PS3Finding("anterior_km", MODERATE, f"Anterior Km {km:g} D is 48-50 D."))
    else:
        findings.append(PS3Finding("anterior_km", NORMAL, f"Anterior Km {km:g} D < 48 D."))

    thinnest = _num(eye.thinnest_um)
    if thinnest is None:
        findings.append(PS3Finding("thinnest", NOT_EVALUATED, "Thinnest pachymetry unavailable."))
    elif thinnest < 470.0:
        findings.append(PS3Finding("thinnest", HIGH, f"Thinnest {thinnest:g} µm < 470 µm."))
    elif thinnest <= 500.0:
        findings.append(PS3Finding("thinnest", MODERATE, f"Thinnest {thinnest:g} µm is 470-500 µm."))
    else:
        findings.append(PS3Finding("thinnest", NORMAL, f"Thinnest {thinnest:g} µm > 500 µm."))

    topo_astig = _num(eye.topographic_astig_d)
    manifest_astig = _num(eye.manifest_astig_d)
    axis_diff = _axis_difference_deg(eye.topographic_steep_axis_deg, eye.manifest_axis_deg)
    if topo_astig is None or manifest_astig is None or axis_diff is None:
        findings.append(PS3Finding("astigmatic_study", NOT_EVALUATED, "Manifest/topographic astigmatism magnitude or axis unavailable."))
    else:
        magnitude_diff = abs(abs(manifest_astig) - abs(topo_astig))
        if magnitude_diff > 1.0 or axis_diff > 10.0:
            findings.append(PS3Finding("astigmatic_study", MODERATE, f"Astigmatism difference {magnitude_diff:.2f} D; axis difference {axis_diff:.1f}°."))
        else:
            findings.append(PS3Finding("astigmatic_study", NORMAL, f"Astigmatism difference {magnitude_diff:.2f} D; axis difference {axis_diff:.1f}°."))

    findings.append(_elevation_finding(eye))

    ppi = _num(eye.ppi_avg)
    if ppi is None:
        findings.append(PS3Finding("ppi_average", NOT_EVALUATED, "PPI Average unavailable."))
    elif ppi > 1.2:
        findings.append(PS3Finding("ppi_average", MODERATE, f"PPI Average {ppi:g} > 1.20."))
    else:
        findings.append(PS3Finding("ppi_average", NORMAL, f"PPI Average {ppi:g} <= 1.20."))

    derived_srax = derive_srax_deg(
        kisa_percent=eye.kisa_percent,
        kmax_d=eye.kmax_d,
        i_s_d=eye.i_s_d,
        astig_d=eye.topographic_astig_d,
    )
    if derived_srax is None:
        findings.append(PS3Finding("derived_srax", NOT_EVALUATED, "Derived SRAX unavailable/invalid; requires KISA%, Kmax, I-S, and topographic astigmatism."))
    elif derived_srax > 22.0:
        findings.append(PS3Finding("derived_srax", HIGH, f"Derived SRAX {derived_srax:.1f}° > 22°. Not directly reported by Pentacam."))
    else:
        findings.append(PS3Finding("derived_srax", NORMAL, f"Derived SRAX {derived_srax:.1f}° <= 22°. Not directly reported by Pentacam."))

    inter_eye_score, inter_eye_finding = _inter_eye_score(inter_eye)
    findings.append(inter_eye_finding)

    review_notes = (
        "Corneal Thickness Map morphology (Dome/Bell/Globus) not evaluated — surgeon review required.",
        "Relative Thickness Map not evaluated — surgeon review required.",
        "PTI/CTSP thickness-profile morphology (S-shape/quick slope/inverted slope) not evaluated — surgeon review required.",
    )
    findings.extend((
        PS3Finding("corneal_thickness_map_morphology", NOT_EVALUATED, review_notes[0]),
        PS3Finding("relative_thickness_map", NOT_EVALUATED, review_notes[1]),
        PS3Finding("pti_ctsp_morphology", NOT_EVALUATED, review_notes[2]),
    ))

    moderate_count = sum(f.status == MODERATE for f in findings)
    high_count = sum(f.status == HIGH for f in findings)
    if high_count >= 1 or moderate_count >= 2:
        disposition = PS3ProcedureDisposition(DEFER, DEFER, DEFER)
    elif moderate_count == 1:
        disposition = PS3ProcedureDisposition(ALLOWED, ALLOWED, DEFER)
    else:
        disposition = PS3ProcedureDisposition(ALLOWED, ALLOWED, ALLOWED)

    return PS3Result(
        findings=tuple(findings),
        moderate_count=moderate_count,
        high_count=high_count,
        disposition=disposition,
        derived_srax_deg=derived_srax,
        inter_eye_score=inter_eye_score,
        review_notes=review_notes,
    )
