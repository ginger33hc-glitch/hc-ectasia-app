"""Regression locks preventing neighboring Pentacam fields from interchanging."""

import pytest

from pentacam_canonical_source_lock import (
    BAD_CENTER,
    BAD_PPI,
    BAD_STRIP,
    FOUR_MAPS_LOWER_LEFT,
    SHOW_2_CORNEA_BACK,
    SHOW_2_CORNEA_FRONT,
    SHOW_2_INDICES,
    canonical_source_id,
)
from pentacam_targeted_reread import label_supports_field, source_supports_field


@pytest.mark.parametrize(
    ("field", "own_label", "neighbor_labels"),
    (
        ("K1_D", "K1", ("K2", "Km", "Kmax")),
        ("K2_D", "K2", ("K1", "Km", "Kmax")),
        ("Kmean_D", "Km", ("K1", "K2", "Kmax")),
        ("Kmax_D", "Kmax", ("K1", "K2", "Km")),
        ("central_pachy_um", "Pupil Center", ("Thinnest Location",)),
        ("pachy_thinnest_um", "Thinnest Location", ("Pupil Center",)),
        ("I_S", "I-S", ("ISV",)),
        ("ISV", "ISV", ("I-S",)),
        ("PPI_min", "Min", ("Avg", "Max")),
        ("PPI_avg", "Avg", ("Min", "Max")),
        ("PPI_max", "Max", ("Min", "Avg")),
        ("F_Ele_Th_um", "F.Ele.Th", ("B.Ele.Th", "Elevation Back")),
        ("B_Ele_Th_um", "B.Ele.Th", ("F.Ele.Th", "Elevation Back")),
        ("Df", "Df", ("Db", "Dp", "Dt", "Da", "Final D")),
        ("Db", "Db", ("Df", "Dp", "Dt", "Da", "Final D")),
        ("Dp", "Dp", ("Df", "Db", "Dt", "Da", "Final D")),
        ("Dt", "Dt", ("Df", "Db", "Dp", "Da", "Final D")),
        ("Da", "Da", ("Df", "Db", "Dp", "Dt", "Final D")),
        ("BAD_D", "Final D", ("Df", "Db", "Dp", "Dt", "Da")),
    ),
)
def test_neighboring_printed_labels_cannot_populate_each_other(field, own_label, neighbor_labels):
    group = "Progression Index" if field.startswith("PPI_") else None
    assert label_supports_field(field, own_label, group)
    assert all(not label_supports_field(field, label, group) for label in neighbor_labels)


def test_posterior_and_topometric_rmin_are_separate_source_locked_fields():
    assert canonical_source_id("Rmin_mm") == SHOW_2_CORNEA_BACK
    assert canonical_source_id("topometric_RMin") == SHOW_2_INDICES
    assert source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "Rmin_mm", "Cornea Back")
    assert not source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "Rmin_mm", "Indices (in 8 mm zone)")
    assert source_supports_field(
        "SHOW_2_EXAMS_TOPOMETRIC", "topometric_RMin", "Indices (in 8 mm zone)"
    )
    assert not source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "topometric_RMin", "Cornea Back")


def test_interchange_pairs_retain_distinct_canonical_source_regions():
    assert canonical_source_id("K1_D") == canonical_source_id("K2_D") == SHOW_2_CORNEA_FRONT
    assert canonical_source_id("Kmax_D") == FOUR_MAPS_LOWER_LEFT
    assert canonical_source_id("central_pachy_um") == canonical_source_id("pachy_thinnest_um") == FOUR_MAPS_LOWER_LEFT
    assert canonical_source_id("PPI_min") == canonical_source_id("PPI_avg") == canonical_source_id("PPI_max") == BAD_PPI
    assert canonical_source_id("F_Ele_Th_um") == canonical_source_id("B_Ele_Th_um") == BAD_CENTER
    assert {canonical_source_id(key) for key in ("Df", "Db", "Dp", "Dt", "Da", "BAD_D")} == {BAD_STRIP}

