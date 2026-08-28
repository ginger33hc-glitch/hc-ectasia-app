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
    erss_total: Optional[int]


@dataclass(frozen=True)
class AssessmentResult:
    status: str
    bad_d_status: str
    calculations: CalculatedValues
    scores: ScoreValues
    hard_stops: Tuple[str, ...] = field(default_factory=tuple)
    missing: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)
