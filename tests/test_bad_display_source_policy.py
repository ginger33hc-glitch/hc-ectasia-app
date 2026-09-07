import importlib
from pathlib import Path

from clinical_core.bad import BADContext, evaluate_bad


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


def test_normal_final_bad_d_remains_normal_despite_adjunctive_component_flags():
    result = evaluate_bad(0.83, context=BADContext(
        df=-1.01, db=-0.58, dp=1.05, dt=-0.10, da=0.70, artmax_um=400
    ))
    assert result.classification == "NORMAL"
    assert result.final_d == 0.83
    assert result.context.artmax_um == 400
    assert result.context.dt == -0.10
    assert result.context.da == 0.70


def test_bad_decision_is_owned_by_final_d_not_visual_map_patterns():
    normal = evaluate_bad(0.83, context=BADContext(df=-1.01, db=-0.58, dp=1.05, dt=-0.65, da=0.38))
    suspicious = evaluate_bad(1.61)
    abnormal = evaluate_bad(2.60)
    assert normal.classification == "NORMAL"
    assert suspicious.classification == "SUSPICIOUS"
    assert abnormal.classification == "ABNORMAL"
