/* CER-AI public-site PWA registration. Presentation/installability only. */
(() => {
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", async () => {
    try {
      await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    } catch (error) {
      console.error("CER-AI public service worker registration failed", error);
    }
  });
})();
