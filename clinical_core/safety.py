"""Pure CER-AI procedural safety calculations.

Hard stops follow the master order and subsequent approved amendments.
LASIK and PRK PTA at or above 40.0% fail the evaluated plan.
"""
from __future__ import annotations

from math import atan2, cos, degrees, isfinite, radians, sin, sqrt

PRK_EPITHELIUM_UM = 50.0
LASIK_RSB_MIN_UM = 300.0
PRK_RST_MIN_UM = 310.0
PTA_LIMIT_PERCENT = 40.0
CORNEAL_EFFECT_PER_INTENDED_MRSE_D = 0.8
FINAL_KMEAN_MIN_D = 36.0
FINAL_KMEAN_MAX_D = 48.0
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


def estimated_final_kmean_d(preop_kmean_d, intended_mrse_d):
    if not all(_finite(x) for x in (preop_kmean_d, intended_mrse_d)):
        return None
    return float(preop_kmean_d) + CORNEAL_EFFECT_PER_INTENDED_MRSE_D * float(intended_mrse_d)


def predicted_postop_keratometry(
    preop_k1_d,
    preop_k2_d,
    preop_kmean_d,
    preop_flat_axis_deg,
    intended_sphere_d,
    intended_cylinder_d,
    intended_axis_deg,
):
    """Predict postoperative principal K values with one canonical power-vector model.

    The preoperative cornea and intended spherocylindrical treatment are added in
    Thibos M/J0/J45 space.  CER-AI's approved 0.8 corneal-effect factor is applied
    to the complete intended treatment vector, so the result reduces exactly to
    the existing Kmean + 0.8 * MRSE rule while remaining axis-aware.

    Basis: Thibos et al., Optom Vis Sci 1997;74:367-375; Thibos et al.,
    J Cataract Refract Surg 2001;27:80-85; Moshirfar et al., Clin Ophthalmol
    2023;17:2563-2573 (doi:10.2147/OPTH.S423087).
    """
    values = (
        preop_k1_d, preop_k2_d, preop_kmean_d, preop_flat_axis_deg,
        intended_sphere_d, intended_cylinder_d, intended_axis_deg,
    )
    if not all(_finite(value) for value in values):
        return None

    k1 = float(preop_k1_d)
    k2 = float(preop_k2_d)
    if k2 < k1:
        return None

    flat_axis = float(preop_flat_axis_deg) % 180.0
    treatment_axis = float(intended_axis_deg) % 180.0
    cylinder = float(intended_cylinder_d)
    k_astigmatism = k2 - k1

    corneal_j0 = -(k_astigmatism / 2.0) * cos(radians(2.0 * flat_axis))
    corneal_j45 = -(k_astigmatism / 2.0) * sin(radians(2.0 * flat_axis))
    treatment_m = CORNEAL_EFFECT_PER_INTENDED_MRSE_D * (
        float(intended_sphere_d) + cylinder / 2.0
    )
    treatment_j0 = CORNEAL_EFFECT_PER_INTENDED_MRSE_D * (
        -(cylinder / 2.0) * cos(radians(2.0 * treatment_axis))
    )
    treatment_j45 = CORNEAL_EFFECT_PER_INTENDED_MRSE_D * (
        -(cylinder / 2.0) * sin(radians(2.0 * treatment_axis))
    )

    final_mean = float(preop_kmean_d) + treatment_m
    final_j0 = corneal_j0 + treatment_j0
    final_j45 = corneal_j45 + treatment_j45
    final_astigmatism_half = sqrt(final_j0 ** 2 + final_j45 ** 2)

    if final_astigmatism_half <= 1e-12:
        final_flat_axis = None
        final_steep_axis = None
    else:
        final_flat_axis = (0.5 * degrees(atan2(-final_j45, -final_j0))) % 180.0
        if abs(final_flat_axis - 180.0) <= 1e-10:
            final_flat_axis = 0.0
        final_steep_axis = (final_flat_axis + 90.0) % 180.0

    return {
        "flat_D": final_mean - final_astigmatism_half,
        "steep_D": final_mean + final_astigmatism_half,
        "mean_D": final_mean,
        "flat_axis_deg": final_flat_axis,
        "steep_axis_deg": final_steep_axis,
        "method": "THIBOS_POWER_VECTOR_0.8_INTENDED_TREATMENT",
    }


def preop_thickness_hard_stop(thinnest_um) -> bool:
    return _finite(thinnest_um) and float(thinnest_um) < PREOP_THINNEST_HARD_STOP_UM


def lasik_rsb_hard_stop(rsb_um) -> bool:
    return _finite(rsb_um) and float(rsb_um) < LASIK_RSB_MIN_UM


def pta_hard_stop(pta_percent) -> bool:
    return _finite(pta_percent) and float(pta_percent) >= PTA_LIMIT_PERCENT


def prk_rst_hard_stop(rst_um) -> bool:
    return _finite(rst_um) and float(rst_um) < PRK_RST_MIN_UM


def final_kmean_hard_stop(final_kmean_d) -> bool:
    return _finite(final_kmean_d) and not (FINAL_KMEAN_MIN_D <= float(final_kmean_d) <= FINAL_KMEAN_MAX_D)


def sphere_magnitude_hard_stop(intended_sphere_d) -> bool:
    if not _finite(intended_sphere_d):
        return False
    value = float(intended_sphere_d)
    return value < MYOPIC_SPHERE_LIMIT_D or value > HYPEROPIC_SPHERE_LIMIT_D
