"""Research input contract for Clareon PanOptix Toric; no clinical selection.

Model suffixes are product steps, not diopters. The IOL-plane cylinders are
documented in Alcon's product specifications and Australian device listing.
"""

from dataclasses import dataclass
from math import isfinite
from iol_module.toric_formula import SURGEON_SIA_D


@dataclass(frozen=True)
class IOLMaster500ToricInput:
    """Anterior keratometry as read from a single eye's standard printout.

    Axes use degrees modulo 180. This object does not infer posterior corneal
    astigmatism, ELP, an IOL spherical power, or an implant recommendation.
    """

    k1_d: float
    k2_d: float
    k1_axis_deg: float
    k2_axis_deg: float

    def __post_init__(self):
        values = (self.k1_d, self.k2_d, self.k1_axis_deg, self.k2_axis_deg)
        if not all(isfinite(value) for value in values):
            raise ValueError("K readings and axes must be finite.")
        if not 20 <= self.k1_d <= self.k2_d <= 70:
            raise ValueError("K1 must be positive and no greater than K2.")
        if not all(0 <= axis <= 180 for axis in (self.k1_axis_deg, self.k2_axis_deg)):
            raise ValueError("K axes must be in the 0–180 degree range.")
        separation = (self.k2_axis_deg - self.k1_axis_deg) % 180
        if abs(separation - 90) > 5:
            raise ValueError("K1 and K2 axes must be approximately perpendicular.")

    @property
    def incision_axis_deg(self) -> float:
        """Surgeon's specified steep meridian: the measured K2 axis."""
        return self.k2_axis_deg % 180

    @property
    def sia_d(self) -> float:
        return SURGEON_SIA_D


@dataclass(frozen=True)
class PentacamPosteriorInput:
    """Same-eye 4 Maps Refractive / Cornea Back numeric panel.

    Rh and Rv are measured horizontal and vertical radii, not necessarily the
    flat and steep cardinal radii required by Castrop in an oblique cornea.
    K1/K2 are signed posterior powers whose optical convention needs checking
    before reconstructing the cardinal radii. No clinical conversion here.
    """

    eye: str
    posterior_k1_d: float
    posterior_k2_d: float
    posterior_k1_axis_deg: float
    posterior_rh_mm: float
    posterior_rv_mm: float
    source_screen: str = "4 Maps Refractive / Cornea Back"

    def __post_init__(self):
        if self.eye not in ("OD", "OS"):
            raise ValueError("Posterior readings must be assigned to OD or OS.")
        if self.source_screen != "4 Maps Refractive / Cornea Back":
            raise ValueError("Posterior readings need their source-locked panel.")
        values = (self.posterior_k1_d, self.posterior_k2_d,
                  self.posterior_k1_axis_deg, self.posterior_rh_mm,
                  self.posterior_rv_mm)
        if not all(isfinite(value) for value in values):
            raise ValueError("Posterior readings and axis must be finite.")
        if not (-12 <= self.posterior_k2_d <= self.posterior_k1_d < 0):
            raise ValueError("Posterior K powers must be signed negative values.")
        if not 0 <= self.posterior_k1_axis_deg <= 180:
            raise ValueError("Posterior K1 axis must be in the 0–180 range.")
        if not all(3 <= radius <= 12 for radius in
                   (self.posterior_rh_mm, self.posterior_rv_mm)):
            raise ValueError("Posterior Rh and Rv must be physical millimeter radii.")
