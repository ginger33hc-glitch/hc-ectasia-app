"""Source-locked Belin/Ambrósio BAD display extraction and interpretation policy.

CER-AI must read BAD component values exactly as printed on the Pentacam
Belin/Ambrósio Display. It must not reverse-calculate Df/Db/Dp/Dt/Da or Final D
from neighboring elevation, pachymetry, PPI, or ART values.
"""

from __future__ import annotations

from typing import Any, Dict


BAD_SOURCE_LOCK_PROMPT = r"""

BELIN/AMBRÓSIO BAD DISPLAY SOURCE LOCK — authoritative for BAD values:
- BAD_D, Df, Db, Dp, Dt, and Da may be transcribed ONLY from the explicitly
  labeled BAD component strip/panel on a visible Pentacam Belin/Ambrósio
  Display for the same eye.
- Preserve every printed sign exactly. A negative D-component is a valid
  normalized deviation and must never be converted to positive magnitude.
- Map the printed labels exactly: Df = front-elevation deviation; Db =
  back-elevation deviation; Dp = pachymetric-progression deviation; Dt =
  minimum-thickness deviation; Da = Ambrósio relational-thickness deviation;
  BAD_D = the printed final D value.
- Never derive or reconstruct Df from anterior elevation, Db from B.Ele.Th or
  any posterior-elevation value, Dp from PPI, Dt from thinnest pachymetry, Da
  from ARTmax, or BAD_D from the five component values. These fields are
  source-locked printed outputs, not CER-AI calculations.
- Never substitute a color, map spot, neighboring value, or a D value from a
  different Pentacam page/eye. If the BAD strip label, sign, digits, or
  laterality is unreadable, return null for that field.
- The five component D values are explanatory normalized deviations. They may
  be displayed individually, but they do not replace the printed Final BAD-D
  as the BAD display's overall classification signal.
"""


def install(core):
    """Install the BAD source lock once into the canonical runtime."""
    if getattr(core, "_cerai_bad_display_source_lock_installed", False):
        return

    if "BELIN/AMBRÓSIO BAD DISPLAY SOURCE LOCK" not in core.PROMPT:
        core.PROMPT = core.PROMPT.rstrip() + BAD_SOURCE_LOCK_PROMPT

    previous_tomography_review = core.tomography_review

    def tomography_review_with_final_bad_authority(eye: Dict[str, Any]) -> Dict[str, Any]:
        """Keep components explanatory while Final BAD-D remains the BAD authority.

        Independent anterior/posterior map pattern review is preserved. Published
        cross-sectional component flags remain visible as adjunctive evidence but
        do not independently promote the BAD display status.
        """
        review = previous_tomography_review(eye)
        final_class = core.bad_classification(eye.get("BAD_D"), final=True)
        map_patterns = (eye.get("anterior_pattern"), eye.get("posterior_pattern"))

        if "ABNORMAL" in map_patterns:
            status = "ABNORMAL"
        elif final_class == "ABNORMAL":
            status = "ABNORMAL"
        elif "BORDERLINE" in map_patterns:
            status = "SUSPICIOUS"
        elif final_class == "SUSPICIOUS":
            status = "SUSPICIOUS"
        elif final_class == "UNAVAILABLE" or "UNREADABLE" in map_patterns:
            status = "INCOMPLETE"
        else:
            status = "REASSURING"

        review["status"] = status
        review["BAD_source_policy"] = "BELIN_AMBROSIO_LABELED_BAD_PANEL_ONLY"
        review["BAD_component_role"] = (
            "Df/Db/Dp/Dt/Da are explanatory normalized deviations; Final BAD-D is the "
            "BAD display classification authority."
        )
        review["evidence_note"] = (
            "BAD values are transcribed from the labeled Belin/Ambrósio BAD panel only. "
            "Component D values and ARTmax/TP adjunctive flags are descriptive review signals; "
            "they are not reverse-calculated and do not independently replace Final BAD-D."
        )
        return review

    core.tomography_review = tomography_review_with_final_bad_authority
    core._cerai_bad_display_previous_tomography_review = previous_tomography_review
    core._cerai_bad_display_source_lock_installed = True
