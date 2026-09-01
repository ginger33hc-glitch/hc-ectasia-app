import base64
import csv
from io import StringIO
import json

import case_archive
import case_catalog
import research_export


ARCHIVE_KEY = bytes(range(32))
RESEARCH_KEY = bytes(reversed(range(32)))


def make_archive():
    return case_archive.EncryptedArchive(case_archive.MemoryObjectStore(), ARCHIVE_KEY)


def assessment(*, patient_id="P-123", patient_name="Şule Işık", report_date="2026-08-31", overall="PASS"):
    return {
        "patient": {
            "id": patient_id,
            "name": patient_name,
            "age": 42,
            "reviewer": "Dr. Private Reviewer",
            "report_date": report_date,
        },
        "decision": {
            "status": overall,
            "eyes": [
                {
                    "eye": "OS",
                    "status": "PASS",
                    "values": {
                        "procedure": "LASIK",
                        "laser_platform": "Alcon WaveLight EX500",
                        "prior_refractive_surgery": "no",
                        "age_years": 42,
                        "pachy_thinnest_um": 505,
                        "MRSE_D": -4.5,
                        "intended_MRSE_D": -4.0,
                        "max_ablation_um": 70,
                        "LASIK_RSB_um": 335,
                        "LASIK_PTA_percent": 33.7,
                        "optical_zone_mm": 6.5,
                        "transition_zone_mm": 9.0,
                        "flap_thickness_um": 100,
                        "preoperative_Kmean_D": 43.2,
                        "estimated_final_Kmean_D": 40.0,
                        "pentacam_qs": "OK",
                    },
                    "bad_summary": {"value": 1.8, "category": "SUSPICIOUS"},
                    "randleman_erss": {"total": 2, "category": "LOW RISK"},
                    "nice": {"total": 4, "category": "NO NICE ESCALATION"},
                    "score": {"total": 2, "category": "LOW"},
                    "topography_classification": {"scoring_category": "NORMAL_SYMMETRIC"},
                },
                {
                    "eye": "OD",
                    "status": "PASS",
                    "values": {
                        "procedure": "PRK",
                        "laser_platform": "Alcon WaveLight EX500",
                        "prior_refractive_surgery": "no",
                        "age_years": 42,
                        "pachy_thinnest_um": 520,
                        "MRSE_D": -3.0,
                        "intended_MRSE_D": -3.0,
                        "max_ablation_um": 45,
                        "PRK_RST_um": 425,
                        "PRK_PTA_percent": 18.3,
                        "optical_zone_mm": 6.5,
                        "transition_zone_mm": 9.0,
                        "preoperative_Kmean_D": 43.0,
                        "estimated_final_Kmean_D": 40.6,
                        "pentacam_qs": "OK",
                    },
                    "bad_summary": {"value": 1.2, "category": "NORMAL"},
                    "randleman_erss": {"total": 1, "category": "LOW RISK"},
                    "nice": {"total": 4, "category": "NO NICE ESCALATION"},
                    "score": {"total": 1, "category": "LOW"},
                    "topography_classification": {"scoring_category": "NORMAL_SYMMETRIC"},
                },
            ],
        },
        "extracted": {
            "document_contexts": [
                {
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "exam_date": "2026-08-29",
                    "source_filename": "private-patient-file.png",
                }
            ],
            "eyes": [
                {
                    "eye": "OD",
                    "K1_D": 42.5,
                    "K2_D": 43.5,
                    "Kmax_D": 44.0,
                    "Kmean_D": 43.0,
                    "I_S": 0.4,
                    "Rmin_mm": 7.8,
                    "ARTmax_um": 390,
                    "PPI_min": 0.8,
                    "PPI_avg": 1.0,
                    "PPI_max": 1.3,
                    "anterior_elevation_thinnest_um": 5,
                    "posterior_elevation_thinnest_um": 12,
                    "source_files": ["private-patient-file.png"],
                },
                {
                    "eye": "OS",
                    "K1_D": 42.7,
                    "K2_D": 43.7,
                    "Kmax_D": 44.2,
                    "Kmean_D": 43.2,
                    "I_S": 0.5,
                    "Rmin_mm": 7.7,
                    "ARTmax_um": 370,
                    "PPI_min": 0.9,
                    "PPI_avg": 1.1,
                    "PPI_max": 1.4,
                    "anterior_elevation_thinnest_um": 6,
                    "posterior_elevation_thinnest_um": 14,
                    "source_files": ["private-patient-file.png"],
                },
            ],
        },
    }


