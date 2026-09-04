"""Deterministic SRAX measurement from Pentacam Axial/Sagittal Curvature (Front).

This module performs pixel geometry only. It does not visually classify morphology and does not
use KISA, I-S, Kmax, keratometric axes, BAD values, elevation, pachymetry, or any other surrogate.
When the map cannot be localized or the lobe geometry is not sufficiently directional, it fails
closed and leaves SRAX unresolved.
"""
from __future__ import annotations

from io import BytesIO
import math
import os
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageOps

ALGORITHM_VERSION = "srax-geom-v1"
MAX_SOURCE_PIXELS = 60_000_000
SRAX_THRESHOLD_DEG = 20.0


def _enabled() -> bool:
    return os.getenv("CERAI_GEOMETRIC_SRAX_ENABLED", "1").strip() == "1"


def _is_four_maps_eye(eye: dict[str, Any]) -> bool:
    for screen_type in eye.get("screen_types") or []:
        text = str(screen_type).upper().replace("_", " ")
        if "4 MAP" in text or "FOUR MAP" in text or "4MAP" in text:
            return True
    return False


def _load_hsv(raw: bytes) -> np.ndarray:
    with Image.open(BytesIO(raw)) as opened:
        width, height = opened.size
        if width <= 0 or height <= 0 or width * height > MAX_SOURCE_PIXELS:
            raise ValueError("image dimensions are outside the geometric-SRAX safety limit")
        image = ImageOps.exif_transpose(opened).convert("RGB")
        image.load()
    max_dim = max(image.size)
    if max_dim > 1200:
        scale = 1200.0 / max_dim
        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
    return np.asarray(image.convert("HSV"), dtype=np.uint8)


def _ring_saturation_coverage(hsv: np.ndarray, cx: float, cy: float, radius: float, r1: float, r2: float) -> float:
    height, width = hsv.shape[:2]
    hits = 0
    total = 0
    for fraction in np.linspace(r1, r2, 3):
        for angle_deg in range(0, 360, 6):
            angle = math.radians(angle_deg)
            x = round(cx + radius * fraction * math.cos(angle))
            y = round(cy - radius * fraction * math.sin(angle))
            if 0 <= x < width and 0 <= y < height:
                total += 1
                if int(hsv[y, x, 1]) > 55:
                    hits += 1
    return hits / total if total else 0.0


def _locate_axial_front_map(hsv: np.ndarray) -> dict[str, float] | None:
    """Locate the upper-left colored corneal map on a Pentacam 4 Maps Refractive page.

    The search uses only page geometry and saturation. It does not inspect labels or infer SRAX.
    """
    height, width = hsv.shape[:2]
    minimum_dimension = min(height, width)
    best: tuple[float, float, float, float, float, float, float] | None = None
    for x_ratio in np.linspace(0.43, 0.56, 8):
        for y_ratio in np.linspace(0.24, 0.44, 9):
            cx = x_ratio * width
            cy = y_ratio * height
            for radius_fraction in np.linspace(0.10, 0.21, 12):
                radius = radius_fraction * minimum_dimension
                inner = _ring_saturation_coverage(hsv, cx, cy, radius, 0.20, 0.80)
                edge = _ring_saturation_coverage(hsv, cx, cy, radius, 0.85, 0.98)
                outer = _ring_saturation_coverage(hsv, cx, cy, radius, 1.08, 1.18)
                score = inner + 0.50 * edge - 0.80 * outer - abs(x_ratio - 0.50) * 0.05
                if inner < 0.70:
                    score -= 1.0
                candidate = (score, cx, cy, radius, inner, edge, outer)
                if best is None or candidate[0] > best[0]:
                    best = candidate
    if best is None:
        return None
    score, cx, cy, radius, inner, edge, outer = best
    if inner < 0.75 or edge < 0.55 or outer > 0.35:
        return None
    return {
        "score": float(score),
        "cx": float(cx),
        "cy": float(cy),
        "radius": float(radius),
        "inner_coverage": float(inner),
        "edge_coverage": float(edge),
        "outer_coverage": float(outer),
    }


def _lobe_axis(hsv: np.ndarray, map_geometry: dict[str, float], superior: bool) -> dict[str, float] | None:
    cx = map_geometry["cx"]
    cy = map_geometry["cy"]
    radius = map_geometry["radius"]
    height, width = hsv.shape[:2]
    x0 = max(0, int(cx - radius))
    x1 = min(width, int(cx + radius + 1))
    y0 = max(0, int(cy - radius))
    y1 = min(height, int(cy + radius + 1))
    yy, xx = np.mgrid[y0:y1, x0:x1]
    x_norm = (xx - cx) / radius
    y_norm = (yy - cy) / radius
    radial = np.sqrt(x_norm * x_norm + y_norm * y_norm)
    hue = hsv[y0:y1, x0:x1, 0].astype(float)
    saturation = hsv[y0:y1, x0:x1, 1].astype(float)
    value = hsv[y0:y1, x0:x1, 2].astype(float)

    mask = (radial > 0.15) & (radial < 0.78) & (saturation > 55) & (value > 40)
    mask &= y_norm < 0 if superior else y_norm > 0
    if int(mask.sum()) < 250:
        return None

    # Pentacam relative-curvature palette is monotonic from warm/high curvature toward
    # green/cyan/blue/purple lower curvature. Use hue only as an ordered within-map quantity;
    # no dioptric value is reconstructed from color.
    score = (255.0 - hue) / 255.0
    score *= np.clip((saturation - 55.0) / 130.0, 0.0, 1.0)
    threshold = float(np.percentile(score[mask], 75.0))
    selected = mask & (score >= threshold)
    if int(selected.sum()) < 120:
        return None
    weights = np.maximum(score - threshold, 1e-6) * selected
    total_weight = float(weights.sum())
    if total_weight <= 0:
        return None

    x_mean = float((x_norm * weights).sum() / total_weight)
    y_mean = float((y_norm * weights).sum() / total_weight)
    centroid_radius = math.hypot(x_mean, y_mean)
    safe_radial = np.where(radial > 0, radial, 1.0)
    ux = x_norm / safe_radial
    uy = -y_norm / safe_radial
    ux_mean = float((ux * weights).sum() / total_weight)
    uy_mean = float((uy * weights).sum() / total_weight)
    angular_concentration = math.hypot(ux_mean, uy_mean)
    angle_deg = math.degrees(math.atan2(-y_mean, x_mean)) % 360.0

    if centroid_radius < 0.18 or angular_concentration < 0.75:
        return None
    return {
        "axis_deg": float(angle_deg),
        "centroid_radius": float(centroid_radius),
        "angular_concentration": float(angular_concentration),
        "selected_pixels": float(int(selected.sum())),
    }


