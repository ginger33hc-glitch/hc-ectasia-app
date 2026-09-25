"""Published numerical example, Langenbucher et al., 2021, Table 2."""

from research.toric_vergence import CastropEye, Vergence, continuous_toric_power


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
