"""Phase 3 guarded runtime-seam behavior locks."""

import importlib

import canonical_engine
import phase3_runtime_seam
from clinical_core.pipeline import ClinicalCoreInput


core = canonical_engine.core


def test_flag_is_disabled_by_default_and_accepts_explicit_true_values():
    assert phase3_runtime_seam.linear_pipeline_enabled({}) is False
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert phase3_runtime_seam.linear_pipeline_enabled({phase3_runtime_seam.ENV_FLAG: value}) is True
    for value in ("0", "false", "off", "no", ""):
        assert phase3_runtime_seam.linear_pipeline_enabled({phase3_runtime_seam.ENV_FLAG: value}) is False


def test_installation_does_not_replace_production_clinical_functions():
    before = (core.assess_eye, core.hc_engine, core.merge_extractions)
    phase3_runtime_seam.install(core)
    after = (core.assess_eye, core.hc_engine, core.merge_extractions)
    assert after == before
    assert core._cerai_phase3_runtime_seam_installed is True
    assert core._cerai_linear_pipeline_env_flag == "CERAI_LINEAR_PIPELINE_ENABLED"


def test_disabled_route_preserves_legacy_authority():
    marker = object()
    legacy_calls = []

    def legacy(inp):
        legacy_calls.append(inp)
        return marker

    inp = ClinicalCoreInput(procedure="LASIK")
    result = phase3_runtime_seam.route_normalized_case(inp, legacy_evaluator=legacy, enabled=False)
    assert result is marker
    assert legacy_calls == [inp]


def test_enabled_route_uses_linear_pipeline_only_at_normalized_boundary():
    inp = ClinicalCoreInput(
        procedure="PRK",
        age_years=35,
        thinnest_um=550,
        i_s_d=0.0,
        intended_sphere_d=-2.0,
        ablation_um=50,
        preop_kmean_d=43.0,
        intended_mrse_d=-2.0,
        final_bad_d=1.0,
        nice_k2_d=44.0,
        nice_central_pachy_um=530,
        nice_b_ele_th_um=10.0,
    )

    def should_not_run(_):
        raise AssertionError("legacy evaluator must not run when linear route is explicitly enabled")

    result = phase3_runtime_seam.route_normalized_case(inp, legacy_evaluator=should_not_run, enabled=True)
    assert result["procedure"] == "PRK"
    assert result["pipeline_order"][0] == "normalized_input"


def test_runtime_composition_declares_phase3_cutover_seam():
    runtime_composition = importlib.import_module("runtime_composition")
    assert runtime_composition.COMPOSITION_PHASES["phase3_cutover"] == ("phase3_runtime_seam",)
