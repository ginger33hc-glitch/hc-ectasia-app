"""UI patch: deterministic report highlighting and clinical reference appendix."""
from pathlib import Path
import hc_age_policy
import hc_bad_final_policy
import bootstrap
import extraction_guard
import erss_topography_guard
APP_VERSION="0.7.26"
APP_LABEL=f"HC Ectasia App v{APP_VERSION}"
index_path=Path(__file__).parent/"static"/"index.html"
CSS="""
<style id="hc-critical-score-style">
.critical-score-alert{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;border-radius:5px!important;padding:2px 6px!important;font-weight:900!important;display:inline-block!important}td.hc-critical-score-box,.hc-bad-abnormal{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;font-weight:900!important}td.hc-moderate-score-box,.hc-bad-suspicious{background:#fff1d6!important;color:#9a4d00!important;border:2px solid #e58a00!important;font-weight:900!important}.hc-bad-normal{background:#e6f4ea!important;color:#176b3a!important;border:1px solid #76a987!important;font-weight:800!important}.hc-reference-appendix{margin-top:24px;border-top:2px solid #8aa0b8;padding-top:16px}.hc-reference-appendix h3{margin:12px 0 6px;color:#173b57}.hc-reference-appendix .clinical-table{margin-bottom:14px}
</style>
"""
SCRIPT=r"""
<script id="hc-critical-score-script">
(function(){
 function setClass(el,names,wanted){names.forEach(n=>{if(n===wanted){el.classList.add(n)}else{el.classList.remove(n)}})}
 function appendix(){return `<section class="hc-reference-appendix" id="hcReferenceAppendix"><h3>HC BAD-D reference points</h3><table class="clinical-table"><thead><tr><th>Final BAD-D</th><th>HC interpretation / action</th></tr></thead><tbody><tr><td>≤ 1.6</td><td class="hc-bad-normal">NORMAL</td></tr><tr><td>&gt; 1.6 to &lt; 3.0</td><td class="hc-bad-suspicious">SUSPICIOUS — REVIEW / NOT CLEARED</td></tr><tr><td>≥ 3.0</td><td class="hc-bad-abnormal">ABNORMAL CORNEA — DO NOT PROCEED</td></tr></tbody></table><p class="note"><strong>BAD-D source:</strong> Pentacam BAD display. BAD-D is independent of Randleman/ERSS topography scoring.</p><h3>Randleman / ERSS scoring points</h3><table class="clinical-table"><thead><tr><th>Variable</th><th>Finding</th><th>Points</th></tr></thead><tbody><tr><td rowspan="4">Anterior topography</td><td>Normal / symmetrical</td><td>0</td></tr><tr><td>Asymmetric bow-tie</td><td>1</td></tr><tr><td>Inferior steepening / significant SRA-SRAX</td><td>3</td></tr><tr><td>Abnormal ectatic pattern</td><td>4</td></tr><tr><td rowspan="5">Residual stromal bed</td><td>≥300 µm</td><td>0</td></tr><tr><td>280–299 µm</td><td>1</td></tr><tr><td>260–279 µm</td><td>2</td></tr><tr><td>240–259 µm</td><td>3</td></tr><tr><td>&lt;240 µm</td><td>4</td></tr><tr><td rowspan="4">Age</td><td>18–21</td><td>3</td></tr><tr><td>22–25</td><td>2</td></tr><tr><td>26–29</td><td>1</td></tr><tr><td>≥30</td><td>0</td></tr><tr><td rowspan="4">Published ERSS CCT</td><td>&lt;450 µm</td><td>4</td></tr><tr><td>451–480 µm</td><td>3</td></tr><tr><td>481–510 µm</td><td>2</td></tr><tr><td>≥510 µm</td><td>0</td></tr><tr><td rowspan="5">MRSE</td><td>≤8 D myopia</td><td>0</td></tr><tr><td>&gt;8–10 D</td><td>1</td></tr><tr><td>&gt;10–12 D</td><td>2</td></tr><tr><td>&gt;12–14 D</td><td>3</td></tr><tr><td>&gt;14 D</td><td>4</td></tr></tbody></table><p class="note"><strong>Source separation:</strong> Randleman anterior-topography points may be generated only from a qualifying anterior curvature/topography image. BAD/Belin-Ambrosio, BAD-D, elevation-only displays and BAD components cannot generate a Randleman topography score.</p><p class="note"><strong>ERSS total:</strong> 0–2 low, 3 moderate, ≥4 high. HC-specific hard stops remain independent.</p></section>`}
 function mark(){document.querySelectorAll('tr').forEach(row=>{const c=row.querySelectorAll('th,td');if(c.length<2)return;const label=(c[0].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();if(label==='morphology category'){row.remove();return}if(label==='bad-d final'){const score=parseFloat(c[1].textContent);if(Number.isFinite(score)){const cls=score>=3?'hc-bad-abnormal':score>1.6?'hc-bad-suspicious':'hc-bad-normal';setClass(c[1],['hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal'],cls)}}});const sheet=document.querySelector('.report-sheet');const footer=sheet&&sheet.querySelector('.report-footer-note');const eyes=document.querySelector('#eye-results');if(sheet&&footer&&eyes&&eyes.children.length&&!document.querySelector('#hcReferenceAppendix'))footer.insertAdjacentHTML('beforebegin',appendix())}
 let scheduled=false;function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;mark()})}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',schedule);else schedule();new MutationObserver(ms=>{if(ms.some(m=>m.type==='childList'&&m.addedNodes.length))schedule()}).observe(document.documentElement,{childList:true,subtree:true});
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
