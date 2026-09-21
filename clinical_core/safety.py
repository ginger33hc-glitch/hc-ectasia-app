"""Pure CER-AI procedural safety calculations.

Hard stops follow the master order and subsequent approved amendments.
LASIK and PRK PTA at or above 40.0% fail the evaluated plan.
"""
from __future__ import annotations

from math import isfinite

PRK_EPITHELIUM_UM = 50.0
LASIK_RSB_MIN_UM = 300.0
PRK_RST_MIN_UM = 310.0
PTA_LIMIT_PERCENT = 40.0
MYOPIC_CORNEAL_EFFECT_PER_INTENDED_MRSE_D = 0.8
HYPEROPIC_SCREENING_EFFECT_PER_INTENDED_MRSE_D = 1.0
FINAL_KMEAN_MIN_D = 36.0
FINAL_KMEAN_MAX_D = 48.0
HYPEROPIC_FINAL_K_REVIEW_D = 48.0
HYPEROPIC_FINAL_K_ENHANCED_REVIEW_D = 49.0
HYPEROPIC_TREATMENT_ENHANCED_REVIEW_D = 4.0
PREOP_THINNEST_HARD_STOP_UM = 480.0
MYOPIC_SPHERE_LIMIT_D = -10.0
HYPEROPIC_SPHERE_LIMIT_D = 6.0


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def ablation_um_is_valid(ablation_um) -> bool:
    """Return whether an ablation value is finite and physically nonnegative."""
    return _finite(ablation_um) and float(ablation_um) >= 0.0


def lasik_rsb_um(thinnest_um, flap_um, ablation_um):
    if not all(_finite(x) for x in (thinnest_um, flap_um)) or not ablation_um_is_valid(ablation_um):
        return None
    return float(thinnest_um) - float(flap_um) - float(ablation_um)


def prk_rst_um(thinnest_um, ablation_um):
    if not _finite(thinnest_um) or not ablation_um_is_valid(ablation_um):
        return None
    return float(thinnest_um) - PRK_EPITHELIUM_UM - float(ablation_um)


def pta_percent(thinnest_um, anterior_tissue_um, ablation_um):
    """PTA using LASIK flap thickness or fixed PRK epithelial thickness."""
    if (
        not all(_finite(x) for x in (thinnest_um, anterior_tissue_um))
        or not ablation_um_is_valid(ablation_um)
        or float(thinnest_um) <= 0
    ):
        return None
    return 100.0 * (float(anterior_tissue_um) + float(ablation_um)) / float(thinnest_um)


def estimated_final_kmean_d(preop_kmean_d, intended_mrse_d, refractive_group):
    """Return the sole canonical postoperative Kmean estimate.

    The 0.8 coefficient is limited to myopic treatments. Hyperopic treatments
    use the conservative 1.0 screening heuristic and must not be interpreted as
    a laser-platform prediction. Mixed astigmatism has no validated scalar
    final-K model and therefore returns ``None``.
    """
    if not all(_finite(x) for x in (preop_kmean_d, intended_mrse_d)):
        return None
    group = str(refractive_group or "").upper()
    if group == "MYOPIC":
        coefficient = MYOPIC_CORNEAL_EFFECT_PER_INTENDED_MRSE_D
    elif group == "HYPEROPIC":
        coefficient = HYPEROPIC_SCREENING_EFFECT_PER_INTENDED_MRSE_D
    elif group == "PLANO":
        coefficient = 0.0
    else:
        return None
    return float(preop_kmean_d) + coefficient * float(intended_mrse_d)


def preop_thickness_hard_stop(thinnest_um) -> bool:
    return _finite(thinnest_um) and float(thinnest_um) < PREOP_THINNEST_HARD_STOP_UM


def lasik_rsb_hard_stop(rsb_um) -> bool:
    return _finite(rsb_um) and float(rsb_um) < LASIK_RSB_MIN_UM


def pta_hard_stop(pta_percent) -> bool:
    return _finite(pta_percent) and float(pta_percent) >= PTA_LIMIT_PERCENT


def prk_rst_hard_stop(rst_um) -> bool:
    return _finite(rst_um) and float(rst_um) < PRK_RST_MIN_UM


def final_kmean_hard_stop(final_kmean_d, refractive_group) -> bool:
    """Apply the 36-48 D hard-stop interval only to the myopic model."""
    return (
        str(refractive_group or "").upper() == "MYOPIC"
        and _finite(final_kmean_d)
        and not (FINAL_KMEAN_MIN_D <= float(final_kmean_d) <= FINAL_KMEAN_MAX_D)
    )


def hyperopic_final_k_review_level(final_kmean_d, refractive_group):
    """Return the evidence-based review level for a hyperopic Kmean screen."""
    if str(refractive_group or "").upper() != "HYPEROPIC" or not _finite(final_kmean_d):
        return None
    value = float(final_kmean_d)
    if value >= HYPEROPIC_FINAL_K_ENHANCED_REVIEW_D:
        return "MANDATORY_PLATFORM_OR_SURGEON_CONFIRMATION"
    if value >= HYPEROPIC_FINAL_K_REVIEW_D:
        return "PLATFORM_VERIFICATION"
    return None


def sphere_magnitude_hard_stop(intended_sphere_d) -> bool:
    if not _finite(intended_sphere_d):
        return False
    value = float(intended_sphere_d)
    return value < MYOPIC_SPHERE_LIMIT_D or value > HYPEROPIC_SPHERE_LIMIT_D
