"""Resolve patient age and enforce surgeon-entered age precedence."""
from copy import deepcopy
from datetime import date
from exam_date_reconciliation_policy import possible_calendar_dates, _is_four_maps_refractive


def resolve_patient_age(extractions):
    contexts = [r.get("document_context") or {} for r in extractions
                if (r.get("document_context") or {}).get("document_type") == "PENTACAM_TOPOGRAPHY"]
    printed = {c["patient_age_years"] for c in contexts
               if isinstance(c.get("patient_age_years"), int)
               and not isinstance(c.get("patient_age_years"), bool)}
    sources = [r.get("document_context") or {} for r in extractions
               if _is_four_maps_refractive(r)
               and (r.get("document_context") or {}).get("document_type") == "PENTACAM_TOPOGRAPHY"]
    evidence = [{"file": c.get("source_filename"), "date_of_birth": c.get("patient_date_of_birth"),
                 "exam_date": c.get("exam_date")} for c in sources]
    births = [possible_calendar_dates(c["patient_date_of_birth"]) for c in sources if c.get("patient_date_of_birth")]
    exams = [possible_calendar_dates(c["exam_date"]) for c in sources if c.get("exam_date")]
    derived = set()
    problem = None
    if births and exams:
        birth_dates = set.intersection(*births)
        exam_dates = set.intersection(*exams)
        if not birth_dates or not exam_dates:
            problem = "Unreadable, invalid, or conflicting birth/exam dates; enter surgeon-confirmed age."
        else:
            for b in birth_dates:
                for e in exam_dates:
                    dob, exam = date.fromisoformat(b), date.fromisoformat(e)
                    if exam < dob:
                        problem = "Exam date precedes birth date; enter surgeon-confirmed age."
                        continue
                    derived.add(exam.year - dob.year - ((exam.month, exam.day) < (dob.month, dob.day)))
            if len(derived) != 1:
                problem = "Ambiguous dates do not establish one age; enter surgeon-confirmed age."
    ages = printed | derived
    if len(ages) > 1:
        problem = "Printed and/or calculated patient ages conflict; enter surgeon-confirmed age."
    value = next(iter(ages)) if len(ages) == 1 and not problem else None
    return {"age_years": value, "candidate_ages": sorted(ages), "warning": problem,
            "source": "DOB_AT_EXAM" if derived else "PRINTED_AGE", "date_evidence": evidence}


def apply_surgeon_age_precedence(extracted, surgeon_age):
    """Keep source evidence but remove derived-age conflict when the surgeon enters age."""
    working = deepcopy(extracted)
    if not isinstance(surgeon_age, int) or isinstance(surgeon_age, bool):
        return working
    resolution = working.get("patient_age_resolution") or {}
    warning = resolution.get("warning")
    if warning:
        working["global_warnings"] = [
            item for item in working.get("global_warnings") or [] if item != warning
        ]
    working.pop("patient_age_conflict_values", None)
    working["surgeon_confirmed_age_years"] = surgeon_age
    working["resolved_age_years"] = surgeon_age
    working["age_source"] = "SURGEON_CONFIRMED"
    return working
