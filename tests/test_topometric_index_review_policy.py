from types import SimpleNamespace

import topometric_index_review_policy as policy


def test_reference_boundaries_are_locked():
    assert policy._numeric_status("ISV", 36.9) == "NORMAL"
    assert policy._numeric_status("ISV", 37) == "YELLOW"
    assert policy._numeric_status("ISV", 41) == "RED"

    assert policy._numeric_status("IVA", 0.279) == "NORMAL"
    assert policy._numeric_status("IVA", 0.28) == "YELLOW"
    assert policy._numeric_status("IVA", 0.32) == "RED"

    assert policy._numeric_status("KI", 1.07) == "NORMAL"
    assert policy._numeric_status("KI", 1.071) == "RED"
    assert policy._numeric_status("CKI", 1.029) == "NORMAL"
    assert policy._numeric_status("CKI", 1.03) == "RED"

    assert policy._numeric_status("IHA", 18.9) == "NORMAL"
    assert policy._numeric_status("IHA", 19) == "YELLOW"
    assert policy._numeric_status("IHA", 21) == "YELLOW"
    assert policy._numeric_status("IHA", 21.01) == "RED"

    assert policy._numeric_status("IHD", 0.0139) == "NORMAL"
    assert policy._numeric_status("IHD", 0.014) == "YELLOW"
    assert policy._numeric_status("IHD", 0.016) == "RED"

    assert policy._numeric_status("Rmin_mm", 6.71) == "NORMAL"
    assert policy._numeric_status("Rmin_mm", 6.70) == "RED"

    assert policy._numeric_status("KISA", 59.9) == "NORMAL"
    assert policy._numeric_status("KISA", 60) == "YELLOW"
    assert policy._numeric_status("KISA", 100) == "YELLOW"
    assert policy._numeric_status("KISA", 100.1) == "RED"

    assert policy._numeric_status("I_S", 1.2) == "NORMAL"
    assert policy._numeric_status("I_S", 1.21) == "RED"


def test_tkc_is_conservative_and_never_inferred():
    for normal in ("0", "TKC0", "normal", "no kc"):
        assert policy._tkc_status(normal) == "NORMAL"
    for suspect in ("suspect", "possible KC", "borderline"):
        assert policy._tkc_status(suspect) == "YELLOW"
    for abnormal in ("1", "1-2", "2", "2-3", "3", "3-4", "4", "TKC2"):
        assert policy._tkc_status(abnormal) == "RED"
    assert policy._tkc_status("unreadable device comment") == "UNINTERPRETED"
    assert policy._tkc_status(None) == "UNAVAILABLE"


def test_review_escalates_visually_but_has_no_scoring_effect():
    review = policy.build_review({
        "ISV": 38,
        "IVA": 0.20,
        "KI": 1.00,
        "CKI": 1.00,
        "IHA": 10,
        "IHD": 0.010,
        "Rmin_mm": 7.2,
        "KISA": 20,
        "I_S": 0.4,
        "TKC": "0",
    })
    assert review["status"] == "YELLOW"
    assert review["report_only"] is True
    assert review["scoring_effect"] == "NONE"

    review_red = policy.build_review({"IVA": 0.33})
    assert review_red["status"] == "RED"
    assert review_red["scoring_effect"] == "NONE"


def test_tkc_schema_is_string_and_report_only_prompt_is_explicit():
    core = SimpleNamespace(
        SCHEMA={
            "properties": {
                "eyes": {
                    "items": {
                        "properties": {},
                        "required": [],
                    }
                }
            }
        },
        PROMPT="base prompt",
    )
    policy._install_tkc_extraction(core)
    eye_schema = core.SCHEMA["properties"]["eyes"]["items"]
    assert eye_schema["properties"]["TKC"] == {"type": ["string", "null"]}
    assert "TKC" in eye_schema["required"]
    assert "TKC is not a scoring input" in core.PROMPT
    assert "Never infer TKC" in core.PROMPT


def test_tkc_conflict_is_removed_before_clinical_engine():
    extracted = {
        "eyes": [
            {
                "eye": "OD",
                "TKC": "1",
                "data_conflicts": ["TKC: 1 vs 2", "BAD_D: 1.2 vs 2.8"],
            }
        ]
    }
    safe = policy._strip_tkc_conflicts(extracted)
    assert safe["eyes"][0]["data_conflicts"] == ["BAD_D: 1.2 vs 2.8"]
    assert extracted["eyes"][0]["data_conflicts"] == ["TKC: 1 vs 2", "BAD_D: 1.2 vs 2.8"]
