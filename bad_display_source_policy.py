"""Source-locked Belin/Ambrósio BAD display extraction policy.

CER-AI must read BAD component values exactly as printed on the Pentacam
Belin/Ambrósio Display. It must not reverse-calculate Df/Db/Dp/Dt/Da or Final D
from neighboring elevation, pachymetry, PPI, or ART values.

This policy intentionally changes extraction provenance only. Existing CER-AI
clinical interpretation, adjunctive tomography flags, and Final BAD-D decision
logic remain untouched.
"""


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
  any posterior-elevation value, Dp from PPI, Dt from thinnest pachymetry,
  Da from ARTmax, or BAD_D from the five component values. These fields are
  source-locked printed outputs, not CER-AI calculations.
- Never substitute a color, map spot, neighboring value, or a D value from a
  different Pentacam page/eye. If the BAD strip label, sign, digits, or
  laterality is unreadable, return null for that field.
- The five component D values are explanatory normalized deviations. They may
  be displayed individually, but they do not replace the printed Final BAD-D
  as the BAD display's overall classification signal.
"""


def install(core):
    """Install the extraction source lock once without altering clinical logic."""
    if getattr(core, "_cerai_bad_display_source_lock_installed", False):
        return

    if "BELIN/AMBRÓSIO BAD DISPLAY SOURCE LOCK" not in core.PROMPT:
        core.PROMPT = core.PROMPT.rstrip() + BAD_SOURCE_LOCK_PROMPT

    core._cerai_bad_display_source_lock_installed = True
