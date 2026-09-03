"""Remove visual ERSS morphology work from the production extraction prompt.

The legacy extraction schema still carries neutral morphology fields for backward
compatibility with merge/report code, but the model is explicitly instructed not
to inspect or classify visual morphology. ERSS topography is numeric-only:
Topometric signed I-S plus derived SRAX.
"""

_START = "Only the categorical fields that genuinely require map inspection may be produced visually:"
_END = "For an Excimer Laser Takip Karti, extract treatment_corrections only from the row explicitly labeled"
_REPLACEMENT = """ERSS VISUAL MORPHOLOGY DISABLED:
Do not inspect, classify, or interpret anterior curvature-map morphology for ERSS/Randleman scoring.
Do not visually evaluate asymmetric bow-tie, inferior steepening, SRA/SRAX, keratoconus pattern,
forme-fruste pattern, PMD pattern, or any other ERSS morphology category. CER-AI uses only the
explicitly printed signed Topometric I-S value and a downstream derived SRAX calculation for ERSS
topography scoring.
For backward-compatible output fields, always return morphology=UNCERTAIN,
morphology_evidence=[], asymmetric_bow_tie=UNCERTAIN, srax=UNCERTAIN, srax_deg=null, and
inferior_opposite_steepening_D=null. Do not spend image-analysis effort on these fields.
Anterior/posterior tomography pattern fields remain separate non-ERSS review inputs and are not
changed by this rule.

"""


def install(core) -> None:
    if getattr(core, "_cerai_erss_numeric_extraction_installed", False):
        return
    prompt = core.PROMPT
    start = prompt.find(_START)
    end = prompt.find(_END)
    if start != -1 and end != -1 and end > start:
        core.PROMPT = prompt[:start] + _REPLACEMENT + prompt[end:]
    elif "ERSS VISUAL MORPHOLOGY DISABLED:" not in prompt:
        core.PROMPT += "\n\n" + _REPLACEMENT
    core._cerai_erss_numeric_extraction_installed = True
