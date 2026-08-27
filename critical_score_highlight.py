"""UI patch: highlight only the numeric score box when HC score is >=4."""
from pathlib import Path

import bootstrap

index_path = Path(__file__).parent / "static" / "index.html"

CSS = """
<style id="hc-critical-score-style">
.critical-score-alert{background:var(--red)!important;color:var(--redInk)!important;border:2px solid #c52b2b!important;border-radius:5px!important;padding:2px 6px!important;font-weight:900!important;display:inline-block!important}
.critical-score-alert::before{content:none!important}
@media print{.critical-score-alert{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fde5e5!important;color:#a31212!important;border-color:#c52b2b!important}}
</style>
"""

SCRIPT = r"""
<script id="hc-critical-score-script">
(function(){
  function markCriticalScores(root){
    const scope=root&&root.querySelectorAll?root:document;
    // Restore any legacy whole-row highlighting from v0.7.11.
    scope.querySelectorAll('.critical-score-alert').forEach(function(el){
      if(!el.classList.contains('hc-score-value'))el.classList.remove('critical-score-alert');
    });
    const nodes=scope.querySelectorAll('li, p, div, td, span');
    nodes.forEach(function(el){
      if(el.querySelector&&el.querySelector('.hc-score-value'))return;
      const text=(el.textContent||'').trim();
      if(!text.includes('HC SCORE — SOURCE & BREAKDOWN'))return;
      const m=text.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);
      if(!m)return;
      const score=parseFloat(m[1]);
      if(!Number.isFinite(score)||score<4)return;
      // Highlight only the TOTAL score value, leaving the rest of the report unchanged.
      const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);
      let node;
      while((node=walker.nextNode())){
        const match=node.nodeValue.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);
        if(!match)continue;
        const full=match[0], value=match[1], start=node.nodeValue.indexOf(full);
        if(start<0)continue;
        const valueStart=start+full.lastIndexOf(value);
        const before=node.nodeValue.slice(0,valueStart), after=node.nodeValue.slice(valueStart+value.length);
        const frag=document.createDocumentFragment();
        frag.appendChild(document.createTextNode(before));
        const span=document.createElement('span');
        span.className='hc-score-value critical-score-alert';
        span.textContent=value;
        frag.appendChild(span);
        frag.appendChild(document.createTextNode(after));
        node.parentNode.replaceChild(frag,node);
        break;
      }
    });
  }
  function run(){markCriticalScores(document);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
  new MutationObserver(function(){run();}).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
})();
</script>
"""

try:
    html=index_path.read_text(encoding="utf-8")
    html=html.replace("HC Ectasia App v0.7.11","HC Ectasia App v0.7.12")
    # Replace the prior v0.7.11 injected blocks rather than stacking styles/scripts.
    import re
    # Use callable replacements so JavaScript backslashes (for example \\s)
    # are returned literally instead of being parsed as Python re.sub escapes.
    html=re.sub(r'<style id="hc-critical-score-style">.*?</style>',lambda _m: CSS.strip(),html,flags=re.S)
    html=re.sub(r'<script id="hc-critical-score-script">.*?</script>',lambda _m: SCRIPT.strip(),html,flags=re.S)
    if 'id="hc-critical-score-style"' not in html: html=html.replace("</head>",CSS+"\n</head>")
    if 'id="hc-critical-score-script"' not in html: html=html.replace("</body>",SCRIPT+"\n</body>")
    index_path.write_text(html,encoding="utf-8")
except OSError:
    pass

bootstrap.core.app.title="HC Ectasia App v0.7.12"
app=bootstrap.app
