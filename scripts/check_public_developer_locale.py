"""Browser regression for the public developer section. No clinical requests."""
import argparse
import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from playwright.sync_api import expect, sync_playwright

BASES = {
    "local": "http://127.0.0.1:8765",
    "staging": "https://cer-ai-staging-staging.up.railway.app",
    "production": "https://cer-ai.com",
}
SCRIPTS = ("static/public-i18n.js", "static/public-tr-home-overrides.js")
KEY = "cerai-public-language"


def read_ref(ref, path):
    if not re.fullmatch(r"[0-9a-f]{40}", ref):
        raise ValueError("Baseline must be an immutable full commit SHA")
    return subprocess.check_output(["git", "show", f"{ref}:{path}"], text=True)


def wait_for_public_scripts(base):
    """Bounded deployment check using public assets only, never secrets or reports."""
    expected = {path: Path(path).read_bytes() for path in SCRIPTS}
    last_error = "Not checked"
    for attempt in range(9):
        try:
            rows = []
            for path, content in expected.items():
                request = Request(base + "/" + path, headers={
                    "User-Agent": "CER-AI-Public-Locale-Check/1.0", "Cache-Control": "no-cache",
                })
                with urlopen(request, timeout=10) as response:
                    actual = response.read(1024 * 1024)
                    if response.status != 200 or actual != content:
                        raise RuntimeError(f"Deployed public script does not match release: {path}")
                    rows.append({"path": path, "status": response.status,
                                 "sha256": hashlib.sha256(actual).hexdigest()})
            return rows
        except (OSError, RuntimeError) as error:
            last_error = str(error)
            if attempt < 8:
                time.sleep(10)
    raise RuntimeError(last_error)


def context_with_language(browser, width, initial):
    context = browser.new_context(viewport={"width": width, "height": 1000 if width > 600 else 844},
                                  service_workers="block")
    if initial is not None:
        context.add_init_script(
            f"if (localStorage.getItem('{KEY}') === null) "
            f"localStorage.setItem('{KEY}', {json.dumps(initial)});"
        )
    return context


def settled(page):
    page.evaluate("() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=tuple(BASES), default="local")
    parser.add_argument("--baseline-ref")
    args = parser.parse_args()
    base = BASES[args.environment]
    url = base + ("/static/public-home.html" if args.environment == "local" else "/")
    out = Path("public-developer-artifacts") / args.environment
    out.mkdir(parents=True, exist_ok=True)
    html = Path("static/public-home.html").read_text(encoding="utf-8")
    i18n = Path(SCRIPTS[0]).read_text(encoding="utf-8")
    translations = json.loads(re.search(r"  const TR = (\{.*?\n  \});", i18n, re.S).group(1))
    summary = {"environment": args.environment, "started_at_utc": datetime.now(timezone.utc).isoformat(),
               "public_assets": [], "legacy_bug_reproduced": False, "scenarios": []}
    if args.environment != "local":
        summary["public_assets"] = wait_for_public_scripts(base)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        if args.baseline_ref:
            if args.environment != "local":
                raise ValueError("Legacy reproduction is local only")
            assert read_ref(args.baseline_ref, "static/public-home.html") == html, "Homepage markup changed"
            legacy = {"/" + path: read_ref(args.baseline_ref, path) for path in SCRIPTS}
            context = context_with_language(browser, 1440, "tr")

            def original_scripts(route):
                path = urlparse(route.request.url).path
                if path in legacy:
                    route.fulfill(status=200, content_type="application/javascript", body=legacy[path])
                else:
                    route.continue_()

            context.route("**/static/public-*.js*", original_scripts)
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            page.locator('#cerai-public-language button[data-lang="en"]').click()
            settled(page)
            expect(page.locator("html")).to_have_attribute("lang", "en")
            expect(page.locator("#developer .section-kicker")).to_have_text("Geliştirici ve Klinik Lider")
            summary["legacy_bug_reproduced"] = True
            page.locator("#developer").screenshot(path=str(out / "legacy-english-shows-turkish.png"))
            context.close()
            print("REPRODUCED on original scripts: saved TR -> English selected -> Turkish developer heading")

        for width in (1440, 390):
            for initial in (None, "en", "tr"):
                context = context_with_language(browser, width, initial)
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto(url, wait_until="networkidle")
                assert response is not None and response.status == 200
                expected = page.evaluate("""({html, translations}) => {
                    const documentCopy = new DOMParser().parseFromString(html, 'text/html');
                    const section = documentCopy.querySelector('#developer');
                    const en = section.innerHTML;
                    const walker = documentCopy.createTreeWalker(section, NodeFilter.SHOW_TEXT);
                    while (walker.nextNode()) {
                        const node = walker.currentNode, original = node.nodeValue, key = original.trim();
                        if (translations[key]) node.nodeValue = original.replace(key, translations[key]);
                    }
                    return {en, tr: section.innerHTML};
                }""", {"html": html, "translations": translations})
                page.evaluate("window.__developerGrid = document.querySelector('#developer .developer-grid')")

                def verify(locale):
                    settled(page)
                    expect(page.locator("html")).to_have_attribute("lang", locale)
                    actual = page.locator("#developer").inner_html()
                    assert actual == expected[locale], (width, initial, locale, "Developer text/markup mismatch")
                    assert page.evaluate("window.__developerGrid === document.querySelector('#developer .developer-grid')"), "Developer DOM was replaced"
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), "Horizontal overflow"
                    assert not errors, errors

                verify(initial or "en")
                for locale in ("tr", "en", "tr", "en", "tr", "en"):
                    page.locator(f'#cerai-public-language button[data-lang="{locale}"]').click()
                    verify(locale)
                    if initial == "tr":
                        page.locator("#developer").screenshot(path=str(out / f"developer-{width}-{locale}.png"))
                for locale in ("tr", "en"):
                    page.locator(f'#cerai-public-language button[data-lang="{locale}"]').click()
                    verify(locale)
                    page.reload(wait_until="networkidle")
                    page.evaluate("window.__developerGrid = document.querySelector('#developer .developer-grid')")
                    verify(locale)
                    opposite = "en" if locale == "tr" else "tr"
                    page.locator(f'#cerai-public-language button[data-lang="{opposite}"]').click()
                    verify(opposite)
                summary["scenarios"].append({"width": width, "initial_language": initial or "unset", "passed": True})
                print(f"PASS {args.environment}: {width}px / initial={initial or 'unset'} / full developer text, repeated toggles and persisted reloads")
                context.close()
        browser.close()
    summary["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
