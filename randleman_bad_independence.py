"""Hard separation of Randleman/ERSS scoring from Pentacam BAD tomography.

Randleman ERSS uses only its own five inputs: anterior topographic pattern,
RSB, age, preoperative corneal thickness, and manifest MRSE. BAD-D and the
Belin/Ambrosio component deviations are never Randleman prerequisites.
"""
import bootstrap

core = bootstrap.core
_previous_assess_eye = core.assess_eye

_RANDLEMAN_ROWS = ("topography", "RSB", "age", "pachymetry", "MRSE")
_BAD_FIELDS = {"BAD_D", "Df", "Db", "Dp", "Dt", "Da", "ARTmax_um", "PPI_max"}


def _independent_lasik_erss(eye, plan, age, result):
    """Calculate ERSS without reading or testing any BAD/Belin-Ambrosio field."""
    normalized = core.normalize_signed_refraction_plan(plan or {})
    topo = core.scoring_morphology(eye)
    topo_category = topo.get("category")
    topo_points = core.lasik_topography_points(topo_category)

    values = result.get("values") or {}
    rsb = values.get("LASIK_RSB_um")
    if not core.is_number(rsb):
        pachy = eye.get("pachy_thinnest_um")
        flap = normalized.get("flap_um")
        ablation = values.get("max_ablation_um")
        if all(core.is_number(x) for x in (pachy, flap, ablation)):
            rsb = float(pachy) - float(flap) - float(ablation)

    sphere = normalized.get("manifest_sphere_D")
    cyl_mag = normalized.get("manifest_cylinder_magnitude_D")
    mrse = values.get("MRSE_D")
    if not core.is_number(mrse) and core.is_number(sphere) and core.is_number(cyl_mag):
        mrse = float(sphere) - float(cyl_mag) / 2.0

    rows = {
        "topography": topo_points,
        "RSB": core.lasik_rsb_points(rsb),
        "age": core.age_points(age),
        "pachymetry": core.lasik_pachy_points(eye.get("pachy_thinnest_um")),
        "MRSE": core.lasik_mrse_points(mrse),
    }
    missing = [name for name in _RANDLEMAN_ROWS if rows.get(name) is None]
    total = None if missing else sum(int(rows[name]) for name in _RANDLEMAN_ROWS)
    category = core.score_category("LASIK", total) if total is not None else None
    return {
        "rows": rows,
        "total": total,
        "category": category,
        "missing_erss_inputs": missing,
        "source": "Randleman/ERSS — BAD-independent five-variable pathway",
        "topography_category": topo_category,
        "topography_evidence": topo.get("evidence") or [],
        "bad_dependency": False,
    }


def assess_eye_with_bad_independent_randleman(eye, plan, age, patient_modifiers):
    result = _previous_assess_eye(eye, plan, age, patient_modifiers)
    procedure = (result.get("values") or {}).get("procedure") or (plan or {}).get("procedure")
    if procedure != "LASIK":
        return result

    erss = _independent_lasik_erss(eye, plan, age, result)
    result["randleman_erss"] = erss

    # Publish ERSS whenever its own five inputs exist, even if the separate CERAI
    # tomography pathway is incomplete because BAD data are absent.
    if erss["total"] is not None:
        score = dict(result.get("score") or {})
        score.update({
            "rows": erss["rows"],
            "total": erss["total"],
            "category": erss["category"],
            "source": erss["source"],
            "bad_dependency": False,
        })
        result["score"] = score

    tomography_missing = []
    other_missing = []
    for item in list(result.get("missing") or []):
        text = str(item)
        if any(field in text for field in _BAD_FIELDS) or "BAD" in text.upper() or "BELIN" in text.upper():
            tomography_missing.append(item)
        else:
            other_missing.append(item)
    if tomography_missing:
        result["tomography_missing"] = list(dict.fromkeys(tomography_missing))
        result["missing"] = list(dict.fromkeys(other_missing + tomography_missing))

    warnings = list(result.get("warnings") or [])
    warnings.append(
        "RANDLEMAN/BAD SEPARATION: Randleman ERSS is calculated only from anterior topography, RSB, age, preoperative corneal thickness, and manifest MRSE. BAD-D/Belin-Ambrosio data are a separate CERAI tomography pathway and are never required to calculate the Randleman score."
    )
    if tomography_missing and erss["total"] is not None:
        warnings.append(
            "Randleman ERSS is complete despite missing BAD tomography data; the BAD/tomography pathway remains separately incomplete."
        )
    result["warnings"] = list(dict.fromkeys(warnings))
    return result


core.assess_eye = assess_eye_with_bad_independent_randleman
core._randleman_bad_independence_installed = True
