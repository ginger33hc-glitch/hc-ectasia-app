"""Research-only toric vergence calculation; not connected to patient workflows.

Independent implementation of the published Castrop paraxial model. It returns
continuous optical powers, not an implant model or a clinical recommendation.
See https://doi.org/10.1007/s00417-021-05287-w (equations 1–4).
"""

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, radians, sin


@dataclass(frozen=True)
class Vergence:
    equivalent_d: float
    c0_d: float
    c45_d: float

    @classmethod
    def from_meridians(cls, first_d: float, second_d: float, first_axis_deg: float):
        cylinder = second_d - first_d
        angle = radians(2 * first_axis_deg)
        return cls((first_d + second_d) / 2, cylinder * cos(angle), cylinder * sin(angle))

    def __add__(self, other):
        return Vergence(self.equivalent_d + other.equivalent_d,
                        self.c0_d + other.c0_d, self.c45_d + other.c45_d)

    def __neg__(self):
        return Vergence(-self.equivalent_d, -self.c0_d, -self.c45_d)

    @property
    def cylinder_d(self):
        return hypot(self.c0_d, self.c45_d)

    @property
    def sphere_d(self):
        return self.equivalent_d - self.cylinder_d / 2

    @property
    def axis_deg(self):
        return (degrees(atan2(self.c45_d, self.c0_d)) / 2) % 180

    def propagate(self, distance_m: float, refractive_index: float):
        """Move vergence through a homogeneous medium, independently by meridian."""
        cylinder = self.cylinder_d
        flat = self.equivalent_d - cylinder / 2
        steep = self.equivalent_d + cylinder / 2
        first = flat / (1 - flat * distance_m / refractive_index)
        second = steep / (1 - steep * distance_m / refractive_index)
        return Vergence.from_meridians(first, second, self.axis_deg)


@dataclass(frozen=True)
class CastropEye:
    axial_length_mm: float
    acd_external_mm: float
    crystalline_lens_thickness_mm: float
    corneal_thickness_um: float
    anterior_r1_mm: float
    anterior_r2_mm: float
    anterior_flat_axis_deg: float
    posterior_r1_mm: float
    posterior_r2_mm: float
    posterior_first_axis_deg: float
    constant_c: float
    constant_h_mm: float
    constant_r_d: float
    sia_d: float = 0
    sia_axis_deg: float = 0
    posterior_correction_d: float = 0


def continuous_toric_power(eye: CastropEye, *, target_sphere_d: float,
                           target_cylinder_d: float = 0, target_axis_deg: float = 0) -> Vergence:
    """Calculate optical power at IOL plane; no discrete lens selection."""
    if min(eye.axial_length_mm, eye.acd_external_mm, eye.crystalline_lens_thickness_mm,
           eye.corneal_thickness_um, eye.anterior_r1_mm, eye.anterior_r2_mm,
           eye.posterior_r1_mm, eye.posterior_r2_mm) <= 0:
        raise ValueError("Biometry and radii must be positive.")
    nc, na, nv = 1.376, 1.336, 1.336
    al_corrected_mm = (1.23854 + 0.95855 * eye.axial_length_mm
                       - 0.05467 * eye.crystalline_lens_thickness_mm)
    elp_mm = (eye.acd_external_mm + eye.constant_c * eye.crystalline_lens_thickness_mm
              + eye.constant_h_mm)
    cct_mm = eye.corneal_thickness_um / 1000
    if not cct_mm < elp_mm < al_corrected_mm:
        raise ValueError("Effective lens position is outside optical bounds.")

    target = Vergence.from_meridians(target_sphere_d,
                                    target_sphere_d + target_cylinder_d, target_axis_deg)
    correction = Vergence(-eye.constant_r_d, 0, 0)
    anterior = Vergence.from_meridians(
        (nc - 1) * 1000 / eye.anterior_r1_mm,
        (nc - 1) * 1000 / eye.anterior_r2_mm, eye.anterior_flat_axis_deg)
    posterior = Vergence.from_meridians(
        (na - nc) * 1000 / eye.posterior_r1_mm,
        (na - nc) * 1000 / eye.posterior_r2_mm, eye.posterior_first_axis_deg)
    sia = Vergence.from_meridians(-eye.sia_d / 2, eye.sia_d / 2, eye.sia_axis_deg)
    posterior_adjustment = Vergence(0, -eye.posterior_correction_d, 0)

    at_front = (target + correction).propagate(0.012, 1.0)
    at_back = (at_front + anterior + sia + posterior_adjustment).propagate(cct_mm / 1000, nc)
    at_iol = (at_back + posterior).propagate((elp_mm - cct_mm) / 1000, na)
    at_retina = Vergence(nv * 1000 / (al_corrected_mm - elp_mm), 0, 0)
    return at_retina + (-at_iol)
