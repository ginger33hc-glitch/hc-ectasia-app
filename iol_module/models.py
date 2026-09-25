"""Validated input and output contracts for the independent IOL module."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Demand(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class Frequency(str, Enum):
    NONE = "NONE"
    OCCASIONAL = "OCCASIONAL"
    FREQUENT = "FREQUENT"


class AstigmatismType(str, Enum):
    REGULAR = "REGULAR"
    IRREGULAR = "IRREGULAR"


class RetinaStatus(str, Enum):
    NONE = "NONE"
    MILD = "MILD"
    SIGNIFICANT = "SIGNIFICANT"


class GlaucomaStatus(str, Enum):
    NONE = "NONE"
    SUSPECT = "SUSPECT"
    PRESENT = "PRESENT"


class OcularSurfaceStatus(str, Enum):
    NONE = "NONE"
    MILD = "MILD"
    MODERATE = "MODERATE"
    SIGNIFICANT = "SIGNIFICANT"
    RESOLVED_AFTER_TREATMENT = "RESOLVED_AFTER_TREATMENT"


class BiometrySource(str, Enum):
    IOLMASTER_500_EXTRACTED = "IOLMASTER_500_EXTRACTED"
    SURGEON_ENTERED_UNREADABLE = "SURGEON_ENTERED_UNREADABLE"


class PriorCornealSurgery(str, Enum):
    NONE = "NONE"
    MYOPIC_LASIK_PRK = "MYOPIC_LASIK_PRK"
    HYPEROPIC_LASIK_PRK = "HYPEROPIC_LASIK_PRK"
    RK = "RK"


class IOLCaseInput(StrictModel):
    patient_name: str = Field(min_length=1, max_length=200)
    patient_age_years: int = Field(ge=18, le=120)
    eye: Literal["OD", "OS"]

    near_demand: Demand
    night_driving: Frequency
    halo_tolerance: Demand

    total_corneal_hoa_4mm_um: float = Field(ge=0, le=5)
    angle_kappa_mm: float = Field(ge=0, le=3)
    angle_alpha_mm: float = Field(ge=0, le=3)
    pentacam_pupil_3d_mm: float = Field(gt=0, le=12)

    iolm500_k1_d: float = Field(ge=30, le=60)
    iolm500_k1_axis_deg: float = Field(ge=0, le=180)
    iolm500_k2_d: float = Field(ge=30, le=60)
    iolm500_k2_axis_deg: float = Field(ge=0, le=180)
    iolm500_measurement_source: BiometrySource
    surgeon_k1_d: float | None = Field(default=None, ge=30, le=60)
    surgeon_k2_d: float | None = Field(default=None, ge=30, le=60)
    astigmatism_type: AstigmatismType | None = None

    retina_status: RetinaStatus
    macular_pathology_present: bool
    glaucoma_status: GlaucomaStatus
    ocular_surface_status: OcularSurfaceStatus
    post_treatment_measurements_stable: bool | None = None

    @model_validator(mode="after")
    def validate_conditional_fields(self):
        if self.active_astigmatism_d >= 1.0 and self.astigmatism_type is None:
            raise ValueError(
                "Surgeon-classified regularity is required when the active IOLMaster K difference is 1.00 D or more."
            )
        if (
            self.ocular_surface_status
            == OcularSurfaceStatus.RESOLVED_AFTER_TREATMENT
            and self.post_treatment_measurements_stable is not True
        ):
            raise ValueError(
                "Resolved ocular-surface disease requires surgeon-confirmed stable repeat measurements."
            )
        return self

    @property
    def active_k1_d(self) -> float:
        return self.surgeon_k1_d if self.surgeon_k1_d is not None else self.iolm500_k1_d

    @property
    def active_k2_d(self) -> float:
        return self.surgeon_k2_d if self.surgeon_k2_d is not None else self.iolm500_k2_d

    @property
    def active_astigmatism_d(self) -> float:
        return abs(self.active_k2_d - self.active_k1_d)


class IOLRecommendation(StrictModel):
    engine_version: str
    patient_name: str
    eye: Literal["OD", "OS"]
    main_category: Literal["MULTIFOCAL", "EDOF", "MONOFOCAL"]
    toric_modifier: Literal["TORIC", "NON_TORIC"]
    formatted_recommendation: str
    eligible_categories: list[Literal["MULTIFOCAL", "EDOF", "MONOFOCAL"]]
    alternative_category: Literal["MULTIFOCAL", "EDOF", "MONOFOCAL"] | None
    multifocal_eligible: bool
    decisive_reason_codes: list[str]
    warning_codes: list[str]
    information_codes: list[str]
    active_k1_d: float
    active_k2_d: float
    k1_axis_deg: float
    k2_axis_deg: float
    active_astigmatism_d: float
    toric_evaluation_required: bool
    clinical_explanation: list[str]
    legal_notice: str


class PosteriorCorneaInput(StrictModel):
    """One operative eye's Pentacam 4 Maps Refractive / Cornea Back panel."""

    eye: Literal["OD", "OS"]
    source: Literal["PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK"]
    k1_d: float = Field(ge=-12, lt=0)
    k2_d: float = Field(ge=-12, lt=0)
    k1_axis_deg: float = Field(ge=0, le=180)
    k2_axis_deg: float = Field(ge=0, le=180)
    rh_mm: float = Field(ge=3, le=12)
    rv_mm: float = Field(ge=3, le=12)

    @model_validator(mode="after")
    def validate_posterior_axes(self):
        if self.k1_d < self.k2_d:
            raise ValueError("Cornea Back signed K1 must be no more negative than K2.")
        if abs((self.k2_axis_deg - self.k1_axis_deg) % 180 - 90) > 5:
            raise ValueError("Cornea Back K axes must be approximately orthogonal.")
        return self


