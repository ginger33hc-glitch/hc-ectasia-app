"""Final-report consistency policy for ML7 microkeratome planning.

ML7 planning is computed before some outer independent CER-AI policies can
further restrict the selected LASIK procedure. The final report must therefore
reconcile any stored ML7 planning record with the final eye disposition and
must never present an intermediate ML7 PASS as final LASIK eligibility.
"""

FAVORABLE_FINAL_STATUSES = {"PASS", "CAUTION"}


def final_lasik_eligible(eye):
    values = eye.get("values") or {}
    return (
        str(values.get("procedure") or "").upper() == "LASIK"
        and str(eye.get("status") or "").upper() in FAVORABLE_FINAL_STATUSES
    )


def install(reports):
    if getattr(reports, "_cerai_microkeratome_report_policy_installed", False):
        return

    original_rows = reports._microkeratome_rows

    def rows_with_final_disposition(eye, locale="en"):
        plan = eye.get("microkeratome_planning") or {}
        if not plan:
            return []
        if final_lasik_eligible(eye):
            return original_rows(eye, locale)

        # A later CER-AI policy has made LASIK ineligible. Remove stale
        # intermediate ML7 planning commentary before the common PDF/DOCX
        # renderers inspect the same planning payload.
        plan["warnings"] = []
        plan["notes"] = []
        source = str(plan.get("source") or "Not applicable")
        na = "Not applicable"
        rows = [
            ("Assessment gate", "NOT APPLICABLE — LASIK not eligible by CER-AI"),
            ("Steep-flat K spread", na),
            ("Vacuum ring", na),
            ("Vacuum pressure", na),
            ("Blade recommendation(s)", na),
            ("Primary hinge", na),
            ("Conditional alternative", na),
            ("Alternative projected RSB / PTA", na),
            ("Alternative safety", na),
            ("Ring-zone clearance", na),
            ("Source", source),
        ]
        return [
            (reports.translate_text(label, locale), reports.translate_text(value, locale))
            for label, value in rows
        ]

    reports._microkeratome_rows = rows_with_final_disposition
    reports._cerai_microkeratome_report_policy_installed = True
