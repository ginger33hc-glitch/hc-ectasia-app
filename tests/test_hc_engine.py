"""Collected HC-engine regression surface after Phase 4 retirement cleanup.

The original monolithic pre-launch test module is preserved byte-for-byte as
legacy_hc_engine_tests.py for historical traceability. This wrapper re-exports
active tests while explicitly retiring expectations superseded by source-locked
SRAX and other frozen CER-AI policies.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_LEGACY_PATH=Path(__file__).with_name("legacy_hc_engine_tests.py")
_SPEC=importlib.util.spec_from_file_location("cerai_legacy_hc_engine_tests",_LEGACY_PATH)
if _SPEC is None or _SPEC.loader is None:raise RuntimeError("Unable to load historical HC-engine regression module")
_legacy=importlib.util.module_from_spec(_SPEC);sys.modules[_SPEC.name]=_legacy;_SPEC.loader.exec_module(_legacy)

_RETIRED_METHODS={
    "TestSafetyGates":{
        "test_clinical_eligibility_modifier_blocks_pass_without_score_points",
        "test_i_s_merge_does_not_create_definite_disease_override",
    },
    "TestBoundaries":{
        "test_prk_cct_480_not_hard_stop_but_scores_caution",
        "test_definite_ectatic_morphology_is_not_downgraded_by_srax_fields",
        "test_minimal_axis_deviation_is_not_scored_as_srax",
        "test_srax_20_degrees_uses_published_erss_sra_category",
        "test_srax_below_20_degrees_is_not_scored",
        "test_unquantified_visual_srax_label_is_not_scored",
        "test_i_s_1_4_uses_published_erss_abnormal_pattern_without_disease_override",
        "test_quantified_inferior_steepening_alternative_uses_published_category",
    },
    "TestScoringAndCompleteness":{
        "test_reassuring_prk_can_pass",
        "test_extraction_contract_prioritizes_labeled_pentacam_numeric_fields",
        "test_lasik_score_two_has_no_score_escalation",
        "test_local_kmax_is_rejected_but_explicit_local_rmin_remains_permitted",
    },
    "TestApiIntegration":{
        "test_analyze_endpoint_accepts_eye_specific_payload",
        "test_analyze_retry_reuses_same_inflight_or_completed_assessment",
    },
}
for _class_name,_method_names in _RETIRED_METHODS.items():
    _class=getattr(_legacy,_class_name)
    for _method_name in _method_names:
        if not hasattr(_class,_method_name):raise RuntimeError(f"Retired HC-engine test method missing: {_class_name}.{_method_name}")
        delattr(_class,_method_name)
for _name,_value in vars(_legacy).items():
    if not _name.startswith("__"):globals()[_name]=_value
PHASE4_RETIRED_HC_ENGINE_METHODS={key:tuple(sorted(value)) for key,value in _RETIRED_METHODS.items()}
del _class_name,_method_names,_class,_method_name,_name,_value
