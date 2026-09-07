"""Launch behavior contract locks for the canonical runtime."""
from pathlib import Path

import canonical_engine
from clinical_core.disposition import CAUTION, PASS, STOP_DEFER, DecisionFinding, finalize_disposition
from clinical_core.safety import FINAL_KMEAN_MAX_D, FINAL_KMEAN_MIN_D, PRK_EPITHELIUM_UM


def test_launch_behavior_contract_document_exists():
    assert Path("docs/CER-AI_LAUNCH_BEHAVIOR_CONTRACT_v0.7.71.md").exists()


def test_direct_canonical_runtime_is_ready():
    assert canonical_engine.runtime_invariants()
    assert canonical_engine.app.state.cerai_canonical_runtime_ready is True


def test_final_disposition_order_is_frozen():
    assert finalize_disposition((DecisionFinding("a", PASS), DecisionFinding("b", CAUTION))).status == CAUTION
    assert finalize_disposition((DecisionFinding("a", CAUTION), DecisionFinding("b", STOP_DEFER))).status == STOP_DEFER


def test_key_safety_constants_are_frozen():
    assert PRK_EPITHELIUM_UM == 50.0
    assert FINAL_KMEAN_MIN_D == 36.0
    assert FINAL_KMEAN_MAX_D == 48.0


def test_phase1_contract_uses_direct_canonical_clinical_authority():
    import runtime_composition

    # Step 2A flattened the ERSS/SRAX extraction prompt into app.py. The retired
    # prompt installer must stay absent; direct prompt ownership is the invariant.
    assert not hasattr(canonical_engine.core, "_cerai_erss_numeric_extraction_installed")
    assert "ERSS VISUAL MORPHOLOGY DISABLED:" in canonical_engine.core.PROMPT
    assert "ERSS SRAX SOURCE LOCK — MODEL ESTIMATION DISABLED:" in canonical_engine.core.PROMPT
    assert "erss_numeric_extraction_policy" not in {
        name for values in runtime_composition.COMPOSITION_PHASES.values() for name in values
    }

    assert canonical_engine.core._cerai_mandatory_source_set_installed
    assert canonical_engine.core._hc_readiness_installed
    assert "clinical_policy_legacy_pending_retirement" not in runtime_composition.COMPOSITION_PHASES

    workflow_source = Path("assessment_workflow.py").read_text(encoding="utf-8")
    assert "evaluate_case(" in workflow_source
    assert "core.hc_engine" not in workflow_source
    assert "apply_extracted_corrections" not in workflow_source
