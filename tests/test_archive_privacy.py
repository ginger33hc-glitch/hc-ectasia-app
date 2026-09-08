from io import BytesIO

from PIL import Image

import archive_privacy


def test_owner_assessment_scrubs_identity_literals_and_source_filenames():
    source = {
        "patient": {
            "name": "Şule Işık",
            "id": "P-123",
            "age": 40,
            "reviewer": "Dr. Reviewer",
        },
        "extracted": {
            "document_contexts": [{
                "patient_name": "Şule Işık",
                "patient_first_name": "Şule",
                "patient_last_name": "Işık",
                "patient_id": "P-123",
                "patient_date_of_birth": "1986-01-02",
                "source_filename": "Şule_Işık_OD.png",
            }],
            "identity_warnings": ["Şule Işık / P-123 needs confirmation"],
        },
        "decision": {"status": "PASS"},
    }

    cleaned = archive_privacy.owner_assessment(source)

    rendered = repr(cleaned)
    for private in ("Şule Işık", "Şule", "Işık", "P-123", "1986-01-02", "Şule_Işık_OD.png"):
        assert private not in rendered
    assert cleaned["patient"]["age"] == 40
    assert cleaned["patient"]["reviewer"] == "Dr. Reviewer"
    assert cleaned["decision"]["status"] == "PASS"


def test_owner_source_image_masks_only_header_band():
    source = BytesIO()
    Image.new("RGB", (100, 100), "blue").save(source, format="PNG")

    masked = archive_privacy.owner_source_image(source.getvalue())

    with Image.open(BytesIO(masked)) as image:
        assert image.format == "PNG"
        assert image.getpixel((95, 5)) == (255, 255, 255)
        assert image.getpixel((95, 95)) == (0, 0, 255)
