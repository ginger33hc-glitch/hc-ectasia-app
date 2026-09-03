from types import SimpleNamespace

import ps3_report_policy


def _module():
    return SimpleNamespace(
        _eye_metrics=lambda eye, locale="en": [("Base", "Metric")],
        _findings=lambda eye, locale="en": [("Base findings", ["Existing finding"])],
        translate_text=lambda text, locale: text,
    )


def test_report_policy_appends_ps3_metrics_and_moderate_interpretation_without_replacing_base_content():
    report_module = _module()
    ps3_report_policy.install(report_module)

    eye = {
        "ps3": {
            "applicable": True,
            "moderate_count": 1,
            "high_count": 0,
            "srax_deg": 18.5,
            "inter_eye_score": 2,
            "disposition": {"prk": "ALLOWED", "smile": "ALLOWED", "lasik": "DEFER"},
            "findings": [
                {"key": "ppi_average", "status": "MODERATE", "detail": "PPI Average 1.3 > 1.20."},
                {"key": "srax", "status": "NORMAL", "detail": "Front-map SRAX 18.5° <= 20°."},
            ],
            "review_notes": [
                "PTI/CTSP thickness-profile morphology not evaluated — surgeon review required.",
            ],
        }
    }

    metrics = report_module._eye_metrics(eye)
    findings = report_module._findings(eye)

    assert metrics[0] == ("Base", "Metric")
    assert ("PS3 / classification", "1 moderate / 0 high — MODERATE") in metrics
    assert ("PS3 procedure disposition", "PRK ALLOWED / SMILE ALLOWED / LASIK DEFER") in metrics
    assert any(label == "PS3 SRAX (Front map only)" and "18.5" in value for label, value in metrics)
    assert not any("derived" in (label + value).lower() for label, value in metrics)
    assert findings[0] == ("Base findings", ["Existing finding"])
    assert findings[-3][0] == "PS3 summary and interpretation"
    assert any("exactly one Moderate" in line for line in findings[-3][1])
    assert any("LASIK is DEFERRED" in line for line in findings[-3][1])
    assert any("Ppi Average: MODERATE" in line for line in findings[-3][1])
    assert findings[-2][0] == "PS3 criteria audit"
    assert findings[-1][0] == "PS3 surgeon review required"


def test_report_policy_explains_fail_defer_and_front_map_srax_trigger():
    report_module = _module()
    ps3_report_policy.install(report_module)

    eye = {
        "ps3": {
            "applicable": True,
            "moderate_count": 2,
            "high_count": 1,
            "srax_deg": 24.0,
            "inter_eye_score": 5,
            "disposition": {"prk": "DEFER", "smile": "DEFER", "lasik": "DEFER"},
            "findings": [
                {"key": "thinnest", "status": "MODERATE", "detail": "Thinnest 490 µm is 470-500 µm."},
                {"key": "ppi_average", "status": "MODERATE", "detail": "PPI Average 1.3 > 1.20."},
                {"key": "srax", "status": "HIGH", "detail": "Front-map SRAX 24.0° > 20°. Source: Axial/Sagittal Curvature (Front)."},
            ],
            "review_notes": [],
        }
    }

    metrics = report_module._eye_metrics(eye)
    findings = report_module._findings(eye)

    assert ("PS3 / classification", "2 moderate / 1 high — FAIL / DEFER") in metrics
    assert any(label == "PS3 SRAX (Front map only)" and value == "24.0 degrees" for label, value in metrics)
    summary = next(lines for title, lines in findings if title == "PS3 summary and interpretation")
    assert any("FAIL / DEFER" in line and "2 Moderate and 1 High" in line for line in summary)
    assert any("DEFER PRK/surface ablation, SMILE, and LASIK" in line for line in summary)
    assert sum("Triggering PS3 criterion:" in line for line in summary) == 3
    assert any("Front-map SRAX 24.0° > 20°" in line for line in summary)


def test_report_policy_no_risk_factor_has_concise_normal_interpretation():
    report_module = _module()
    ps3_report_policy.install(report_module)

    eye = {
        "ps3": {
            "applicable": True,
            "moderate_count": 0,
            "high_count": 0,
            "srax_deg": 5.0,
            "inter_eye_score": 0,
            "disposition": {"prk": "ALLOWED", "smile": "ALLOWED", "lasik": "ALLOWED"},
            "findings": [],
            "review_notes": [],
        }
    }

    metrics = report_module._eye_metrics(eye)
    findings = report_module._findings(eye)
    assert ("PS3 / classification", "0 moderate / 0 high — NO PS3 RISK FACTOR") in metrics
    summary = next(lines for title, lines in findings if title == "PS3 summary and interpretation")
    assert any("NO PS3 RISK FACTOR" in line for line in summary)


def test_report_policy_marks_missing_srax_for_surgeon_confirmation():
    report_module = _module()
    ps3_report_policy.install(report_module)
    eye = {
        "ps3": {
            "applicable": True,
            "moderate_count": 0,
            "high_count": 0,
            "srax_deg": None,
            "inter_eye_score": 0,
            "disposition": {"prk": "ALLOWED", "smile": "ALLOWED", "lasik": "ALLOWED"},
            "findings": [],
            "review_notes": [],
        }
    }
    metrics = report_module._eye_metrics(eye)
    value = next(value for label, value in metrics if label == "PS3 SRAX (Front map only)")
    assert "surgeon confirmation required" in value.lower()


def test_report_policy_is_idempotent_and_ignores_non_applicable_ps3():
    report_module = _module()
    ps3_report_policy.install(report_module)
    installed_metrics = report_module._eye_metrics
    installed_findings = report_module._findings
    ps3_report_policy.install(report_module)

    assert report_module._eye_metrics is installed_metrics
    assert report_module._findings is installed_findings
    assert report_module._eye_metrics({"ps3": {"applicable": False}}) == [("Base", "Metric")]
    assert report_module._findings({"ps3": {"applicable": False}}) == [("Base findings", ["Existing finding"])]
