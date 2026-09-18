import app


def test_five_mandatory_images_start_together_by_default(monkeypatch):
    monkeypatch.delenv("IMAGE_EXTRACTION_CONCURRENCY", raising=False)

    assert app.primary_extraction_concurrency(5) == 5


def test_primary_image_concurrency_never_exceeds_five(monkeypatch):
    monkeypatch.setenv("IMAGE_EXTRACTION_CONCURRENCY", "20")

    assert app.primary_extraction_concurrency(6) == 5


def test_primary_image_concurrency_respects_lower_operational_override(monkeypatch):
    monkeypatch.setenv("IMAGE_EXTRACTION_CONCURRENCY", "3")

    assert app.primary_extraction_concurrency(5) == 3


def test_primary_image_concurrency_does_not_exceed_uploaded_images(monkeypatch):
    monkeypatch.delenv("IMAGE_EXTRACTION_CONCURRENCY", raising=False)

    assert app.primary_extraction_concurrency(2) == 2
