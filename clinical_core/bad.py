"""Pure Belin/Ambrosio BAD evaluation for CER-AI.

Final BAD-D is the only BAD decision signal. Df/Db/Dp/Dt/Da, ARTmax and PPI are
contextual values only and never independently change disposition in this module.
No BAD value is reconstructed from another value.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Optional

NORMAL = "NORMAL"
SUSPICIOUS = "SUSPICIOUS"
ABNORMAL = "ABNORMAL"
UNAVAILABLE = "UNAVAILABLE"
BAD_SUSPICIOUS_LIMIT = 1.60
BAD_ABNORMAL_LIMIT = 2.60
# Ghiasian et al. J Curr Ophthalmol. 2022;34:200-207, Table 1.
# doi:10.4103/joco.joco_249_21. Reference display bands, not scoring rules.
PACHYMETRIC_DISPLAY_BANDS = {
    "ppi_min": (0.80, 0.86, False),
    "ppi_avg": (1.08, 1.17, False),
    "ppi_max": (1.40, 1.52, False),
    "artmax_um": (357.0, 368.0, True),
}


@dataclass(frozen=True)
class BADContext:
    df: Optional[float] = None
    db: Optional[float] = None
    dp: Optional[float] = None
    dt: Optional[float] = None
    da: Optional[float] = None
    artmax_um: Optional[float] = None
    ppi_min: Optional[float] = None
    ppi_avg: Optional[float] = None
    ppi_max: Optional[float] = None


@dataclass(frozen=True)
class BADResult:
    final_d: Optional[float]
    classification: str
    context: BADContext

    @property
    def component_interpretations(self) -> dict:
        """Canonical contextual display bands; never disposition inputs.

        Source: Pentacam Interpretation Guide, 3rd edition (2017), BAD display.
        Component suspicious band includes 1.60; the accepted CER-AI Final D
        decision boundary is preserved separately below.
        """
        result = {}
        for key in ("df", "db", "dp", "dt", "da"):
            value = getattr(self.context, key)
            if not _finite(value):
                classification, band = UNAVAILABLE, "Not documented"
            elif value < BAD_SUSPICIOUS_LIMIT:
                classification, band = NORMAL, f"< {BAD_SUSPICIOUS_LIMIT:.2f}"
            elif value < BAD_ABNORMAL_LIMIT:
                classification, band = SUSPICIOUS, f"{BAD_SUSPICIOUS_LIMIT:.2f} to < {BAD_ABNORMAL_LIMIT:.2f}"
            else:
                classification, band = ABNORMAL, f">= {BAD_ABNORMAL_LIMIT:.2f}"
            result[key] = {"classification": classification, "range": band}
        for key, (lower, upper, inverse) in PACHYMETRIC_DISPLAY_BANDS.items():
            value = getattr(self.context, key)
            low = f"{lower:g}" if inverse else f"{lower:.2f}"
            high = f"{upper:g}" if inverse else f"{upper:.2f}"
            unit = " um" if inverse else ""
            if not _finite(value) or value <= 0:
                classification, band = UNAVAILABLE, "Not documented / invalid"
            elif value < lower:
                classification = ABNORMAL if inverse else NORMAL
                band = f"< {low}{unit}"
            elif value > upper:
                classification = NORMAL if inverse else ABNORMAL
                band = f"> {high}{unit}"
            else:
                classification, band = SUSPICIOUS, f"{low}-{high}{unit}"
            result[key] = {"classification": classification, "range": band}
        return result


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def final_bad_d_classification(value) -> str:
    if not _finite(value):
        return UNAVAILABLE
    value = float(value)
    if value <= BAD_SUSPICIOUS_LIMIT:
        return NORMAL
    if value < BAD_ABNORMAL_LIMIT:
        return SUSPICIOUS
    return ABNORMAL


def evaluate_bad(final_d, *, context: BADContext | None = None) -> BADResult:
    """Evaluate only readable Final D; adjunct values are preserved unchanged."""
    numeric_final = float(final_d) if _finite(final_d) else None
    return BADResult(
        final_d=numeric_final,
        classification=final_bad_d_classification(final_d),
        context=context or BADContext(),
    )
