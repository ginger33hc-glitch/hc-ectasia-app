"""Phase 2 equivalence gates for the pure launch-contract clinical core."""

import canonical_engine
from clinical_core.rules import (
    bad_d_classification,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
)

core = canonical_engine.core


def test_age_points_match_frozen_production_boundaries():
    values = (17, 18, 18.999, 19, 20, 20.999, 21, 35)
    assert [erss_age_points(x) for x in values] == [core.age_points(x) for x in values]


def test_pachymetry_points_match_frozen_production_boundaries():
    values = (479, 480, 499.999, 500, 509.999, 510, 560)
    assert [erss_pachymetry_points(x) for x in values] == [core.lasik_pachy_points(x) for x in values]


def test_final_bad_d_matches_frozen_production_boundaries():
    values = (1.0, 1.6, 1.6001, 2.5999, 2.6, 3.0)
    assert [bad_d_classification(x) for x in values] == [
        core.bad_classification(x, final=True) for x in values
    ]


def test_signed_i_s_boundaries_are_frozen():
    expected = {
        -5.0: "ASYMMETRIC_BOWTIE",
        -0.5001: "ASYMMETRIC_BOWTIE",
        -0.50: "NORMAL_SYMMETRIC",
        0.0: "NORMAL_SYMMETRIC",
        0.50: "NORMAL_SYMMETRIC",
        0.5001: "ASYMMETRIC_BOWTIE",
        1.00: "ASYMMETRIC_BOWTIE",
        1.0001: "INFERIOR_STEEPENING_SRA",
        1.3999: "INFERIOR_STEEPENING_SRA",
        1.40: "ABNORMAL_ECTATIC",
    }
    assert {value: signed_i_s_category(value) for value in expected} == expected


def test_numeric_topography_higher_single_category_wins():
    assert erss_topography_category(0.0, None) == "NORMAL_SYMMETRIC"
    assert erss_topography_category(0.8, None) == "ASYMMETRIC_BOWTIE"
    assert erss_topography_category(0.8, 19.999) == "ASYMMETRIC_BOWTIE"
    assert erss_topography_category(0.8, 20.0) == "INFERIOR_STEEPENING_SRA"
    assert erss_topography_category(1.2, 20.0) == "INFERIOR_STEEPENING_SRA"
    assert erss_topography_category(1.4, 20.0) == "ABNORMAL_ECTATIC"


def test_visual_morphology_is_not_an_input_to_pure_topography_rule():
    # Deliberately no morphology argument exists in the pure API.
    assert erss_topography_category(0.0, None) == "NORMAL_SYMMETRIC"
