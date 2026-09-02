from types import SimpleNamespace

import ps3_report_policy


def test_report_policy_appends_ps3_metrics_and_review_findings_without_replacing_base_content():
    report_module = SimpleNamespace(
        _eye_metrics=lambda eye, locale="en": [("Base", "Metric")],
        _findings=lambda eye, locale="en": [("Base findings", ["Existing finding"])],
        translate_text=lambda text, locale: text,
    )
    ps3_report_policy.install(report_module)

    eye = {
        "ps3": {
            "applicable": True,
            "moderate_count": 1,
            "high_count": 0,
            "derived_srax_deg": 18.5,
            "inter_eye_score": 2,
            "disposition": {"prk": "ALLOWED", "smile": "ALLOWED", "lasik": "DEFER"},
            "findings": [
                {"key": "ppi_average", "status": "MODERATE", "detail": "PPI Average 1.3 > 1.20."},
            ],
            "review_notes": [
                "PTI/CTSP thickness-profile morphology not evaluated — surgeon review required.",
            ],
        }
    }

    metrics = report_module._eye_metrics(eye)
    findings = report_module._findings(eye)

    assert metrics[0] == ("Base", "Metric")
    assert ("PS3 procedure disposition", "PRK ALLOWED / SMILE ALLOWED / LASIK DEFER") in metrics
    assert any(label == "PS3 derived SRAX" and "18.5" in value for label, value in metrics)
    assert findings[0] == ("Base findings", ["Existing finding"])
    assert any(title == "PS3 component assessment" for title, _ in findings)
    assert any(title == "PS3 surgeon review required" for title, _ in findings)


def test_report_policy_is_idempotent_and_ignores_non_applicable_ps3():
    report_module = SimpleNamespace(
        _eye_metrics=lambda eye, locale="en": [("Base", "Metric")],
        _findings=lambda eye, locale="en": [("Base findings", ["Existing finding"])],
        translate_text=lambda text, locale: text,
    )
    ps3_report_policy.install(report_module)
    installed_metrics = report_module._eye_metrics
    installed_findings = report_module._findings
    ps3_report_policy.install(report_module)

    assert report_module._eye_metrics is installed_metrics
    assert report_module._findings is installed_findings
    assert report_module._eye_metrics({"ps3": {"applicable": False}}) == [("Base", "Metric")]
    assert report_module._findings({"ps3": {"applicable": False}}) == [("Base findings", ["Existing finding"])]
