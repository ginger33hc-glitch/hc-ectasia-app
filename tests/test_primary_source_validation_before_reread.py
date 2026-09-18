import json
from types import SimpleNamespace

import pytest
import app
import pentacam_targeted_reread as reread
from pentacam_canonical_source_lock import BAD_CENTER


@pytest.mark.parametrize("verified, source", [(False, BAD_CENTER), (True, None)])
def test_rejected_optional_axis_is_bypassed_without_targeted_reread(monkeypatch, verified, source):
    primary = {"document_context": {"document_type": "PENTACAM_TOPOGRAPHY"}, "eyes": [{
        "eye": "OS", "screen_types": ["BAD_DISPLAY"], "bad_flat_axis_deg": 178.5,
        "table_verified_numeric_fields": ["bad_flat_axis_deg"] if verified else [],
        "canonical_source_ids": {"bad_flat_axis_deg": source},
    }]}
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: SimpleNamespace(
        output_text=json.dumps(primary), status="completed", incomplete_details=None)))
    monkeypatch.setattr(app, "openai_client", lambda: client)
    extracted = app.extract_one_image(b"test", "bad.jpg")
    assert extracted["eyes"][0]["bad_flat_axis_deg"] is None
    assert "bad_flat_axis_deg" not in reread.missing_targets_by_eye(extracted)["OS"]
    eye = app.merge_extractions([extracted])["eyes"][0]
    assert eye["bad_flat_axis_deg"] is None
    assert "bad_flat_axis_deg" not in eye.get("missing_or_unreadable", [])
