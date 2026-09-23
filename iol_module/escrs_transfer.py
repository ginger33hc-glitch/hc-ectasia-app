"""De-identified BiomPIN handoff to the ESCRS IOL Calculator."""

from __future__ import annotations

import json
import os
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import EscrsTransferInput


BIOMAPI_PROCESS_URL = os.getenv(
    "BIOMAPI_PROCESS_URL", "https://biomapi.com/api/v1/biom/process"
)
ESCRS_IOL_CALCULATOR_URL = "https://iolcalculator.escrs.org/"


def build_biomdirect(case: EscrsTransferInput) -> dict[str, object]:
    eye_data: dict[str, object] = {
        "lens_status": "Phakic",
        "AL": case.axial_length_mm,
        "ACD": case.acd_internal_mm,
        "K1_magnitude": case.k1_d,
        "K2_magnitude": case.k2_d,
        "keratometric_index": 1.3375,
    }
    if case.lens_thickness_mm is not None:
        eye_data["LT"] = case.lens_thickness_mm
    if case.cct_um is not None:
        eye_data["CCT"] = case.cct_um
    if case.wtw_mm is not None:
        eye_data["WTW"] = case.wtw_mm

    return {
        "data": {
            "biometer": {"device_name": "Other", "manufacturer": "Other"},
            "patient": {"gender": case.biological_sex},
            "right_eye": eye_data if case.eye == "OD" else {},
            "left_eye": eye_data if case.eye == "OS" else {},
        },
        "extra_data": {
            "notes": (
                "CER-AI composite source: AL and K values from IOLMaster 500; "
                "ACD, CCT and WTW from Pentacam Cataract Pre-Op. ACD is "
                "Pentacam ACD (Int.), excluding CCT. Verify every imported "
                "value before calculation."
            )
        },
    }


def _multipart(document: dict[str, object]) -> tuple[bytes, str]:
    boundary = f"----CerAiBiomAPI{uuid.uuid4().hex}"
    file_data = json.dumps(document, separators=(",", ":")).encode("utf-8")
    body = b"".join(
        (
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="cerai-escrs.json"\r\n',
            b"Content-Type: application/json\r\n\r\n",
            file_data,
            b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="biompin"\r\n\r\ntrue\r\n',
            f"--{boundary}--\r\n".encode(),
        )
    )
    return body, f"multipart/form-data; boundary={boundary}"


def create_escrs_transfer(case: EscrsTransferInput) -> dict[str, str | None]:
    body, content_type = _multipart(build_biomdirect(case))
    headers = {
        "Content-Type": content_type,
        "Accept": "application/json",
        "User-Agent": "CER-AI-IOL/1.0",
        "X-BiomAPI-Integrator-ID": "cer-ai",
    }
    api_key = os.getenv("BIOMAPI_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(BIOMAPI_PROCESS_URL, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"BiomAPI rejected the ESCRS transfer ({exc.code}): {detail[:300]}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("BiomAPI could not be reached for the ESCRS transfer.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("BiomAPI returned an invalid response for the ESCRS transfer.") from exc

    biompin = result.get("biompin") if isinstance(result, dict) else None
    pin = biompin.get("pin") if isinstance(biompin, dict) else None
    if not isinstance(pin, str) or not pin.strip():
        raise RuntimeError("BiomAPI did not return a BiomPIN for the ESCRS transfer.")
    expires_at = biompin.get("expires_at") if isinstance(biompin.get("expires_at"), str) else None
    return {
        "escrs_url": f"{ESCRS_IOL_CALCULATOR_URL}?biompin={quote(pin.strip())}",
        "expires_at": expires_at,
    }
