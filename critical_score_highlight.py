"""UI patch: color-code ERSS score, topography concern, and Final BAD-D gate."""
from pathlib import Path

import hc_age_policy
import hc_bad_final_policy
import bootstrap

APP_VERSION = "0.7.21"
APP_LABEL = f"HC Ectasia App v{APP_VERSION}"
index_path = Path(__file__).parent / "static" / "index.html"

CSS = """
<style id="hc-critical-score-style">
.critical-score-alert{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;border-radius:5px!important;padding:2px 6px!important;font-weight:900!important;display:inline-block!important}
.critical-score-alert::before{content:none!important}
td.hc-critical-score-box,.hc-bad-abnormal,.hc-topography-abnormal{background:#fde5e5!important;color:#a31212!important;border:2px solid #c52b2b!important;font-weight:900!important}
td.hc-moderate-score-box,.hc-bad-suspicious,.hc-topography-suspicious{background:#fff1d6!important;color:#9a4d00!important;border:2px solid #e58a00!important;font-weight:900!important}
.hc-bad-normal,.hc-topography-normal{background:#e6f4ea!important;color:#176b3a!important;border:1px solid #76a987!important;font-weight:800!important}
.hc-framework-reference{margin-top:18px;padding-top:14px;border-top:2px solid #d5d9df}.hc-framework-reference h3{margin:8px 0}.hc-framework-reference h4{margin:14px 0 6px}.hc-framework-note{font-size:.92em;line-height:1.45;background:#f7f8fa;border:1px solid #d5d9df;border-radius:6px;padding:10px 12px;margin-top:12px}.hc-framework-reference table{width:100%;border-collapse:collapse;margin:6px 0 12px}.hc-framework-reference th,.hc-framework-reference td{border:1px solid #d5d9df;padding:6px 8px;text-align:left;vertical-align:top}.hc-framework-reference th{font-weight:800}
@media print{.critical-score-alert,td.hc-critical-score-box,.hc-bad-abnormal,.hc-topography-abnormal{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fde5e5!important;color:#a31212!important;border-color:#c52b2b!important}td.hc-moderate-score-box,.hc-bad-suspicious,.hc-topography-suspicious{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#fff1d6!important;color:#9a4d00!important;border-color:#e58a00!important}.hc-bad-normal,.hc-topography-normal{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important;background:#e6f4ea!important;color:#176b3a!important;border-color:#76a987!important}.hc-framework-note{-webkit-print-color-adjust:exact!important;print-color-adjust:exact!important}}
</style>
"""

