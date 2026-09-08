from __future__ import annotations

import base64
from io import BytesIO
import json
from types import SimpleNamespace

from PIL import Image

import pentacam_targeted_reread as targeted
from pentacam_canonical_source_lock import (
    CANONICAL_FIELD_SOURCES,
    CANONICAL_VISUAL_CONTRACTS,
)


def _image_bytes(width=1000, height=800):
    output = BytesIO()
    Image.new("RGB", (width, height), "white").save(output, format="PNG")
    return output.getvalue()


class _Core:
    MODEL = "gpt-5.6-terra"

    def __init__(self, payload):
        self._payload = payload

    @staticmethod
    def is_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    @staticmethod
    def data_url(raw, _filename):
        return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")

    def openai_client(self):
        return SimpleNamespace(responses=SimpleNamespace(
            create=lambda **_kwargs: SimpleNamespace(output_text=json.dumps(self._payload)),
        ))


def _localized(field, value, label, group):
    return {
        "eye": "OD", "field": field, "value": value, "status": "CONFIDENT",
        "printed_label": label, "group_label": group, "source_tile": "UPPER_RIGHT",
        "source_box": [100, 100, 600, 500],
    }


def test_every_locked_field_has_one_label_first_visual_contract():
    assert set(CANONICAL_VISUAL_CONTRACTS) == set(CANONICAL_FIELD_SOURCES)
    for field, (source_id, label) in CANONICAL_FIELD_SOURCES.items():
        contract = CANONICAL_VISUAL_CONTRACTS[field]
        assert contract["source_id"] == source_id
        assert contract["field_label"] == label

    assert CANONICAL_VISUAL_CONTRACTS["K1_D"]["section_label"] == "Cornea Front"
    assert CANONICAL_VISUAL_CONTRACTS["Rmin_mm"]["section_label"] == "Cornea Back"
    assert CANONICAL_VISUAL_CONTRACTS["Df"]["field_label"] == "Df"
    assert CANONICAL_VISUAL_CONTRACTS["BAD_D"]["field_label"] == "D"


def test_k1_crop_is_rejected_when_pixels_show_cornea_back_section():
    reading = _localized("K1_D", 42.1, "K1", "Cornea Front")
    payload = {"readings": [{
        "eye": "OD", "field": "K1_D", "visible_section_label": "Cornea Back",
        "visible_field_label": "K1", "observed_value_text": "42.1", "value": 42.1,
        "adjacent_value": True, "status": "CONFIRMED",
    }], "warnings": []}
    confirmed = targeted.confirm_labeled_reading_crops(
        _Core(payload), _image_bytes(), "show2.png", "SHOW_2_EXAMS_TOPOMETRIC", [reading],
    )
    assert confirmed == []


def test_rmin_crop_is_accepted_only_from_cornea_back_section():
    reading = _localized("Rmin_mm", 5.65, "Rmin", "Cornea Back")
    payload = {"readings": [{
        "eye": "OD", "field": "Rmin_mm", "visible_section_label": "Cornea Back",
        "visible_field_label": "Rmin", "observed_value_text": "5.65", "value": 5.65,
        "adjacent_value": True, "status": "CONFIRMED",
    }], "warnings": []}
    confirmed = targeted.confirm_labeled_reading_crops(
        _Core(payload), _image_bytes(), "show2.png", "SHOW_2_EXAMS_TOPOMETRIC", [reading],
    )
    assert len(confirmed) == 1
    assert confirmed[0]["field"] == "Rmin_mm"
    assert confirmed[0]["value"] == 5.65
    assert confirmed[0]["group_label"] == "Cornea Back"
    assert confirmed[0]["pixel_label_value_confirmed"] is True


def test_bad_elevation_confirmation_rejects_k1_axis_crop():
    payload = {"readings": [{
        "eye": "OD", "field": "F_Ele_Th_um", "visible_field_label": "Axis",
        "visible_companion_label": "K1", "row_identity": "WRONG_ROW",
        "observed_value_text": "3", "value": 3, "status": "CONFIDENT",
    }], "warnings": []}
    confirmed = targeted.confirm_bad_elevation_crops(
        _Core(payload), {("OD", "F_Ele_Th_um"): _image_bytes(180, 80)},
    )
    assert confirmed == {}


def test_wrong_crop_is_relocalized_once_before_surgeon_fallback(monkeypatch):
    first = {"screen_family": "SHOW_2_EXAMS_TOPOMETRIC", "readings": [
        _localized("K1_D", 42.1, "K1", "Cornea Front"),
    ], "warnings": []}
    second = {"screen_family": "SHOW_2_EXAMS_TOPOMETRIC", "readings": [
        _localized("K1_D", 42.1, "K1", "Cornea Front"),
    ], "warnings": []}
    reread_calls = []

    def reread(*_args, **_kwargs):
        reread_calls.append(True)
        return first if len(reread_calls) == 1 else second

    confirmations = iter([[], [{
        **second["readings"][0], "pixel_label_value_confirmed": True,
    }]])
    monkeypatch.setattr(targeted, "targeted_reread", reread)
    monkeypatch.setattr(
        targeted, "confirm_labeled_reading_crops", lambda *_args, **_kwargs: next(confirmations),
    )

    guarded = targeted.targeted_reread_with_visual_guard(
        _Core({}), _image_bytes(), "show2.png", {"OD": ["K1_D"]},
    )

    assert len(reread_calls) == 2
    assert guarded["readings"][0]["pixel_label_value_confirmed"] is True
