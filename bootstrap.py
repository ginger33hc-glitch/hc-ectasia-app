"""Runtime bootstrap for the HC Ectasia App."""
from pathlib import Path

import app as core
from lasik_planning import install

install(core)

# Keep the browser defaults synchronized with the HC LASIK planning policy.
# The server-side engine still enforces Plan A first even if a stale browser submits
# different values, so this UI patch is convenience/visibility rather than a safety control.
index_path = Path(__file__).parent / "static" / "index.html"
try:
    html = index_path.read_text(encoding="utf-8")
    replacements = {
        "HC Ectasia App v0.7.4": "HC Ectasia App v0.7.5",
        '<option value="100">100 µm</option>': '<option value="100" selected>100 µm</option>',
        '<option value="6.5">6.5 mm</option>': '<option value="6.5" selected>6.5 mm</option>',
        '<option value="9.0">9.0 mm</option>': '<option value="9.0" selected>9.0 mm</option>',
    }
    patched = html
    for old, new in replacements.items():
        patched = patched.replace(old, new)
    if patched != html:
        index_path.write_text(patched, encoding="utf-8")
except OSError:
    # Failure to patch display defaults must not prevent startup; server-side enforcement remains active.
    pass

core.app.title = "HC Ectasia App v0.7.5"
app = core.app
