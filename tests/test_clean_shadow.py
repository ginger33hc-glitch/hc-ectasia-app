from dataclasses import FrozenInstanceError
import pytest

from clean_engine.input_adapter import ReconciledEyeInput
from clean_engine.migration import run_clean_assessment
from clean_engine.shadow import ClinicalSnapshot, compare_snapshots, snapshot_clean


def _clean():
    inp = ReconciledEyeInput(
        age_years=30, pachy_thinnest_um=520, bad_d=1.0,
        morphology="NORMAL_SYMMETRIC", procedure="LASIK",
        ablation_um=60, flap_um=100, preop_kmean_d=43,
        intended_mrse_d=-3, intended_sphere_d=-3,
        intended_cylinder_magnitude_d=0, laser_platform="EX500",
    )
    return snapshot_clean(run_clean_assessment(inp).result)


def test_identical_snapshots_are_equivalent():
    clean = _clean()
    out = compare_snapshots(clean, clean)
    assert out.equivalent is True
    assert out.differences == ()


def test_difference_is_observed_without_overriding_canonical():
    clean = _clean()
    canonical = ClinicalSnapshot(
        status="CAUTION — DEFER",
        hard_stops=clean.hard_stops,
        missing=clean.missing,
        bad_d_status=clean.bad_d_status,
        lasik_erss_total=clean.lasik_erss_total,
        prk_score_total=clean.prk_score_total,
    )
    out = compare_snapshots(canonical, clean)
    assert out.equivalent is False
    assert out.differences == ("status",)
    assert out.canonical.status == "CAUTION — DEFER"
    assert out.clean.status == clean.status


def test_multiple_differences_have_stable_order():
    clean = _clean()
    canonical = ClinicalSnapshot(status="X", hard_stops=("X",), missing=("x",))
    out = compare_snapshots(canonical, clean)
    assert out.differences[:3] == ("status", "hard_stops", "missing")


def test_shadow_records_are_immutable():
    clean = _clean()
    with pytest.raises(FrozenInstanceError):
        clean.status = "DO NOT PROCEED"
