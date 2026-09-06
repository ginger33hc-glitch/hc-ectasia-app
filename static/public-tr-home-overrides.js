/* CER-AI public homepage access guard and PWA bootstrap. No clinical logic. */
(() => {
  const NOTICE_PATH = "/static/testing-notice.html";

  function routePublicAccessButtons() {
    document.querySelectorAll('a[href="/app"]').forEach(link => {
      link.setAttribute("href", NOTICE_PATH);
    });
  }

  function ensurePwaMetadata() {
    if (!document.querySelector('link[rel="manifest"]')) {
      const manifest = document.createElement("link");
      manifest.rel = "manifest";
      manifest.href = "/static/manifest.webmanifest?v=10";
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
    registerServiceWorker();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
