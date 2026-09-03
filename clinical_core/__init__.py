"""Pure launch-contract clinical rules for CER-AI.

This package is intentionally side-effect free. It does not import the FastAPI
application, mutate runtime functions, or participate in production composition
until explicit equivalence gates are satisfied.
"""

from .disposition import combine_status, presentation_class
from .erss import (
    erss_disposition,
    erss_mrse_points,
    erss_rsb_points,
    erss_topography_points,
    erss_total,
)
from .nice import nice_disposition, score_nice
from .pipeline import ClinicalCoreInput, PIPELINE_ORDER, evaluate_normalized_case
from .planning import (
    LASIK_PLANS,
    LASIK_PTA_CUTOFF_PERCENT,
    independent_hard_stop,
    plan_payload,
    plan_responsive_failure,
    planning_summary,
    pta_cutoff,
)
from .ps3 import PS3EyeInput, PS3InterEyeInput, evaluate_ps3
from .rules import (
    bad_d_classification,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
)
from .safety import (
    estimated_final_kmean_d,
    final_kmean_hard_stop,
    lasik_pta_hard_stop,
    lasik_pta_percent,
    lasik_rsb_hard_stop,
    lasik_rsb_um,
    preop_thickness_hard_stop,
    prk_rst_hard_stop,
    prk_rst_um,
    sphere_magnitude_hard_stop,
)

__all__ = [
    "ClinicalCoreInput",
    "LASIK_PLANS",
    "LASIK_PTA_CUTOFF_PERCENT",
    "PIPELINE_ORDER",
    "PS3EyeInput",
    "PS3InterEyeInput",
    "bad_d_classification",
    "combine_status",
    "erss_age_points",
    "erss_disposition",
    "erss_mrse_points",
    "erss_pachymetry_points",
    "erss_rsb_points",
    "erss_topography_category",
    "erss_topography_points",
    "erss_total",
    "estimated_final_kmean_d",
    "evaluate_normalized_case",
    "evaluate_ps3",
    "final_kmean_hard_stop",
    "independent_hard_stop",
    "lasik_pta_hard_stop",
    "lasik_pta_percent",
    "lasik_rsb_hard_stop",
    "lasik_rsb_um",
    "nice_disposition",
    "plan_payload",
    "plan_responsive_failure",
    "planning_summary",
    "preop_thickness_hard_stop",
    "presentation_class",
    "prk_rst_hard_stop",
    "prk_rst_um",
    "pta_cutoff",
    "score_nice",
    "signed_i_s_category",
    "sphere_magnitude_hard_stop",
]
