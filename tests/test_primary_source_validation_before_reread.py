import json
from types import SimpleNamespace

import pytest
import app
import pentacam_targeted_reread as reread
from pentacam_canonical_source_lock import BAD_CENTER


@pytest.mark.parametrize("verified, source", [(False, BAD_CENTER), (True, None)])
def test_primary_axis_rejected_by_source_lock_remains_available_to_post_gate_reread(monkeypatch, verified, source):
    primary = {"document_context": {"document_type": "PENTACAM_TOPOGRAPHY"}, "eyes": [{
        "eye": "OS", "screen_types": ["BAD_DISPLAY"], "bad_flat_axis_deg": 178.5,
        "table_verified_numeric_fields": ["bad_flat_axis_deg"] if verified else [],
        "canonical_source_ids": {"bad_flat_axis_deg": source},
    }]}
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: SimpleNamespace(
        output_text=json.dumps(primary), status="completed", incomplete_details=None)))
    monkeypatch.setattr(app, "openai_client", lambda: client)
    def second_pass(core, result, raw, filename):
        assert result["eyes"][0]["bad_flat_axis_deg"] is None
        targets = reread.missing_targets_by_eye(result)
        assert "bad_flat_axis_deg" in targets["OS"]
        return reread.apply_targeted_readings(core, result, {
            "screen_family": "BAD_DISPLAY", "readings": [{"eye": "OS",
            "field": "bad_flat_axis_deg", "value": 178.5, "status": "CONFIDENT",
            "printed_label": "Axis", "group_label": None, "source_tile": "UPPER_RIGHT"}]},
            targets, filename)
    monkeypatch.setattr(reread, "enrich_extraction", second_pass)
    extracted = app.extract_one_image(b"test", "bad.jpg")
    assert extracted["eyes"][0]["bad_flat_axis_deg"] is None
    enriched = reread.enrich_extraction(app, extracted, b"test", "bad.jpg")
    eye = app.merge_extractions([enriched])["eyes"][0]
    assert eye["bad_flat_axis_deg"] == 178.5
    assert eye["canonical_source_ids"]["bad_flat_axis_deg"] == BAD_CENTER
