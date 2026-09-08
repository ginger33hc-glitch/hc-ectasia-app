/* CER-AI public homepage access guard, PWA bootstrap, mobile navigation, and targeted Founder localization. No clinical logic. */
(() => {
  const NOTICE_PATH = "/static/testing-notice.html";
  const LANGUAGE_KEY = "cerai-public-language";
  let developerOriginalHtml = null;

  const DEVELOPER_TR_HTML = `
    <div class="wrap developer-grid">
      <div class="developer-card">
        <div class="section-kicker">Geliştirici ve Klinik Lider</div>
        <p class="developer-name">Hüseyin Cengiz, M.D.</p>
        <p class="developer-role">Göz Cerrahı · CER-AI Geliştiricisi</p>
        <p class="developer-meta">Yaklaşık 30 yıllık klinik ve cerrahi oftalmoloji deneyimi</p>
        <p class="developer-meta">Refraktif · Katarakt · Vitreoretinal Cerrahi</p>
        <p class="developer-meta">Kurucu, Vision Eye Hospital</p>
      </div>
      <div class="founder-note">
        <h2>Kurucunun Notu</h2>
        <p>Otuz yılı aşkın cerrahi ve idari deneyimden sonra, biriktirdiğim bilgi ve deneyimin bir bölümünü benden sonraki kuşaklara aktarabilmenin bir yolunu bulmak istedim.</p>
        <p>Bir refraktif cerrah olarak en çok çekindiğimiz komplikasyonlardan biri korneal ektazidir. Amacım, cerrahi öncesinde ektazi yatkınlığını daha güvenilir biçimde belirlemeye yardımcı olabilecek ve sonuçta hastaları önlenebilir bir komplikasyondan korumaya katkı sağlayabilecek bir sistem geliştirmekti. Yapay zekânın hızlı gelişimiyle birlikte, yerleşik klinik kanıtları, modern görüntüleme verilerini ve kendi cerrahi deneyimimi yapılandırılmış bir klinik karar destek platformunda birleştirmeye karar verdim.</p>
        <p><strong>CER-AI — Cornea Ectasia Risk Assessment Intelligence</strong>, platform genelinde kullanılan tek güncel ürün adıdır.</p>
        <p>Yazılım 0.1, 0.2, 0.3 sürümleri ve sonraki geliştirmelerle aşamalı olarak ilerledi; bu metnin yazıldığı sırada <strong>0.7.71</strong> sürümüne ulaştı. Geliştirme sürekli devam ettiği için siz bunu okurken daha yeni bir sürüm kullanımda olabilir.</p>
        <p>Geliştirme sürecinde korneal ektazi, keratokonus yatkınlığı, refraktif cerrahi taraması, kornea tomografisi, topografi, biyomekanik ve doku güvenliğiyle ilgili tıbbi literatürü kapsamlı biçimde gözden geçirdim. Bu kanıtları pratik cerrahi deneyimle birleştirerek farklı ektazi risk değerlendirme sistemlerini tek bir çerçeve içinde bir araya getirdim.</p>
        <p>CER-AI'nin temel ilkelerinden biri, bu sistemlerin <strong>birbirinden bağımsız kalmasıdır</strong>. Bunları tek ve şeffaf olmayan bir puanda birleştirmek yerine, her değerlendirme yolu vakayı ayrı olarak inceler; böylece cerrah farklı risk değerlendirme yaklaşımlarının nerede uyumlu, nerede farklı sonuç verdiğini görebilir.</p>
        <p>CER-AI'nin temel amacı hekimin yerine cerrahi karar vermek değildir. Sistem; <strong>hekimin karar verme sürecini desteklemek</strong>, karmaşık preoperatif bilgiyi düzenlemek ve en önemlisi gözden kaçabilecek bir bulgunun fark edilmesine yardımcı olmak üzere tasarlanmıştır.</p>
        <p>Özellikle genç meslektaşlarıma, cerrahi kariyerim boyunca bana yol gösteren şu ilkeyi vurgulamak isterim: <strong>Hangi işlemi yaparsak yapalım, ilk sorumluluğumuz hastaya zarar vermemektir.</strong></p>
        <p>Teknoloji, görüntüleme, puanlama sistemleri ve yapay zekâ bize yardımcı olabilir; ancak bunların tümü her zaman bu temel klinik sorumluluğa hizmet etmelidir.</p>
      </div>
    </div>`;

  function routePublicAccessButtons() {
    document.querySelectorAll('a[href="/app"]').forEach(link => {
      link.setAttribute("href", NOTICE_PATH);
    });
  }

  function ensurePwaMetadata() {
    if (!document.querySelector('link[rel="manifest"]')) {
      const manifest = document.createElement("link");
      manifest.rel = "manifest";
      manifest.href = "/static/manifest.webmanifest?v=12";
      document.head.appendChild(manifest);
    }
    if (!document.querySelector('link[rel="apple-touch-icon"]')) {
      const appleIcon = document.createElement("link");
      appleIcon.rel = "apple-touch-icon";
      appleIcon.sizes = "180x180";
      appleIcon.href = "/static/icons/apple-touch-icon.png?v=8";
      document.head.appendChild(appleIcon);
    }
    if (!document.querySelector('meta[name="theme-color"]')) {
      const theme = document.createElement("meta");
      theme.name = "theme-color";
      theme.content = "#05090d";
      document.head.appendChild(theme);
    }
  }

  function ensureMobileSectionNav() {
    if (document.getElementById("cerAiMobileSectionNav")) return;
    const host = document.querySelector(".nav-bar");
    if (!host) return;

    const style = document.createElement("style");
    style.textContent = `
      .cerai-mobile-section-nav{display:none}
      @media(max-width:560px){
        .cerai-mobile-section-nav{display:block;position:sticky;top:54px;z-index:49;background:#f7fafc;border-bottom:1px solid #d8e2e9;padding:7px 8px;box-shadow:0 2px 8px rgba(23,59,87,.06)}
        .cerai-mobile-section-scroll{display:flex;gap:7px;overflow-x:auto;overscroll-behavior-inline:contain;scrollbar-width:none;padding:1px 2px 3px;-webkit-overflow-scrolling:touch}
        .cerai-mobile-section-scroll::-webkit-scrollbar{display:none}
        .cerai-mobile-section-link{flex:0 0 auto;display:inline-flex;align-items:center;min-height:34px;padding:7px 11px;border:1px solid #b7cad8;border-radius:999px;background:#fff;color:#173b57;text-decoration:none;font:700 12px Arial,sans-serif;white-space:nowrap}
        .cerai-mobile-section-link:active,.cerai-mobile-section-link:focus{background:#eaf3f8;border-color:#6f98b5;outline:none}
        section[id]{scroll-margin-top:108px}
      }
    `;
    document.head.appendChild(style);

    const nav = document.createElement("nav");
    nav.id = "cerAiMobileSectionNav";
    nav.className = "cerai-mobile-section-nav";
    nav.setAttribute("aria-label", "Section navigation");
    const scroller = document.createElement("div");
    scroller.className = "cerai-mobile-section-scroll";

    [
      ["Evaluation", "#evaluation"],
      ["How CER-AI Works", "#science"],
      ["User Guide", "#guide"],
      ["About", "#about"],
      ["Developer", "#developer"]
    ].forEach(([label, href]) => {
      if (!document.querySelector(href)) return;
      const link = document.createElement("a");
      link.className = "cerai-mobile-section-link";
      link.href = href;
      link.textContent = label;
      scroller.appendChild(link);
    });

    if (!scroller.children.length) return;
    nav.appendChild(scroller);
    host.insertAdjacentElement("afterend", nav);
  }

  function applyDeveloperLocale() {
    const section = document.querySelector("#developer");
    if (!section) return;
    if (developerOriginalHtml === null) developerOriginalHtml = section.innerHTML;
    const locale = (localStorage.getItem(LANGUAGE_KEY) || "en").toLowerCase();
    section.innerHTML = locale === "tr" ? DEVELOPER_TR_HTML : developerOriginalHtml;
  }

  function watchLanguageSwitch() {
    document.addEventListener("click", event => {
      const button = event.target.closest?.("#cerai-public-language button[data-lang]");
      if (!button) return;
      queueMicrotask(applyDeveloperLocale);
    });
  }

  function registerServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    window.addEventListener("load", async () => {
      try {
        await navigator.serviceWorker.register("/sw.js", { scope: "/" });
      } catch (error) {
        console.error("CER-AI service worker registration failed", error);
      }
    }, { once: true });
  }

  function init() {
    routePublicAccessButtons();
    ensurePwaMetadata();
    ensureMobileSectionNav();
    applyDeveloperLocale();
    watchLanguageSwitch();
    registerServiceWorker();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
