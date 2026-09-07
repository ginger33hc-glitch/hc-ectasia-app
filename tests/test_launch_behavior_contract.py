"""Phase 1 launch-contract golden tests for the direct canonical CER-AI runtime."""
from pathlib import Path

import pytest

import canonical_engine
import mandatory_source_set_policy
from clinical_core.bad import final_bad_d_classification
from clinical_core.disposition import (
    CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
)
from clinical_core.erss import erss_topography_points
from clinical_core.nice import score_nice
from clinical_core.ps3 import ALLOWED, DEFER, PS3EyeInput, PS3InterEyeInput, evaluate_ps3
from clinical_core.rules import (
    ASYMMETRIC_BOWTIE,
    INFERIOR_STEEPENING_SRA,
    NORMAL_SYMMETRIC,
    ABNORMAL_ECTATIC,
    erss_age_points,
    erss_pachymetry_points,
    erss_topography_category,
    signed_i_s_category,
)
from clinical_core.safety import FINAL_KMEAN_MAX_D, FINAL_KMEAN_MIN_D, PRK_EPITHELIUM_UM


def _source(screen, eye=None, *, document_type="PENTACAM_TOPOGRAPHY", laterality=None):
    eyes = [] if eye is None else [{"eye": eye, "screen_types": [screen]}]
    return {
        "document_context": {
            "document_type": document_type,
            "laterality": laterality or eye or "UNKNOWN",
        },
        "eyes": eyes,
        "treatment_corrections": [],
    }


def _mandatory_set(include_card=False):
    items = [
        _source("4 Maps Refractive", "OD"),
        _source("FOUR_MAPS_REFRACTIVE", "OS"),
        _source("Belin/Ambrósio Enhanced Ectasia Display", "OD"),
        _source("BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY", "OS"),
        _source("Show 2 Exams Topometric", "OD"),
    ]
    if include_card:
        items.append(_source("EXCIMER_LASER_TREATMENT_CARD", document_type="TREATMENT_CARD"))
    return items


def test_launch_contract_version_and_runtime_startup():
    assert canonical_engine.CANONICAL_VERSION == "0.7.71"
    assert canonical_engine.runtime_invariants() is True


def test_mandatory_five_source_set_accepts_real_label_variants():
    summary = mandatory_source_set_policy.validate_source_set(_mandatory_set())
    assert summary["mandatory_count"] == 5
    assert summary["missing"] == []
    assert summary["uploaded_count"] == 5


def test_optional_excimer_card_is_sixth_source_only():
    summary = mandatory_source_set_policy.validate_source_set(_mandatory_set(include_card=True))
    assert summary["mandatory_count"] == 5
    assert summary["treatment_card_count"] == 1
    assert summary["uploaded_count"] == 6


def test_missing_mandatory_source_blocks_before_assessment():
    items = _mandatory_set()
    items.pop(3)
    with pytest.raises(Exception) as exc:
        mandatory_source_set_policy.validate_source_set(items)
    assert getattr(exc.value, "status_code", None) == 422
    assert "OS Belin/Ambrosio Display" in str(getattr(exc.value, "detail", exc.value))


@pytest.mark.parametrize(
    ("i_s", "category", "points"),
    [
        (-5.0, ASYMMETRIC_BOWTIE, 1),
        (-0.5001, ASYMMETRIC_BOWTIE, 1),
        (-0.50, NORMAL_SYMMETRIC, 0),
        (0.0, NORMAL_SYMMETRIC, 0),
        (0.50, NORMAL_SYMMETRIC, 0),
        (0.5001, ASYMMETRIC_BOWTIE, 1),
        (1.00, ASYMMETRIC_BOWTIE, 1),
        (1.0001, INFERIOR_STEEPENING_SRA, 3),
        (1.3999, INFERIOR_STEEPENING_SRA, 3),
        (1.40, ABNORMAL_ECTATIC, 4),
    ],
)
def test_signed_i_s_golden_boundaries(i_s, category, points):
    assert signed_i_s_category(i_s) == category
    assert erss_topography_points(category) == points


def test_randleman_srax_threshold_is_strictly_greater_than_twenty_degrees():
    assert erss_topography_category(0.5, 20.0, None) == NORMAL_SYMMETRIC
    assert erss_topography_category(0.5, 20.1, None) == INFERIOR_STEEPENING_SRA


def test_erss_channels_choose_one_topography_category_not_sum():
    category = erss_topography_category(0.8, 21.0, None)
    assert category == INFERIOR_STEEPENING_SRA
    assert erss_topography_points(category) == 3


@pytest.mark.parametrize(("age", "points"), [(18, 3), (19, 2), (20, 2), (21, 0), (30, 0)])
def test_age_policy_golden_boundaries(age, points):
    assert erss_age_points(age) == points


@pytest.mark.parametrize(
    ("pachy", "points"),
    [(479, None), (480, 2), (499, 2), (500, 1), (509, 1), (510, 0), (511, 0)],
)
def test_pachymetry_policy_golden_boundaries(pachy, points):
    assert erss_pachymetry_points(pachy) == points


