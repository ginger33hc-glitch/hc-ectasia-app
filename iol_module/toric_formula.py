"""Castrop toric vergence core inside the IOL module; clinical routing disabled.

Independent implementation of the published Castrop paraxial model. It returns
continuous optical powers, not an implant model or a clinical recommendation.
Its ELP calculation requires measured crystalline lens thickness and optimized
C/H/R constants for the particular lens. K6's optical A-constant alone does
not supply those quantities; do not silently substitute guessed values.
See https://doi.org/10.1007/s00417-021-05287-w (equations 1–4).
"""

from dataclasses import dataclass
from math import atan2, cos, degrees, hypot, isfinite, radians, sin, sqrt


# Nominal cylinder at the IOL plane. These are optical steps, not inventory
# assertions. PanOptix regional availability must be verified before release.
# Clareon Toric: FDA PMA P190018, SSED Table 3 (P190018B).
# PanOptix: Japanese ophthalmic device registry's CNWTT2–6 listing.
# TECNIS Eyhance: Johnson & Johnson EMEA product catalogue, model/power table.
VERIFIED_LENS_STEPS: dict[str, dict[str, float]] = {
    "clareon-toric-cnw0t8": {
        "CNW0T3": 1.50, "CNW0T4": 2.25, "CNW0T5": 3.00,
        "CNW0T6": 3.75, "CNW0T7": 4.50, "CNW0T8": 5.25,
        "CNW0T9": 6.00,
    },
    "clareon-panoptix-toric-cnwtt3": {
        "CNWTT2": 1.00, "CNWTT3": 1.50, "CNWTT4": 2.25,
        "CNWTT5": 3.00, "CNWTT6": 3.75,
    },
    "tecnis-eyhance-toric-diu525": {
        "DIU100": 1.00, "DIU150": 1.50, "DIU225": 2.25,
        "DIU300": 3.00, "DIU375": 3.75, "DIU450": 4.50,
        "DIU525": 5.25,
    },
}


def holladay1_elp_mm(axial_length_mm: float, mean_k_d: float, optical_a_constant: float) -> float:
    """Published Holladay 1 ELP with Alcon's A-constant to SF conversion.

    Cooke & Aramberri (2024), Holladay Formulas, eqs. 44.7–44.10;
    Alcon IOL Lens Constant Optimization white paper, Appendix A:
    SF = 0.5663 * optical A - 65.6008. This predicts an effective optical
    position without requiring crystalline lens thickness. Research only:
    toric IOL model/axis selection still requires validated full-eye optics.
    """
    if not all(isfinite(v) for v in (axial_length_mm, mean_k_d, optical_a_constant)):
        raise ValueError("Holladay 1 inputs must be finite.")
    if not 12 <= axial_length_mm <= 40 or not 20 <= mean_k_d <= 80:
        raise ValueError("Axial length and mean K are outside the source's bounds.")
    radius_mm = max(7.0, 337.5 / mean_k_d)
    diameter_mm = min(13.5, 12.5 * axial_length_mm / 23.45)
    surgeon_factor_mm = 0.5663 * optical_a_constant - 65.6008
    elp_mm = 0.56 + radius_mm - sqrt(radius_mm**2 - diameter_mm**2 / 4) + surgeon_factor_mm
    if not 0 < elp_mm < axial_length_mm:
        raise ValueError("Calculated ELP is outside optical eye bounds.")
    return elp_mm


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
    biometric = (eye.axial_length_mm, eye.acd_external_mm, eye.crystalline_lens_thickness_mm,
                 eye.corneal_thickness_um, eye.anterior_r1_mm, eye.anterior_r2_mm,
                 eye.posterior_r1_mm, eye.posterior_r2_mm)
    remaining = (eye.anterior_flat_axis_deg, eye.posterior_first_axis_deg,
                 eye.constant_c, eye.constant_h_mm, eye.constant_r_d,
                 eye.sia_d, eye.sia_axis_deg, eye.posterior_correction_d,
                 target_sphere_d, target_cylinder_d, target_axis_deg)
    if not all(isfinite(value) for value in (*biometric, *remaining)):
        raise ValueError("Optical inputs and constants must be finite.")
    if min(biometric) <= 0:
        raise ValueError("Biometry and radii must be positive.")
    if eye.sia_d < 0:
        raise ValueError("SIA must be nonnegative.")
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


@dataclass(frozen=True)
class ToricOpticalCandidate:
    model: str
    cylinder_iol_plane_d: float
    marker_axis_deg: float
    residual_iol_plane_d: float


def nearest_optical_step(required: Vergence, selected_lens_id: str) -> ToricOpticalCandidate:
    """Rank listed Alcon steps in the IOL plane; research only.

    Marker axis corresponds to plus-cylinder flat meridian (FDA P190018B).
    This IOL-plane residual is NOT a predicted postoperative spectacle Rx.
    K6/Castrop spherical compatibility, availability and clinical concordance
    remain unverified; never expose this as an implant recommendation.
    """
    steps = VERIFIED_LENS_STEPS.get(selected_lens_id)
    if not steps:
        raise ValueError("No verified cylinder series for the selected lens family.")
    if not all(isfinite(v) for v in (required.equivalent_d, required.c0_d, required.c45_d)):
        raise ValueError("The optical toric result must be finite.")
    model, cylinder = min(steps.items(), key=lambda item: (abs(item[1] - required.cylinder_d), item[1]))
    lens_vector = Vergence.from_meridians(-cylinder / 2, cylinder / 2, required.axis_deg)
    residual = required + (-lens_vector)
    return ToricOpticalCandidate(model, cylinder, required.axis_deg, residual.cylinder_d)


