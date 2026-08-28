"""Contract tests for identifier-free migration evidence."""
from dataclasses import FrozenInstanceError, fields
import pytest

from clean_engine.shadow import ClinicalSnapshot, compare_snapshots
from clean_engine.shadow_evidence import ShadowEvidence, build_shadow_evidence


def test_equivalent_comparison_builds_compact_evidence():
    snap = ClinicalSnapshot(status="PASS WITH CAUTION", lasik_erss_total=1)
    evidence = build_shadow_evidence(compare_snapshots(snap, snap))
    assert evidence == ShadowEvidence(
        equivalent=True,
        differences=(),
        canonical_status="PASS WITH CAUTION",
        clean_status="PASS WITH CAUTION",
    )


def test_divergence_preserves_fields_and_both_statuses():
    canonical = ClinicalSnapshot(status="PASS", hard_stops=())
    clean = ClinicalSnapshot(status="DO NOT PROCEED", hard_stops=("X",))
    evidence = build_shadow_evidence(compare_snapshots(canonical, clean))
    assert evidence.equivalent is False
    assert evidence.differences == ("status", "hard_stops")
    assert evidence.canonical_status == "PASS"
    assert evidence.clean_status == "DO NOT PROCEED"


def test_evidence_schema_contains_no_patient_identifiers_or_raw_clinical_payload():
    names = {field.name for field in fields(ShadowEvidence)}
    assert names == {"equivalent", "differences", "canonical_status", "clean_status"}
    forbidden = {"name", "patient", "patient_id", "dob", "age", "eye", "mrn", "image", "input"}
    assert names.isdisjoint(forbidden)


def test_evidence_is_immutable():
    evidence = ShadowEvidence(True, (), "PASS", "PASS")
    with pytest.raises(FrozenInstanceError):
        evidence.equivalent = False
