from io import BytesIO
import math

import numpy as np
from PIL import Image

import geometric_srax_policy as policy


def _synthetic_four_maps(superior_axis, inferior_axis):
    width, height = 1200, 900
    hsv = np.zeros((height, width, 3), dtype=np.uint8)
    hsv[..., 1] = 0
    hsv[..., 2] = 225
    cx, cy, radius = 600, 330, 135
    yy, xx = np.mgrid[:height, :width]
    xn = (xx - cx) / radius
    yn = (yy - cy) / radius
    rr = np.sqrt(xn * xn + yn * yn)
    angle = np.degrees(np.arctan2(-yn, xn)) % 360.0
    inside = rr <= 1.0
    hsv[inside, 1] = 220
    hsv[inside, 2] = 210
    hsv[inside, 0] = 145

    def angular_distance(a, b):
        return np.abs(((a - b + 180.0) % 360.0) - 180.0)

    sup = inside & (yn < 0)
    inf = inside & (yn > 0)
    sup_d = angular_distance(angle, superior_axis)
    inf_d = angular_distance(angle, inferior_axis)
    # Broad warm lobes, not single hot pixels.
    hsv[sup, 0] = np.clip(25 + sup_d[sup] * 2.2, 25, 145).astype(np.uint8)
    hsv[inf, 0] = np.clip(25 + inf_d[inf] * 2.2, 25, 145).astype(np.uint8)

    image = Image.fromarray(hsv, mode="HSV").convert("RGB")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_symmetric_geometry_is_not_srax_positive():
    result = policy.measure_srax(_synthetic_four_maps(80.0, 260.0))
    assert result["status"] == "CONFIDENT"
    assert result["srax"] == "NO"
    assert result["srax_deg"] <= 5.0


def test_skewed_geometry_over_20_is_srax_positive():
    result = policy.measure_srax(_synthetic_four_maps(80.0, 230.0))
    assert result["status"] == "CONFIDENT"
    assert result["srax"] == "YES"
    assert 20.0 < result["srax_deg"] < 40.0


def test_exact_threshold_rule_is_strictly_greater_than_20():
    assert policy.SRAX_THRESHOLD_DEG == 20.0
    # Clinical threshold semantics are locked independently of image quantization.
    assert (20.0 > policy.SRAX_THRESHOLD_DEG) is False
    assert (20.1 > policy.SRAX_THRESHOLD_DEG) is True


def test_extractor_uses_geometry_not_model_visual_srax(monkeypatch):
    raw = _synthetic_four_maps(80.0, 230.0)

    def previous(_raw, _filename):
        return {
            "eyes": [{
                "eye": "OS",
                "screen_types": ["FOUR_MAPS_REFRACTIVE"],
                "srax": "UNCERTAIN",
                "srax_deg": None,
                "morphology_evidence": [],
            }],
            "global_warnings": [],
        }

    extractor = policy.make_geometric_srax_extractor(object(), previous)
    result = extractor(raw, "synthetic.png")
    eye = result["eyes"][0]
    assert eye["srax"] == "YES"
    assert eye["srax_deg"] > 20.0
    assert eye["field_provenance"]["srax"][0]["source"] == "AXIAL_SAGITTAL_CURVATURE_FRONT_GEOMETRIC"
    assert "srax-geom-v1" in eye["morphology_evidence"][0]
