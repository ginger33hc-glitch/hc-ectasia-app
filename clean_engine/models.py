"""Typed domain models for the parallel clean assessment engine."""
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class EyeInput:
    age_years: Optional[float]
    pachy_thinnest_um: Optional[float]
    bad_d: Optional[float]
    morphology: str
    procedure: str
    ablation_um: Optional[float] = None
    flap_um: Optional[float] = None
    preop_kmean_d: Optional[float] = None
    intended_mrse_d: Optional[float] = None
    intended_sphere_d: Optional[float] = None
    intended_cylinder_magnitude_d: Optional[float] = None
    laser_platform: Optional[str] = None
    use_lasik_fallback_planning: bool = False


@dataclass(frozen=True)
class CalculatedValues:
    lasik_rsb_um: Optional[float] = None
    lasik_pta_percent: Optional[float] = None
    prk_rst_um: Optional[float] = None
    prk_pta_percent: Optional[float] = None
    final_kmean_d: Optional[float] = None


@dataclass(frozen=True)
class ScoreValues:
    age_points: Optional[int]
    pachymetry_points: Optional[int]
    topography_points: Optional[int]
    rsb_points: Optional[int]
    mrse_points: Optional[int]
    erss_total: Optional[int]


@dataclass(frozen=True)
class PrkScoreValues:
    age_points: Optional[int] = None
    pachymetry_points: Optional[int] = None
    morphology_points: Optional[int] = None
    total: Optional[int] = None
    category: Optional[str] = None
    pta_evidence_gap: bool = False


@dataclass(frozen=True)
class LasikPlanningStep:
    plan_name: str
    flap_um: float
    optical_zone_mm: float
    transition_zone_mm: float
    ablation_um: Optional[float]
    ablation_source: str
    rsb_um: Optional[float]
    pta_percent: Optional[float]
    status: str


@dataclass(frozen=True)
class AssessmentResult:
    status: str
    bad_d_status: str
    calculations: CalculatedValues
    scores: ScoreValues
    hard_stops: Tuple[str, ...] = field(default_factory=tuple)
    missing: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
    lasik_planning_sequence: Tuple[LasikPlanningStep, ...] = field(default_factory=tuple)
    prk_scores: PrkScoreValues = field(default_factory=PrkScoreValues)