@pytest.mark.parametrize(
    ("bad_d", "classification"),
    [(1.60, "NORMAL"), (1.6001, "SUSPICIOUS"), (2.5999, "SUSPICIOUS"), (2.60, "ABNORMAL")],
)
def test_final_bad_d_golden_boundaries(bad_d, classification):
    assert final_bad_d_classification(bad_d) == classification


def test_nice_golden_disposition_bands():
    a = score_nice(44.0, 530.0, 15.0, 0.5)
    b = score_nice(46.0, 510.0, 16.0, 1.2)
    c = score_nice(48.0, 490.0, 18.0, 1.5)
    assert (a["total"], a["category"]) == (4, "NO_NICE_ESCALATION")
    assert (b["total"], b["category"]) == (8, "CAUTION")
    assert (c["total"], c["category"]) == (12, "HARD_STOP")


def test_nice_missing_input_is_incomplete():
    result = score_nice(44.0, None, 15.0, 0.5)
    assert result["total"] is None
    assert result["category"] == "INCOMPLETE"
    assert "central_pachy_um" in result["missing"]


def _ps3_inter_eye():
    return PS3InterEyeInput(
        od_anterior_km_d=43.0,
        os_anterior_km_d=43.1,
        od_posterior_km_d=-6.0,
        os_posterior_km_d=-6.05,
        od_thinnest_um=520.0,
        os_thinnest_um=525.0,
        od_front_elevation_thinnest_um=2.0,
        os_front_elevation_thinnest_um=3.0,
        od_back_elevation_thinnest_um=5.0,
        os_back_elevation_thinnest_um=8.0,
    )


def _ps3_base(**changes):
    values = dict(
        anterior_km_d=47.0,
        thinnest_um=520.0,
        topographic_astig_d=1.0,
        topographic_steep_axis_deg=90.0,
        manifest_astig_d=1.0,
        manifest_axis_deg=90.0,
        ppi_avg=1.0,
        srax="NO",
        srax_deg=0.0,
        f_ele_th_um=10.0,
        b_ele_th_um=10.0,
    )
    values.update(changes)
    return evaluate_ps3(PS3EyeInput(**values), _ps3_inter_eye())


def test_ps3_no_flags_allows_all_three_procedures():
    result = _ps3_base()
    assert result.high_count == 0
    assert result.moderate_count == 0
    assert (result.disposition.prk, result.disposition.smile, result.disposition.lasik) == (
        ALLOWED, ALLOWED, ALLOWED
    )


def test_ps3_one_moderate_defers_lasik_only():
    result = _ps3_base(thinnest_um=490.0)
    assert result.high_count == 0
    assert result.moderate_count == 1
    assert (result.disposition.prk, result.disposition.smile, result.disposition.lasik) == (
        ALLOWED, ALLOWED, DEFER
    )


def test_ps3_two_moderates_defer_all():
    result = _ps3_base(thinnest_um=490.0, ppi_avg=1.3)
    assert result.moderate_count >= 2
    assert (result.disposition.prk, result.disposition.smile, result.disposition.lasik) == (
        DEFER, DEFER, DEFER
    )


def test_ps3_high_finding_defers_all():
    result = _ps3_base(anterior_km_d=51.0)
    assert result.high_count >= 1
    assert (result.disposition.prk, result.disposition.smile, result.disposition.lasik) == (
        DEFER, DEFER, DEFER
    )


def test_ps3_srax_uses_same_strict_twenty_degree_front_map_threshold():
    at_20 = _ps3_base(srax_deg=20.0)
    above_20 = _ps3_base(srax="YES", srax_deg=20.1)
    at_finding = next(item for item in at_20.findings if item.key == "srax")
    above_finding = next(item for item in above_20.findings if item.key == "srax")
    assert at_finding.status == "NORMAL"
    assert above_finding.status == "HIGH"


def test_canonical_finalizer_status_order_is_frozen():
    assert finalize_disposition((DecisionFinding("a", PASS), DecisionFinding("b", CAUTION))).status == CAUTION
    assert finalize_disposition((DecisionFinding("a", CAUTION), DecisionFinding("b", STOP_DEFER))).status == STOP_DEFER


def test_key_safety_constants_are_frozen():
    assert PRK_EPITHELIUM_UM == 50.0
    assert FINAL_KMEAN_MIN_D == 36.0
    assert FINAL_KMEAN_MAX_D == 48.0


def test_phase1_contract_uses_direct_canonical_clinical_authority():
    import runtime_composition

    assert canonical_engine.core._cerai_erss_numeric_extraction_installed
    assert canonical_engine.core._cerai_mandatory_source_set_installed
    assert canonical_engine.core._hc_readiness_installed
    assert "clinical_policy_legacy_pending_retirement" not in runtime_composition.COMPOSITION_PHASES

    workflow_source = Path("assessment_workflow.py").read_text(encoding="utf-8")
    assert "evaluate_case(" in workflow_source
    assert "core.hc_engine" not in workflow_source
    assert "apply_extracted_corrections" not in workflow_source
