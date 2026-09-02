"""Shared derived-SRAX calculation for CER-AI.

This module owns the arithmetic only. Clinical thresholds belong to the
consuming policy (e.g. ERSS/Randleman or PS3).
"""
from math import isfinite


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if isfinite(value) else None


def derive_srax_deg(*, kisa_percent, kmax_d, i_s_d, astig_d):
    """Return operational derived SRAX in degrees, or None when unavailable/invalid.

    CER-AI operational formula:
      K_index = max(1, Kmax - 47.2)
      IS_index = max(1, |I-S|)
      AST_index = max(1, |AST|)
      SRAX = (KISA% * 3) / (K_index * IS_index * AST_index)

    The result is derived, not directly reported by Pentacam.
    """
    kisa = _num(kisa_percent)
    kmax = _num(kmax_d)
    i_s = _num(i_s_d)
    astig = _num(astig_d)
    if None in (kisa, kmax, i_s, astig):
        return None

    k_index = max(1.0, kmax - 47.2)
    is_index = max(1.0, abs(i_s))
    astig_index = max(1.0, abs(astig))
    denominator = k_index * is_index * astig_index
    if denominator <= 0:
        return None

    value = (kisa * 3.0) / denominator
    if not isfinite(value) or value < 0 or value > 180:
        return None
    return value
