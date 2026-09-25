(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const numberOrNull = id => $(id).value === "" ? null : Number($(id).value);
  const setIfPresent = (id, value) => { if (value !== null && value !== undefined) $(id).value = value; };
  const originals = {OD:null, OS:null};
  const pentacamByEye = {OD:null, OS:null};
  const corneaBackByEye = {OD:null, OS:null};
  let pentacamEyeConfirmed = false;
  let recommendation = null;
  let lensCatalog = [];

  function clearSourceCase() {
    originals.OD = null; originals.OS = null;
    pentacamByEye.OD = null; pentacamByEye.OS = null;
    corneaBackByEye.OD = null; corneaBackByEye.OS = null;
    pentacamEyeConfirmed = false; recommendation = null;
    $("eye").value = "";
    for (const id of ["patientName", "patientAge", "al", "k1", "k1Axis", "k2", "k2Axis", "lensThickness", "hoa", "kappa", "alpha", "pupil3d", "cct", "wtw", "acd"]) {
      $(id).value = ""; $(id).readOnly = false;
    }
    $("result").hidden = true; $("powerSection").hidden = true;
    $("powerResult").replaceChildren(); $("alMarker").textContent = "";
    updateAstigmatism();
  }

  const errorMessage = data => typeof data.detail === "string" ? data.detail : "Required information is incomplete or invalid.";
  const kDifference = () => $("k1").value === "" || $("k2").value === "" ? NaN : Math.abs(Number($("k2").value) - Number($("k1").value));

  function updateAstigmatism() {
    const difference = kDifference();
    $("kDifference").value = Number.isFinite(difference) ? `${difference.toFixed(2)} D` : "";
    const required = difference >= 1;
    $("astigType").required = required;
    $("incisionField").hidden = !required;
    $("siaField").hidden = !required;
    $("siaAxisField").hidden = !required;
    $("incisionAxis").required = required;
    $("sia").required = required;
    if (required) {
      const steep = numberOrNull("k2Axis");
      $("incisionAxis").value = steep === null ? "" : steep;
      $("siaAxis").value = steep === null ? "" : steep;
      $("sia").value = "0.25";
    }
  }

  function populateEye() {
    const eye = $("eye").value;
    const bio = originals[eye];
    const pentacam = pentacamByEye[eye];
    if (bio) {
      setIfPresent("al", bio.axial_length_mm); setIfPresent("k1", bio.k1_d);
      setIfPresent("k1Axis", bio.k1_axis_deg); setIfPresent("k2", bio.k2_d);
      setIfPresent("k2Axis", bio.k2_axis_deg); setIfPresent("lensThickness", bio.lens_thickness_mm);
      if (!pentacam) setIfPresent("acd", bio.acd_mm);
      $("alMarker").textContent = bio.axial_length_edited_marker ? "IOLMaster printed an edited-value (*) marker; retained for visibility." : "";
      $("al").readOnly = bio.axial_length_mm !== null; $("k1Axis").readOnly = bio.k1_axis_deg !== null; $("k2Axis").readOnly = bio.k2_axis_deg !== null;
    }
    if (pentacam) {
      setIfPresent("hoa", pentacam.total_corneal_hoa_4mm_um); setIfPresent("kappa", pentacam.angle_kappa_mm);
      setIfPresent("alpha", pentacam.angle_alpha_mm); setIfPresent("pupil3d", pentacam.pupil_dia_3d_mm);
      setIfPresent("cct", pentacam.cct_pachy_vertex_um); setIfPresent("wtw", pentacam.hwtw_mm);
      setIfPresent("acd", pentacam.acd_internal_mm);
      $("cct").readOnly = pentacam.cct_pachy_vertex_um !== null; $("wtw").readOnly = pentacam.hwtw_mm !== null;
      $("acd").readOnly = pentacam.acd_internal_mm !== null;
    }
    updateAstigmatism();
  }

  $("surface").addEventListener("change", () => { $("stableField").hidden = $("surface").value !== "RESOLVED_AFTER_TREATMENT"; });
  $("priorSurgery").addEventListener("change", () => { $("historyField").hidden = !["MYOPIC_LASIK_PRK","HYPEROPIC_LASIK_PRK"].includes($("priorSurgery").value); });
  $("eye").addEventListener("change", populateEye); $("k1").addEventListener("input", updateAstigmatism); $("k2").addEventListener("input", updateAstigmatism); $("k2Axis").addEventListener("input", updateAstigmatism);
  $("sourceImages").addEventListener("change", () => {
    clearSourceCase();
    const files = [...$("sourceImages").files];
    $("selectedFiles").textContent = files.length ? `Selected images (${files.length}): ${files.map(file => file.name).join(", ")}` : "";
    $("extractStatus").textContent = ""; $("powerStatus").textContent = "";
  });

  $("extractButton").addEventListener("click", async () => {
    const files = [...$("sourceImages").files];
    const status = $("extractStatus"); status.className = "status";
    if (files.length !== 3) { status.textContent = "Select exactly three images: Pentacam Cataract Pre-Op, same-eye 4 Maps Refractive, and IOLMaster 500."; status.classList.add("error"); return; }
    const form = new FormData(); files.forEach(file => form.append("images", file));
    clearSourceCase();
    $("extractButton").disabled = true; status.textContent = "Transcribing source-locked fields…";
    try {
      const response = await fetch("/iol/extract", {method:"POST", body:form, credentials:"same-origin"});
      const data = await response.json(); if (!response.ok) throw new Error(errorMessage(data));
      const unreadable = [];
      const pentacamEyes = new Set();
      const expectedTypes = ["PENTACAM_CATARACT_PREOP", "PENTACAM_4_MAPS_REFRACTIVE", "IOLMASTER_500_BIOMETRY"];
      const typeCounts = Object.fromEntries(expectedTypes.map(type => [type, 0]));
      let unreadablePentacamLaterality = false;
      for (const source of data.sources || []) {
        const item = source.extraction || {}; setIfPresent("patientName", item.patient_name); setIfPresent("patientAge", item.patient_age_years);
        if (Object.hasOwn(typeCounts, item.document_type)) typeCounts[item.document_type]++;
        if (item.document_type === "PENTACAM_CATARACT_PREOP") {
          if (["OD","OS"].includes(item.eye)) { pentacamByEye[item.eye] = item.pentacam; pentacamEyes.add(item.eye); }
          else unreadablePentacamLaterality = true;
        }
        if (item.document_type === "PENTACAM_4_MAPS_REFRACTIVE" && ["OD","OS"].includes(item.eye)) {
          corneaBackByEye[item.eye] = item.cornea_back;
        }
        if (item.document_type === "IOLMASTER_500_BIOMETRY") {
          const report = item.iolmaster500 || {}; ["OD","OS"].forEach(eye => { if (report[eye] && report[eye].axial_length_mm !== null) originals[eye] = report[eye]; });
        }
        (item.unreadable_fields || []).forEach(field => unreadable.push(`${source.filename}: ${field}`));
      }
      if (expectedTypes.some(type => typeCounts[type] !== 1)) throw new Error("The three images must contain one Pentacam Cataract Pre-Op, one 4 Maps Refractive, and one IOLMaster 500 report. Check the selected files.");
      if (unreadablePentacamLaterality || pentacamEyes.size === 0) throw new Error("Pentacam laterality was not read. Upload a readable Pentacam Cataract Pre-Op report showing OD or OS.");
      if (pentacamEyes.size > 1) throw new Error("Conflicting Pentacam laterality was detected. Upload the Cataract Pre-Op report for one operative eye only.");
      $("eye").value = [...pentacamEyes][0];
      if (!corneaBackByEye[$("eye").value]) throw new Error("4 Maps Refractive Cornea Back could not be assigned to the operative eye.");
      pentacamEyeConfirmed = true;
      populateEye();
      status.textContent = unreadable.length ? `Extraction completed. Surgeon entry is required only for unreadable fields: ${unreadable.join(", ")}.` : "Three reports extracted. Review values before evaluation.";
    } catch (error) { status.textContent = error.message || "Image transcription failed."; status.classList.add("error"); }
    finally { $("extractButton").disabled = false; }
  });

  function populateLenses() {
    const eligible = new Set(recommendation.eligible_categories || []);
    const toric = recommendation.toric_evaluation_required;
    const options = lensCatalog.filter(lens => eligible.has(lens.category) && (!toric || lens.subtype?.toLowerCase().includes("toric")));
    $("selectedLens").innerHTML = `<option value="">Select an eligible lens</option>` + options.map(lens => `<option value="${lens.id}">${lens.name} — ${lens.category} — A ${lens.a_constant.toFixed(1)}</option>`).join("");
  }

  function escrsTransferPayload(data) {
    const inputs = data.inputs;
    return {
      biological_sex: inputs.biological_sex, eye: inputs.eye,
      axial_length_mm: inputs.axial_length_mm, acd_internal_mm: inputs.acd_internal_mm,
      k1_d: inputs.k1_d, k2_d: inputs.k2_d,
      cct_um: inputs.cct_um ?? null, lens_thickness_mm: inputs.lens_thickness_mm ?? null,
      wtw_mm: inputs.wtw_mm ?? null
    };
  }

  $("iolForm").addEventListener("submit", async event => {
    event.preventDefault(); const status = $("evaluationStatus"); status.className = "status";
    if (!pentacamEyeConfirmed) { status.textContent = "The operative eye must come from a readable Pentacam Cataract Pre-Op report."; status.classList.add("error"); return; }
    if (!event.currentTarget.reportValidity()) return;
    const eye = $("eye").value; const source = originals[eye];
    const originalK1 = source?.k1_d ?? Number($("k1").value); const originalK2 = source?.k2_d ?? Number($("k2").value);
    const payload = {
      patient_name: $("patientName").value, patient_age_years: Number($("patientAge").value), eye,
      near_demand: $("nearDemand").value, night_driving: $("nightDriving").value, halo_tolerance: $("haloTolerance").value,
      total_corneal_hoa_4mm_um: Number($("hoa").value), angle_kappa_mm: Number($("kappa").value), angle_alpha_mm: Number($("alpha").value), pentacam_pupil_3d_mm: Number($("pupil3d").value),
      iolm500_k1_d: originalK1, iolm500_k1_axis_deg: Number($("k1Axis").value), iolm500_k2_d: originalK2, iolm500_k2_axis_deg: Number($("k2Axis").value),
      iolm500_measurement_source: source ? "IOLMASTER_500_EXTRACTED" : "SURGEON_ENTERED_UNREADABLE",
      surgeon_k1_d: Number($("k1").value) === originalK1 ? null : Number($("k1").value), surgeon_k2_d: Number($("k2").value) === originalK2 ? null : Number($("k2").value),
      astigmatism_type: $("astigType").value || null, retina_status: $("retina").value, macular_pathology_present: $("macular").value === "true", glaucoma_status: $("glaucoma").value, ocular_surface_status: $("surface").value,
      post_treatment_measurements_stable: $("surface").value === "RESOLVED_AFTER_TREATMENT" ? $("stable").value === "true" : null
    };
    $("evaluateButton").disabled = true; status.textContent = "Applying canonical IOL rules…";
    try {
      const response = await fetch("/iol/evaluate", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(payload)});
      const data = await response.json(); if (!response.ok) throw new Error(errorMessage(data)); recommendation = data;
      $("recommendation").textContent = `Recommended IOL: ${data.formatted_recommendation}`;
      $("eligible").innerHTML = (data.eligible_categories || []).map(v => `<span class="pill">Eligible: ${v}</span>`).join("");
      $("warnings").innerHTML = (data.warning_codes || []).map(v => `<div class="warning">${v}</div>`).join("");
      $("reasons").replaceChildren(...(data.clinical_explanation || []).map(value => { const p=document.createElement("p"); p.className="reason"; p.textContent=value; return p; }));
      $("legal").textContent = data.legal_notice; $("result").hidden = false;
      if (!lensCatalog.length) { const lenses = await fetch("/iol/lenses", {credentials:"same-origin"}); const body = await lenses.json(); if (!lenses.ok) throw new Error(errorMessage(body)); lensCatalog = body.lenses || []; }
      populateLenses(); $("powerSection").hidden = false; updateAstigmatism(); status.textContent = "Recommendation generated. Select the lens for Stage 2."; $("result").scrollIntoView({behavior:"smooth"});
    } catch (error) { status.textContent = error.message || "Recommendation could not be generated."; status.classList.add("error"); }
    finally { $("evaluateButton").disabled = false; }
  });

  $("powerButton").addEventListener("click", async () => {
    const status = $("powerStatus"); status.className="status"; const difference = kDifference();
    const corneaBack = corneaBackByEye[$("eye").value];
    const posteriorFields = ["k1_d","k2_d","k1_axis_deg","k2_axis_deg","rh_mm","rv_mm"];
    const posteriorInput = corneaBack && posteriorFields.every(key => Number.isFinite(corneaBack[key])) ? {
      eye:$("eye").value, source:"PENTACAM_4_MAPS_REFRACTIVE_CORNEA_BACK",
      ...Object.fromEntries(posteriorFields.map(key => [key, corneaBack[key]]))
    } : null;
    const payload = {patient_name:$("patientName").value, biological_sex:$("biologicalSex").value, eye:$("eye").value, selected_lens_id:$("selectedLens").value,
      axial_length_mm:Number($("al").value), acd_mm:Number($("acd").value), k1_d:Number($("k1").value), k1_axis_deg:Number($("k1Axis").value), k2_d:Number($("k2").value), k2_axis_deg:Number($("k2Axis").value), astigmatism_type:$("astigType").value || null,
      prior_corneal_surgery:$("priorSurgery").value, historical_data_available:$("historicalData").value === "true", incision_axis_deg:difference>=1?numberOrNull("incisionAxis"):null, sia_d:difference>=1?numberOrNull("sia"):null, sia_axis_deg:difference>=1?numberOrNull("siaAxis"):null,
      cct_um:numberOrNull("cct"), lens_thickness_mm:numberOrNull("lensThickness"), wtw_mm:numberOrNull("wtw"), posterior_cornea:posteriorInput};
    if (!payload.selected_lens_id) { status.textContent="Select a clinic lens."; status.classList.add("error"); return; }
    $("powerButton").disabled=true; status.textContent="Determining the canonical calculation route…";
    try {
      const response=await fetch("/iol/power/plan",{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}); const data=await response.json(); if(!response.ok) throw new Error(errorMessage(data));
      let html=`<div class="warning"><strong>${data.calculator_name}</strong><br>${data.message}</div>`;
      html+=`<p><span>ACD target</span>: ${Number(data.target_refraction_d).toFixed(2)} D (<span>locked</span>)</p>`;
      if(data.second_formula_required) html+=`<div class="warning"><span>Second modern formula verification required</span> (AL ${Number(data.inputs.axial_length_mm).toFixed(2)} mm). <span>Use ESCRS where available and verify all values manually.</span></div>`;
      if(data.escrs_url) html+=`<button id="escrsTransfer" class="external" type="button">Transfer values to ESCRS</button>`;
      const toricRoute = data.route === "MANUFACTURER_TORIC";
      if(toricRoute && data.toric_candidates?.length) {
        const fmt = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "—";
        const candidates = data.toric_candidates.filter(c => /^[A-Z0-9]+$/.test(c.model));
        html += `<div class="warning"><strong>TEST ONLY — unvalidated toric optical prototype.</strong> Independently check the source readings, model availability, implantation axis, and residual with the manufacturer's calculator before any clinical use.</div>`;
        html += `<h3>Embedded toric calculation — ${fmt(candidates[0]?.spherical_equivalent_iol_d)} D K6 spherical equivalent</h3>`;
        html += `<div class="recommendation">${candidates[0]?.model ?? "—"} · ${fmt(candidates[0]?.marker_axis_deg, 1)}° marker axis</div>`;
        html += `<p>Predicted residual cylinder: ${fmt(candidates[0]?.residual_spectacle_cylinder_d)} D at ${fmt(candidates[0]?.residual_spectacle_axis_deg, 1)}° (prototype estimate).</p>`;
        html += `<div style="overflow-x:auto"><table class="table"><thead><tr><th>Model</th><th>IOL cylinder</th><th>Marker axis</th><th>Predicted residual cylinder</th></tr></thead><tbody>${candidates.map(c => `<tr><td>${c.model}</td><td>${fmt(c.cylinder_iol_d)} D</td><td>${fmt(c.marker_axis_deg, 1)}°</td><td>${fmt(c.residual_spectacle_cylinder_d)} D at ${fmt(c.residual_spectacle_axis_deg, 1)}°</td></tr>`).join("")}</tbody></table></div>`;
      } else if(toricRoute) html += `<div class="warning"><strong>No embedded toric model or axis available.</strong> ${data.toric_status === "INPUTS_INCOMPLETE" ? "Upload the same-eye Pentacam 4 Maps Refractive image and verify Pachy Vertex." : "Review source measurements and the selected lens family."}</div>`;
      if(data.predictions?.length){html+=`<h3>${toricRoute?"Stage 1 — Cooke K6 spherical power":"Cooke K6 power"}</h3><table class="table"><thead><tr><th>IOL power</th><th>Predicted refraction</th><th>Selection</th></tr></thead><tbody>${data.predictions.map(p=>`<tr><td>${Number(p.IOL ?? p.iol_power).toFixed(2)}</td><td>${Number(p.Rx ?? p.predicted_refraction).toFixed(2)}</td><td>${p.IsBestOption ? "K6 best option" : ""}</td></tr>`).join("")}</tbody></table>`;}
      if(data.calculator_url) html+=`<a class="external" target="_blank" rel="noopener noreferrer" href="${data.calculator_url}">Optional manufacturer toric calculator comparison</a>`;
      $("powerResult").innerHTML=html; status.textContent=data.calculation_status.replaceAll("_"," ");
      if(data.escrs_url) $("escrsTransfer").addEventListener("click", async () => {
        const button = $("escrsTransfer");
        const escrsWindow = window.open("about:blank", "_blank");
        if (escrsWindow) escrsWindow.opener = null;
        button.disabled = true; status.className = "status";
        status.textContent = "Creating a secure, de-identified ESCRS transfer…";
        try {
          const response = await fetch("/iol/escrs-transfer", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json"}, body:JSON.stringify(escrsTransferPayload(data))});
          const transfer = await response.json(); if(!response.ok) throw new Error(errorMessage(transfer));
          if (escrsWindow) escrsWindow.location.replace(transfer.escrs_url);
          else window.location.assign(transfer.escrs_url);
          status.textContent = "Biometry transferred to ESCRS. Verify every imported value before calculation.";
        } catch(error) {
          if (escrsWindow) escrsWindow.close();
          status.textContent = error.message || "ESCRS transfer could not be completed."; status.classList.add("error");
        } finally { button.disabled = false; }
      });
    } catch(error){status.textContent=error.message||"Power route could not be completed.";status.classList.add("error");}
    finally{$("powerButton").disabled=false;}
  });
  updateAstigmatism();
})();
