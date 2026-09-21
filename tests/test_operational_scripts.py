import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import start


ROOT = Path(__file__).resolve().parents[1]


def run_script(path):
    env = dict(os.environ)
    for name in (
        "BUCKET",
        "ACCESS_KEY_ID",
        "SECRET_ACCESS_KEY",
        "ENDPOINT",
        "CERAI_ARCHIVE_MASTER_KEY_B64",
    ):
        env.pop(name, None)
    return subprocess.run(
        [sys.executable, str(ROOT / path)],
        cwd=ROOT,
        env=env,
        input="",
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def test_direct_canary_script_resolves_project_modules_before_configuration_gate():
    result = run_script("scripts/verify_case_archive.py")
    assert result.returncode != 0
    assert "ModuleNotFoundError" not in result.stderr
    assert "CERAI_ARCHIVE_MASTER_KEY_B64 is required" in result.stderr


def test_direct_migration_script_resolves_project_modules_before_configuration_gate():
    result = run_script("scripts/migrate_case_archive.py")
    assert result.returncode != 0
    assert "ModuleNotFoundError" not in result.stderr
    assert "missing source archive migration configuration" in result.stderr.lower()


def test_direct_password_hash_script_resolves_project_modules_before_prompt_eof():
    result = run_script("scripts/generate_user_password_hash.py")
    assert result.returncode != 0
    assert "ModuleNotFoundError" not in result.stderr
    assert "New CER-AI account password" in result.stderr


def test_startup_verifies_required_archive_with_non_phi_canary(monkeypatch):
    archive = object()
    expected = {
        "status": "VERIFIED",
        "verified_at_utc": "2026-09-21T00:00:00+00:00",
        "sha256": "a" * 64,
        "plaintext_bytes": 100,
    }
    calls = []
    monkeypatch.setattr(
        start,
        "verify_storage_canary",
        lambda value: calls.append(value) or expected,
    )
    core = SimpleNamespace(
        _cerai_case_archive_runtime=SimpleNamespace(
            required=True,
            enabled=True,
            archive=archive,
        )
    )

    assert start.verify_required_archive(core) == expected
    assert calls == [archive]


def test_startup_does_not_probe_optional_archive(monkeypatch):
    monkeypatch.setattr(
        start,
        "verify_storage_canary",
        lambda _archive: pytest.fail("optional archive must not be probed at startup"),
    )
    core = SimpleNamespace(
        _cerai_case_archive_runtime=SimpleNamespace(
            required=False,
            enabled=True,
            archive=object(),
        )
    )

    assert start.verify_required_archive(core) is None
