/* CER-AI public homepage access guard. No clinical logic. */
(() => {
  const NOTICE_PATH = "/static/testing-notice.html";

  function routePublicAccessButtons() {
    document.querySelectorAll('a[href="/app"]').forEach(link => {
      link.setAttribute("href", NOTICE_PATH);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", routePublicAccessButtons, { once: true });
  } else {
    routePublicAccessButtons();
  }
})();
