import base64
import json

import pytest

from scripts import verify_railway_archive_config as preflight


ARCHIVE_KEY = base64.b64encode(bytes(range(32))).decode()
RESEARCH_KEY = base64.b64encode(bytes(reversed(range(32)))).decode()


def env():
    return {
        "BUCKET": "cer-ai-archive-abc123",
        "RAILWAY_BUCKET_NAME": "cer-ai-archive",
        "ACCESS_KEY_ID": "access-key-id",
        "SECRET_ACCESS_KEY": "secret-access-key",
        "REGION": "auto",
        "ENDPOINT": "https://storage.railway.app",
        "AWS_S3_URL_STYLE": "virtual",
        "CERAI_ARCHIVE_MASTER_KEY_B64": ARCHIVE_KEY,
        "CERAI_ARCHIVE_ENABLED": "0",
        "CERAI_ARCHIVE_REQUIRED": "0",
        "CERAI_NAMED_USERS_ENABLED": "0",
        "CERAI_RESEARCH_EXPORT_ENABLED": "0",
    }


def test_valid_railway_configuration_passes_without_exposing_secrets():
    result = preflight.validate_environment(env())
    assert result["bucket_configured"] is True
    assert result["endpoint"] == "https://storage.railway.app"
    assert result["url_style"] == "virtual"
    assert "ACCESS_KEY_ID" not in result
    assert "SECRET_ACCESS_KEY" not in result


def test_display_bucket_name_cannot_replace_s3_bucket_name():
    values = env()
    values["BUCKET"] = values["RAILWAY_BUCKET_NAME"]
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)


def test_endpoint_must_be_https_railway_storage():
    values = env()
    values["ENDPOINT"] = "http://storage.railway.app"
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)
    values["ENDPOINT"] = "https://example.invalid"
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)


def test_path_style_is_allowed_for_legacy_bucket_credentials():
    values = env()
    values["AWS_S3_URL_STYLE"] = "path"
    assert preflight.validate_environment(values)["url_style"] == "path"


def test_archive_key_must_be_exactly_32_bytes():
    values = env()
    values["CERAI_ARCHIVE_MASTER_KEY_B64"] = base64.b64encode(b"short").decode()
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)


def test_research_key_must_be_separate_from_archive_key():
    values = env()
    values["CERAI_RESEARCH_EXPORT_ENABLED"] = "1"
    values["CERAI_RESEARCH_PSEUDONYM_KEY_B64"] = ARCHIVE_KEY
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)
    values["CERAI_RESEARCH_PSEUDONYM_KEY_B64"] = RESEARCH_KEY
    assert preflight.validate_environment(values)["research_export_enabled"] is True


def test_named_users_require_hashed_owner_registry_and_reject_raw_password_field():
    values = env()
    values["CERAI_NAMED_USERS_ENABLED"] = "1"
    values["CERAI_USERS_JSON"] = json.dumps([
        {"user_id": "doctor-1", "role": "DOCTOR", "password_hash": "scrypt$placeholder"}
    ])
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)

    values["CERAI_USERS_JSON"] = json.dumps([
        {"user_id": "owner-1", "role": "OWNER", "password": "do-not-store-this"}
    ])
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)

    values["CERAI_USERS_JSON"] = json.dumps([
        {
            "user_id": "owner-1",
            "role": "OWNER",
            "password": "do-not-store-this",
            "password_hash": "scrypt$placeholder",
        }
    ])
    with pytest.raises(preflight.PreflightError):
        preflight.validate_environment(values)

    values["CERAI_USERS_JSON"] = json.dumps([
        {"user_id": "owner-1", "role": "OWNER", "password_hash": "scrypt$placeholder"}
    ])
    assert preflight.validate_environment(values)["named_users_enabled"] is True


def test_required_mode_implies_archive_enabled_in_preflight_result():
    values = env()
    values["CERAI_ARCHIVE_REQUIRED"] = "1"
    result = preflight.validate_environment(values)
    assert result["archive_enabled"] is True
    assert result["archive_required"] is True
