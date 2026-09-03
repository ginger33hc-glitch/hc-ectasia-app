"""Pure CER-AI procedural safety calculations frozen by the launch contract.

No FastAPI imports, runtime mutation, reporting, or persistence concerns.
"""
from __future__ import annotations

from math import isfinite

PRK_EPITHELIUM_UM = 50.0
LASIK_RSB_MIN_UM = 300.0
PRK_RST_MIN_UM = 310.0
LASIK_PTA_CUTOFF_PERCENT = 40.0
CORNEAL_EFFECT_PER_INTENDED_MRSE_D = 0.8
FINAL_KMEAN_MIN_D = 36.0
FINAL_KMEAN_MAX_D = 48.0
PREOP_THINNEST_HARD_STOP_UM = 480.0
MYOPIC_SPHERE_LIMIT_D = -10.0
HYPEROPIC_SPHERE_LIMIT_D = 6.0


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def lasik_rsb_um(thinnest_um, flap_um, ablation_um):
    if not all(_finite(x) for x in (thinnest_um, flap_um, ablation_um)):
        return None
    return float(thinnest_um) - float(flap_um) - float(ablation_um)


def prk_rst_um(thinnest_um, ablation_um):
    if not all(_finite(x) for x in (thinnest_um, ablation_um)):
        return None
    return float(thinnest_um) - PRK_EPITHELIUM_UM - float(ablation_um)


def lasik_pta_percent(thinnest_um, flap_um, ablation_um):
    if not all(_finite(x) for x in (thinnest_um, flap_um, ablation_um)) or float(thinnest_um) <= 0:
        return None
    return 100.0 * (float(flap_um) + float(ablation_um)) / float(thinnest_um)


def estimated_final_kmean_d(preop_kmean_d, intended_mrse_d):
    if not all(_finite(x) for x in (preop_kmean_d, intended_mrse_d)):
        return None
    return float(preop_kmean_d) + CORNEAL_EFFECT_PER_INTENDED_MRSE_D * float(intended_mrse_d)


def preop_thickness_hard_stop(thinnest_um) -> bool:
    return _finite(thinnest_um) and float(thinnest_um) < PREOP_THINNEST_HARD_STOP_UM


def lasik_rsb_hard_stop(rsb_um) -> bool:
    return _finite(rsb_um) and float(rsb_um) < LASIK_RSB_MIN_UM


def prk_rst_hard_stop(rst_um) -> bool:
    return _finite(rst_um) and float(rst_um) < PRK_RST_MIN_UM


def lasik_pta_hard_stop(pta_percent) -> bool:
    return _finite(pta_percent) and float(pta_percent) >= LASIK_PTA_CUTOFF_PERCENT


def final_kmean_hard_stop(final_kmean_d) -> bool:
    return _finite(final_kmean_d) and not (FINAL_KMEAN_MIN_D <= float(final_kmean_d) <= FINAL_KMEAN_MAX_D)


def sphere_magnitude_hard_stop(intended_sphere_d) -> bool:
    if not _finite(intended_sphere_d):
        return False
    value = float(intended_sphere_d)
    return value < MYOPIC_SPHERE_LIMIT_D or value > HYPEROPIC_SPHERE_LIMIT_D
