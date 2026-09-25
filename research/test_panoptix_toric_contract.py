"""Check the model mapping and the steep-axis incision convention."""

import pytest

from research.panoptix_toric_contract import (
    CNWTT_IOL_CYLINDER_D, IOLMaster500ToricInput,
)


def test_catalog_steps_are_actual_iol_plane_diopters():
    assert list(CNWTT_IOL_CYLINDER_D.items()) == [
        ("CNWTT2", 1.0), ("CNWTT3", 1.5), ("CNWTT4", 2.25),
        ("CNWTT5", 3.0), ("CNWTT6", 3.75),
    ]
    assert "CNWTT1" not in CNWTT_IOL_CYLINDER_D


def test_steep_k2_axis_is_incision_axis_and_sia_is_fixed():
    record = IOLMaster500ToricInput(42.0, 43.5, 170, 80)
    assert record.incision_axis_deg == 80
    assert record.sia_d == 0.25


def test_180_degree_axis_wraps_to_zero():
    assert IOLMaster500ToricInput(42, 43, 90, 180).incision_axis_deg == 0


@pytest.mark.parametrize("values", [(43, 42, 90, 0), (42, 43, 90, 10),
                                    (42, 43, 180, 180), (42, 43, 0, float("nan"))])
def test_invalid_or_discrepant_keratometry_is_rejected(values):
    with pytest.raises(ValueError):
        IOLMaster500ToricInput(*values)
