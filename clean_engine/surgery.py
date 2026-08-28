"""Pure surgical calculations for the parallel clean engine."""
from dataclasses import dataclass
from typing import Optional

from .policy import POLICY


@dataclass(frozen=True)
class LasikPlan:
    name: str
    flap_um: float
    optical_zone_mm: float
    transition_zone_mm: float


LASIK_PLANS = (
    LasikPlan("Plan A", 100.0, 6.5, 9.0),
    LasikPlan("Plan B", 100.0, 6.0, 8.5),
    LasikPlan("Plan C", 90.0, 6.0, 8.5),
)


def lasik_rsb_um(cct_um: float, flap_um: float, ablation_um: float) -> float:
    return float(cct_um) - float(flap_um) - float(ablation_um)


def lasik_pta_percent(cct_um: float, flap_um: float, ablation_um: float) -> float:
    return 100.0 * (float(flap_um) + float(ablation_um)) / float(cct_um)


def prk_rst_um(cct_um: float, ablation_um: float) -> float:
    return float(cct_um) - POLICY.prk_epithelium_um - float(ablation_um)


def prk_pta_percent(cct_um: float, ablation_um: float) -> float:
    return 100.0 * (POLICY.prk_epithelium_um + float(ablation_um)) / float(cct_um)


def final_kmean_d(preop_kmean_d: float, intended_mrse_d: float) -> float:
    return float(preop_kmean_d) + POLICY.corneal_effect_per_intended_mrse_d * float(intended_mrse_d)


def final_kmean_within_hc_range(value: float) -> bool:
    return POLICY.final_kmean_min_d <= float(value) <= POLICY.final_kmean_max_d


def lasik_pta_cutoff(pta_percent: Optional[float]) -> bool:
    return isinstance(pta_percent, (int, float)) and not isinstance(pta_percent, bool) and float(pta_percent) >= POLICY.lasik_pta_cutoff_percent
