"""Procedure-specific scoring stage for the parallel clean engine."""
from dataclasses import dataclass
from typing import Optional, Tuple

from .models import PrkScoreValues, ScoreValues
from .policy import age_points, lasik_mrse_points, lasik_pachymetry_points, lasik_rsb_points, randleman_topography_points
from .prk import prk_morphology_points, prk_pachymetry_points, prk_pta_evidence_gap, prk_score_category, prk_score_total


@dataclass(frozen=True)
class ScoringInput:
    procedure: str
    age_years: Optional[float]
    pachy_thinnest_um: Optional[float]
    morphology: str
    manifest_mrse_d: Optional[float]
    lasik_rsb_um: Optional[float]
    prk_pta_percent: Optional[float]


def calculate_scores(inp: ScoringInput) -> Tuple[ScoreValues, PrkScoreValues]:
    """Calculate LASIK ERSS and separate PRK provisional scores without mixing models."""
    procedure = (inp.procedure or "").upper()
    age = age_points(inp.age_years)
    pachy = lasik_pachymetry_points(inp.pachy_thinnest_um)
    topo = randleman_topography_points(inp.morphology)
    rsb = lasik_rsb_points(inp.lasik_rsb_um) if procedure == "LASIK" else None
    mrse = lasik_mrse_points(inp.manifest_mrse_d) if procedure == "LASIK" else None
    erss_total = None if procedure != "LASIK" or None in (age, pachy, topo, rsb, mrse) else int(age + pachy + topo + rsb + mrse)
    lasik = ScoreValues(age, pachy, topo, rsb, mrse, erss_total)

    prk = PrkScoreValues()
    if procedure == "PRK":
        total = prk_score_total(inp.age_years, inp.pachy_thinnest_um, inp.morphology)
        prk = PrkScoreValues(
            age_points=age,
            pachymetry_points=prk_pachymetry_points(inp.pachy_thinnest_um),
            morphology_points=prk_morphology_points(inp.morphology),
            total=total,
            category=prk_score_category(total),
            pta_evidence_gap=prk_pta_evidence_gap(inp.prk_pta_percent),
        )
    return lasik, prk
