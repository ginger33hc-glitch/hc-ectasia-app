import inspect

from clinical_core.bad import BADContext, BADResult
from clinical_core.disposition import CAUTION, PASS, DecisionFinding, finalize_disposition
from clinical_core.report_payload import build_report_payload
from ps3_policy import PS3Finding, PS3ProcedureDisposition, PS3Result


def _assessment(procedure="LASIK"):
    final = finalize_disposition((
        DecisionFinding("bad_d", CAUTION, "Final BAD-D suspicious"),
        DecisionFinding("nice", PASS, "NICE reassuring"),
    ))
    return {
        "procedure": procedure,
        "status": final.status,
        "erss": {
            "category": "ASYMMETRIC_BOWTIE",
            "rows": {"topography": 1, "RSB": 0, "age": 0, "pachymetry": 0, "MRSE": 0},
            "total": 1,
        },
        "erss_status": PASS,
        "nice": {
            "rows": {"K2": 1, "central_pachymetry": 1, "B_Ele_Th": 1, "I_S": 1},
            "total": 4,
            "category": "NO_NICE_ESCALATION",
            "values": {"K2_D": 44.0, "central_pachy_um": 540, "B_Ele_Th_um": 10, "I_S_D": 0.6},
            "missing": [],
        },
        "nice_status": PASS,
        "bad_d": {
            "result": BADResult(2.0, "SUSPICIOUS", BADContext(df=-0.2, db=1.1, da=1.4, artmax_um=350)),
            "classification": "SUSPICIOUS",
            "status": CAUTION,
        },
        "ps3": PS3Result(
            findings=(PS3Finding("anterior_km", "NORMAL", "normal"),),
            moderate_count=0,
            high_count=0,
            disposition=PS3ProcedureDisposition("ALLOWED", "ALLOWED", "ALLOWED"),
            complete=True,
            missing_keys=(),
        ),
        "ps3_status": PASS,
        "procedural_safety": {
            "LASIK_RSB_um": 320,
            "LASIK_PTA_percent": 37,
            "hard_stops": {},
            "status": PASS,
        },
        "final_disposition": final,
    }


def test_report_payload_copies_calculated_rows_and_drivers_without_recalculation():
    payload = build_report_payload(
        _assessment(),
        eye="OD",
        software_version="0.8.0-test",
        clinical_policy_version="2026-09-07",
        source_registry_version="2026-09-07",
        srax_algorithm_version="srax-geom-v2",
    )
    assert payload["status"] == CAUTION
    assert payload["randleman"]["rows"]["topography"] == 1
    assert payload["nice"]["total"] == 4
    assert payload["bad"]["final_d"] == 2.0
    assert payload["bad"]["context"]["df"] == -0.2
    assert payload["bad"]["context"]["artmax_um"] == 350
    assert payload["ps3"]["complete"] is True
    assert payload["decision_drivers"]["caution"][0]["key"] == "bad_d"


def test_prk_flap_is_presented_as_na_without_changing_clinical_payload():
    payload = build_report_payload(
        _assessment("PRK"),
        eye="OS",
        software_version="x",
        clinical_policy_version="y",
        source_registry_version="z",
        srax_algorithm_version="s",
    )
    assert payload["procedure_display"]["flap"] == "N/A"


def test_manual_correction_is_labeled_surgeon_confirmed():
    payload = build_report_payload(
        _assessment(),
        eye="OD",
        software_version="x",
        clinical_policy_version="y",
        source_registry_version="z",
        srax_algorithm_version="s",
        manual_corrections=({"field": "I_S", "value": 0.58},),
    )
    assert payload["manual_corrections"] == [
        {"field": "I_S", "value": 0.58, "label": "SURGEON_CONFIRMED"}
    ]


def test_versions_are_printable_from_one_payload():
    payload = build_report_payload(
        _assessment(), eye="OD", software_version="1", clinical_policy_version="2",
        source_registry_version="3", srax_algorithm_version="4",
    )
    assert payload["versions"] == {
        "software": "1", "clinical_policy": "2", "source_registry": "3", "srax_algorithm": "4"
    }


def test_report_projection_has_no_clinical_module_imports_or_threshold_logic():
    import clinical_core.report_payload as module
    source = inspect.getsource(module)
    assert "from .rules" not in source
    assert "from .safety" not in source
    assert "from .nice" not in source
    assert "from .bad" not in source
    assert ">= 2.6" not in source
    assert ">= 4" not in source
