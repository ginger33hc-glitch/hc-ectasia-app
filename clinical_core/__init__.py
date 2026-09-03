"""Pure launch-contract clinical rules for CER-AI.

This package is intentionally side-effect free. It does not import the FastAPI
application, mutate runtime functions, or participate in production composition
until explicit equivalence gates are satisfied.
"""

from .rules import (
    bad_d_classification,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
)

__all__ = [
    "bad_d_classification",
    "erss_age_points",
    "erss_pachymetry_points",
    "erss_topography_category",
    "signed_i_s_category",
]
