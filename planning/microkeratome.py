"""Post-assessment ML7 microkeratome planning.

The vacuum-ring/blade rules are kept outside the ectasia engine.  They can only
produce a surgeon-review recommendation after a favorable LASIK assessment and
can never change the CERAI disposition.

Source rules: the user-supplied Turkish ML7 reference (MED-LOGICS document
200-0386, Rev. 22) plus the binding CERAI hinge rule for a K spread >4.00 D.
"""
from dataclasses import asdict, dataclass, field
from typing import Optional, Tuple
import math


FAVORABLE_LASIK_STATUSES = frozenset({"PASS", "PASS WITH CAUTION"})
LASIK_RSB_MIN_UM = 300.0
LASIK_PTA_MAX_EXCLUSIVE_PERCENT = 40.0


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
    planned_flap_um: Optional[float] = None
    max_ablation_um: Optional[float] = None


@dataclass(frozen=True)
class MicrokeratomePlan:
    applicable: bool
    assessment_gate: str
    vacuum_ring_mm: Optional[float] = None
    vacuum_pressure_mmhg: Optional[str] = None
    blade_recommendations: Tuple[str, ...] = field(default_factory=tuple)
    primary_hinge: Optional[str] = None
    alternative_hinge: Optional[str] = None
    delta_k_d: Optional[float] = None
    ring_tzone_clearance_mm: Optional[float] = None
    alternative_rsb_um: Optional[float] = None
    alternative_pta_percent: Optional[float] = None
    alternative_safety: str = "NOT_APPLICABLE"
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    notes: Tuple[str, ...] = field(default_factory=tuple)
    source: str = "MED-LOGICS ML7 Rev. 22 active Turkish reference + CERAI hinge amendment"

    def as_dict(self):
        return asdict(self)


def _finite(value: Optional[float]) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _nomogram_k(k: float) -> int:
    # Active Turkish reference: XX.50 is rounded upward. Other decimals remain
    # in their lower integer band until the next integer threshold.
    whole = math.floor(k)
    return whole + 1 if k - whole >= 0.50 else whole


def _ring_for(k: float, w2w: float, hyperopic: bool) -> Tuple[Optional[float], Optional[str], Tuple[str, ...]]:
    notes = []
    k_band = _nomogram_k(k)
    effective_w2w = w2w
    frac = w2w - math.floor(w2w)
    if hyperopic and frac >= 0.60:
        effective_w2w = float(math.ceil(w2w))
        notes.append("Hyperopic W2W xx.60+ rounded upward under the active ML7 reference.")

    large = effective_w2w >= 11.5
    if k_band <= 41:
        return (9.5 if large else 9.0), "580-590", tuple(notes)
    if 42 <= k_band <= 46:
        return (9.0 if large else 8.5), "550", tuple(notes)
    if k_band == 47:
        return (8.5 if large else 8.0), "550", tuple(notes)
    if k_band == 48:
        return 8.0, "550", tuple(notes)
    return None, None, tuple(notes)


def _alternative_tissue_safety(
    pachy_um: Optional[float], planned_flap_um: Optional[float], max_ablation_um: Optional[float]
) -> Tuple[Optional[float], Optional[float], str]:
    """Project tissue metrics for a +10 blade relative to the selected flap.

    The +10 blade is modeled as a 10-µm increase in flap thickness.  The
    contingency is allowed only when projected RSB remains >=300 µm and PTA
    remains <40.0%, matching the active CERAI tissue gates.
    """
    pachy = _finite(pachy_um)
    flap = _finite(planned_flap_um)
    ablation = _finite(max_ablation_um)
    if pachy is None or flap is None or ablation is None or pachy <= 0:
        return None, None, "UNAVAILABLE"
    alternative_flap = flap + 10.0
    rsb = pachy - alternative_flap - ablation
    pta = 100.0 * (alternative_flap + ablation) / pachy
    allowed = rsb >= LASIK_RSB_MIN_UM and pta < LASIK_PTA_MAX_EXCLUSIVE_PERCENT
    return round(rsb, 2), round(pta, 3), "ALLOWED" if allowed else "NOT_ALLOWED"


