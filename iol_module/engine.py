"""Pure canonical IOL category and toric-modifier decision engine."""

from __future__ import annotations

from .models import (
    AstigmatismType,
    Demand,
    GlaucomaStatus,
    IOLCaseInput,
    IOLRecommendation,
    OcularSurfaceStatus,
    RetinaStatus,
)

ENGINE_VERSION = "IOL_CANONICAL_3.3"
LEGAL_NOTICE = (
    "This application provides clinical decision support only. "
    "Final responsibility rests with the surgeon at all times and under all circumstances."
)


def _age_band(age: int) -> str:
    if age < 50:
        return "LT_50"
    if age <= 60:
        return "AGE_50_60"
    if age <= 70:
        return "AGE_60_70"
    return "GT_70"


def evaluate_case(case: IOLCaseInput) -> IOLRecommendation:
    warnings: list[str] = []
    information: list[str] = []
    exclusions: list[str] = []
    decisive: list[str] = []
    explanation: list[str] = []

    hoa_low = case.total_corneal_hoa_4mm_um < 0.300
    hoa_moderate = 0.300 <= case.total_corneal_hoa_4mm_um < 0.510
    hoa_high = case.total_corneal_hoa_4mm_um >= 0.510
    kappa_high = case.angle_kappa_mm > 0.50
    alpha_high = case.angle_alpha_mm > 0.50
    pupil_small = case.pentacam_pupil_3d_mm < 2.00
    pupil_large = case.pentacam_pupil_3d_mm > 4.00
    irregular = (
        case.tcrp_astigmatism_d >= 1.0
        and case.astigmatism_type == AstigmatismType.IRREGULAR
    )
    ocular_active = case.ocular_surface_status in {
        OcularSurfaceStatus.MODERATE,
        OcularSurfaceStatus.SIGNIFICANT,
    }

    if case.retina_status == RetinaStatus.SIGNIFICANT:
        exclusions.append("MF_EXCL_RETINA_SIGNIFICANT")
        warnings.append("WARN_RETINA_SIGNIFICANT")
    elif case.retina_status == RetinaStatus.MILD:
        warnings.append("WARN_RETINA_MILD")
    if case.macular_pathology_present:
        exclusions.append("MF_EXCL_MACULAR_PATHOLOGY")
        warnings.append("WARN_MACULAR_PATHOLOGY")
    if case.glaucoma_status == GlaucomaStatus.PRESENT:
        exclusions.append("MF_EXCL_GLAUCOMA_PRESENT")
        warnings.append("WARN_GLAUCOMA_PRESENT")
    elif case.glaucoma_status == GlaucomaStatus.SUSPECT:
        warnings.append("WARN_GLAUCOMA_SUSPECT")
    if ocular_active:
        exclusions.append("MF_EXCL_OCULAR_SURFACE_ACTIVE")
        warnings.append(f"WARN_OCULAR_SURFACE_{case.ocular_surface_status.value}")
    elif case.ocular_surface_status == OcularSurfaceStatus.MILD:
        warnings.append("WARN_OCULAR_SURFACE_MILD")
    elif case.ocular_surface_status == OcularSurfaceStatus.RESOLVED_AFTER_TREATMENT:
        information.append("INFO_OCULAR_SURFACE_RESOLVED_STABLE")
    if hoa_high:
        exclusions.append("MF_EXCL_HOA_HIGH")
        warnings.append("WARN_HOA_HIGH")
    elif hoa_moderate:
        warnings.append("WARN_HOA_MODERATE")
    if kappa_high:
        exclusions.append("MF_EXCL_KAPPA_HIGH")
        warnings.append("WARN_KAPPA_HIGH")
    if alpha_high:
        exclusions.append("MF_EXCL_ALPHA_HIGH")
        warnings.append("WARN_ALPHA_HIGH")
    if pupil_small:
        exclusions.append("MF_EXCL_PUPIL_SMALL")
        warnings.append("WARN_PUPIL_TOO_SMALL")
    if pupil_large:
        exclusions.append("MF_EXCL_PUPIL_LARGE")
        warnings.append("WARN_PUPIL_TOO_LARGE")
    if irregular:
        exclusions.append("MF_EXCL_IRREGULAR_ASTIG")
        warnings.append("WARN_IRREGULAR_ASTIGMATISM")
    exclusions = list(dict.fromkeys(exclusions))
    warnings = list(dict.fromkeys(warnings))
    multifocal_eligible = not exclusions
    priority_one = []
    if case.retina_status == RetinaStatus.SIGNIFICANT:
        priority_one.append("MONO_RETINA_SIGNIFICANT")
    if hoa_high:
        priority_one.append("MONO_HOA_HIGH")
    if irregular:
        priority_one.append("MONO_IRREGULAR_ASTIGMATISM")
    preference_only_mono = False
    if case.near_demand == Demand.LOW:
        priority_one.append("MONO_LOW_NEAR_DEMAND")
        preference_only_mono = True
    if case.halo_tolerance == Demand.LOW:
        priority_one.append("MONO_LOW_HALO_TOLERANCE")
        preference_only_mono = True

    age_gt70 = _age_band(case.patient_age_years) == "GT_70"
    if priority_one:
        main = "MONOFOCAL"
        decisive.extend(priority_one)
        eligible = ["MONOFOCAL"]
        if preference_only_mono and not any(code.startswith("MONO_RETINA") or code in {
            "MONO_HOA_HIGH", "MONO_IRREGULAR_ASTIGMATISM"
        } for code in priority_one):
            eligible.insert(0, "EDOF")
        alternative = "EDOF" if eligible[0] == "EDOF" else None
    elif not multifocal_eligible:
        main = "EDOF"
        decisive.extend(exclusions)
        eligible = ["EDOF", "MONOFOCAL"]
        alternative = "MONOFOCAL"
    elif age_gt70:
        main = "EDOF"
        decisive.append("AGE_SOFT_PREFERENCE_GT70")
        information.append("INFO_AGE_SOFT_PREFERENCE_GT70")
        eligible = ["EDOF", "MULTIFOCAL", "MONOFOCAL"]
        alternative = "MONOFOCAL"
    else:
        main = "MULTIFOCAL"
        decisive.append("MF_BALANCED_POSITIVE_PROFILE")
        eligible = ["MULTIFOCAL", "EDOF", "MONOFOCAL"]
        alternative = "EDOF"

    toric = (
        "TORIC"
        if case.tcrp_astigmatism_d >= 1.0
        and case.astigmatism_type == AstigmatismType.REGULAR
        else "NON_TORIC"
    )
    label = main.title().replace("Edof", "EDOF")
    formatted = f"Toric {label}" if toric == "TORIC" else label

    explanation.append(
        f"Age: {case.patient_age_years} years ({_age_band(case.patient_age_years)})."
    )
    explanation.append(
        f"Near-vision demand is {case.near_demand.value.lower()} and halo/glare tolerance is {case.halo_tolerance.value.lower()}."
    )
    explanation.append(f"Night-driving requirement is {case.night_driving.value.lower()}.")
    hoa_class = "low" if hoa_low else ("moderate" if hoa_moderate else "high")
    explanation.append(
        f"Total Corneal HOA (4 mm) is {case.total_corneal_hoa_4mm_um:.3f} µm ({hoa_class})."
    )
    explanation.append(
        f"Pentacam Pupil Dia (3D) is {case.pentacam_pupil_3d_mm:.2f} mm; the multifocal permitted range is 2.00–4.00 mm inclusive."
    )
    explanation.append(
        f"Angle kappa is {case.angle_kappa_mm:.2f} mm and angle alpha is {case.angle_alpha_mm:.2f} mm."
    )
    explanation.append(
        f"Retinal status is {case.retina_status.value.lower()}; macular pathology is {'present' if case.macular_pathology_present else 'absent'}; glaucoma status is {case.glaucoma_status.value.lower()}."
    )
    explanation.append(
        f"Ocular-surface status is {case.ocular_surface_status.value.lower().replace('_', ' ')}."
    )
    astig_type = case.astigmatism_type.value.lower() if case.astigmatism_type else "not required below threshold"
    explanation.append(
        f"TCRP astigmatism is {case.tcrp_astigmatism_d:.2f} D ({astig_type}); toric threshold is 1.00 D inclusive."
    )

    return IOLRecommendation(
        engine_version=ENGINE_VERSION,
        patient_name=case.patient_name,
        eye=case.eye,
        main_category=main,
        toric_modifier=toric,
        formatted_recommendation=formatted,
        eligible_categories=eligible,
        alternative_category=alternative,
        multifocal_eligible=multifocal_eligible,
        decisive_reason_codes=decisive,
        warning_codes=warnings,
        information_codes=list(dict.fromkeys(information)),
        clinical_explanation=explanation,
        legal_notice=LEGAL_NOTICE,
    )
