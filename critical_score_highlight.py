"""UI patch: highlight HC score 3 orange and critical scores (>=4) red."""
from pathlib import Path

import bootstrap

index_path = Path(__file__).parent / "static" / "index.html"

CSS = """
<style id="hc-critical-score-style">
.critical-score-alert{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;border-radius:5px!important;padding:2px 6px!important;font-weight:900!important;display:inline-block!important}
.critical-score-alert::before{content:none!important}
td.hc-critical-score-box{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;font-weight:900!important}
td.hc-moderate-score-box{background:#fff1d6!important;color:#9a4d00!important;border:2px solid #e58a00!important;font-weight:900!important}
@media print{.critical-score-alert,td.hc-critical-score-box{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fde5e5!important;color:#a31212!important;border-color:#c52b2b!important}td.hc-moderate-score-box{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fff1d6!important;color:#9a4d00!important;border-color:#e58a00!important}}
</style>
"""

SCRIPT = r"""
<script id="hc-critical-score-script">
(function(){
  function markCriticalScores(root){
    const scope=root&&root.querySelectorAll?root:document;

    // ERSS score/category table: score 3 = moderate (orange); >=4 = high (red).
    scope.querySelectorAll('tr').forEach(function(row){
      const cells=row.querySelectorAll('th,td');
      if(cells.length<2)return;
      const label=(cells[0].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
      if(label!=='score / category' && label!=='score/category')return;
      const result=cells[1];
      const m=(result.textContent||'').trim().match(/^\s*([0-9]+(?:\.[0-9]+)?)/);
      result.classList.remove('hc-critical-score-box','hc-moderate-score-box');
      if(!m)return;
      const score=parseFloat(m[1]);
      if(!Number.isFinite(score))return;
      if(score>=4)result.classList.add('hc-critical-score-box');
      else if(score===3)result.classList.add('hc-moderate-score-box');
    });

    // Keep the detailed HC SCORE TOTAL numeric value highlighted red for >=4.
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
    html=html.replace("HC Ectasia App v0.7.11","HC Ectasia App v0.7.14")
    html=html.replace("HC Ectasia App v0.7.12","HC Ectasia App v0.7.14")
    html=html.replace("HC Ectasia App v0.7.13","HC Ectasia App v0.7.14")
    import re
    # Callable replacements preserve JavaScript backslashes literally.
    html=re.sub(r'<style id="hc-critical-score-style">.*?</style>',lambda _m: CSS.strip(),html,flags=re.S)
    html=re.sub(r'<script id="hc-critical-score-script">.*?</script>',lambda _m: SCRIPT.strip(),html,flags=re.S)
    if 'id="hc-critical-score-style"' not in html: html=html.replace("</head>",CSS+"\n</head>")
    if 'id="hc-critical-score-script"' not in html: html=html.replace("</body>",SCRIPT+"\n</body>")
    index_path.write_text(html,encoding="utf-8")
except OSError:
    pass

bootstrap.core.app.title="HC Ectasia App v0.7.14"
app=bootstrap.app
