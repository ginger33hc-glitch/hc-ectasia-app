import cv2
import numpy as np

from srax_geometry import analyze_srax_bytes


def _synthetic_front_map(superior_deg: float, inferior_deg: float) -> bytes:
    height, width = 800, 1000
    cx, cy, radius = 500, 300, 170
    image = np.full((height, width, 3), 235, dtype=np.uint8)
    yy, xx = np.indices((height, width))
    dx = xx - cx
    dy = cy - yy
    rr = np.hypot(dx, dy)
    theta = np.degrees(np.arctan2(dy, dx)) % 360.0
    circle = rr <= radius
    base = np.array([180.0, 90.0, 50.0])  # BGR cool curvature
    target = np.array([20.0, 210.0, 240.0])  # BGR warm curvature
    image[circle] = base.astype(np.uint8)

    def angular_difference(angle, center):
        return np.abs(((angle - center + 180.0) % 360.0) - 180.0)

    radial = np.clip((rr / radius - 0.15) / 0.70, 0.0, 1.0)
    heat = np.exp(-(angular_difference(theta, superior_deg) / 18.0) ** 2) * radial * (dy > 0)
    heat += np.exp(-(angular_difference(theta, inferior_deg) / 18.0) ** 2) * radial * (dy < 0)
    alpha = np.clip(heat, 0.0, 1.0)[..., None]
    values = (base * (1.0 - alpha) + target * alpha).astype(np.uint8)
    image[circle] = values[circle]
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    return encoded.tobytes()


def test_symmetric_axes_are_srax_negative():
    result = analyze_srax_bytes(_synthetic_front_map(90.0, 270.0))
    assert result.status == "NO"
    assert result.confidence == "HIGH"
    assert result.srax_deg is not None and result.srax_deg < 10.0


def test_skew_over_20_is_srax_positive():
    result = analyze_srax_bytes(_synthetic_front_map(60.0, 270.0))
    assert result.status == "YES"
    assert result.confidence == "HIGH"
    assert result.srax_deg is not None and result.srax_deg > 20.0


def test_borderline_geometry_fails_closed():
    result = analyze_srax_bytes(_synthetic_front_map(70.0, 270.0))
    assert result.status == "UNCERTAIN"
    assert result.confidence == "BORDERLINE"


def test_non_map_image_fails_closed():
    image = np.full((800, 1000, 3), 230, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    result = analyze_srax_bytes(encoded.tobytes())
    assert result.status == "UNCERTAIN"
    assert result.srax_deg is None
