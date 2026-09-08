"""Boundary gates for the authoritative CER-AI clinical core.

Step-60 retirement note:
Old rule/test authority -> base ``app.py`` age/pachymetry/BAD helper functions.
New canonical authority -> ``clinical_core`` rule modules.
Why retired -> production assessment no longer executes the base clinical scorer;
comparing canonical rules to that dormant implementation would force duplicate
clinical truth back into the runtime.
"""

from clinical_core.bad import final_bad_d_classification
from clinical_core.rules import (
    UNCERTAIN,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
)


def test_canonical_age_points_boundaries():
    values = (17, 18, 18.999, 19, 20, 20.999, 21, 35)
    assert [erss_age_points(x) for x in values] == [None, 3, 3, 2, 2, 2, 0, 0]


def test_canonical_pachymetry_points_boundaries():
    values = (479, 480, 499, 500, 509, 510, 560)
    assert [erss_pachymetry_points(x) for x in values] == [None, 2, 2, 1, 1, 0, 0]


def test_canonical_final_bad_d_boundaries():
    values = (1.0, 1.6, 1.6001, 2.5999, 2.6, 3.0)
    assert [final_bad_d_classification(x) for x in values] == [
        "NORMAL", "NORMAL", "SUSPICIOUS", "SUSPICIOUS", "ABNORMAL", "ABNORMAL"
    ]


def test_signed_i_s_monday_boundaries():
    expected = {
        -0.51: "ASYMMETRIC_BOWTIE",
        -0.50: "NORMAL_SYMMETRIC",
        0.50: "NORMAL_SYMMETRIC",
        0.51: "ASYMMETRIC_BOWTIE",
        1.00: "ASYMMETRIC_BOWTIE",
        1.01: "INFERIOR_STEEPENING_SRA",
        1.39: "INFERIOR_STEEPENING_SRA",
        1.40: "ABNORMAL_ECTATIC",
    }
    assert {value: signed_i_s_category(value) for value in expected} == expected


def test_negative_i_s_has_no_artificial_lower_ast_limit():
    for value in (-0.51, -1.0, -1.5, -3.0):
        assert signed_i_s_category(value) == "ASYMMETRIC_BOWTIE"


def test_srax_boundary_is_strictly_greater_than_20_degrees():
    assert erss_topography_category(0.8, 19.9) == "ASYMMETRIC_BOWTIE"
    assert erss_topography_category(0.8, 20.0) == "ASYMMETRIC_BOWTIE"
    assert erss_topography_category(0.8, 20.1) == "INFERIOR_STEEPENING_SRA"


def test_srax_never_converts_negative_i_s_to_inferior_steepening():
    assert erss_topography_category(-0.51, 20.1) == "ASYMMETRIC_BOWTIE"
    assert erss_topography_category(-3.0, 90.0) == "ASYMMETRIC_BOWTIE"
    assert erss_topography_category(-0.50, 90.0) == "NORMAL_SYMMETRIC"


def test_i_s_higher_categories_do_not_need_srax():
    assert erss_topography_category(1.01, None) == "INFERIOR_STEEPENING_SRA"
    assert erss_topography_category(1.39, 90.0) == "INFERIOR_STEEPENING_SRA"
    assert erss_topography_category(1.40, None) == "ABNORMAL_ECTATIC"


def test_missing_i_s_does_not_disappear_behind_srax():
    assert erss_topography_category(None, 30.0) == UNCERTAIN


def test_missing_srax_is_not_treated_as_negative_when_i_s_is_below_three_point_band():
    assert erss_topography_category(0.0, None) == UNCERTAIN
    assert erss_topography_category(0.8, None) == UNCERTAIN
    assert erss_topography_category(-0.8, None) == "ASYMMETRIC_BOWTIE"


def test_i_s_and_srax_are_one_category_never_additive():
    assert erss_topography_category(0.51, 20.1) == "INFERIOR_STEEPENING_SRA"


def test_visual_morphology_is_not_an_input_to_pure_topography_rule():
    assert erss_topography_category(0.0, 0.0) == "NORMAL_SYMMETRIC"
