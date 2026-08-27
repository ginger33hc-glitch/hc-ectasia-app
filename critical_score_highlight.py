"""UI patch: make score-based failure immediately visible in preliminary results and printed report."""
from pathlib import Path

import bootstrap

index_path = Path(__file__).parent / "static" / "index.html"

CSS = """
<style id="hc-critical-score-style">
.critical-score-alert{background:var(--red)!important;color:var(--redInk)!important;border:2px solid #c52b2b!important;border-left:7px solid #c52b2b!important;border-radius:6px!important;padding:10px 12px!important;font-weight:800!important;margin:8px 0!important}
.critical-score-alert::before{content:"CRITICAL SCORE — ";font-weight:900;letter-spacing:.25px}
@media print{.critical-score-alert{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fde5e5!important;color:#a31212!important;border-color:#c52b2b!important}}
</style>
"""

SCRIPT = r"""
<script id="hc-critical-score-script">
(function(){
  function markCriticalScores(root){
    const scope=root&&root.querySelectorAll?root:document;
    const nodes=scope.querySelectorAll('li, p, div, td, span');
    nodes.forEach(function(el){
      if(el.children.length>4)return;
      const text=(el.textContent||'').trim();
      if(!text.includes('HC SCORE — SOURCE & BREAKDOWN'))return;
      const m=text.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);
      if(!m)return;
      const score=parseFloat(m[1]);
      // Current HC failure threshold: LASIK ERSS >=4; PRK high-concern score >=4.
      if(Number.isFinite(score)&&score>=4)el.classList.add('critical-score-alert');
      else el.classList.remove('critical-score-alert');
    });
  }
  function run(){markCriticalScores(document);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
  new MutationObserver(function(){run();}).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
})();
</script>
"""

try:
    html = index_path.read_text(encoding="utf-8")
    html = html.replace("HC Ectasia App v0.7.10", "HC Ectasia App v0.7.11")
    if 'id="hc-critical-score-style"' not in html:
        html = html.replace("</head>", CSS + "\n</head>")
    if 'id="hc-critical-score-script"' not in html:
        html = html.replace("</body>", SCRIPT + "\n</body>")
    index_path.write_text(html, encoding="utf-8")
except OSError:
    pass

bootstrap.core.app.title = "HC Ectasia App v0.7.11"
app = bootstrap.app
