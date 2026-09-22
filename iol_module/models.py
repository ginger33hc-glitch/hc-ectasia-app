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

    tcrp_astigmatism_d: float = Field(ge=0, le=15)
    tcrp_steep_axis_deg: float | None = Field(default=None, ge=0, le=180)
    astigmatism_type: AstigmatismType | None = None

    retina_status: RetinaStatus
    macular_pathology_present: bool
    glaucoma_status: GlaucomaStatus
    ocular_surface_status: OcularSurfaceStatus
    post_treatment_measurements_stable: bool | None = None

    @model_validator(mode="after")
    def validate_conditional_fields(self):
        if self.tcrp_astigmatism_d >= 1.0:
            if self.tcrp_steep_axis_deg is None or self.astigmatism_type is None:
                raise ValueError(
                    "TCRP K2 axis and surgeon-classified regularity are required at 1.00 D or more."
                )
        if self.ocular_surface_status == OcularSurfaceStatus.RESOLVED_AFTER_TREATMENT:
            if self.post_treatment_measurements_stable is not True:
                raise ValueError(
                    "Resolved ocular-surface disease requires surgeon-confirmed stable repeat measurements."
                )
        return self


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
    clinical_explanation: list[str]
    legal_notice: str