class IOLPowerPlanInput(StrictModel):
    patient_name: str = Field(min_length=1, max_length=200)
    biological_sex: Literal["Male", "Female"]
    eye: Literal["OD", "OS"]
    selected_lens_id: str = Field(min_length=1, max_length=100)
    axial_length_mm: float = Field(ge=12, le=38)
    acd_mm: float = Field(gt=0, le=10)
    k1_d: float = Field(ge=30, le=60)
    k1_axis_deg: float = Field(ge=0, le=180)
    k2_d: float = Field(ge=30, le=60)
    k2_axis_deg: float = Field(ge=0, le=180)
    astigmatism_type: AstigmatismType | None = None
    prior_corneal_surgery: PriorCornealSurgery = PriorCornealSurgery.NONE
    historical_data_available: bool = False
    incision_axis_deg: float | None = Field(default=None, ge=0, le=180)
    sia_d: float | None = Field(default=None, ge=0, le=5)
    sia_axis_deg: float | None = Field(default=None, ge=0, le=180)
    cct_um: float | None = Field(default=None, ge=300, le=900)
    lens_thickness_mm: float | None = Field(default=None, ge=2.5, le=7)
    wtw_mm: float | None = Field(default=None, ge=8, le=16)
    posterior_cornea: PosteriorCorneaInput | None = None

    @property
    def astigmatism_d(self) -> float:
        return abs(self.k2_d - self.k1_d)

    @model_validator(mode="after")
    def validate_power_route(self):
        if self.posterior_cornea is not None and self.posterior_cornea.eye != self.eye:
            raise ValueError("Cornea Back laterality must match the operative eye.")
        if self.astigmatism_d >= 1.0 and self.astigmatism_type is None:
            raise ValueError("Astigmatism regularity is required for toric routing.")
        toric = self.astigmatism_d >= 1.0 and self.astigmatism_type == AstigmatismType.REGULAR
        if toric and (self.incision_axis_deg is None or self.sia_d is None):
            raise ValueError("Incision axis and surgeon-specific SIA are required for toric routing.")
        if toric:
            if self.k1_d > self.k2_d or abs((self.k2_axis_deg - self.k1_axis_deg) % 180 - 90) > 5:
                raise ValueError("IOLMaster K1/K2 must identify approximately orthogonal flat/steep axes.")
            if abs(self.sia_d - 0.25) > 1e-6:
                raise ValueError("This surgeon's toric planning SIA is fixed at 0.25 D.")
            if abs((self.incision_axis_deg - self.k2_axis_deg + 90) % 180 - 90) > 1:
                raise ValueError("This surgeon's incision must coincide with the steep K2 axis.")
            if self.sia_axis_deg is not None and abs((self.sia_axis_deg - self.k2_axis_deg + 90) % 180 - 90) > 1:
                raise ValueError("SIA axis must coincide with the steep K2 axis.")
        if (
            self.axial_length_mm < 22.0
            and self.prior_corneal_surgery == PriorCornealSurgery.NONE
            and (self.lens_thickness_mm is None or self.wtw_mm is None)
        ):
            raise ValueError(
                "Cooke K6 requires lens thickness and WTW when axial length is below 22.00 mm."
            )
        return self


class EscrsTransferInput(StrictModel):
    """De-identified biometry accepted by the ESCRS BiomPIN handoff."""

    biological_sex: Literal["Male", "Female"]
    eye: Literal["OD", "OS"]
    axial_length_mm: float = Field(ge=12, le=38)
    acd_internal_mm: float = Field(gt=0, le=10)
    k1_d: float = Field(ge=30, le=60)
    k2_d: float = Field(ge=30, le=60)
    cct_um: float | None = Field(default=None, ge=300, le=900)
    lens_thickness_mm: float | None = Field(default=None, ge=2.5, le=7)
    wtw_mm: float | None = Field(default=None, ge=8, le=16)


class IOLPowerPlan(StrictModel):
    route: Literal[
        "COOKE_K6",
        "MANUFACTURER_TORIC",
        "BARRETT_TRUE_K_EXTERNAL",
        "POST_RK_EXTERNAL",
    ]
    calculation_status: Literal["COMPLETED", "TEST_ONLY", "EXTERNAL_REQUIRED", "CALCULATION_UNAVAILABLE"]
    selected_lens_id: str
    selected_lens_name: str
    lens_category: Literal["MULTIFOCAL", "EDOF", "MONOFOCAL"]
    a_constant: float
    target_refraction_d: float
    target_locked: bool
    target_warning: str | None
    second_formula_required: bool
    calculator_name: str
    calculator_url: str | None
    escrs_url: str | None
    inputs: dict[str, object]
    predictions: list[dict[str, object]]
    message: str
    toric_candidates: list[dict[str, object]] = Field(default_factory=list)
    toric_status: Literal["NOT_APPLICABLE", "TEST_ONLY", "TEST_RESTRICTED", "INPUTS_INCOMPLETE", "UNSUPPORTED", "CALCULATION_UNAVAILABLE"] = "NOT_APPLICABLE"