def measure_srax(raw: bytes) -> dict[str, Any]:
    hsv = _load_hsv(raw)
    map_geometry = _locate_axial_front_map(hsv)
    if map_geometry is None:
        return {"status": "UNCERTAIN", "reason": "AXIAL_FRONT_MAP_NOT_RELIABLY_LOCALIZED"}
    superior = _lobe_axis(hsv, map_geometry, superior=True)
    inferior = _lobe_axis(hsv, map_geometry, superior=False)
    if superior is None or inferior is None:
        return {"status": "UNCERTAIN", "reason": "HEMIMERIDIAN_GEOMETRY_NOT_DIRECTIONAL_ENOUGH"}

    separation = (inferior["axis_deg"] - superior["axis_deg"]) % 360.0
    srax_deg = abs(separation - 180.0)
    if srax_deg > 180.0:
        srax_deg = 360.0 - srax_deg
    srax_deg = min(float(srax_deg), 90.0)
    positive = srax_deg > SRAX_THRESHOLD_DEG
    confidence = min(
        map_geometry["inner_coverage"],
        superior["angular_concentration"],
        inferior["angular_concentration"],
    )
    return {
        "status": "CONFIDENT",
        "algorithm": ALGORITHM_VERSION,
        "source": "AXIAL_SAGITTAL_CURVATURE_FRONT_GEOMETRIC",
        "superior_axis_deg": round(superior["axis_deg"], 1),
        "inferior_axis_deg": round(inferior["axis_deg"], 1),
        "srax_deg": round(srax_deg, 1),
        "srax": "YES" if positive else "NO",
        "threshold_rule": "SRAX >20.0 degrees is positive; exactly 20.0 degrees is negative.",
        "confidence": round(float(confidence), 3),
        "map_geometry": map_geometry,
        "superior_metrics": superior,
        "inferior_metrics": inferior,
    }


def make_geometric_srax_extractor(core: Any, previous: Callable[[bytes, str], dict[str, Any]]):
    def extract_one_image_with_geometric_srax(raw: bytes, filename: str) -> dict[str, Any]:
        result = previous(raw, filename)
        if not _enabled():
            return result
        eyes = [eye for eye in result.get("eyes") or [] if eye.get("eye") in {"OD", "OS"} and _is_four_maps_eye(eye)]
        if len(eyes) != 1:
            return result
        eye = eyes[0]
        try:
            measurement = measure_srax(raw)
        except Exception as exc:
            result.setdefault("global_warnings", []).append(
                f"Geometric SRAX measurement failed for {filename}: {type(exc).__name__}; SRAX remains unresolved."
            )
            eye["srax"] = "UNCERTAIN"
            eye["srax_deg"] = None
            return result

        eye["srax_geometry"] = measurement
        if measurement.get("status") != "CONFIDENT":
            eye["srax"] = "UNCERTAIN"
            eye["srax_deg"] = None
            return result

        eye["srax"] = measurement["srax"]
        eye["srax_deg"] = measurement["srax_deg"]
        eye.setdefault("morphology_evidence", []).append(
            "Deterministic Front-map SRAX geometry "
            f"({ALGORITHM_VERSION}): superior axis {measurement['superior_axis_deg']:.1f}°, "
            f"inferior axis {measurement['inferior_axis_deg']:.1f}°, "
            f"SRAX {measurement['srax_deg']:.1f}°; strict >20° criterion."
        )
        provenance = eye.setdefault("field_provenance", {})
        provenance["srax"] = [{"source": "AXIAL_SAGITTAL_CURVATURE_FRONT_GEOMETRIC", "file": filename}]
        provenance["srax_deg"] = [{"source": "AXIAL_SAGITTAL_CURVATURE_FRONT_GEOMETRIC", "file": filename}]
        return result

    return extract_one_image_with_geometric_srax


_previous_extract_one_image = None
extract_one_image_with_geometric_srax = None


def install(core: Any, previous_owner: Any = None) -> None:
    global _previous_extract_one_image, extract_one_image_with_geometric_srax
    if getattr(core, "_cerai_geometric_srax_installed", False):
        return
    _previous_extract_one_image = core.extract_one_image
    extract_one_image_with_geometric_srax = make_geometric_srax_extractor(core, _previous_extract_one_image)
    core.extract_one_image = extract_one_image_with_geometric_srax
    core._cerai_geometric_srax_installed = True
    core._cerai_geometric_srax_algorithm = ALGORITHM_VERSION
