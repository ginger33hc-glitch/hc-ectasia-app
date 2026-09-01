(() => {
  const topographyRows = [
    ["Normal / symmetric", "Normal or symmetric map", "0"],
    ["Asymmetric bow-tie", "Mild asymmetric bow-tie: >0.5 D and <1.0 D, with no SRA/SRAX", "1"],
    ["Inferior steepening / SRA", "Inferior point ≥1.0 D steeper than the matching superior point with I-S <1.4 D, or SRAX ≥20°", "3"],
    ["Abnormal / ectatic", "Abnormal or ectatic pattern, or I-S ≥1.4 D", "4"],
  ];
  const activeErssRows = [
    ["Anterior topography", "Use the category table above", "0 / 1 / 3 / 4"],
    ["Residual stromal bed", "<240 / 240–259 / 260–279 / 280–299 / ≥300 µm", "4 / 3 / 2 / 1 / 0"],
    ["Age — active CER-AI policy", "18 / 19–20 / ≥21 years", "3 / 2 / 0"],
    ["Preop corneal thickness — active CER-AI policy", "<480 / 480–499 / 500–509 / ≥510 µm", "Hard stop / 2 / 1 / 0"],
    ["Manifest MRSE", "<−14 / −14–<−12 / −12–<−10 / −10–<−8 / ≥−8 D", "4 / 3 / 2 / 1 / 0"],
  ];

  const tableBody = rows => rows.map(row => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td></tr>`).join("");
  const topographyReferenceHtml = () => `<section class="erss-reference" aria-label="Randleman anterior topography reference guide"><h4>Randleman topography assessment</h4><p>CER-AI evaluates only the upper-left Axial/Sagittal Curvature (Front) map on the Pentacam 4 Maps Refractive page.</p><table><thead><tr><th>Category</th><th>What to look for</th><th>ERSS points</th></tr></thead><tbody>${tableBody(topographyRows)}</tbody></table><p class="reference-warning">If CER-AI cannot read the complete map with HIGH confidence, it asks the surgeon to choose the category. It never guesses a number. Only the highest applicable single category is scored; categories are not added.</p><p class="note">Superior steepening alone is not automatically assigned 3 points and requires surgeon review. BAD-D and other tomography indices are not substituted for Randleman topography.</p><p class="note">Source: <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC3748728/" target="_blank" rel="noopener">Randleman et al., 2008 validation study</a>.</p></section>`;
  const reportReferenceHtml = () => `<section id="hcReferenceAppendix" class="hc-reference-appendix"><h3>CER-AI BAD-D reference points</h3><table class="clinical-table"><thead><tr><th>Final BAD-D</th><th>CER-AI interpretation / action</th></tr></thead><tbody><tr><td>≤ 1.6</td><td class="hc-bad-normal">NORMAL</td></tr><tr><td>&gt; 1.6 to &lt; 2.60</td><td class="hc-bad-suspicious">SUSPICIOUS — contextual finding; final decision follows the CER-AI hierarchy</td></tr><tr><td>≥ 2.60</td><td class="hc-bad-abnormal">ABNORMAL CORNEA — DO NOT PROCEED</td></tr></tbody></table>${topographyReferenceHtml()}<h3>Active CER-AI Randleman / ERSS points</h3><table class="clinical-table"><thead><tr><th>Variable</th><th>Finding</th><th>Points</th></tr></thead><tbody>${tableBody(activeErssRows)}</tbody></table><p class="note">Randleman/ERSS is calculated from five independent LASIK inputs. BAD-D and NICE remain separate pathways. Overall ERSS: 0–2 low, 3 moderate, ≥4 high; CER-AI does not clear totals ≥3.</p></section>`;
  let queued = false;

  function installStaticPolicyUI() {
    document.title = "CER-AI v0.7.61";
    const heading = document.querySelector("body > header h1");
    if (heading) heading.textContent = "CER-AI v0.7.61";

    document.querySelectorAll('[data-erss-reference="surgeon"]').forEach(container => {
      if (!container.children.length) container.innerHTML = topographyReferenceHtml();
      window.CERAI_I18N?.translateDOM(container);
    });

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
    if (!document.getElementById("hcReferenceAppendix")) footer.insertAdjacentHTML("beforebegin", reportReferenceHtml());
    window.CERAI_I18N?.translateDOM(document.getElementById("hcReferenceAppendix"));
    document.querySelectorAll(".status").forEach(element => {
      if (["PASS WITH CAUTION", "DİKKATLE UYGUN"].includes((element.textContent || "").trim())) {
        element.classList.remove("caution", "review", "fail", "insufficient");
        element.classList.add("pass");
      }
    });
    document.querySelectorAll("tr").forEach(row => {
      const cells = row.querySelectorAll("td,th");
      if (cells.length && ["morphology category", "morphology", "morfoloji kategorisi", "morfoloji"].includes((cells[0].textContent || "").trim().toLowerCase())) row.remove();
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
