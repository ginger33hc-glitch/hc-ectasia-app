"""Post-PASS LASIK microkeratome planning.

This module is intentionally isolated from ectasia eligibility and scoring.
Source rules: MED-LOGICS Operations Manual Doc 200-0386 Rev 22, p.43,
plus HC protocol rule for corneal K spread >4.00 D.
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple
import math


@dataclass(frozen=True)
class MicrokeratomePlanningInput:
    assessment_status: str
    procedure: str
    steepest_k_d: Optional[float]
    flattest_k_d: Optional[float]
    w2w_mm: Optional[float]
    pachy_um: Optional[float]
    t_zone_mm: Optional[float] = None
    steep_axis_deg: Optional[float] = None
    hyperopic: bool = False
    mixed_cylinder: bool = False
    hinge_site_lowest_k_d: Optional[float] = None
    perpendicular_hinge_anatomically_possible: Optional[bool] = None
    lasik_rsb_um: Optional[float] = None
    lasik_pta_percent: Optional[float] = None
    rsb_pta_allow_alternative: Optional[bool] = None


@dataclass(frozen=True)
class MicrokeratomePlan:
    applicable: bool
    vacuum_ring_mm: Optional[float] = None
    vacuum_pressure_mmhg: Optional[str] = None
    blade_recommendations: Tuple[str, ...] = field(default_factory=tuple)
    primary_hinge: Optional[str] = None
    alternative_hinge: Optional[str] = None
    delta_k_d: Optional[float] = None
    ring_tzone_clearance_mm: Optional[float] = None
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    notes: Tuple[str, ...] = field(default_factory=tuple)


def _finite(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _nomogram_k(k: float) -> int:
    # Manual: XX.50 is rounded upward. Other decimals remain in their lower
    # integer band until the next integer threshold.
    whole = math.floor(k)
    return whole + 1 if k - whole >= 0.50 else whole


def _ring_for(k: float, w2w: float, hyperopic: bool) -> Tuple[Optional[float], Optional[str], Tuple[str, ...]]:
    notes = []
    k_band = _nomogram_k(k)
    effective_w2w = w2w
    frac = w2w - math.floor(w2w)
    if hyperopic and frac >= 0.60:
        effective_w2w = float(math.ceil(w2w))
        notes.append("Hyperopic W2W xx.60+ may be rounded upward per manual.")

    large = effective_w2w >= 11.5
    if k_band <= 40:
        return (9.5 if large else 9.0), "580-590", tuple(notes)
    if k_band == 41:
        return (9.5 if large else 9.0), "580-590", tuple(notes)
    if 42 <= k_band <= 46:
        return (9.0 if large else 8.5), "550", tuple(notes)
    if k_band == 47:
        return (8.5 if large else 8.0), "550", tuple(notes)
    if k_band == 48:
        return 8.0, "550", tuple(notes)
    return None, None, tuple(notes)


def plan_microkeratome(inp: MicrokeratomePlanningInput) -> MicrokeratomePlan:
    """Return a non-eligibility-changing surgical planning recommendation."""
    if (inp.procedure or "").upper() != "LASIK" or (inp.assessment_status or "").upper() != "PASS":
        return MicrokeratomePlan(False, notes=("Planning module runs only after LASIK PASS.",))

    steep = _finite(inp.steepest_k_d)
    flat = _finite(inp.flattest_k_d)
    w2w = _finite(inp.w2w_mm)
    pachy = _finite(inp.pachy_um)
    tzone = _finite(inp.t_zone_mm)
    hinge_low_k = _finite(inp.hinge_site_lowest_k_d)
    warnings = []
    notes = []
    blades = []

    ring = pressure = None
    if steep is not None and w2w is not None:
        ring, pressure, ring_notes = _ring_for(steep, w2w, inp.hyperopic)
        notes.extend(ring_notes)
        if ring is None:
            warnings.append("Steepest K is outside the supplied nomogram range; no ring is inferred.")
    else:
        warnings.append("Steepest K and W2W are required for vacuum-ring selection.")

    if pachy is not None and pachy < 530:
        notes.append("Manual advises 580-590 mmHg when pachymetry is <530 µm, with corneal K taking priority.")
    if pachy is not None and pachy <= 500:
        blades.append("-10 blade")
        notes.append("Pachymetry <=500 µm: manual recommends -10 blade when seeking a thinner flap/more residual stroma.")
    if steep is not None and steep <= 39:
        blades.extend(("+10 blade", "+20 blade"))
        notes.append("K <=39 D: manual recommends +10 or +20 blade.")

    clearance = None
    if ring is not None and tzone is not None:
        clearance = round(ring - tzone, 2)
        if not (0.4 <= clearance <= 0.5):
            warnings.append("Ablation zone is not 0.4-0.5 mm smaller than the selected ring (manual optimum).")

    delta = round(steep - flat, 2) if steep is not None and flat is not None else None
    primary_hinge = None
    alternative_hinge = None

    # HC rule: strict >4.00 D, not >=4.00 D.
    if delta is not None and delta > 4.00:
        primary_hinge = "Perpendicular to steep axis"
        if inp.steep_axis_deg is not None:
            primary_hinge += f" ({(float(inp.steep_axis_deg) + 90.0) % 180.0:.0f}° hinge axis)"
        if inp.perpendicular_hinge_anatomically_possible is False:
            if inp.rsb_pta_allow_alternative is True:
                alternative_hinge = "+10 blade; temporal or nasal hinge"
                notes.append("HC alternative permitted only because perpendicular hinge is anatomically impractical and RSB/PTA allow it.")
            elif inp.rsb_pta_allow_alternative is False:
                warnings.append("Perpendicular hinge is anatomically impractical; +10 temporal/nasal alternative is not permitted by RSB/PTA safety check.")
            else:
                warnings.append("Perpendicular hinge is anatomically impractical; RSB/PTA safety clearance is required before +10 temporal/nasal alternative.")

    if (inp.hyperopic or inp.mixed_cylinder) and hinge_low_k is not None and hinge_low_k <= 37:
        notes.append("Manual hinge rule triggered: hinge-site lowest K <=37 D; plan toward a higher-K T/N/S direction or consider +10/+20 blade.")
        if "+10 blade" not in blades:
            blades.append("+10 blade")
        if "+20 blade" not in blades:
            blades.append("+20 blade")

    if not blades:
        blades.append("Standard blade unless another rule/clinical factor applies")

    if ring is not None:
        notes.append("If the selected ring leaks/does not hold vacuum or is too large, the manual directs selection of one smaller ring.")

    return MicrokeratomePlan(
        True, ring, pressure, tuple(blades), primary_hinge, alternative_hinge,
        delta, clearance, tuple(warnings), tuple(notes),
    )