SCRIPT = r"""
<script id="hc-critical-score-script">
(function(){
  const referenceHTML=`<section id="hc-framework-reference" class="hc-framework-reference"><h3>HC scoring framework — reference</h3><h4>Final BAD-D evaluation</h4><table><thead><tr><th>Final BAD-D</th><th>HC interpretation</th><th>HC action</th></tr></thead><tbody><tr><td>≤1.6</td><td>NORMAL</td><td>Does not trigger the BAD-D gate</td></tr><tr><td>&gt;1.6 to &lt;3.0</td><td>SUSPICIOUS</td><td>REVIEW — NOT CLEARED</td></tr><tr><td>≥3.0</td><td>ABNORMAL CORNEA</td><td>DO NOT PROCEED — HC hard stop</td></tr></tbody></table><h4>HC-modified Randleman / ERSS scoring used by this application (LASIK)</h4><table><thead><tr><th>Parameter</th><th>Finding</th><th>Points / action</th></tr></thead><tbody><tr><td rowspan="4">Anterior topography</td><td>Normal / symmetric</td><td>0</td></tr><tr><td>Asymmetric bow-tie — suspicious</td><td>1</td></tr><tr><td>Inferior steepening / significant SRA-SRAX — suspicious</td><td>3</td></tr><tr><td>Abnormal ectatic topographic pattern</td><td>4</td></tr><tr><td rowspan="5">LASIK residual stromal bed</td><td>≥300 µm</td><td>0</td></tr><tr><td>280–&lt;300 µm</td><td>1; HC RSB hard stop also applies below 300 µm</td></tr><tr><td>260–&lt;280 µm</td><td>2; HC hard stop</td></tr><tr><td>240–&lt;260 µm</td><td>3; HC hard stop</td></tr><tr><td>&lt;240 µm</td><td>4; HC hard stop</td></tr><tr><td rowspan="3">Age — HC modified</td><td>18 years</td><td>3</td></tr><tr><td>19–20 years</td><td>2</td></tr><tr><td>≥21 years</td><td>0</td></tr><tr><td rowspan="4">Thinnest pachymetry — HC modified</td><td>≤480 µm</td><td>DO NOT PROCEED — HC hard stop</td></tr><tr><td>481–499 µm</td><td>2</td></tr><tr><td>500–510 µm</td><td>1</td></tr><tr><td>≥511 µm</td><td>0</td></tr><tr><td rowspan="5">Manifest MRSE</td><td>≥−8.00 D</td><td>0</td></tr><tr><td>&lt;−8 to −10 D</td><td>1</td></tr><tr><td>&lt;−10 to −12 D</td><td>2</td></tr><tr><td>&lt;−12 to −14 D</td><td>3</td></tr><tr><td>&lt;−14 D</td><td>4</td></tr></tbody></table><div class="hc-framework-note"><strong>Interpretation note.</strong> Randleman/ERSS anterior topography and Pentacam Final BAD-D are independent pathways. Suspicious anterior topography is highlighted orange. Final BAD-D ≥3.0 defines the cornea as ABNORMAL under the HC BAD-D gate, is highlighted red, and is a DO NOT PROCEED hard stop. Df, Db, Dp, Dt and Da remain contextual component indices and do not independently determine BAD-D clearance. Age and pachymetry bands shown above are HC protocol modifications.</div></section>`;
  function setClass(el,names,wanted){names.forEach(n=>{if(n===wanted){if(!el.classList.contains(n))el.classList.add(n)}else if(el.classList.contains(n))el.classList.remove(n)});}
  function markClinicalSignals(root){
    const scope=root&&root.querySelectorAll?root:document;
    scope.querySelectorAll('tr').forEach(function(row){
      const cells=row.querySelectorAll('th,td');if(cells.length<2)return;
      const label=(cells[0].textContent||'').replace(/\s+/g,' ').trim().toLowerCase();
      if(label==='morphology category'){row.remove();return;}
      if(label==='score / category'||label==='score/category'){const result=cells[1],m=(result.textContent||'').trim().match(/^\s*([0-9]+(?:\.[0-9]+)?)/);let wanted='';if(m){const score=parseFloat(m[1]);if(Number.isFinite(score)){if(score>=4)wanted='hc-critical-score-box';else if(score===3)wanted='hc-moderate-score-box';}}setClass(result,['hc-critical-score-box','hc-moderate-score-box'],wanted);}
      if(label==='bad-d final'){const result=cells[1],score=parseFloat((result.textContent||'').trim());if(Number.isFinite(score)){const wanted=score>=3?'hc-bad-abnormal':score>1.6?'hc-bad-suspicious':'hc-bad-normal';setClass(result,['hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal'],wanted);const desired=score.toFixed(2)+(score>=3?' — ABNORMAL':score>1.6?' — SUSPICIOUS':' — NORMAL');if(result.textContent!==desired)result.textContent=desired;}}
      if(label==='tomography review'){const result=cells[1],t=(result.textContent||'').toUpperCase(),wanted=/\bABNORMAL\b/.test(t)?'hc-bad-abnormal':/\bSUSPICIOUS\b|\bBORDERLINE\b/.test(t)?'hc-bad-suspicious':/\bNORMAL\b|\bREASSURING\b/.test(t)?'hc-bad-normal':'';setClass(result,['hc-bad-normal','hc-bad-suspicious','hc-bad-abnormal'],wanted);}
      if(label==='morphology'||label==='anterior pattern'){const result=cells[1],t=(result.textContent||'').toUpperCase(),wanted=/ABNORMAL|ECTATIC|KERATOCONUS|PELLUCID|FFKC/.test(t)?'hc-topography-abnormal':/SUSPICIOUS|BORDERLINE|ASYMMETRIC|INFERIOR_STEEPENING|SRA|SRAX/.test(t)?'hc-topography-suspicious':/NORMAL|SYMMETRIC/.test(t)?'hc-topography-normal':'';setClass(result,['hc-topography-normal','hc-topography-suspicious','hc-topography-abnormal'],wanted);}
    });
    const eyeResults=document.querySelector('#eyeResults');if(eyeResults&&eyeResults.children.length&&!document.querySelector('#hc-framework-reference'))eyeResults.insertAdjacentHTML('afterend',referenceHTML);
    const nodes=scope.querySelectorAll('li,p,div,td,span');nodes.forEach(function(el){if(el.querySelector&&el.querySelector('.hc-score-value'))return;const text=(el.textContent||'').trim();if(!text.includes('HC SCORE — SOURCE & BREAKDOWN'))return;const m=text.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);if(!m)return;const score=parseFloat(m[1]);if(!Number.isFinite(score)||score<4)return;const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode())){const match=node.nodeValue.match(/TOTAL:\s*([0-9]+(?:\.[0-9]+)?)/i);if(!match)continue;const full=match[0],value=match[1],start=node.nodeValue.indexOf(full);if(start<0)continue;const valueStart=start+full.lastIndexOf(value),before=node.nodeValue.slice(0,valueStart),after=node.nodeValue.slice(valueStart+value.length),frag=document.createDocumentFragment();frag.appendChild(document.createTextNode(before));const span=document.createElement('span');span.className='hc-score-value critical-score-alert';span.textContent=value;frag.appendChild(span);frag.appendChild(document.createTextNode(after));node.parentNode.replaceChild(frag,node);break;}});
  }
  let scheduled=false;function scheduleRun(){if(scheduled)return;scheduled=true;requestAnimationFrame(function(){scheduled=false;markClinicalSignals(document);});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',scheduleRun);else scheduleRun();
  new MutationObserver(function(mutations){if(mutations.some(m=>m.type==='childList'&&m.addedNodes.length))scheduleRun();}).observe(document.documentElement,{childList:true,subtree:true});
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
    if 'id="hc-critical-score-style"' not in html:html=html.replace("</head>",CSS+"\n</head>")
    if 'id="hc-critical-score-script"' not in html:html=html.replace("</body>",SCRIPT+"\n</body>")
    index_path.write_text(html,encoding="utf-8")
except OSError:pass
bootstrap.core.APP_VERSION=APP_VERSION
bootstrap.core.app.title=APP_LABEL
app=bootstrap.app
