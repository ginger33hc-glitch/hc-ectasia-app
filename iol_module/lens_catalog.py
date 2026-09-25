"""Single authoritative catalog of clinic-approved IOLs and constants."""

from __future__ import annotations

from dataclasses import asdict, dataclass

ALCON_TORIC_URL = "https://www.myalcon-toriccalc.com/"
TECNIS_TORIC_URL = "https://www.tecnistoriccalc.com/"


@dataclass(frozen=True)
class Lens:
    id: str
    name: str
    category: str
    subtype: str | None
    a_constant: float
    manufacturer: str
    toric_calculator_url: str | None

    def public_dict(self) -> dict[str, object]:
        return asdict(self)


LENSES = (
    Lens("clareon-panoptix-cnwtt0", "CLAREON PanOptix CNWTT0", "MULTIFOCAL", None, 119.1, "Alcon", ALCON_TORIC_URL),
    Lens("clareon-panoptix-toric-cnwtt3", "CLAREON PanOptix Toric CNWTT3", "MULTIFOCAL", "Toric", 119.1, "Alcon", ALCON_TORIC_URL),
    Lens("clareon-toric-cnw0t8", "CLAREON Toric CNW0T8", "MONOFOCAL", "Toric", 119.1, "Alcon", ALCON_TORIC_URL),
    Lens("tecnis-eyhance-toric-diu525", "TECNIS Eyhance Toric DIU525", "MONOFOCAL", "Enhanced monofocal toric", 119.3, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("enova-advance-toric", "ENOVA Advance Toric", "EDOF", "Toric; exact model code to verify", 118.0, "ENOVA", None),
    Lens("tecnis-eyhance-gib00", "TECNIS Eyhance GIB00", "MONOFOCAL", "Enhanced monofocal", 119.3, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("acrysof-single-sa60at", "AcrySof Single SA60AT", "MONOFOCAL", None, 118.7, "Alcon", ALCON_TORIC_URL),
    Lens("acrysof-ultrasert-au00t0", "AcrySof UltraSert AU00T0", "MONOFOCAL", None, 119.0, "Alcon", ALCON_TORIC_URL),
    Lens("tecnis-multifocal-zlb00", "TECNIS Multifocal ZLB00", "MULTIFOCAL", None, 119.3, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("enova-adc-advance", "ENOVA ADC Advance", "EDOF", None, 118.0, "ENOVA", None),
    Lens("enova-maestro", "ENOVA Maestro", "MULTIFOCAL", None, 118.0, "ENOVA", None),
    Lens("tecnis-puresee-den00v", "TECNIS PureSee DEN00V", "EDOF", None, 119.3, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("tecnis-odyssey-drn00v", "TECNIS Odyssey DRN00V", "MULTIFOCAL", None, 119.3, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("acrysof-three-piece-ma60ac", "AcrySof Three-Piece MA60AC", "MONOFOCAL", None, 118.4, "Alcon", ALCON_TORIC_URL),
    Lens("eyecryl-three-piece", "Eyecryl Three-Piece", "MONOFOCAL", None, 118.0, "Eyecryl", None),
    Lens("acrysof-vivity-dft015", "AcrySof Vivity DFT015", "EDOF", None, 119.2, "Alcon", ALCON_TORIC_URL),
    Lens("clareon-mono-sy60wf", "CLAREON Mono SY60WF", "MONOFOCAL", None, 119.1, "Alcon", ALCON_TORIC_URL),
    Lens("tecnis-sensar-gab00", "TECNIS Sensar GAB00", "MONOFOCAL", None, 118.4, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("tecnis-optiblue-gcb00v", "TECNIS OptiBlue GCB00V", "MONOFOCAL", None, 118.8, "Johnson & Johnson", TECNIS_TORIC_URL),
    Lens("acrysof-iq-sn60wf", "AcrySof IQ SN60WF", "MONOFOCAL", None, 119.0, "Alcon", ALCON_TORIC_URL),
)

LENSES_BY_ID = {lens.id: lens for lens in LENSES}


def get_lens(lens_id: str) -> Lens | None:
    return LENSES_BY_ID.get(lens_id)


def public_catalog() -> list[dict[str, object]]:
    return [lens.public_dict() for lens in LENSES]
