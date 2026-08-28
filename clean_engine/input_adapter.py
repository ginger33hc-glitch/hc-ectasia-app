"""Typed boundary between extraction/reconciliation and clinical assessment.

The clean clinical engine must never inspect raw image-extraction payloads. This
adapter accepts already-adjudicated principal values and constructs EyeInput.
Reconciliation remains an explicit upstream responsibility.
"""
from dataclasses import dataclass
from typing import Optional

from .models import EyeInput


@dataclass(frozen=True)
class ReconciledEyeInput:
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


def to_eye_input(inp: ReconciledEyeInput) -> EyeInput:
    """Convert an adjudicated/reconciled record to the clean clinical input."""
    return EyeInput(
        age_years=inp.age_years,
        pachy_thinnest_um=inp.pachy_thinnest_um,
        bad_d=inp.bad_d,
        morphology=inp.morphology,
        procedure=inp.procedure,
        ablation_um=inp.ablation_um,
        flap_um=inp.flap_um,
        preop_kmean_d=inp.preop_kmean_d,
        intended_mrse_d=inp.intended_mrse_d,
        intended_sphere_d=inp.intended_sphere_d,
        intended_cylinder_magnitude_d=inp.intended_cylinder_magnitude_d,
        laser_platform=inp.laser_platform,
        use_lasik_fallback_planning=inp.use_lasik_fallback_planning,
    )
