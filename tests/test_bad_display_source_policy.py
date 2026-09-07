import importlib
from pathlib import Path


def test_bad_display_prompt_is_source_locked_directly_in_canonical_extractor():
    runtime = importlib.import_module("canonical_engine")
    prompt = runtime.core.PROMPT
    assert "BELIN/AMBROSIO BAD DISPLAY SOURCE LOCK" in prompt
    assert "Preserve every printed sign" in prompt
    assert "Never derive or reconstruct Df from anterior elevation" in prompt
    assert "Dt from thinnest pachymetry" in prompt
    assert "Da from ARTmax" in prompt
    assert "Final D from the component values" in prompt
    assert not hasattr(runtime.core, "_cerai_bad_display_source_lock_installed")
    assert not Path("bad_display_source_policy.py").exists()


def test_source_lock_does_not_change_existing_tomography_flag_behavior():
    runtime = importlib.import_module("canonical_engine")
    eye = {
        "BAD_D": 0.83,
        "Df": -1.01,
        "Db": -0.58,
        "Dp": 1.05,
        "Dt": -0.10,
        "Da": 0.70,
        "ARTmax_um": 400,
        "pachy_thinnest_um": 530,
        "anterior_pattern": "REASSURING",
        "posterior_pattern": "REASSURING",
    }
    review = runtime.core.tomography_review(eye)
    assert review["BAD_display"]["BAD_D"] == "NORMAL"
    assert review["status"] == "CONCERN FLAGS"


def test_independent_map_abnormality_is_not_suppressed_by_normal_final_bad_d():
    runtime = importlib.import_module("canonical_engine")
    eye = {
        "BAD_D": 0.83,
        "Df": -1.01,
        "Db": -0.58,
        "Dp": 1.05,
        "Dt": -0.65,
        "Da": 0.38,
        "ARTmax_um": 447,
        "pachy_thinnest_um": 561,
        "anterior_pattern": "ABNORMAL",
        "posterior_pattern": "REASSURING",
    }
    review = runtime.core.tomography_review(eye)
    assert review["status"] == "ABNORMAL"
