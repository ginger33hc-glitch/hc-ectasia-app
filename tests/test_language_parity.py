from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_secure_interfaces_load_the_canonical_language_controller():
    for filename in ("index.html", "iol.html", "login.html", "module-select.html", "archive.html", "trial-login.html"):
        html = (ROOT / "static" / filename).read_text(encoding="utf-8")
        expected_version = "17" if filename == "iol.html" else "11"
        assert html.count(f'/static/i18n.js?v={expected_version}') == 1, filename


def test_secure_source_markup_is_english_only_and_turkish_is_canonicalized():
    trial = (ROOT / "static" / "trial-login.html").read_text(encoding="utf-8")
    assert '<html lang="en">' in trial
    for mixed_or_turkish in ("Deneme erişimi / Trial access", "Doktor adı / Doctor name", "Devam / Continue", "Giriş başarısız / Sign-in failed"):
        assert mixed_or_turkish not in trial

    i18n = (ROOT / "static" / "i18n.js").read_text(encoding="utf-8")
    for english, turkish in (
        ("Choose a clinical module", "Bir klinik modül seçin"),
        ("IOL Decision Assistant — Advanced Mode", "IOL Karar Asistanı — Gelişmiş Mod"),
        ("Internal ACD excludes corneal thickness; ACD (Ext.) is never substituted.", "İnternal ACD kornea kalınlığını içermez"),
        ("Toric trigger: ≥1.00 D and regular astigmatism.", "Torik tetikleyici: ≥1,00 D ve düzenli astigmatizma."),
        ("Transfer values to ESCRS", "Değerleri ESCRS'ye aktar"),
        ("Biological sex", "Biyolojik cinsiyet"),
        ("Archived cases", "Arşivlenmiş vakalar"),
        ("No password is required during the trial.", "Deneme süresince parola gerekmez."),
    ):
        assert english in i18n
        assert turkish in i18n
    assert "new MutationObserver" in i18n
    assert 'document.title=translate(document.title)' in i18n


def test_turkish_learning_center_localizes_presentation_section():
    source = (ROOT / "public_education.py").read_text(encoding="utf-8")
    assert 'if locale == "tr":\n        presentations =' in source
    assert "Hekim sunumu" in source
    assert "İngilizce sunumu indir" in source
    assert "Türkçe sunumu indir" in source
