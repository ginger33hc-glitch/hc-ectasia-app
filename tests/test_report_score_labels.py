from pathlib import Path

import reports


def _eye(procedure):
    return {
        "values": {"procedure": procedure},
        "score": {"total": 2, "category": "LOW"},
        "randleman_erss": {"total": 2, "category": "LOW"},
    }


def test_lasik_report_does_not_duplicate_randleman_as_generic_score():
    labels = [label for label, _value in reports._eye_metrics(_eye("LASIK"))]
    assert "Score / category" not in labels
    assert "CER-AI provisional PRK-EWSS score / category" not in labels
    assert labels.count("Randleman ERSS / category") == 1


def test_prk_report_labels_provisional_score_explicitly():
    labels = [label for label, _value in reports._eye_metrics(_eye("PRK"))]
    assert "Score / category" not in labels
    assert labels.count("CER-AI provisional PRK-EWSS score / category") == 1


def test_browser_report_uses_the_same_procedure_specific_label_rule():
    html = (Path(__file__).resolve().parents[1] / "static" / "index.html").read_text()
    assert '["Score / category"' not in html
    assert 'toUpperCase()==="PRK"' in html
    assert "CER-AI provisional PRK-EWSS score / category" in html
