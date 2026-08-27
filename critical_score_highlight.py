"""UI patch: color-code ERSS score and Final BAD-D decision gate."""
from pathlib import Path

import hc_age_policy
import hc_bad_final_policy
import bootstrap

APP_VERSION = "0.7.18"
APP_LABEL = f"HC Ectasia App v{APP_VERSION}"
index_path = Path(__file__).parent / "static" / "index.html"

CSS = """
<style id="hc-critical-score-style">
.critical-score-alert{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;border-radius:5px!important;padding:2px 6px!important;font-weight:900!important;display:inline-block!important}
.critical-score-alert::before{content:none!important}
td.hc-critical-score-box,.hc-bad-abnormal{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;font-weight:900!important}
td.hc-moderate-score-box,.hc-bad-suspicious{background:#fff1d6!important;color:#9a4d00!important;border:2px solid #e58a00!important;font-weight:900!important}
.hc-bad-normal{background:#e6f4ea!important;color:#176b3a!important;border:1px solid #76a987!important;font-weight:800!important}
@media print{.critical-score-alert,td.hc-critical-score-box,.hc-bad-abnormal{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fde5e5!important;color:#a31212!important;border-color:#c52b2b!important}td.hc-moderate-score-box,.hc-bad-suspicious{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fff1d6!important;color:#9a4d00!important;border-color:#e58a00!important}.hc-bad-normal{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#e6f4ea!important;color:#176b3a!important;border-color:#76a987!important}}
</style>
"""

SCRIPT = r"""
<script id="hc-critical-score-script">
(function(){
  function markClinicalSignals(root){
    const scope=root&&root.querySelectorAll?root:document;
    scope.querySelectorAll('tr').forEach(function(row){
      const cells=row.querySelectorAll('th,td');
      if(cells.length<2)return;
      const label=(cells[0].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
      if(label==='morphology category'){row.remove();return;}
      if(label==='score / category' || label==='score/category'){
        const result=cells[1],m=(result.textContent||'').trim().match(/^\s*([0-9]+(?:\.[0-9]+)?)/);
        result.classList.remove('hc-critical-score-box','hc-moderate-score-box');
        if(m){const score=parseFloat(m[1]);if(Number.isFinite(score)){if(score>=4)result.classList.add('hc-critical-score-box');else if(score===3)result.classList.add('hc-moderate-score-box');}}
      }
      // Final BAD-D is the HC BAD decision gate. Individual D components remain
      // visible but are not independently color-coded as decision makers.
      if(label==='bad-d final'){
        const result=cells[1],score=parseFloat((result.textContent||'').trim());
        result.classList.remove('hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal');
        if(Number.isFinite(score)){if(score>=3.0)result.classList.add('hc-bad-abnormal');else if(score>1.6)result.classList.add('hc-bad-suspicious');else result.classList.add('hc-bad-normal');}
      }
      if(label==='tomography review'){
        const result=cells[1],t=(result.textContent||'').toUpperCase();
        result.classList.remove('hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal');
        if(/\bABNORMAL\b/.test(t))result.classList.add('hc-bad-abnormal');else if(/\bSUSPICIOUS\b|\bBORDERLINE\b/.test(t))result.classList.add('hc-bad-suspicious');else if(/\bNORMAL\b|\bREASSURING\b/.test(t))result.classList.add('hc-bad-normal');
      }
    });
    scope.querySelectorAll('.critical-score-alert').forEach(function(el){if(!el.classList.contains('hc-score-value'))el.classList.remove('critical-score-alert');});
    const nodes=scope.querySelectorAll('li, p, div, td, span');
    nodes.forEach(function(el){if(el.querySelector&&el.querySelector('.hc-score-value'))return;const text=(el.textContent||'').trim();if(!text.includes('HC SCORE — SOURCE & BREAKDOWN'))return;const m=text.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);if(!m)return;const score=parseFloat(m[1]);if(!Number.isFinite(score)||score<4)return;const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode())){const match=node.nodeValue.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);if(!match)continue;const full=match[0],value=match[1],start=node.nodeValue.indexOf(full);if(start<0)continue;const valueStart=start+full.lastIndexOf(value);const before=node.nodeValue.slice(0,valueStart),after=node.nodeValue.slice(valueStart+value.length);const frag=document.createDocumentFragment();frag.appendChild(document.createTextNode(before));const span=document.createElement('span');span.className='hc-score-value critical-score-alert';span.textContent=value;frag.appendChild(span);frag.appendChild(document.createTextNode(after));node.parentNode.replaceChild(frag,node);break;}});
  }
  function run(){markClinicalSignals(document);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',run);else run();
  new MutationObserver(function(){run();}).observe(document.documentElement,{childList:true,subtree:true,characterData:true});
})();
</script>
"""

try:
    import re
    html=index_path.read_text(encoding="utf-8")
    html=re.sub(r'HC Ectasia App v\d+\.\d+\.\d+',APP_LABEL,html)
    html=re.sub(r'Software v\d+\.\d+\.\d+',f'Software v{APP_VERSION}',html)
    html=re.sub(r'<style id="hc-critical-score-style">.*?</style>',lambda _m: CSS.strip(),html,flags=re.S)
    html=re.sub(r'<script id="hc-critical-score-script">.*?</script>',lambda _m: SCRIPT.strip(),html,flags=re.S)
    if 'id="hc-critical-score-style"' not in html: html=html.replace("</head>",CSS+"\n</head>")
    if 'id="hc-critical-score-script"' not in html: html=html.replace("</body>",SCRIPT+"\n</body>")
    index_path.write_text(html,encoding="utf-8")
except OSError:
    pass

bootstrap.core.APP_VERSION = APP_VERSION
bootstrap.core.app.title = APP_LABEL
app=bootstrap.app
