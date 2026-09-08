"""Acceptance locks for the direct assessment-workflow cutover."""
from types import SimpleNamespace
import inspect

import assessment_workflow as workflow


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
        "srax_deg": 10.0,
        "critical_input_issues": [],
    }
    values.update(overrides)
    return values


def _plan(**overrides):
    values = {
        "prior": "no",
        "procedure": "LASIK",
        "flap_um": 100.0,
        "ablation_um": 50.0,
        "manifest_entered_sphere_D": -2.0,
        "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0,
        "stable": "yes",
        "progression": "no",
        "cdva_below_20_20": "no",
    }
    values.update(overrides)
    return values


def _modifiers(**overrides):
    values = {
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
    values.update(overrides)
    return values


def _session(od=None, os=None):
    return {
        "extracted": {
            "eyes": [od or _eye("OD"), os or _eye("OS")],
            "critical_input_issues": [],
            "treatment_corrections": [],
        },
        "ready": None,
        "expires": 0,
        "source_images": [],
    }


def _respond(session=None, plans=None, modifiers=None):
    # Deliberately no hc_engine/apply_extracted_corrections attributes.
    core = SimpleNamespace(APP_VERSION="test")
    return workflow._respond(
        core,
        "token",
        session or _session(),
        35,
        plans or {"OD": _plan(), "OS": _plan()},
        modifiers or _modifiers(),
        {"name": "Test Patient"},
        {},
    )


def test_ready_workflow_uses_direct_canonical_runtime_without_legacy_engine():
    result = _respond()
    assert result["workflow_status"] == "READY"
    assert result["decision"]["engine"] == "CERAI_CANONICAL_CLINICAL_CORE"
    assert result["decision"]["status"] == "PASS"
    assert result["report_token"]
    assert result["effective_eye_plans"]["OD"]["intended_source"] == "DEFAULTED_FROM_MANIFEST"


def test_workflow_source_contains_no_legacy_clinical_call_or_plan_prepass():
    source = inspect.getsource(workflow._respond)
    assert "core.hc_engine" not in source
    assert "apply_extracted_corrections" not in source
    assert "evaluate_case(" in source


def test_missing_i_s_produces_one_canonical_i_s_request_for_eye():
    result = _respond(session=_session(od=_eye("OD", I_S=None)))
    assert result["workflow_status"] == "NEEDS_INPUT"
    requests = [
        item for item in result["input_requests"]
        if item.get("eye") == "OD" and item.get("key") == "I_S"
    ]
    assert len(requests) == 1
    assert requests[0]["source_screen"] == "Show 2 Exams – Topometric"
    assert requests[0]["source_box"] == "center — Indices (in 8 mm zone) → I-S"


def test_unresolved_srax_creates_one_question_shared_by_erss_and_ps3():
    od = _eye("OD", srax_deg=None)
    os = _eye("OS", srax_deg=10.0)
    result = _respond(session=_session(od=od, os=os))
    assert result["workflow_status"] == "NEEDS_INPUT"
    requests = [
        item for item in result["input_requests"]
        if item.get("eye") == "OD" and item.get("key") == "srax"
    ]
    assert len(requests) == 1
    assert requests[0]["options"] == ["YES", "NO"]
    assert "Exact 20.0° is NO" in requests[0]["help"]


def test_contact_lens_washout_blocks_before_canonical_clinical_evaluation():
    result = _respond(modifiers=_modifiers(contact_lens_type="SOFT", contact_lens_discontinuation_days=9))
    assert result["workflow_status"] == "CONTACT_LENS_WASHOUT_REQUIRED"
    assert result["report_token"] is None
    assert "decision" not in result
