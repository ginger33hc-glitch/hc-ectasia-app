"""Canonical refraction normalization for CER-AI.

All clinical consumers receive one normalized minus-cylinder representation.
Manifest refraction and intended treatment remain separate values; normalization
changes notation only and never substitutes one for the other.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional

MYOPIC = "MYOPIC"
HYPEROPIC = "HYPEROPIC"
MIXED = "MIXED"
PLANO = "PLANO"
INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class Refraction:
    sphere_d: float
    cylinder_d: float
    axis_deg: float

    @property
    def mrse_d(self) -> float:
        return self.sphere_d + self.cylinder_d / 2.0

    @property
    def principal_meridians_d(self) -> tuple[float, float]:
        return self.sphere_d, self.sphere_d + self.cylinder_d


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def normalize_minus_cylinder(sphere_d, cylinder_d, axis_deg) -> Optional[Refraction]:
    """Return mathematically equivalent minus-cylinder notation.

    Plus cylinder is transposed by adding cylinder to sphere, reversing the
    cylinder sign, and rotating axis by 90 degrees modulo 180. Minus or zero
    cylinder is preserved except for canonical axis normalization to [0, 180).
    """
    if not all(_finite(value) for value in (sphere_d, cylinder_d, axis_deg)):
        return None
    sphere = float(sphere_d)
    cylinder = float(cylinder_d)
    axis = float(axis_deg) % 180.0
    if cylinder > 0:
        sphere += cylinder
        cylinder = -cylinder
        axis = (axis + 90.0) % 180.0
    return Refraction(sphere, cylinder, axis)


def refractive_group(refraction: Optional[Refraction]) -> str:
    """Classify treatment by the signs of its two principal meridians."""
    if refraction is None:
        return INCOMPLETE
    first, second = refraction.principal_meridians_d
    if first == 0 and second == 0:
        return PLANO
    if first <= 0 and second <= 0 and (first < 0 or second < 0):
        return MYOPIC
    if first >= 0 and second >= 0 and (first > 0 or second > 0):
        return HYPEROPIC
    return MIXED


def scalar_final_k_is_valid(refraction: Optional[Refraction]) -> bool:
    """Mixed astigmatism must not use a scalar MRSE/Kmean final-K model."""
    return refractive_group(refraction) in {MYOPIC, HYPEROPIC, PLANO}
