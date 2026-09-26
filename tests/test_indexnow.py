"""IndexNow submission contract for public CER-AI discovery pages."""

import json

import pytest

from scripts.submit_indexnow import CANONICAL_HOST, DEFAULT_PATHS, INDEXNOW_KEY, build_payload


def test_indexnow_payload_uses_only_canonical_public_urls():
    payload = build_payload(list(DEFAULT_PATHS))
    assert payload["host"] == CANONICAL_HOST == "cer-ai.com"
    assert payload["key"] == INDEXNOW_KEY
    assert payload["keyLocation"] == f"https://cer-ai.com/{INDEXNOW_KEY}.txt"
    assert len(payload["urlList"]) == len(DEFAULT_PATHS)
    assert all(url.startswith("https://cer-ai.com/") for url in payload["urlList"])
    json.dumps(payload)


@pytest.mark.parametrize("unsafe", ["https://example.com/x", "//example.com/x", "relative"])
def test_indexnow_rejects_noncanonical_targets(unsafe):
    with pytest.raises(ValueError):
        build_payload([unsafe])
