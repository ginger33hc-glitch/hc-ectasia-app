"""Deterministic SRAX geometry from Pentacam Axial/Sagittal Curvature (Front) images.

Fail-closed design: locate only the expected upper-left Four Maps Refractive
curvature map; derive superior/inferior steep hemimeridian axes from broad
curvature signal over multiple annuli; never use KISA, I-S, K1/K2 axis, BAD-D,
Kmax, elevation, or another numeric surrogate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class SraxGeometryResult:
    status: str
    srax_deg: float | None
    superior_axis_deg: float | None
    inferior_axis_deg: float | None
    uncertainty_deg: float | None
    confidence: str
    source: str = "DETERMINISTIC_AXIAL_SAGITTAL_CURVATURE_FRONT_GEOMETRY"
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _angular_skew(superior_deg: float, inferior_deg: float) -> float:
    separation = (inferior_deg - superior_deg) % 360.0
    skew = abs(180.0 - separation)
    if skew > 180.0:
        skew = 360.0 - skew
    return min(skew, 90.0)


def _circular_mean_deg(values: list[float]) -> float:
    radians = np.deg2rad(np.asarray(values, dtype=np.float64))
    x = float(np.cos(radians).mean())
    y = float(np.sin(radians).mean())
    return float(np.degrees(np.arctan2(y, x)) % 360.0)


def _detect_front_map(image_bgr: np.ndarray):
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        return None
    height, width = image_bgr.shape[:2]
    if min(height, width) < 420:
        return None

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    x0, x1 = int(0.25 * width), int(0.70 * width)
    y0, y1 = int(0.03 * height), int(0.62 * height)
    mask = np.zeros((height, width), dtype=np.uint8)
    mask[y0:y1, x0:x1] = (saturation[y0:y1, x0:x1] > 70).astype(np.uint8) * 255

    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates = []
    min_area = max(3000, int(0.005 * height * width))
    for idx in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[idx])
        if area < min_area or w <= 0 or h <= 0:
            continue
        square = min(w, h) / max(w, h)
        if square < 0.72:
            continue
        relative_size = max(w, h) / min(height, width)
        if not 0.16 <= relative_size <= 0.50:
            continue
        cx, cy = x + w / 2.0, y + h / 2.0
        if not (0.35 * width <= cx <= 0.60 * width):
            continue
        if not (0.10 * height <= cy <= 0.53 * height):
            continue
        fill = area / float(w * h)
        if fill < 0.45:
            continue
        radius = (w + h) / 4.0
        score = area * square * (0.70 + 0.30 * min(fill, 1.0))
        candidates.append((score, (cx, cy, radius, square, fill)))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _measure_variant(image_rgb, cx, cy, radius, inner, outer, quantile):
    image = image_rgb.astype(np.float64, copy=False)
    height, width = image.shape[:2]
    yy, xx = np.indices((height, width), dtype=np.float64)
    dx = xx - cx
    dy = cy - yy
    rr = np.hypot(dx, dy)
    theta = np.degrees(np.arctan2(dy, dx)) % 360.0

    red, green, blue = image[:, :, 0], image[:, :, 1], image[:, :, 2]
    maximum = np.maximum.reduce([red, green, blue])
    minimum = np.minimum.reduce([red, green, blue])
    saturation = (maximum - minimum) / (maximum + 1e-6)
    warmth = (red - blue) / (red + green + blue + 1e-6)
    annulus = (rr > inner * radius) & (rr < outer * radius) & (saturation > 0.20)

    axes = []
    radians = np.deg2rad(theta)
    for superior in (True, False):
        hemi = annulus & ((dy > 0) if superior else (dy < 0))
        if int(hemi.sum()) < 120:
            return None
        baseline = float(np.quantile(warmth[hemi], quantile))
        weights = np.clip(warmth - baseline, 0.0, None) * saturation
        weights = np.where(hemi, weights, 0.0)
        total = float(weights.sum())
        if total <= 1e-9:
            return None
        vx = float((weights * np.cos(radians)).sum())
        vy = float((weights * np.sin(radians)).sum())
        axis = float(np.degrees(np.arctan2(vy, vx)) % 360.0)
        resultant = float(np.hypot(vx, vy) / total)
        axes.append((axis, resultant))

    superior_axis, inferior_axis = axes[0][0], axes[1][0]
    return superior_axis, inferior_axis, _angular_skew(superior_axis, inferior_axis), min(axes[0][1], axes[1][1])


def analyze_srax_bytes(raw: bytes) -> SraxGeometryResult:
    encoded = np.frombuffer(raw, dtype=np.uint8)
    image_bgr = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image_bgr is None:
        return SraxGeometryResult("UNCERTAIN", None, None, None, None, "NONE", reason="Image could not be decoded.")

    detected = _detect_front_map(image_bgr)
    if detected is None:
        return SraxGeometryResult(
            "UNCERTAIN", None, None, None, None, "NONE",
            reason="Reliable upper-left Axial/Sagittal Curvature (Front) map geometry was not detected.",
        )
    cx, cy, radius, square, fill = detected
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    variants = []
    for inner in (0.20, 0.25, 0.30):
        for outer in (0.72, 0.80, 0.86):
            for quantile in (0.55, 0.60, 0.65):
                value = _measure_variant(image_rgb, cx, cy, radius, inner, outer, quantile)
                if value is not None:
                    variants.append(value)
    if len(variants) < 20:
        return SraxGeometryResult("UNCERTAIN", None, None, None, None, "LOW", reason="Too few stable geometric measurements.")

    samples = np.asarray([item[2] for item in variants], dtype=np.float64)
    median_srax = float(np.median(samples))
    mad = float(np.median(np.abs(samples - median_srax)))
    uncertainty = max(2.5, 2.0 * 1.4826 * mad)
    superior_axis = _circular_mean_deg([item[0] for item in variants])
    inferior_axis = _circular_mean_deg([item[1] for item in variants])
    min_resultant = float(np.median([item[3] for item in variants]))

    stable = mad <= 4.0 and min_resultant >= 0.65 and square >= 0.78 and fill >= 0.50
    if not stable:
        return SraxGeometryResult(
            "UNCERTAIN", round(median_srax, 1), round(superior_axis, 1), round(inferior_axis, 1),
            round(uncertainty, 1), "LOW",
            reason=f"Geometric solution not sufficiently stable (MAD {mad:.1f}°, resultant {min_resultant:.2f}).",
        )

    lower, upper = median_srax - uncertainty, median_srax + uncertainty
    if lower > 20.0:
        status = "YES"
    elif upper <= 20.0:
        status = "NO"
    else:
        status = "UNCERTAIN"
    confidence = "HIGH" if status in {"YES", "NO"} else "BORDERLINE"
    return SraxGeometryResult(
        status, round(median_srax, 1), round(superior_axis, 1), round(inferior_axis, 1),
        round(uncertainty, 1), confidence,
        reason=f"Median geometric SRAX {median_srax:.1f}° ±{uncertainty:.1f}° from {len(variants)} annular measurements.",
    )
