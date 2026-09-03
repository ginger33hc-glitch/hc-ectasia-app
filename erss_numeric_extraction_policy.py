"""Restrict ERSS visual work to source-locked SRAX on the anterior Front map.

Signed Topometric I-S remains a labeled numeric ERSS input. SRAX may be read
only from the Axial/Sagittal Curvature (Front) map. Other visual morphology is
not an ERSS scoring authority in this adapter.
"""

_START = "Only the categorical fields that genuinely require map inspection may be produced visually:"
_END = "For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled"
_REPLACEMENT = """ERSS VISUAL MORPHOLOGY DISABLED:
General ERSS/Randleman visual morphology classification is disabled. The sole permitted visual ERSS
measurement is the source-locked SRAX geometry described below.

ERSS SRAX SOURCE LOCK:
Do not inspect or classify general anterior curvature-map morphology for ERSS/Randleman scoring.
Do not visually score asymmetric bow-tie, inferior steepening, keratoconus pattern, forme-fruste
pattern, PMD pattern, or any other ERSS morphology category.

The ONE permitted visual ERSS measurement is SRAX, and its source is strictly the
Axial/Sagittal Curvature (Front) map. On a standard Pentacam 4 Maps Refractive page this is the
UPPER-LEFT panel whose title explicitly contains "Axial/Sagittal Curvature (Front)". First verify
that exact panel title before attempting SRAX. Never use any other quadrant of the 4 Maps page.
Never obtain SRAX from KISA, Kmax, I-S, astigmatism tables, BAD/Belin-Ambrosio values, Elevation
Front, Elevation Back, Corneal Thickness, pachymetry, or any other map or numeric surrogate. Never
reverse-calculate SRAX from KISA or any composite index.

SRAX VISUAL GEOMETRY PROCEDURE:
1) Restrict visual analysis to the corneal color map inside the upper-left Axial/Sagittal Curvature
   (Front) panel. Ignore the numeric side tables while determining SRAX geometry.
2) Identify the dominant astigmatic/bow-tie geometry and the principal steep and flat/radial axis
   directions represented by the superior and inferior parts of the anterior curvature pattern.
3) Estimate the relevant axis directions from the CENTERLINES of the broad curvature lobes/meridians,
   not from isolated hot pixels, peripheral color islands, map borders, text, or the pupil/vertex marker.
4) Determine the angular skew as the DEVIATION from the expected approximately orthogonal/continuous
   principal-axis relationship. srax_deg is the amount of skew only. It is NOT the cylinder axis,
   NOT the steep-axis meridian itself, and NOT the raw difference between two arbitrary map angles.
5) Use the smallest anatomically meaningful angular deviation after accounting for the 180-degree
   periodicity of corneal meridians. Do not report an angle >90 degrees as SRAX.
6) A numeric srax_deg may be returned only when BOTH relevant axis directions are clearly visible
   enough that the skew can be estimated reliably from this Front map. If either axis is ambiguous,
   fragmented, strongly irregular, obscured, cropped, or the map resolution is insufficient, do not
   guess and do not infer from other parameters.
7) If reliable, return srax_deg in the range 0-90 degrees and classify strictly as:
      srax_deg > 20.0 degrees  -> srax=YES
      srax_deg <= 20.0 degrees -> srax=NO
   Exact 20.0 degrees is NO.
8) If unreliable, return srax_deg=null and srax=UNCERTAIN. The downstream workflow must ask the
   surgeon: "On the Axial/Sagittal Curvature (Front) map, is the skewed axis greater than 20 degrees?"

CONFIDENCE RULE:
A visually plausible bow-tie is not enough to manufacture a numeric SRAX. The model must be able to
state that it identified the correct upper-left Front panel and could resolve the relevant axis
centerlines. When confidence is insufficient, uncertainty is the required safe output.

For backward-compatible morphology outputs, always return morphology=UNCERTAIN,
morphology_evidence=[], asymmetric_bow_tie=UNCERTAIN, and inferior_opposite_steepening_D=null.
Do not spend image-analysis effort on those retired ERSS morphology fields. Anterior/posterior
tomography pattern fields remain separate non-ERSS review inputs and are not changed by this rule.

"""


def install(core) -> None:
    if getattr(core, "_cerai_erss_numeric_extraction_installed", False):
        return
    prompt = core.PROMPT
    start = prompt.find(_START)
    end = prompt.find(_END)
    if start != -1 and end != -1 and end > start:
        core.PROMPT = prompt[:start] + _REPLACEMENT + prompt[end:]
    elif "ERSS SRAX SOURCE LOCK:" not in prompt:
        core.PROMPT += "\n\n" + _REPLACEMENT
    core._cerai_erss_numeric_extraction_installed = True
