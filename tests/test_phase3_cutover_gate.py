"""Fail-closed behavior locks for the final Phase 3 cutover gate."""

from phase3_cutover_gate import evaluate_cutover_eligibility


def _eligible(**overrides):
    args = {
        "linear_flag_enabled": True,
        "workflow_status": "READY",
        "production_eye_result": {"status": "PASS"},
        "plan": {"prior": "no", "procedure": "LASIK"},
        "shadow_observation": {"observed": True, "cutover_allowed": True, "mismatch_channels": []},
        "observer_error": False,
    }
    args.update(overrides)
    return evaluate_cutover_eligibility(**args)


def test_all_requirements_present_is_eligible():
    result = _eligible()
    assert result["eligible"] is True
    assert result["reasons"] == []
    assert result["candidate_engine_if_eligible"] == "LINEAR_CLINICAL_CORE"


def test_feature_flag_disabled_fails_closed():
    result = _eligible(linear_flag_enabled=False)
    assert result["eligible"] is False
    assert "LINEAR_FEATURE_FLAG_DISABLED" in result["reasons"]


def test_not_ready_fails_closed():
    result = _eligible(workflow_status="NEEDS_INPUT")
    assert result["eligible"] is False
    assert "ASSESSMENT_NOT_READY" in result["reasons"]


def test_post_refractive_status_fails_closed():
    result = _eligible(production_eye_result={"status": "POST-REFRACTIVE PATHWAY REQUIRED"})
    assert result["eligible"] is False
    assert "POST_REFRACTIVE_OR_NON_VIRGIN_PATHWAY" in result["reasons"]


def test_nonvirgin_plan_fails_closed():
    result = _eligible(plan={"prior": "PRK", "procedure": "PRK"})
    assert result["eligible"] is False
    assert "POST_REFRACTIVE_OR_NON_VIRGIN_PATHWAY" in result["reasons"]


def test_missing_or_unsupported_procedure_fails_closed():
    for procedure in (None, "", "OTHER"):
        result = _eligible(plan={"prior": "no", "procedure": procedure})
        assert result["eligible"] is False
        assert "UNSUPPORTED_OR_MISSING_PROCEDURE" in result["reasons"]


def test_observer_error_fails_closed():
    result = _eligible(observer_error=True)
    assert result["eligible"] is False
    assert "SHADOW_OBSERVER_ERROR" in result["reasons"]


def test_missing_shadow_observation_fails_closed():
    result = _eligible(shadow_observation={"observed": False})
    assert result["eligible"] is False
    assert "NO_SHADOW_OBSERVATION" in result["reasons"]


def test_parity_mismatch_fails_closed():
    result = _eligible(shadow_observation={"observed": True, "cutover_allowed": False, "mismatch_channels": ["nice_total"]})
    assert result["eligible"] is False
    assert "PARITY_MISMATCH" in result["reasons"]
    assert result["authoritative_engine_if_ineligible"] == "LEGACY_COMPOSED_RUNTIME"


def test_multiple_failures_are_all_reported():
    result = _eligible(
        linear_flag_enabled=False,
        workflow_status="NEEDS_INPUT",
        plan={"prior": "LASIK", "procedure": "OTHER"},
        shadow_observation={"observed": False},
        observer_error=True,
    )
    assert result["eligible"] is False
    assert set(result["reasons"]) >= {
        "LINEAR_FEATURE_FLAG_DISABLED",
        "ASSESSMENT_NOT_READY",
        "POST_REFRACTIVE_OR_NON_VIRGIN_PATHWAY",
        "UNSUPPORTED_OR_MISSING_PROCEDURE",
        "SHADOW_OBSERVER_ERROR",
        "NO_SHADOW_OBSERVATION",
    }


def test_supported_procedures_can_be_eligible():
    for procedure in ("LASIK", "PRK", "SMILE"):
        result = _eligible(plan={"prior": "no", "procedure": procedure})
        assert result["eligible"] is True
        assert result["procedure"] == procedure
