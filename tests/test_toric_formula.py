"""Published numerical example, Langenbucher et al., 2021, Table 2."""

from iol_module.toric_formula import (CastropEye, Vergence, continuous_toric_power,
                                      ToricBiometry, holladay1_elp_mm,
                                      nearest_optical_step, research_toric_candidates)
import pytest


def test_published_tomography_example_one():
    eye = CastropEye(
        axial_length_mm=23.7, acd_external_mm=3.5,
        crystalline_lens_thickness_mm=4.1, corneal_thickness_um=550,
        anterior_r1_mm=7.9, anterior_r2_mm=7.6, anterior_flat_axis_deg=10,
        posterior_r1_mm=6.8, posterior_r2_mm=6.6, posterior_first_axis_deg=20,
        constant_c=0.424, constant_h_mm=-0.312, constant_r_d=0.077,
    )
    result = continuous_toric_power(
        eye, target_sphere_d=-0.1, target_cylinder_d=-0.1, target_axis_deg=90,
    )
    assert abs(result.sphere_d - 19.32) < 0.01
    assert abs(result.cylinder_d - 2.56) < 0.01
    assert abs(result.equivalent_d - 20.60) < 0.01
    assert abs(result.axis_deg - 99) < 0.6


def test_double_angle_vector_cancellation():
    first = Vergence.from_meridians(-0.1, 0.1, 0)
    opposite = Vergence.from_meridians(-0.1, 0.1, 90)
    assert abs((first + opposite).cylinder_d) < 1e-12


def test_holladay1_position_needs_no_crystalline_lens_thickness():
    # Eq. 44.10, with Alcon's published A to surgeon-factor conversion.
    elp = holladay1_elp_mm(23.45, 43.0, 119.1)
    assert 5.0 < elp < 6.0
    assert holladay1_elp_mm(23.45, 44.0, 119.1) != elp
    with pytest.raises(ValueError):
        holladay1_elp_mm(23.45, float("nan"), 119.1)


def test_optical_step_does_not_claim_spectacle_residual():
    optical = Vergence.from_meridians(19.5, 21.7, 83)
    choice = nearest_optical_step(optical, "clareon-panoptix-toric-cnwtt3")
    assert choice.model == "CNWTT4"
    assert choice.cylinder_iol_plane_d == 2.25
    assert choice.marker_axis_deg == 83
    assert abs(choice.residual_iol_plane_d - 0.05) < 1e-9
    with pytest.raises(ValueError):
        nearest_optical_step(optical, "enova-advance-toric")


def test_research_planner_ranks_discrete_panoptix_steps_and_respects_axes():
    eye = ToricBiometry(24, 42, 43.5, 90, -5.8, -6.1, 0, 550, 119.1)
    values = research_toric_candidates(
        eye, "clareon-panoptix-toric-cnwtt3",
        k6_spherical_equivalent_iol_d=20, k6_predicted_refraction_d=-0.25)
    assert [v.model for v in values] == ["CNWTT4", "CNWTT5", "CNWTT3", "CNWTT6", "CNWTT2"]
    assert values[0].marker_axis_deg == 0
    assert 0.15 < values[0].residual_spectacle_cylinder_d < 0.25
    rotated = ToricBiometry(24, 42, 43.5, 120, -5.8, -6.1, 30, 550, 119.1)
    rotated_values = research_toric_candidates(
        rotated, "clareon-panoptix-toric-cnwtt3",
        k6_spherical_equivalent_iol_d=20, k6_predicted_refraction_d=-0.25)
    assert rotated_values[0].model == values[0].model
    assert abs(rotated_values[0].marker_axis_deg - 30) < 0.2
    assert abs(rotated_values[0].residual_spectacle_cylinder_d - values[0].residual_spectacle_cylinder_d) < 1e-8


def test_average_eye_corneal_conversion_is_close_to_fda_reference_not_fixed_ratio():
    eye = ToricBiometry(24, 43, 43, 0, -5.8, -5.8, 0, 550, 119.1, sia_d=0)
    values = research_toric_candidates(
        eye, "clareon-toric-cnw0t8",
        k6_spherical_equivalent_iol_d=20, k6_predicted_refraction_d=0)
    t3 = next(value for value in values if value.model == "CNW0T3")
    # FDA P190018B lists 0.98 D in its average pseudophakic model eye.
    # This synthetic eye is not that FDA eye and agreement is not clinical validation.
    assert abs(t3.residual_spectacle_cylinder_d - 0.98) < 0.05
    assert len(values) == 7


def test_research_planner_rejects_missing_catalog_or_nonfinite_sources():
    eye = ToricBiometry(24, 42, 43.5, 90, -5.8, -6.1, 0, 550, 119.1)
    with pytest.raises(ValueError):
        research_toric_candidates(eye, "enova-advance-toric",
                                  k6_spherical_equivalent_iol_d=20,
                                  k6_predicted_refraction_d=-0.25)
    with pytest.raises(ValueError):
        research_toric_candidates(eye, "clareon-panoptix-toric-cnwtt3",
                                  k6_spherical_equivalent_iol_d=float("nan"),
                                  k6_predicted_refraction_d=-0.25)