def store_revision(archive, case_id, revision_id, payload, archived_at):
    ready_for_catalog = {
        "patient": payload["patient"],
        "decision": payload["decision"],
        "extracted": payload["extracted"],
    }
    case_catalog.write_entry(
        archive,
        case_archive.RevisionRef(case_id, revision_id, tuple()),
        ready_for_catalog,
    )
    archive.put_bytes(
        case_id,
        f"revisions/{revision_id}",
        "assessment-json",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        media_type="application/json",
    )
    archive.put_bytes(
        case_id,
        f"revisions/{revision_id}",
        "manifest-json",
        json.dumps({"archived_at_utc": archived_at}).encode("utf-8"),
        media_type="application/json",
    )


def test_research_key_must_decode_to_exactly_32_bytes():
    encoded = base64.b64encode(RESEARCH_KEY).decode()
    assert research_export.decode_pseudonym_key(encoded) == RESEARCH_KEY


def test_research_export_contains_two_eye_rows_and_no_direct_identifiers():
    archive = make_archive()
    store_revision(archive, "1" * 32, "2" * 24, assessment(), "2026-08-31T12:00:00+00:00")
    rows = research_export.build_rows(archive, RESEARCH_KEY)
    assert [row["eye"] for row in rows] == ["OD", "OS"]
    assert rows[0]["report_year_month"] == "2026-08"
    assert rows[0]["exam_year_month"] == "2026-08"
    assert rows[0]["study_subject_id"]
    csv_bytes = research_export.render_csv(rows)
    text = csv_bytes.decode("utf-8-sig")
    assert "Şule Işık" not in text
    assert "P-123" not in text
    assert "Dr. Private Reviewer" not in text
    assert "private-patient-file.png" not in text
    assert "2026-08-31" not in text
    assert "2026-08-29" not in text
    parsed = list(csv.DictReader(StringIO(text)))
    assert len(parsed) == 2
    assert parsed[0]["eye"] == "OD"
    assert parsed[1]["eye"] == "OS"


def test_same_patient_id_produces_stable_subject_pseudonym_across_cases():
    archive = make_archive()
    store_revision(archive, "3" * 32, "4" * 24, assessment(), "2026-08-31T12:00:00+00:00")
    store_revision(
        archive,
        "5" * 32,
        "6" * 24,
        assessment(patient_name="Different Display Name"),
        "2026-09-01T12:00:00+00:00",
    )
    rows = research_export.build_rows(archive, RESEARCH_KEY)
    subject_ids = {row["study_subject_id"] for row in rows}
    case_ids = {row["study_case_id"] for row in rows}
    assert len(subject_ids) == 1
    assert len(case_ids) == 2


def test_latest_only_excludes_superseded_revision_of_same_case():
    archive = make_archive()
    case_id = "7" * 32
    store_revision(
        archive,
        case_id,
        "8" * 24,
        assessment(overall="PASS"),
        "2026-08-30T12:00:00+00:00",
    )
    store_revision(
        archive,
        case_id,
        "9" * 24,
        assessment(overall="STOP-DEFER"),
        "2026-08-31T12:00:00+00:00",
    )
    latest = research_export.build_rows(archive, RESEARCH_KEY, latest_only=True)
    all_rows = research_export.build_rows(archive, RESEARCH_KEY, latest_only=False)
    assert len(latest) == 2
    assert {row["overall_status"] for row in latest} == {"STOP-DEFER"}
    assert len(all_rows) == 4


def test_research_csv_header_is_fixed_and_has_no_identity_columns():
    csv_text = research_export.render_csv([]).decode("utf-8-sig")
    header = csv_text.splitlines()[0].split(",")
    assert header == list(research_export.RESEARCH_FIELDS)
    forbidden = {"patient_name", "patient_id", "reviewer", "username", "source_filename"}
    assert forbidden.isdisjoint(header)
