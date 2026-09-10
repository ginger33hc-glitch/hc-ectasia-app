/* CER-AI public homepage access guard, PWA bootstrap, and mobile navigation. No clinical logic.
   public-i18n.js exclusively owns developer/founder text localization. */
(() => {
  const NOTICE_PATH = "/static/testing-notice.html";
  const LANGUAGE_KEY = "cerai-public-language";

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
    const locale = (localStorage.getItem(LANGUAGE_KEY) || "en").toLowerCase();
    const isTurkish = locale === "tr";
    nav.setAttribute("aria-label", isTurkish ? "Bölüm menüsü" : "Section navigation");
    const scroller = document.createElement("div");
    scroller.className = "cerai-mobile-section-scroll";

    const links = isTurkish ? [
      ["Eğitim Merkezi", "/tr/learning-center"],
      ["Ektazi Değerlendirmesi", "/corneal-ectasia-risk-assessment"],
      ["Klinik Kanıtlar", "/clinical-evidence"],
      ["Değerlendirme", "#evaluation"],
      ["CER-AI Nasıl Çalışır", "#science"],
      ["Kullanım Kılavuzu", "#guide"],
      ["Hakkında", "#about"],
      ["Geliştirici", "#developer"]
    ] : [
      ["Learning Center", "/learning-center"],
      ["Ectasia Assessment", "/corneal-ectasia-risk-assessment"],
      ["Clinical Evidence", "/clinical-evidence"],
      ["Evaluation", "#evaluation"],
      ["How CER-AI Works", "#science"],
      ["User Guide", "#guide"],
      ["About", "#about"],
      ["Developer", "#developer"]
    ];
    links.forEach(([label, href]) => {
      if (href.startsWith("#") && !document.querySelector(href)) return;
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

  function watchLanguageSwitch() {
    document.addEventListener("click", event => {
      const button = event.target.closest?.("#cerai-public-language button[data-lang]");
      if (!button) return;
      queueMicrotask(() => {
        document.getElementById("cerAiMobileSectionNav")?.remove();
        ensureMobileSectionNav();
      });
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
    watchLanguageSwitch();
    registerServiceWorker();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
