"""Pure launch-contract clinical rules for CER-AI.

This package is intentionally side-effect free. It does not import the FastAPI
application, mutate runtime functions, or participate in production composition
until explicit equivalence gates are satisfied.
"""

from .disposition import combine_status, presentation_class
from .nice import nice_disposition, score_nice
from .rules import (
    bad_d_classification,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
)

__all__ = [
    "bad_d_classification",
    "combine_status",
    "erss_age_points",
    "erss_pachymetry_points",
    "erss_topography_category",
    "nice_disposition",
    "presentation_class",
    "score_nice",
    "signed_i_s_category",
]
