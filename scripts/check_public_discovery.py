"""Read-only public HTTP audit. This does not establish search-engine indexing."""
import argparse
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

BASES = {
    "production": "https://cer-ai.com",
    "staging": "https://cer-ai-staging-staging.up.railway.app",
}
PATHS = ("/", "/corneal-ectasia-risk-assessment", "/robots.txt", "/sitemap.xml")
MAX_BYTES = 1024 * 1024


class DiscoveryHead(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.robots = []
        self.verification_tag_present = {"google": False, "bing": False}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "robots":
                self.robots.append(attrs.get("content", ""))
            if name == "google-site-verification":
                self.verification_tag_present["google"] = True
            if name == "msvalidate.01":
                self.verification_tag_present["bing"] = True


def inspect_public(environment):
    base = BASES[environment]
    rows = []
    for path in PATHS:
        row = {"path": path, "checks_passed": False}
        try:
            request = Request(base + path, headers={"User-Agent": "CER-AI-Public-Discovery-Audit/1.0"})
            with urlopen(request, timeout=15) as response:
                raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise ValueError("Public response exceeds audit size limit")
                text = raw.decode("utf-8")
                row.update(status=response.status, final_url=response.url,
                           x_robots_tag=response.headers.get("X-Robots-Tag", ""))
                if response.status != 200:
                    raise ValueError("Public endpoint did not return HTTP 200")
                if urlparse(response.url).hostname != urlparse(base).hostname:
                    raise ValueError("Unexpected cross-host redirect")
                if path.endswith(".xml"):
                    root = ElementTree.fromstring(text)
                    urls = [item.text for item in root.findall("{*}url/{*}loc")]
                    row["sitemap_url_count"] = len(urls)
                    if environment == "production":
                        assert base + "/corneal-ectasia-risk-assessment" in urls, "Product page absent from sitemap"
                        assert all(url and url.startswith(base + "/") for url in urls), "Unexpected sitemap host"
                        assert all(not urlparse(url).path.startswith(("/app", "/testing-app", "/api/", "/archive", "/report", "/analyze")) for url in urls), "Private route in sitemap"
                    else:
                        assert not urls, "Staging sitemap exposes URLs"
                elif path.endswith(".txt"):
                    if environment == "production":
                        for agent in ("OAI-SearchBot", "Googlebot", "Bingbot", "PerplexityBot", "Claude-SearchBot"):
                            assert "User-agent: " + agent in text, "Missing crawler group: " + agent
                        for private in ("/app", "/testing-app", "/api/", "/archive", "/report/", "/analyze"):
                            assert "Disallow: " + private in text, "Missing private crawl restriction"
                        assert "Sitemap: " + base + "/sitemap.xml" in text, "Missing sitemap declaration"
                    else:
                        assert text.strip() == "User-agent: *\nDisallow: /", "Staging crawl restriction changed"
                else:
                    head = DiscoveryHead()
                    head.feed(text)
                    row.update(canonicals=head.canonicals, robots_meta=head.robots,
                               verification_tag_present=head.verification_tag_present)
                    assert head.canonicals == [BASES["production"] + path], "Unexpected canonical"
                    expected = "index,follow" if environment == "production" else "noindex,nofollow"
                    assert len(head.robots) == 1 and head.robots[0].startswith(expected), "Unexpected robots meta"
                    assert row["x_robots_tag"].startswith(expected), "Unexpected X-Robots-Tag"
                    assert "CER-AI" in text, "Expected public content missing"
                row["checks_passed"] = True
        except (AssertionError, HTTPError, URLError, OSError, ValueError, UnicodeError, ElementTree.ParseError) as exc:
            row["error"] = str(exc)
        rows.append(row)
    return {"environment": environment, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "Public GETs only; no clinical endpoints, authentication or patient records accessed.",
            "indexing_status": "NOT_VERIFIED: requires authorized search-console inspection.",
            "crawler_identity_note": "Audit user agent used; this does not verify real search-bot IP access.",
            "results": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=tuple(BASES), required=True)
    args = parser.parse_args()
    result = inspect_public(args.environment)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(row["checks_passed"] for row in result["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
