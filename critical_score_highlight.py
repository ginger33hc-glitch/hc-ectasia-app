"""UI patch: deterministic report highlighting and clinical reference appendix."""
from pathlib import Path
import hc_age_policy
import hc_bad_final_policy
import bootstrap
import extraction_guard
import erss_topography_guard
APP_VERSION="0.7.28"
APP_LABEL=f"HC Ectasia App v{APP_VERSION}"
index_path=Path(__file__).parent/"static"/"index.html"
# Preserve the existing injected UI patch; this module update advances the deployed version after
# the v0.7.28 structured Pentacam 4 Maps source-identification fix in erss_topography_guard.
try:
 import re
 html=index_path.read_text(encoding="utf-8")
 html=re.sub(r'HC Ectasia App v\d+\.\d+\.\d+',APP_LABEL,html)
 html=re.sub(r'Software v\d+\.\d+\.\d+',f'Software v{APP_VERSION}',html)
 index_path.write_text(html,encoding='utf-8')
except OSError:pass
bootstrap.core.APP_VERSION=APP_VERSION
bootstrap.core.app.title=APP_LABEL
app=bootstrap.app
