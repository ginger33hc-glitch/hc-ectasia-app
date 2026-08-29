(() => {
  const rows = [
    ["Anterior topography", "Normal / symmetrical", "0"],
    ["Anterior topography", "Asymmetric bow-tie", "1"],
    ["Anterior topography", "Inferior steepening / significant SRA-SRAX", "3"],
    ["Anterior topography", "Abnormal ectatic pattern", "4"],
    ["Residual stromal bed", "≥300 µm", "0"],
    ["Residual stromal bed", "280–299 µm", "1"],
    ["Residual stromal bed", "260–279 µm", "2"],
    ["Residual stromal bed", "240–259 µm", "3"],
    ["Residual stromal bed", "<240 µm", "4"],
    ["Age", "18–21", "3"],
    ["Age", "22–25", "2"],
    ["Age", "26–29", "1"],
    ["Age", "≥30", "0"],
    ["Preop corneal thickness", "<450 µm", "4"],
    ["Preop corneal thickness", "451–480 µm", "3"],
    ["Preop corneal thickness", "481–510 µm", "2"],
    ["Preop corneal thickness", "≥510 µm", "0"],
    ["MRSE", "≤8 D myopia", "0"],
    ["MRSE", ">8–10 D", "1"],
    ["MRSE", ">10–12 D", "2"],
    ["MRSE", ">12–14 D", "3"],
    ["MRSE", ">14 D", "4"],
  ];
  const body = rows.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td></tr>`).join("");
  const html = `<section id="hcReferenceAppendix" class="hc-reference-appendix"><h3>HC BAD-D reference points</h3><table class="clinical-table"><thead><tr><th>Final BAD-D</th><th>HC interpretation / action</th></tr></thead><tbody><tr><td>≤ 1.6</td><td class="hc-bad-normal">NORMAL</td></tr><tr><td>&gt; 1.6 to &lt; 3.0</td><td class="hc-bad-suspicious">SUSPICIOUS — contextual finding; final decision follows the HC hierarchy</td></tr><tr><td>≥ 3.0</td><td class="hc-bad-abnormal">ABNORMAL CORNEA — DO NOT PROCEED</td></tr></tbody></table><h3>Published Randleman / ERSS scoring points</h3><table class="clinical-table"><thead><tr><th>Variable</th><th>Finding</th><th>Points</th></tr></thead><tbody>${body}</tbody></table><p class="note"><strong>Independent pathways:</strong> Randleman anterior-topography points come only from the anterior curvature/topography image; BAD/BAD-D is not used. On Pentacam 4 Maps Refractive the source is the upper-left Axial/Sagittal Curvature (Front) panel. Published ERSS total: 0–2 low, 3 moderate, ≥4 high.</p><p class="note"><strong>Active HC pachymetry policy:</strong> &lt;480 µm = hard stop; 480–499 µm = +2; 500–509 µm = +1; ≥510 µm = +0.</p><p class="note"><strong>HC modification:</strong> the active HC engine intentionally uses HC-modified age and pachymetry rules. The patient score must therefore be read from the HC score breakdown, not reconstructed from this published reference table.</p><p class="note"><strong>Inter-eye tomography:</strong> assessed automatically from bilateral categorical tomography findings. It is a non-scored contextual concern and does not independently change the HC disposition.</p></section>`;
  let queued = false;

  function installStaticPolicyUI() {
    document.title = "HC Ectasia App v0.7.47";
    const heading = document.querySelector("body > header h1");
    if (heading) heading.textContent = "HC Ectasia App v0.7.47";

    const manualInterEye = document.querySelector('input[name="patient_modifier"][value="inter_eye_asymmetry"]');
    if (manualInterEye) {
      const row = manualInterEye.closest("label.multi-option");
      if (row) row.remove();
      else manualInterEye.remove();
    }
  }

  function installReportEnhancements() {
    const eyes = document.getElementById("eye-results");
    const footer = document.querySelector("#reportSheet .report-footer-note");
    if (!eyes || !footer || !eyes.children.length) return;
    if (!document.getElementById("hcReferenceAppendix")) footer.insertAdjacentHTML("beforebegin", html);
    document.querySelectorAll(".status").forEach(element => {
      if ((element.textContent || "").trim() === "PASS WITH CAUTION") {
        element.classList.remove("caution", "review", "fail", "insufficient");
        element.classList.add("pass");
      }
    });
    document.querySelectorAll("tr").forEach(row => {
      const cells = row.querySelectorAll("td,th");
      if (cells.length && ["morphology category", "morphology"].includes((cells[0].textContent || "").trim().toLowerCase())) row.remove();
    });
  }

  function install() {
    installStaticPolicyUI();
    installReportEnhancements();
  }

  function queueInstall() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; install(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", queueInstall);
  else queueInstall();
  new MutationObserver(mutations => {
    if (mutations.some(mutation => mutation.addedNodes.length)) queueInstall();
  }).observe(document.documentElement, {childList: true, subtree: true});
})();
