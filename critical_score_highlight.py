"""UI patch: deterministic final-report topography and Final BAD-D highlighting."""
from pathlib import Path
import hc_age_policy
import hc_bad_final_policy
import bootstrap
import extraction_guard
APP_VERSION="0.7.23"
APP_LABEL=f"HC Ectasia App v{APP_VERSION}"
index_path=Path(__file__).parent/"static"/"index.html"
CSS="""
<style id="hc-critical-score-style">
.critical-score-alert{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;border-radius:5px!important;padding:2px 6px!important;font-weight:900!important;display:inline-block!important}.critical-score-alert::before{content:none!important}
td.hc-critical-score-box,.hc-bad-abnormal,.hc-topography-abnormal{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;font-weight:900!important}td.hc-moderate-score-box,.hc-bad-suspicious,.hc-topography-suspicious{background:#fff1d6!important;color:#9a4d00!important;border:2px solid #e58a00!important;font-weight:900!important}.hc-bad-normal,.hc-topography-normal{background:#e6f4ea!important;color:#176b3a!important;border:1px solid #76a987!important;font-weight:800!important}
@media print{.hc-bad-abnormal,.hc-topography-abnormal,td.hc-critical-score-box{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fde5e5!important;color:#a31212!important}.hc-bad-suspicious,.hc-topography-suspicious,td.hc-moderate-score-box{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fff1d6!important;color:#9a4d00!important}.hc-bad-normal,.hc-topography-normal{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#e6f4ea!important;color:#176b3a!important}}
</style>
"""
SCRIPT=r"""
<script id="hc-critical-score-script">
(function(){
 function setClass(el,names,wanted){names.forEach(n=>{if(n===wanted){if(!el.classList.contains(n))el.classList.add(n)}else if(el.classList.contains(n))el.classList.remove(n)});}
 function topographyInterpret(raw){const t=String(raw||'').toUpperCase();if(/ABNORMAL|ECTATIC|KERATOCONUS|PELLUCID|FFKC/.test(t))return['ABNORMAL','hc-topography-abnormal'];if(/ASYMMETRIC|INFERIOR_STEEPENING|INFERIOR STEEPENING|SRA|SRAX|SUSPICIOUS|BORDERLINE/.test(t))return['SUSPICIOUS','hc-topography-suspicious'];if(/NORMAL|SYMMETRIC/.test(t))return['NORMAL','hc-topography-normal'];return['NOT ASSESSED',''];}
 function mark(root){const scope=root&&root.querySelectorAll?root:document;scope.querySelectorAll('tr').forEach(row=>{const c=row.querySelectorAll('th,td');if(c.length<2)return;let label=(c[0].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
  if(label==='morphology category'){const interpreted=topographyInterpret(c[1].textContent);if(c[0].textContent!=='Topography assessment')c[0].textContent='Topography assessment';if(c[1].textContent!==interpreted[0])c[1].textContent=interpreted[0];setClass(c[1],['hc-topography-normal','hc-topography-suspicious','hc-topography-abnormal'],interpreted[1]);return;}
  if(label==='morphology'||label==='anterior pattern'){const interpreted=topographyInterpret(c[1].textContent);setClass(c[1],['hc-topography-normal','hc-topography-suspicious','hc-topography-abnormal'],interpreted[1]);}
  if(label==='bad-d final'){const score=parseFloat(c[1].textContent);if(Number.isFinite(score)){const cls=score>=3?'hc-bad-abnormal':score>1.6?'hc-bad-suspicious':'hc-bad-normal',word=score>=3?'ABNORMAL':score>1.6?'SUSPICIOUS':'NORMAL',desired=score.toFixed(2)+' — '+word;setClass(c[1],['hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal'],cls);if(c[1].textContent!==desired)c[1].textContent=desired;}}
  if(label==='tomography review'){const t=(c[1].textContent||'').toUpperCase(),cls=/ABNORMAL/.test(t)?'hc-bad-abnormal':/SUSPICIOUS|BORDERLINE/.test(t)?'hc-bad-suspicious':/NORMAL|REASSURING/.test(t)?'hc-bad-normal':'';setClass(c[1],['hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal'],cls);}
  if(label==='score / category'||label==='score/category'){const m=(c[1].textContent||'').match(/^\s*(\d+(?:\.\d+)?)/),score=m?parseFloat(m[1]):NaN,cls=score>=4?'hc-critical-score-box':score===3?'hc-moderate-score-box':'';setClass(c[1],['hc-critical-score-box','hc-moderate-score-box'],cls);}
 });}
 let scheduled=false;function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;mark(document)});}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();new MutationObserver(ms=>{if(ms.some(m=>m.type==='childList'&&m.addedNodes.length))schedule();}).observe(document.documentElement,{childList:true,subtree:true});
})();
</script>
"""
try:
 import re
 html=index_path.read_text(encoding="utf-8")
 html=re.sub(r'HC Ectasia App v\d+\.\d+\.\d+',APP_LABEL,html)
 html=re.sub(r'Software v\d+\.\d+\.\d+',f'Software v{APP_VERSION}',html)
 html=re.sub(r'<style id="hc-critical-score-style">.*?</style>',lambda _m:CSS.strip(),html,flags=re.S)
 html=re.sub(r'<script id="hc-critical-score-script">.*?</script>',lambda _m:SCRIPT.strip(),html,flags=re.S)
 if 'id="hc-critical-score-style"' not in html:html=html.replace('</head>',CSS+'\n</head>')
 if 'id="hc-critical-score-script"' not in html:html=html.replace('</body>',SCRIPT+'\n</body>')
 index_path.write_text(html,encoding='utf-8')
except OSError:pass
bootstrap.core.APP_VERSION=APP_VERSION
bootstrap.core.app.title=APP_LABEL
app=bootstrap.app
