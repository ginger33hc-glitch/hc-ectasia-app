(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const numberOrNull = id => $(id).value === "" ? null : Number($(id).value);
  const setIfPresent = (id, value) => { if (value !== null && value !== undefined) $(id).value = value; };

  $("surface").addEventListener("change", () => {
    $("stableField").hidden = $("surface").value !== "RESOLVED_AFTER_TREATMENT";
  });

  $("tcrpAstig").addEventListener("input", () => {
    const required = Number($("tcrpAstig").value) >= 1;
    $("tcrpAxis").required = required;
    $("astigType").required = required;
  });

  $("extractButton").addEventListener("click", async () => {
    const pentacam = [...$("pentacamImages").files];
    const status = $("extractStatus");
    status.className = "status";
    if (!pentacam.length) {
      status.textContent = "Upload at least one Pentacam Cataract Pre-Op image.";
      status.classList.add("error");
      return;
    }
    const data = new FormData();
    pentacam.forEach(file => data.append("images", file));
    $("extractButton").disabled = true;
    status.textContent = "Transcribing approved fields…";
    try {
      const response = await fetch("/iol/extract", {method:"POST", body:data, credentials:"same-origin"});
      if (!response.ok) throw new Error((await response.json()).detail || "Image transcription failed.");
      const payload = await response.json();
      const unreadable = [];
      for (const source of payload.sources || []) {
        const item = source.extraction || {};
        setIfPresent("patientName", item.patient_name);
        setIfPresent("patientAge", item.patient_age_years);
        setIfPresent("eye", item.eye === "UNKNOWN" ? null : item.eye);
        if (item.document_type === "PENTACAM_CATARACT_PREOP") {
          const p = item.pentacam || {};
          setIfPresent("hoa", p.total_corneal_hoa_4mm_um);
          setIfPresent("kappa", p.angle_kappa_mm); setIfPresent("alpha", p.angle_alpha_mm);
          setIfPresent("pupil3d", p.pupil_dia_3d_mm); setIfPresent("tcrpAstig", p.tcrp_astigmatism_d);
          setIfPresent("tcrpAxis", p.tcrp_k2_axis_deg);
        }
        (item.unreadable_fields || []).forEach(field => unreadable.push(`${source.filename}: ${field}`));
      }
      status.textContent = unreadable.length
        ? `Transcription completed. Enter unreadable required values manually: ${unreadable.join(", ")}.`
        : "Pentacam transcription completed. Review the extracted values before evaluation.";
      $("tcrpAstig").dispatchEvent(new Event("input"));
    } catch (error) {
      status.textContent = error.message || "Image transcription failed.";
      status.classList.add("error");
    } finally { $("extractButton").disabled = false; }
  });

  $("iolForm").addEventListener("submit", async event => {
    event.preventDefault();
    const status = $("evaluationStatus");
    status.className = "status";
    if (!event.currentTarget.reportValidity()) return;
    const payload = {
      patient_name: $("patientName").value,
      patient_age_years: Number($("patientAge").value), eye: $("eye").value,
      near_demand: $("nearDemand").value, night_driving: $("nightDriving").value,
      halo_tolerance: $("haloTolerance").value,
      total_corneal_hoa_4mm_um: Number($("hoa").value),
      angle_kappa_mm: Number($("kappa").value), angle_alpha_mm: Number($("alpha").value),
      pentacam_pupil_3d_mm: Number($("pupil3d").value),
      tcrp_astigmatism_d: Number($("tcrpAstig").value),
      tcrp_steep_axis_deg: numberOrNull("tcrpAxis"), astigmatism_type: $("astigType").value || null,
      retina_status: $("retina").value, macular_pathology_present: $("macular").value === "true",
      glaucoma_status: $("glaucoma").value, ocular_surface_status: $("surface").value,
      post_treatment_measurements_stable: $("surface").value === "RESOLVED_AFTER_TREATMENT" ? $("stable").value === "true" : null
    };
    $("evaluateButton").disabled = true; status.textContent = "Applying canonical IOL rules…";
    try {
      const response = await fetch("/iol/evaluate", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Required information is incomplete or invalid.");
      $("recommendation").textContent = `Recommended IOL: ${data.formatted_recommendation}`;
      $("eligible").innerHTML = (data.eligible_categories || []).map(value => `<span class="pill">Eligible: ${value}</span>`).join("");
      $("warnings").innerHTML = (data.warning_codes || []).map(value => `<div class="warning">${value}</div>`).join("");
      $("reasons").innerHTML = (data.clinical_explanation || []).map(value => `<p class="reason"></p>`).join("");
      [...$("reasons").children].forEach((node, index) => { node.textContent = data.clinical_explanation[index]; });
      $("legal").textContent = data.legal_notice; $("result").hidden = false;
      $("result").scrollIntoView({behavior:"smooth", block:"start"}); status.textContent = "Recommendation generated.";
    } catch (error) { status.textContent = error.message || "Recommendation could not be generated."; status.classList.add("error"); }
    finally { $("evaluateButton").disabled = false; }
  });
})();
