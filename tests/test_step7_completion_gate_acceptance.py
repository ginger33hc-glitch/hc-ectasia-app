"""Official Step 7 acceptance for pre-report completion and missing-data workflow."""
from types import SimpleNamespace

import assessment_workflow as workflow


_DECISION_FIELDS = (
    "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da", "ARTmax_um", "PPI_max"
)


def _eye(name="OD", **overrides):
    values = {
        "eye": name,
        "Kmean_D": 43.0,
        "K2_D": 44.0,
        "central_pachy_um": 550.0,
        "pachy_thinnest_um": 545.0,
        "BAD_D": 1.0,
        "Df": -0.2,
        "Db": 0.4,
        "Dp": 0.3,
        "Dt": 0.2,
        "Da": 0.5,
        "ARTmax_um": 380.0,
        "PPI_min": 0.7,
        "PPI_avg": 1.0,
        "PPI_max": 1.2,
        "I_S": 0.0,
        "topographic_astig_D": 1.0,
        "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0,
        "B_Ele_Th_um": 10.0,
        "srax": "NO",
        "srax_deg": 10.0,
        "table_verified_numeric_fields": list(_DECISION_FIELDS),
        "field_provenance": {key: [{"source": "TEST_CANONICAL_SOURCE", "file": f"{name}.png"}] for key in _DECISION_FIELDS},
        "data_conflicts": [],
        "missing_or_unreadable": [],
        "source_files": [f"{name}.png"],
    }
    values.update(overrides)
    return values


def _plan(procedure="LASIK"):
    return {
        "prior": "no",
        "procedure": procedure,
        "flap_um": 100.0 if procedure == "LASIK" else None,
        "ablation_um": 50.0,
        "manifest_entered_sphere_D": -2.0,
        "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0,
        "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": -1.0,
        "intended_axis_deg": 90.0,
        "stable": "yes",
        "progression": "no",
        "cdva_below_20_20": "no",
    }


def _modifiers():
    return {
        "contact_lens_type": "NONE",
        "eye_rubbing": "no",
        "family_history": "no",
        "inter_eye_asymmetry": "no",
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no",
        "drug_usage": "no",
        "dry_eye": "no",
        "systemic_disease": "no",
    }


def _session(od=None, os=None, *, issues=None):
    return {
        "extracted": {
            "eyes": [od or _eye("OD"), os or _eye("OS")],
            "critical_input_issues": list(issues or []),
            "treatment_corrections": [],
        },
        "ready": None,
        "expires": 0,
        "source_images": [],
    }


def _respond(session, *, overrides=None, procedure="LASIK"):
    return workflow._respond(
        SimpleNamespace(APP_VERSION="step7-runtime-acceptance"),
        "token",
        session,
        35,
        {"OD": _plan(procedure), "OS": _plan(procedure)},
        _modifiers(),
        {"name": "Step 7 Patient"},
        overrides or {},
    )


def test_missing_nice_central_pachymetry_blocks_report_with_one_canonical_request():
    result = _respond(_session(od=_eye("OD", central_pachy_um=None)))
    assert result["workflow_status"] == "NEEDS_INPUT"
    assert result["report_token"] is None
    requests = [item for item in result["input_requests"] if item.get("eye") == "OD" and item.get("key") == "central_pachy_um"]
    assert len(requests) == 1
    assert requests[0]["kind"] == "number"
    assert "Pupil Center (+)" in requests[0]["label"]


def test_missing_ps3_ppi_average_blocks_report_with_one_canonical_ppi_request():
    result = _respond(_session(od=_eye("OD", PPI_avg=None)), procedure="PRK")
    assert result["workflow_status"] == "NEEDS_INPUT"
    assert result["report_token"] is None
    requests = [item for item in result["input_requests"] if item.get("eye") == "OD" and item.get("key") == "PPI_avg"]
    assert len(requests) == 1
    assert requests[0]["kind"] == "number"
    assert "PPI average" in requests[0]["label"]


def test_quality_only_qs_issue_does_not_block_an_otherwise_complete_case():
    issue = "Pentacam acquisition requires a same-exam explicit QS: OK before risk classification."
    result = _respond(_session(issues=[issue]))
    assert result["workflow_status"] == "READY"
    assert result["report_token"]


def test_surgeon_correction_recalculates_dependencies_and_is_audited():
    session = _session(od=_eye("OD", I_S=None))
    first = _respond(session)
    assert first["workflow_status"] == "NEEDS_INPUT"
    assert first["report_token"] is None

    second = _respond(session, overrides={"OD": {"I_S": 0.0}})
    assert second["workflow_status"] == "READY"
    assert second["report_token"]
    od = next(item for item in second["extracted"]["eyes"] if item["eye"] == "OD")
    assert od["I_S"] == 0.0
    assert od["field_provenance"]["I_S"] == [{"source": "SURGEON_CONFIRMED"}]
    corrections = second["decision"]["eyes"][0]["report_payload"]["manual_corrections"]
    assert {"field": "I_S", "original": None, "value": 0.0, "label": "SURGEON_CONFIRMED"} in corrections


def test_irrevocable_stop_is_immediate_but_cannot_authorize_an_incomplete_full_report():
    # I-S >=1.40 already establishes STOP-DEFER, but the revised master order requires
    # PS3 completion before a complete report token can be issued.
    result = _respond(_session(od=_eye("OD", I_S=1.40, srax="UNCERTAIN", srax_deg=None)))
    assert result["workflow_status"] == "NEEDS_INPUT"
    assert result["report_token"] is None
    assert result["hard_stop_summary"]["status"] == "STOP-DEFER"
    assert result["hard_stop_summary"]["complete_report"] is False
    assert [item for item in result["input_requests"] if item.get("eye") == "OD" and item.get("key") == "srax"]


def test_retired_inferior_opposite_steepening_is_not_a_completion_field():
    assert "inferior_opposite_steepening_D" not in workflow.NUMERIC_FIELDS


def test_ps3_high_factor_cannot_skip_shared_srax_to_authorize_full_report():
    result = _respond(_session(od=_eye("OD", B_Ele_Th_um=16.0, I_S=1.40,
                                     srax="UNCERTAIN", srax_deg=None)))
    assert result["workflow_status"] == "NEEDS_INPUT"
    assert result["report_token"] is None
    assert result["hard_stop_summary"]["status"] == "STOP-DEFER"
    assert any(item.get("eye") == "OD" and item.get("key") == "srax"
               for item in result["input_requests"])
