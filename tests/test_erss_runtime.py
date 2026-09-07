"""Canonical Randleman/ERSS topography behavior locks.

Step-60 authority migration:
Old tests called ``canonical_engine.core.scoring_morphology`` from the dormant
monolithic app scorer. The canonical authority is now ``clinical_core.rules``
and ``clinical_core.erss``. The clinical expectations are preserved unchanged.
"""

from clinical_core.erss import erss_topography_points, erss_total
from clinical_core.rules import (
    ABNORMAL_ECTATIC,
    ASYMMETRIC_BOWTIE,
    INFERIOR_STEEPENING_SRA,
    NORMAL_SYMMETRIC,
    UNCERTAIN,
    erss_topography_category,
    signed_i_s_category,
)


def test_i_s_normal_band_scores_zero():
    assert signed_i_s_category(0.0) == NORMAL_SYMMETRIC
    assert erss_topography_points(NORMAL_SYMMETRIC) == 0


def test_i_s_positive_abt_scores_one():
    assert signed_i_s_category(0.8) == ASYMMETRIC_BOWTIE
    assert erss_topography_points(ASYMMETRIC_BOWTIE) == 1


def test_negative_i_s_has_no_lower_boundary_for_abt():
    for value in (-0.51, -1.0, -1.5, -5.0):
        assert signed_i_s_category(value) == ASYMMETRIC_BOWTIE
        assert erss_topography_points(ASYMMETRIC_BOWTIE) == 1


def test_i_s_inferior_steepening_band_scores_three():
    assert signed_i_s_category(1.2) == INFERIOR_STEEPENING_SRA
    assert erss_topography_points(INFERIOR_STEEPENING_SRA) == 3


def test_i_s_at_1_40_is_abnormal_four_point_category():
    assert signed_i_s_category(1.40) == ABNORMAL_ECTATIC
    assert erss_topography_points(ABNORMAL_ECTATIC) == 4


def test_front_map_srax_over_20_scores_three_when_i_s_can_be_upgraded():
    category = erss_topography_category(0.5, 20.1)
    assert category == INFERIOR_STEEPENING_SRA
    assert erss_topography_points(category) == 3


def test_exact_20_does_not_trigger_srax():
    assert erss_topography_category(0.5, 20.0) == NORMAL_SYMMETRIC


def test_higher_single_category_wins_without_addition():
    category = erss_topography_category(0.8, 25.0)
    assert category == INFERIOR_STEEPENING_SRA
    assert erss_topography_points(category) == 3


def test_i_s_1_01_or_higher_does_not_require_srax():
    assert erss_topography_category(1.01, None) == INFERIOR_STEEPENING_SRA
    assert erss_topography_category(1.40, None) == ABNORMAL_ECTATIC


def test_unresolved_srax_blocks_complete_topography_scoring_when_i_s_does_not_set_high_category():
    assert erss_topography_category(0.0, None) == UNCERTAIN
    result = erss_total(
        age_years=30,
        thinnest_um=530,
        i_s_d=0.0,
        derived_srax_deg=None,
        rsb_um=330,
        manifest_mrse_d=-3.0,
    )
    assert result["total"] is None
    assert result["missing"] == ["SRAX"]


def test_missing_i_s_is_incomplete_even_if_srax_geometry_is_positive():
    assert erss_topography_category(None, 25.0) == UNCERTAIN
    result = erss_total(30, 530, None, 25.0, 330, -3.0)
    assert result["total"] is None
    assert "I_S" in result["missing"]
