import app
import mandatory_source_set_policy
from pentacam_canonical_source_lock import (
    BAD_CENTER,
    SHOW_2_CORNEA_FRONT,
    SHOW_2_INDICES,
)


COMMON_EYE_PROPERTIES = {
    "eye",
    "source_family",
    "screen_types",
    "quality",
    "missing_or_unreadable",
    "table_verified_numeric_fields",
    "keratometry_source",
}


def _variants():
    schemas = app.SCHEMA["properties"]["eyes"]["items"]["anyOf"]
    return {
        schema["properties"]["source_family"]["enum"][0]: schema
        for schema in schemas
    }


def test_primary_eye_schema_has_one_compact_variant_per_source_family():
    variants = _variants()

    assert set(variants) == set(app.SOURCE_SPECIFIC_EYE_FIELDS)
    for family, expected_fields in app.SOURCE_SPECIFIC_EYE_FIELDS.items():
        schema = variants[family]
        assert set(schema["properties"]) == COMMON_EYE_PROPERTIES | set(expected_fields)
        assert set(schema["required"]) == set(schema["properties"])
        assert "canonical_source_ids" not in schema["properties"]
        assert "srax" not in schema["properties"]
        assert "srax_deg" not in schema["properties"]


def test_show_two_schema_contains_only_report_and_decision_relevant_fields():
    show_two = set(app.SOURCE_SPECIFIC_EYE_FIELDS["SHOW_2_EXAMS_TOPOMETRIC"])

    assert show_two == {
        "K1_D", "K1_axis_deg", "K2_D", "K2_axis_deg", "Kmean_D",
        "posterior_Kmean_D", "topographic_astig_D",
        "topographic_steep_axis_deg", "I_S",
    }
    assert not show_two & {
        "ISV", "IVA", "KI", "CKI", "IHA", "IHD", "KISA",
        "topometric_RMin", "Rmin_mm", "corneal_volume_mm3",
    }


def test_normalization_reconstructs_registry_provenance_for_show_two():
    eye = app.normalized_eye({
        "eye": "OD",
        "source_family": "SHOW_2_EXAMS_TOPOMETRIC",
        "screen_types": ["SHOW_2_EXAMS_TOPOMETRIC"],
        "quality": "ADEQUATE",
        "missing_or_unreadable": [],
        "table_verified_numeric_fields": ["K2_D", "I_S"],
        "keratometry_source": "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT",
        "K1_D": None,
        "K1_axis_deg": None,
        "K2_D": 44.2,
        "K2_axis_deg": None,
        "Kmean_D": None,
        "posterior_Kmean_D": None,
        "topographic_astig_D": None,
        "topographic_steep_axis_deg": None,
        "I_S": -0.4,
    })

    assert eye["K2_D"] == 44.2
    assert eye["I_S"] == -0.4
    assert eye["canonical_source_ids"]["K2_D"] == SHOW_2_CORNEA_FRONT
    assert eye["canonical_source_ids"]["I_S"] == SHOW_2_INDICES
    assert eye["B_Ele_Th_um"] is None
    assert eye["srax"] is None
    assert eye["srax_deg"] is None


def test_wrong_family_field_cannot_survive_normalization():
    eye = app.normalized_eye({
        "eye": "OS",
        "source_family": "SHOW_2_EXAMS_TOPOMETRIC",
        "screen_types": ["SHOW_2_EXAMS_TOPOMETRIC"],
        "quality": "ADEQUATE",
        "missing_or_unreadable": [],
        "table_verified_numeric_fields": ["bad_flat_axis_deg"],
        "keratometry_source": "SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT",
        "bad_flat_axis_deg": 87,
        "canonical_source_ids": {"bad_flat_axis_deg": BAD_CENTER},
    })

    assert eye["bad_flat_axis_deg"] is None
    assert "bad_flat_axis_deg" not in eye["table_verified_numeric_fields"]
    assert eye["canonical_source_ids"]["bad_flat_axis_deg"] is None


def test_source_set_gate_recognizes_canonical_source_family_directly():
    result = {
        "document_context": {"document_type": "PENTACAM_TOPOGRAPHY", "laterality": "BOTH"},
        "eyes": [{
            "eye": "OD",
            "source_family": "SHOW_2_EXAMS_TOPOMETRIC",
            "screen_types": [],
            "keratometry_source": "UNREADABLE",
        }],
    }

    summary = mandatory_source_set_policy.classify_source_set([result])

    assert summary["present"]["Show 2 Exams Topometric"] is True


def test_prompt_declares_single_source_specific_contract_without_model_provenance():
    assert "CANONICAL SOURCE-SPECIFIC OUTPUT CONTRACT" in app.PROMPT
    assert "Do not return source identifiers" in app.PROMPT
    assert "Return canonical_source_ids" not in app.PROMPT
