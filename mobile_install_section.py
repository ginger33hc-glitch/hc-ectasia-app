"""Presentation-only mobile installation guidance for the public CER-AI site."""
from __future__ import annotations

from typing import Any

import public_site
from fastapi.responses import HTMLResponse


_SECTION = """
<div id="mobile-install" style="margin-top:34px;padding:26px;border:1px solid var(--line);border-radius:15px;background:#fff;box-shadow:0 6px 18px rgba(23,59,87,.045)">
  <div class="section-kicker">Mobile access</div>
  <h2 style="font-size:clamp(25px,3vw,34px);margin-bottom:10px">Install CER-AI on your phone</h2>
  <p class="lead" style="font-size:16px">CER-AI can be added to your phone's Home Screen and opened like an app. No App Store or Google Play download is required.</p>
  <div class="guide-grid" style="margin-top:22px">
    <div class="guide-step">
      <div class="step-no">iOS</div>
      <h3>iPhone or iPad</h3>
      <p><strong>1.</strong> Open <strong>cer-ai.com</strong> in Safari.<br><strong>2.</strong> Tap the <strong>Share</strong> button.<br><strong>3.</strong> Choose <strong>Add to Home Screen</strong>.<br><strong>4.</strong> Tap <strong>Add</strong>.</p>
    </div>
    <div class="guide-step">
      <div class="step-no">AND</div>
      <h3>Android</h3>
      <p><strong>1.</strong> Open <strong>cer-ai.com</strong> in Chrome.<br><strong>2.</strong> Tap the browser menu <strong>⋮</strong>.<br><strong>3.</strong> Choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.<br><strong>4.</strong> Confirm.</p>
    </div>
  </div>
  <div class="guide-alert"><strong>After installation:</strong> CER-AI appears as an icon on the Home Screen and opens in an app-like window. An internet connection is still required for clinical use.</div>
</div>
"""


def install(core: Any) -> None:
    if getattr(core, "_cerai_mobile_install_section_installed", False):
        return

    previous_renderer = public_site._render_public_home

    def render_with_mobile_install(request) -> HTMLResponse:
        response = previous_renderer(request)
        body = bytes(response.body).decode("utf-8")
        if 'id="mobile-install"' not in body:
            # Put the installation instructions visibly inside the existing User Guide,
            # immediately before the clinical-use warning and application button.
            marker = '<div class="guide-alert"><strong>Clinical use:'
            if marker in body:
                body = body.replace(marker, _SECTION + marker, 1)
            else:
                about_marker = '<section id="about">'
                if about_marker in body:
                    body = body.replace(about_marker, _SECTION + about_marker, 1)
                elif "</main>" in body:
                    body = body.replace("</main>", _SECTION + "</main>", 1)
        return HTMLResponse(body, headers={"Cache-Control": "no-store, max-age=0"})

    public_site._render_public_home = render_with_mobile_install
    core._cerai_mobile_install_section_installed = True
