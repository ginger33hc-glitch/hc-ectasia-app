"""Public developer/founder localization contracts; no clinical behavior."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path


class TextNodes(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.texts = []
        self.feed(html)

    def handle_data(self, text):
        if text.strip():
            self.texts.append(text.strip())


def developer_source():
    html = Path("static/public-home.html").read_text(encoding="utf-8")
    match = re.search(r'<section id="developer"[^>]*>(.*?)</section>', html, re.S)
    assert match is not None
    return match.group(1)


def translation_dictionary():
    script = Path("static/public-i18n.js").read_text(encoding="utf-8")
    match = re.search(r'  const TR = (\{.*?\n  \});', script, re.S)
    assert match is not None
    return json.loads(match.group(1))


def test_developer_english_source_is_retained():
    source = developer_source()
    assert "Developer and Clinical Lead" in source
    assert "Founder’s Note" in source
    assert "After more than thirty years" in source
    assert "Geliştirici ve Klinik Lider" not in source
    assert "Kurucunun Notu" not in source


def test_every_developer_text_fragment_has_a_canonical_turkish_translation():
    texts = TextNodes(developer_source()).texts
    translations = translation_dictionary()
    language_neutral = {"Hüseyin Cengiz, M.D.", "0.7.71"}
    missing = [text for text in texts if text not in language_neutral and text not in translations]
    assert not missing, missing
    assert any(text.startswith(". Rather than") for text in texts)
    assert any(text.startswith(", to organize") for text in texts)


def test_homepage_helper_does_not_replace_or_cache_developer_html():
    helper = Path("static/public-tr-home-overrides.js").read_text(encoding="utf-8")
    for retired in ("developerOriginalHtml", "DEVELOPER_TR_HTML", "applyDeveloperLocale", "section.innerHTML"):
        assert retired not in helper
    # The same translator that remembers English source nodes restores them.
    i18n = Path("static/public-i18n.js").read_text(encoding="utf-8")
    assert "const originals = new WeakMap();" in i18n
    assert 'locale === "tr" ? translateText(originals.get(node)) : originals.get(node)' in i18n
