import importlib


def test_bad_display_prompt_is_source_locked():
    runtime = importlib.import_module("canonical_engine")
    prompt = runtime.core.PROMPT
    assert "BELIN/AMBRÓSIO BAD DISPLAY SOURCE LOCK" in prompt
    assert "Preserve every printed sign exactly" in prompt
    assert "Never derive or reconstruct Df from anterior elevation" in prompt
    assert "Dt from thinnest pachymetry" in prompt
    assert "Da from ARTmax" in prompt
    assert "BAD_D from the five component values" in prompt
    assert runtime.core._cerai_bad_display_source_lock_installed is True


def test_final_bad_d_remains_bad_display_authority_when_component_is_high():
    runtime = importlib.import_module("canonical_engine")
    eye = {
        "BAD_D": 0.83,
        "Df": -1.01,
        "Db": -0.58,
        "Dp": 3.20,
        "Dt": -0.65,
        "Da": 0.38,
        "ARTmax_um": 447,
        "pachy_thinnest_um": 561,
        "anterior_pattern": "REASSURING",
        "posterior_pattern": "REASSURING",
    }
    review = runtime.core.tomography_review(eye)
    assert review["BAD_display"]["BAD_D"] == "NORMAL"
    assert review["BAD_display"]["Dp"] == "ABNORMAL"
    assert review["status"] == "REASSURING"
    assert review["BAD_source_policy"] == "BELIN_AMBROSIO_LABELED_BAD_PANEL_ONLY"


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
