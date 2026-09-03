"""Presentation-only mobile installation guidance for the public CER-AI site."""
from __future__ import annotations

from typing import Any

import public_site
from fastapi.responses import HTMLResponse


_SECTION = """
<section id="mobile-install" class="alt"><div class="wrap">
  <div class="section-kicker">Mobile access</div>
  <h2>Install CER-AI on your phone</h2>
  <p class="lead">CER-AI can be added to your phone's Home Screen and opened like an app. No App Store or Google Play download is required.</p>
  <div class="guide-grid">
    <div class="guide-step">
      <div class="step-no">iOS</div>
      <h3>iPhone or iPad</h3>
      <p>1. Open <strong>cer-ai.com</strong> in <strong>Safari</strong>.<br>2. Tap the <strong>Share</strong> button.<br>3. Choose <strong>Add to Home Screen</strong>.<br>4. Tap <strong>Add</strong>.</p>
    </div>
    <div class="guide-step">
      <div class="step-no">AND</div>
      <h3>Android</h3>
      <p>1. Open <strong>cer-ai.com</strong> in <strong>Chrome</strong>.<br>2. Tap the browser menu <strong>⋮</strong>.<br>3. Choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.<br>4. Confirm the installation.</p>
    </div>
  </div>
  <div class="guide-alert"><strong>After installation:</strong> CER-AI appears as an icon on the Home Screen and opens directly in its own app-like window. An internet connection is still required for clinical use.</div>
</div></section>
"""


def install(core: Any) -> None:
    if getattr(core, "_cerai_mobile_install_section_installed", False):
        return

    previous_renderer = public_site._render_public_home

    def render_with_mobile_install(request) -> HTMLResponse:
        response = previous_renderer(request)
        body = bytes(response.body).decode("utf-8")
        if 'id="mobile-install"' not in body:
            marker = '<section id="about">'
            if marker in body:
                body = body.replace(marker, _SECTION + marker, 1)
            elif "</main>" in body:
                body = body.replace("</main>", _SECTION + "</main>", 1)
        return HTMLResponse(body, headers={"Cache-Control": "no-cache"})

    public_site._render_public_home = render_with_mobile_install
    core._cerai_mobile_install_section_installed = True
