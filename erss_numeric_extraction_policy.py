"""Restrict ERSS visual work to source-locked SRAX on the anterior Front map.

Signed Topometric I-S remains a labeled numeric ERSS input. SRAX may be read
only from the Axial/Sagittal Curvature (Front) map. Other visual morphology is
not an ERSS scoring authority in this adapter.
"""

_START = "Only the categorical fields that genuinely require map inspection may be produced visually:"
_END = "For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled"
_REPLACEMENT = """ERSS SRAX SOURCE LOCK:
Do not inspect or classify general anterior curvature-map morphology for ERSS/Randleman scoring.
Do not visually score asymmetric bow-tie, inferior steepening, keratoconus pattern, forme-fruste
pattern, PMD pattern, or any other ERSS morphology category.

The ONE permitted visual ERSS measurement is SRAX, and its source is strictly the
Axial/Sagittal Curvature (Front) map. On a standard Pentacam 4 Maps Refractive page this is the
upper-left anterior curvature panel. Never obtain SRAX from KISA, Kmax, I-S, astigmatism tables,
BAD/Belin-Ambrosio values, Elevation Front, Elevation Back, Corneal Thickness, pachymetry, or any
other map or numeric surrogate. Never reverse-calculate SRAX from KISA or any composite index.

SRAX is the skew amount: the deviation from the expected approximately 90-degree orthogonal
relationship of the relevant principal/radial axes. srax_deg is this skew amount in degrees, NOT a
cylinder axis and NOT the raw meridian angle. Return srax_deg only when that geometry can be
reliably determined from the Axial/Sagittal Curvature (Front) map itself. If it cannot be determined,
return srax_deg=null and srax=UNCERTAIN. When a reliable value is available, set srax=YES only when
srax_deg is strictly greater than 20 degrees; set srax=NO when srax_deg is 20 degrees or less.
Exact 20 degrees is not "greater than 20".

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