@dataclass(frozen=True)
class ToricBiometry:
    """One-eye source-locked anterior and posterior measurements."""

    axial_length_mm: float
    anterior_k1_d: float
    anterior_k2_d: float
    anterior_k1_axis_deg: float
    posterior_k1_d: float
    posterior_k2_d: float
    posterior_k1_axis_deg: float
    corneal_thickness_um: float
    optical_a_constant: float
    sia_d: float = 0.25


@dataclass(frozen=True)
class ToricResearchResult:
    model: str
    spherical_equivalent_iol_d: float
    cylinder_iol_d: float
    marker_axis_deg: float
    residual_spectacle_cylinder_d: float
    residual_spectacle_axis_deg: float
    elp_mm: float


def research_toric_candidates(
    eye: ToricBiometry, selected_lens_id: str,
    *, k6_spherical_equivalent_iol_d: float,
    k6_predicted_refraction_d: float,
) -> list[ToricResearchResult]:
    """K6-anchored thick-cornea/Holladay-ELP optical prototype.

    NOT a published unified formula or clinically validated calculator.
    K6's spherical predicted refraction anchors the retinal scalar vergence;
    measured anterior and posterior meridians drive toricity. Each discrete
    model's marker axis is optimized for the lowest spectacle-plane cylinder.
    External paired-case validation is mandatory before patient routing.
    """
    steps = VERIFIED_LENS_STEPS.get(selected_lens_id)
    if not steps:
        raise ValueError("No verified model series for this lens family.")
    numbers = (eye.axial_length_mm, eye.anterior_k1_d, eye.anterior_k2_d,
               eye.anterior_k1_axis_deg, eye.posterior_k1_d, eye.posterior_k2_d,
               eye.posterior_k1_axis_deg, eye.corneal_thickness_um,
               eye.optical_a_constant, eye.sia_d,
               k6_spherical_equivalent_iol_d, k6_predicted_refraction_d)
    if not all(isfinite(v) for v in numbers):
        raise ValueError("Toric source values must be finite.")
    if not (30 <= eye.anterior_k1_d <= eye.anterior_k2_d <= 60
            and -12 <= eye.posterior_k2_d <= eye.posterior_k1_d < 0
            and 0 <= eye.anterior_k1_axis_deg <= 180
            and 0 <= eye.posterior_k1_axis_deg <= 180
            and 300 <= eye.corneal_thickness_um <= 900
            and 0 <= eye.sia_d <= 2):
        raise ValueError("Corneal readings or SIA are outside supported ranges.")
    elp_mm = holladay1_elp_mm(
        eye.axial_length_mm, (eye.anterior_k1_d + eye.anterior_k2_d) / 2,
        eye.optical_a_constant)
    cct_mm = eye.corneal_thickness_um / 1000
    if elp_mm <= cct_mm:
        raise ValueError("Predicted ELP must lie behind the posterior cornea.")
    nc, na = 1.376, 1.336
    anterior_r1_mm = 337.5 / eye.anterior_k1_d
    anterior_r2_mm = 337.5 / eye.anterior_k2_d
    anterior = Vergence.from_meridians(
        (nc - 1) * 1000 / anterior_r1_mm,
        (nc - 1) * 1000 / anterior_r2_mm, eye.anterior_k1_axis_deg)
    # Cornea Back's signed powers express the true index change, -.040 / r.
    # Do not interpret horizontal/vertical Rh/Rv as principal radii.
    posterior = Vergence.from_meridians(
        eye.posterior_k1_d, eye.posterior_k2_d,
        eye.posterior_k1_axis_deg)
    incision_axis = (eye.anterior_k1_axis_deg + 90) % 180
    sia = Vergence.from_meridians(-eye.sia_d / 2, eye.sia_d / 2,
                                 incision_axis)

    def propagate_to_iol(spectacle: Vergence) -> Vergence:
        front = spectacle.propagate(0.012, 1.0) + anterior + sia
        back = front.propagate(cct_mm / 1000, nc) + posterior
        return back.propagate((elp_mm - cct_mm) / 1000, na)

    def back_to_spectacle(iol: Vergence) -> Vergence:
        back = iol.propagate(-(elp_mm - cct_mm) / 1000, na) + (-posterior)
        front = back.propagate(-cct_mm / 1000, nc) + (-anterior) + (-sia)
        return front.propagate(-0.012, 1.0)

    target = Vergence(k6_predicted_refraction_d, 0, 0)
    incoming = propagate_to_iol(target)
    retinal_scalar = incoming.equivalent_d + k6_spherical_equivalent_iol_d
    results = []
    for model, cylinder in steps.items():
        def spectacle_residual(axis_deg: float) -> Vergence:
            lens = Vergence.from_meridians(
                k6_spherical_equivalent_iol_d - cylinder / 2,
                k6_spherical_equivalent_iol_d + cylinder / 2,
                axis_deg)
            return back_to_spectacle(Vergence(retinal_scalar, 0, 0) + (-lens))

        coarse_axis = min(range(180), key=lambda axis: spectacle_residual(axis).cylinder_d)
        best_axis = min(((coarse_axis + delta / 10) % 180 for delta in range(-10, 11)),
                        key=lambda axis: spectacle_residual(axis).cylinder_d)
        refraction = spectacle_residual(best_axis)
        results.append(ToricResearchResult(
            model, k6_spherical_equivalent_iol_d, cylinder, best_axis,
            refraction.cylinder_d, refraction.axis_deg, elp_mm))
    return sorted(results, key=lambda result: (result.residual_spectacle_cylinder_d,
                                                result.cylinder_iol_d))