def plan_microkeratome(inp: MicrokeratomePlanningInput) -> MicrokeratomePlan:
    """Return a non-eligibility-changing surgeon-review recommendation."""
    status = (inp.assessment_status or "").upper()
    if (inp.procedure or "").upper() != "LASIK" or status not in FAVORABLE_LASIK_STATUSES:
        return MicrokeratomePlan(
            False,
            "NOT_FAVORABLE_LASIK",
            notes=("Planning module runs only after a favorable LASIK assessment.",),
        )

    steep = _finite(inp.steepest_k_d)
    flat = _finite(inp.flattest_k_d)
    w2w = _finite(inp.w2w_mm)
    pachy = _finite(inp.pachy_um)
    tzone = _finite(inp.t_zone_mm)
    hinge_low_k = _finite(inp.hinge_site_lowest_k_d)
    steep_axis = _finite(inp.steep_axis_deg)
    warnings = []
    notes = ["Recommendation only; surgeon must verify anatomy, device setup, and the active ML7 manual before use."]
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
        notes.append("Active ML7 reference advises 580-590 mmHg when pachymetry is <530 µm, with corneal K taking priority.")
    if pachy is not None and pachy <= 500:
        blades.append("-10 blade")
        notes.append("Pachymetry <=500 µm: active ML7 reference recommends -10 blade when seeking a thinner flap/more residual stroma.")
    if steep is not None and steep <= 39:
        blades.extend(("+10 blade", "+20 blade"))
        notes.append("K <=39 D: active ML7 reference recommends +10 or +20 blade.")

    clearance = None
    if ring is not None and tzone is not None:
        clearance = round(ring - tzone, 2)
        if not (0.4 <= clearance <= 0.5):
            warnings.append("Ablation/transition zone is not 0.4-0.5 mm smaller than the selected ring (active ML7 reference optimum).")

    delta = round(steep - flat, 2) if steep is not None and flat is not None else None
    primary_hinge = None
    alternative_hinge = None
    alternative_rsb = alternative_pta = None
    alternative_safety = "NOT_APPLICABLE"

    # Binding CERAI rule: strict >4.00 D, not >=4.00 D.
    if delta is not None and delta > 4.00:
        primary_hinge = "Perpendicular to steep axis"
        if steep_axis is not None and 0 <= steep_axis <= 180:
            primary_hinge += f" ({(steep_axis + 90.0) % 180.0:.0f}° hinge axis)"
        elif steep_axis is None:
            warnings.append("K spread is >4.00 D, but the steep K axis is unavailable; the numeric hinge axis cannot be calculated.")
        else:
            warnings.append("Steep K axis is outside 0-180°; the numeric hinge axis was not calculated.")

        alternative_rsb, alternative_pta, alternative_safety = _alternative_tissue_safety(
            pachy, inp.planned_flap_um, inp.max_ablation_um
        )
        anatomy = inp.perpendicular_hinge_anatomically_possible
        if anatomy is not True:
            if alternative_safety == "ALLOWED":
                alternative_hinge = "+10 blade; temporal or nasal hinge"
                qualifier = (
                    "because the perpendicular hinge was documented as anatomically impractical"
                    if anatomy is False
                    else "only if the surgeon determines that the perpendicular hinge is anatomically impractical"
                )
                notes.append(f"CERAI contingency: {alternative_hinge} may be considered {qualifier}; projected RSB/PTA remain within CERAI limits.")
            elif alternative_safety == "NOT_ALLOWED":
                warnings.append("The +10 temporal/nasal contingency is not permitted: projected RSB and/or PTA reaches an CERAI tissue cutoff.")
            else:
                warnings.append("RSB/PTA inputs are incomplete; the +10 temporal/nasal contingency cannot be cleared.")

    if (inp.hyperopic or inp.mixed_cylinder) and hinge_low_k is not None and hinge_low_k <= 37:
        notes.append("Active ML7 hinge rule triggered: hinge-site lowest K <=37 D; plan toward a higher-K temporal/nasal/superior direction or consider +10/+20 blade.")
        for blade in ("+10 blade", "+20 blade"):
            if blade not in blades:
                blades.append(blade)

    if not blades:
        blades.append("Plano/standard blade unless another rule or clinical factor applies")

    if ring is not None:
        notes.append("If the selected ring leaks, does not hold vacuum, or is too large, the active ML7 reference directs selection of one smaller ring.")

    return MicrokeratomePlan(
        applicable=True,
        assessment_gate=status,
        vacuum_ring_mm=ring,
        vacuum_pressure_mmhg=pressure,
        blade_recommendations=tuple(dict.fromkeys(blades)),
        primary_hinge=primary_hinge,
        alternative_hinge=alternative_hinge,
        delta_k_d=delta,
        ring_tzone_clearance_mm=clearance,
        alternative_rsb_um=alternative_rsb,
        alternative_pta_percent=alternative_pta,
        alternative_safety=alternative_safety,
        warnings=tuple(dict.fromkeys(warnings)),
        notes=tuple(dict.fromkeys(notes)),
    )

