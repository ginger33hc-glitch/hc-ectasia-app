"""Safety locks for PHI-free Phase 3 shadow diagnostics."""

from clinical_core.pipeline import ClinicalCoreInput, evaluate_normalized_case
from ps3_policy import PS3EyeInput
import phase3_shadow_diagnostics as diagnostics


def _normalized():
    return ClinicalCoreInput(
        procedure="LASIK",
        age_years=30,
        thinnest_um=540,
        i_s_d=0.0,
        manifest_mrse_d=-2.0,
        intended_sphere_d=-2.0,
        flap_um=100,
        ablation_um=40,
        preop_kmean_d=44.0,
        intended_mrse_d=-2.0,
        final_bad_d=1.0,
        nice_k2_d=44.0,
        nice_central_pachy_um=540,
        nice_b_ele_th_um=10.0,
        ps3_eye=PS3EyeInput(anterior_km_d=44.0, thinnest_um=540),
    )


def _production_from_linear(linear):
    return {
        "status": linear["status"],
        "score": {"total": linear["erss"]["total"]},
        "bad_summary": {"category": linear["bad_d"]["classification"]},
        "nice": {"total": linear["nice"]["total"]},
        "ps3": {
            "disposition": {
                "lasik": "ALLOWED" if linear["ps3_status"] == "PASS" else "DEFER",
                "prk": "ALLOWED",
                "smile": "ALLOWED",
            }
        },
        "values": {
            "LASIK_RSB_um": linear["procedural_safety"]["LASIK_RSB_um"],
            "LASIK_PTA_percent": linear["procedural_safety"]["LASIK_PTA_percent"],
            "estimated_final_Kmean_D": linear["procedural_safety"]["estimated_final_Kmean_D"],
        },
        # Deliberate identifying/clinical-looking fields must never enter snapshot.
        "patient_name": "SHOULD_NOT_BE_STORED",
        "clinical_secret": 12345.678,
    }


def setup_function():
    diagnostics._reset_diagnostics_for_tests()


def test_shadow_diagnostics_are_disabled_by_default():
    assert diagnostics.shadow_diagnostics_enabled({}) is False
    result = diagnostics.observe_shadow_parity({}, _normalized(), procedure="LASIK", enabled=False)
    assert result == {"observed": False, "reason": "SHADOW_DIAGNOSTICS_DISABLED"}
    assert diagnostics.diagnostics_snapshot()["total_observations"] == 0


def test_matching_shadow_records_aggregate_only():
    normalized = _normalized()
    linear = evaluate_normalized_case(normalized)
    production = _production_from_linear(linear)

    observed = diagnostics.observe_shadow_parity(production, normalized, procedure="LASIK", enabled=True)
    assert observed["observed"] is True
    assert observed["cutover_allowed"] is True
    assert observed["mismatch_channels"] == []

    snapshot = diagnostics.diagnostics_snapshot()
    assert snapshot == {
        "total_observations": 1,
        "parity_matches": 1,
        "parity_mismatches": 0,
        "mismatch_channels": {},
    }
    rendered = repr(snapshot)
    assert "SHOULD_NOT_BE_STORED" not in rendered
    assert "12345.678" not in rendered


def test_mismatch_records_channel_name_not_values():
    normalized = _normalized()
    linear = evaluate_normalized_case(normalized)
    production = _production_from_linear(linear)
    production["status"] = "CAUTION"

    observed = diagnostics.observe_shadow_parity(production, normalized, procedure="LASIK", enabled=True)
    assert observed["cutover_allowed"] is False
    assert "final_status" in observed["mismatch_channels"]

    snapshot = diagnostics.diagnostics_snapshot()
    assert snapshot["total_observations"] == 1
    assert snapshot["parity_matches"] == 0
    assert snapshot["parity_mismatches"] == 1
    assert snapshot["mismatch_channels"] == {"final_status": 1}
    assert "CAUTION" not in repr(snapshot)
