from clinical_core.rules import signed_i_s_category


def test_negative_half_is_normal_boundary():
    assert signed_i_s_category(-0.50) == "NORMAL_SYMMETRIC"


def test_just_below_negative_half_is_abt():
    assert signed_i_s_category(-0.5001) == "ASYMMETRIC_BOWTIE"


def test_negative_one_point_one_four_is_abt():
    assert signed_i_s_category(-1.14) == "ASYMMETRIC_BOWTIE"


def test_far_negative_i_s_has_no_lower_limit_for_abt():
    assert signed_i_s_category(-5.0) == "ASYMMETRIC_BOWTIE"
