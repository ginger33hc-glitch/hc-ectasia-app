"""Disable model-based ERSS morphology and SRAX interpretation.

Signed Topometric I-S remains a labeled numeric ERSS input. SRAX is now measured by the
deterministic pixel-geometry engine from the Axial/Sagittal Curvature (Front) map; the extraction
model must not visually estimate or reconstruct SRAX.
"""

_START = "Only the categorical fields that genuinely require map inspection may be produced visually:"
_END = "For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled"
_REPLACEMENT = """ERSS VISUAL MORPHOLOGY DISABLED:
General ERSS/Randleman visual morphology classification is disabled. Do not visually score asymmetric
bow-tie, inferior steepening, keratoconus pattern, forme-fruste pattern, PMD pattern, or any other ERSS
morphology category.

ERSS SRAX SOURCE LOCK:
ERSS SRAX SOURCE LOCK — MODEL ESTIMATION DISABLED:
SRAX is measured outside this extraction model by CER-AI's deterministic geometric image-analysis
engine using only the Axial/Sagittal Curvature (Front) map on the Pentacam 4 Maps Refractive page.
Do not visually estimate SRAX, do not return a numeric srax_deg from map appearance, and do not derive
SRAX from KISA, Kmax, I-S, astigmatism tables, K1/K2/global Axis, BAD/Belin-Ambrosio values, Elevation
Front, Elevation Back, Corneal Thickness, pachymetry, or any other surrogate.

For every image handled by this model, return srax=UNCERTAIN and srax_deg=null. The deterministic
geometry layer may replace those values after this extraction if, and only if, it can localize the
correct Front map and resolve both superior and inferior steep hemimeridian directions with adequate
confidence. If geometry fails, downstream workflow remains fail-closed and may ask for surgeon
confirmation from the Front map.

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
