#!/usr/bin/env python3
"""Submit explicitly changed public CER-AI URLs to the IndexNow protocol."""

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


CANONICAL_HOST = "cer-ai.com"
DEFAULT_ENDPOINT = "https://api.indexnow.org/indexnow"
INDEXNOW_KEY = "731d2001b05e7e15840a00e98f53447d"
DEFAULT_PATHS = (
    "/what-is-recommended-for-corneal-ectasia-screening",
    "/corneal-ectasia-screening-systems",
    "/tr/korneal-ektazi-taramasi-onerileri",
    "/tr/korneal-ektazi-tarama-sistemleri",
    "/sitemap.xml",
)


def build_payload(paths: list[str]) -> dict:
    urls = []
    for path in paths:
        if not path.startswith("/") or urlparse(path).scheme or urlparse(path).netloc:
            raise ValueError(f"Only canonical absolute paths are accepted: {path!r}")
        urls.append(f"https://{CANONICAL_HOST}{path}")
    return {
        "host": CANONICAL_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{CANONICAL_HOST}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }


def submit(payload: dict, endpoint: str = DEFAULT_ENDPOINT) -> int:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return response.status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args()
    payload = build_payload(args.paths)
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0
    try:
        status = submit(payload, args.endpoint)
    except (HTTPError, URLError, OSError) as exc:
        raise SystemExit(f"IndexNow submission failed: {exc}") from exc
    if status not in {200, 202}:
        raise SystemExit(f"Unexpected IndexNow status: {status}")
    print(f"IndexNow accepted {len(payload['urlList'])} changed URLs: HTTP {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
