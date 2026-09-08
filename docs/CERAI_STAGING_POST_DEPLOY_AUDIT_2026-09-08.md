# CER-AI staging deployment and 66-item re-audit — 8 September 2026

## Outcome and scope

Staging deployed successfully. Production was not modified. All 66 acceptance items were reviewed against the amended matrix, canonical source owners, fresh regression results, exact-commit CI, deployment configuration and available live behavior. This is a software verification record, not a claim of clinical validation.

- Staging branch: `staging/canonical-validation-2026-09-08`.
- Deployed commit: `4d068e06c02af8163d5f24a3cc7d6b79364a62d0`.
- Source tree: `ce0f29a2bc16030b8962594af2b0615ea4f48db7` (local tested tree and fetched GitHub commit match exactly).
- Railway deployment: `9741f77e-4c03-44ab-8773-925491068534`, SUCCESS at 11:33:28 UTC.
- App: https://cer-ai-staging-staging.up.railway.app/app
- App label: `0.7.71`; source policy: `CER-AI-2026-09-08-SHARED-PTA-LT40`. No separate live policy/version endpoint was verified; deployment identity is established by Railway commit metadata.
- Production before and after: `main` at `7b157014c507a83865d7d8332c71c324aa792456`, deployment `1581f239-cce7-410a-9c20-892fff1bbc4f`, SUCCESS. Rechecked after staging deployment.
- Only the staging branch reference was advanced (non-forced update). No service, model, access, archive configuration or production branch was changed.

## Fresh verification evidence

- Full suite: **708 passed**, one existing Starlette/AnyIO deprecation warning, 18.41 seconds, Python 3.12 in the local audit environment. No tests skipped in this run.
- Critical static checks: `python -m ruff check --select E9,F63,F7,F82 .` — PASS.
- Canonical startup invariants — PASS.
- [Exact-commit Canonical Runtime Safety](https://github.com/ginger33hc-glitch/hc-ectasia-app/actions/runs/34220591929) — SUCCESS. Job 102042522794 confirms dependency audit, static checks, startup invariants, all clinical/workflow/archive/mobile/architecture stages, 708 tests, and independent-process test files all succeeded. CI used Python 3.13; logs report no known dependency vulnerabilities.
- [Exact-commit branding verification](https://github.com/ginger33hc-glitch/hc-ectasia-app/actions/runs/34220591946) — SUCCESS.
- Canonical safety inspection confirms one PTA calculation and one threshold; pipeline uses flap for LASIK and fixed 50 µm epithelium for PRK. Both direct PRK and automatic fallback boundary tests passed at 39.99%, 40%, and 40.01%.
- Accepted Word/PDF layout evidence is carried forward from the prior eight-page review. The PTA amendment did not change the renderer; report tests passed again. This turn did not repeat page-by-page visual report QA.

## Live staging checks after deployment

- Railway reports successful application startup and serving on port 8080.
- `/app`: HTTP 200. Browser reload opens the clinical form without username/password prompts.
- `/static/manifest.webmanifest` and `/sw.js`: HTTP 200. `/openapi.json` returned 404; it is not used as a health or version signal.
- OD and OS: selecting PRK changes the LASIK flap control to **None**, empty value, disabled.
- Submitting the empty form keeps assessment blocked, focuses the missing image field, displays “Please complete the required field highlighted by the browser,” and leaves the assessment button enabled. No report is produced.
- App branding, OD-before-OS order and surgeon responsibility notice are visible.
- Browser log inspection returned extension metadata errors, not application-script errors. This is limited to this smoke session.
- No real patient images were uploaded, no clinical case was signed off, and no archive records were created in this turn.

## Remaining defects and acceptance limits

**Presentation defect:** the live form says “Preoperative manifest refraction is used only for LASIK ERSS MRSE.” `clinical_core/pipeline.py` applies ERSS and manifest MRSE to both LASIK and PRK under the approved amendment. That sentence is stale. Scoring behavior passed regression; the explanatory copy requires correction. No clinical behavior was changed during the audit.

**61 items retain local/automated acceptance; five release items are partial or blocked:** 57, 63, 64, 65 and 66. Local acceptance does not establish successful image extraction, real patient outcomes, or all workflows on the deployed service.

- 57: physical phone install/share/upload/report/archive cycle remains untested.
- 63: complete field-by-field source comparison for the exact deployed candidate remains unverified. Historical known-image/SRAX evidence is retained with its original provenance, not represented as a new extraction run.
- 64: full real-case completion/report/archive/reopen and attribution remain incomplete. Staging has no configured archive backend. Local archive tests use their test infrastructure and do not establish persistent staging operation.
- 65: staging deployment and exact commit verification complete; production promotion intentionally pending.
- 66: production smoke testing intentionally not performed; production changes remain unauthorized.

## All 66 items

PASS below means local/automated acceptance unless explicit live evidence is stated. Historical known-image evidence is carried forward; it was not repeated. The new full-suite run supports existing test contracts, not untested physical or real-case claims.

| # | Requirement | Re-audit status | Evidence and scope |
|---:|---|---|---|
| 1 | One canonical clinical engine | **PASS (LOCAL)** | Production path is `assessment_workflow → canonical_runtime_service → clinical_core`; parallel `clean_engine`, HC engine, and clinical wrappers are absent. Locked by `test_phase4_cleanup_contract.py` and `test_step14_architecture_acceptance.py`. |
| 2 | Architecture inventory before clinical changes | **PASS (LOCAL)** | Stage-1 inventory and Step-2 pre-flattening map record old implementation → surviving owner → deletion. This file records the current-state map. |
| 3 | Remove wrapper-on-wrapper architecture | **PASS (LOCAL)** | Source, merge, Rmin, SRAX, NICE, PS3, clinical, planning, report, archive-workflow, and browser correction wrappers were removed; direct calls remain. |
| 4 | One canonical Pentacam source registry | **PASS (LOCAL)** | `pentacam_canonical_source_lock.py` is the sole registry and exposes field, screen, box, label, family, no-fallback, and no-derivation rules. |
| 5 | Show 2 Exams Cornea Front K values | **PASS (LOCAL)** | K1/axes/K2/Km/astigmatism/axis map only to `SHOW_2_EXAMS_TOPOMETRIC_CORNEA_FRONT`; reread requires the Cornea Front group. |
| 6 | Posterior Rmin from Show 2 Cornea Back | **PASS (LOCAL)** | `Rmin_mm` is locked to Cornea Back; front source is rejected; obsolete `rmin_front_source_policy.py` is absent. |
| 7 | Topometric indices from center 8-mm box | **PASS (LOCAL)** | ISV/IVA/KI/CKI/IHA/IHD/topometric RMin/TKC/KISA/I-S are locked to `SHOW_2_INDICES`; no derivation is allowed. |
| 8 | Keep posterior and topometric RMin distinct | **PASS (LOCAL)** | Separate fields and separate source IDs; explicit cross-source rejection in `test_source_interchange_regression.py`. |
| 9 | Signed I-S classification, unlimited negative AST | **PASS (LOCAL)** | Canonical rule classifies every value <−0.50 D as AST; −1.00/−1.50/−3.00 and positive boundaries are tested. Exactly −0.50 is normal. |
| 10 | Four Maps lower-left numerical box | **PASS (LOCAL)** | Pupil Center, Thinnest, Kmax, and HWTW are locked to the labeled lower-left box; label interchange tests prevent Pupil Center/Thinnest and K/Kmax swaps. |
| 11 | BAD central F.Ele.Th and B.Ele.Th | **PASS (LOCAL)** | Both fields are direct BAD-center values; label/source locks reject neighboring or map values. |
| 12 | BAD PPI section | **PASS (LOCAL)** | PPI Min/Avg/Max and ARTmax are direct `BAD_PPI` reads; no CTSP/PTI reconstruction path exists. |
| 13 | BAD bottom strip and direct Final D | **PASS (LOCAL)** | Df/Db/Dp/Dt/Da/Final D are separate direct strip fields; `clinical_core.bad` consumes Final D without reconstructing it. |
| 14 | Delete every alternative locked-field source | **PASS (LOCAL)** | Wrong/missing canonical source ID clears the value to UNREADABLE; direct extraction and reread consult the registry; obsolete enforcement/fallback wrappers are absent. |
| 15 | No reconciliation for canonical fields | **PASS (LOCAL)** | Same-source disagreement clears the field and records conflict. First/highest/lowest/most-concerning/tolerance policies are absent from merge. |
| 16 | One independent geometric SRAX implementation | **PASS (LOCAL + KNOWN IMAGE)** | `geometric_srax_policy.measure_srax` is called directly by extraction; `>20°` positive and exactly `20.0°` negative. Version `srax-geom-v2` directly measured both supplied OD/OS anterior curvature maps; reverse KISA/morphology algorithms are absent. |
| 17 | Retire general morphology scoring | **PASS (LOCAL)** | Direct signed I-S/SRAX owns ERSS topography. General morphology factors are review-only and cannot score; the browser morphology selector and late morphology table were removed. |
| 18 | Independent ERSS disposition | **PASS (LOCAL)** | `clinical_core.erss`: 0–2 PASS, 3 CAUTION, ≥4 STOP-DEFER; finalizer receives ERSS as its own finding and no BAD/NICE/PS3 input. |
| 19 | One non-additive Randleman topography component | **PASS (LOCAL)** | `erss_topography_category` produces one hierarchy category from signed I-S plus applicable SRAX; ERSS adds one topography score, not separate I-S and SRAX points. |
| 20 | ARTmax informational only | **PASS (LOCAL)** | Extracted/reported in BAD context; no disposition or independent risk point references ARTmax. Regression tests confirm no escalation. |
| 21 | Final BAD-D ≥2.60 STOP-DEFER | **PASS (LOCAL)** | 2.59/2.60/2.61 boundary behavior is protected in BAD/core/runtime tests. |
| 22 | Independent NICE and exact four inputs | **PASS (LOCAL)** | Sole scorer accepts K2, Pupil Center pachymetry, B.Ele.Th, and signed I-S; totals ≤4/5–8/≥9 and incomplete behavior are tested. |
| 23 | Independent PS3 audit and explanation | **PASS (LOCAL)** | Sole PS3 evaluator has factor-level thresholds, missing keys, class/disposition, and exact details; report copies each factor and cause. |
| 24 | Mandatory pre-report ERSS/NICE/PS3 gate | **PASS (LOCAL)** | Workflow withholds report token and report renderer rejects incomplete applicable ERSS, NICE, or PS3; requests name eye, field, system, screen, and box. |
| 25 | Immediate hard-stop exception, full report still gated | **PASS (LOCAL)** | Structured hard-stop summary is returned immediately; full report remains unavailable until scoring completion. Covered by Step-7/10/11 tests. |
| 26 | One pre-report execution workflow | **PASS (LOCAL)** | Extraction/source validation → immediate stops/missing requests → canonical core systems → safety/disposition → planning → report is a single workflow path. |
| 27 | Thinnest CCT `<480` stop | **PASS (LOCAL)** | 479 stops; 480 and 481 do not stop from this rule. One constant/function in `clinical_core.safety`. |
| 28 | LASIK RSB `<300` stop | **PASS (LOCAL)** | 299 stops; 300 and 301 pass this boundary. One safety owner. |
| 29 | PRK RST `<310`, epithelium 50 | **PASS (LOCAL)** | 309/310/311 and fixed 50-µm epithelium are tested in canonical safety/runtime. |
| 30 | PTA `<40` only; A→B→C; all fail STOP-DEFER | **PASS (LOCAL)** | One shared `40.0` constant/gate. September 8 approval extends PTA `<40%` to direct PRK and automatic LASIK→PRK using 50 µm epithelium. LASIK retains A→B→C, first safe candidate, otherwise STOP-DEFER; PRK retains its requested treatment settings. |
| 31 | Signed refractive magnitude hard stops | **PASS (LOCAL)** | One normalized-refraction/safety path handles myopic and hyperopic sides; boundary tests protect both directions and negative-sign behavior. |
| 32 | Postoperative K 36–48 inclusive | **PASS (LOCAL)** | 35.99 and 48.01 stop; 36.00 and 48.00 are allowed. |
| 33 | One postoperative K formula, 0.8× intended MRSE | **PASS (LOCAL)** | `clinical_core.safety.estimated_final_kmean_d` is the sole formula; report and planning consume the computed result. |
| 34 | PRK MMC sign-safe rule | **PASS (LOCAL)** | Myopic magnitude 3.99 recommended/4.00 mandatory; hyperopic mandatory; normalized refractive group prevents signed-comparison errors. |
| 35 | PRK selection clears LASIK flap | **PASS (LOCAL)** | Plan resolution forces `flap_um=None` and `NOT_APPLICABLE`; frontend and runtime tests prevent residual-flap conflicts. |
| 36 | Prior refractive surgery separate pathway | **PASS (LOCAL)** | Previous LASIK/PRK/SMILE returns `POST-REFRACTIVE PATHWAY REQUIRED` and cannot obtain a virgin-cornea report token. |
| 37 | ML7/microkeratome planning audit | **PASS (LOCAL)** | Dedicated BAD upper-middle K1/K2 supply ML7 keratometry; HWTW remains Four Maps lower-left. No general-scoring K or Kmax fallback. Canonical planning owns flap/ring/vacuum/blade/hinge and imports safety constants. |
| 38 | One surgeon-completion mechanism with provenance | **PASS (LOCAL)** | `assessment_workflow` creates standardized requests and applies corrections once; report payload labels corrections `SURGEON_CONFIRMED`. |
| 39 | Mandatory source-set gate | **PASS (LOCAL)** | OD/OS Four Maps, OD/OS BAD, and Show 2 are required by direct workflow validation; treatment card is optional and missing screens are not inferred. |
| 40 | Laterality never from upload order | **PASS (LOCAL)** | Explicit visible OD/OS is required; UNKNOWN or inconsistent laterality is blocked. Mandatory-source and extraction tests protect this. |
| 41 | Patient identity/date integrity | **PASS (LOCAL)** | Name/ID/age/date are validated; OCR failure produces warnings/completion rather than cross-eye corruption; authoritative Four Maps date conflicts fail closed. |
| 42 | One visible Pentacam QS policy | **PASS (LOCAL)** | `pentacam_quality_policy.py` owns the non-silent quality warning behavior used by extraction/workflow/report; UI displays quality warnings. |
| 43 | Analyze workflow completeness diagnostics | **PASS (LOCAL)** | Analyze re-enables after incomplete responses and identifies source/manual/flap/scoring blockers; PRK flap=None and historical disabled-button regressions are tested. |
| 44 | Generate Report gate | **PASS (LOCAL)** | No report token/action until applicable ERSS + NICE + PS3 are complete; hard-stop summary is a distinct response. |
| 45 | Randleman report | **PASS (LOCAL)** | Full LASIK and PRK reports show five components, points, total, category, and disposition. Approved PRK amendment uses residual stroma for the tissue component and requires complete ERSS; the earlier non-LASIK-not-applicable statement is retired. |
| 46 | NICE report | **PASS (LOCAL)** | Shows four inputs, four component scores, total, classification, and status from canonical payload; incomplete reports are rejected. |
| 47 | PS3 report | **PASS (LOCAL)** | Shows every finding, status, exact detail, moderate/high counts, final procedure disposition, and missing state; unexplained-high-risk regression is covered. |
| 48 | BAD-D report without recalculation | **PASS (LOCAL)** | Final D, all five D components, interpretation, context, and source provenance are copied from the canonical payload; renderer imports no scorer. |
| 49 | Separate procedural-safety section | **PASS (LOCAL)** | Report has independent tissue-safety output for CCT/RSB/PTA/RST/final K/magnitude stops and retains ectasia-system sections separately. |
| 50 | Canonical Plan A/B/C report/planning | **PASS (LOCAL)** | Runtime records each evaluated candidate, zones, flap, ablation/source, status and rejection reasons; report consumes the planning sequence and selected ML7 plan without recalculation. |
| 51 | Source-interchange regressions | **PASS (LOCAL)** | New explicit matrix rejects all listed K, pachymetry, RMin, I-S/ISV, PPI, elevation, and D-component/Final-D swaps. |
| 52 | Historical false AST case | **PASS (LOCAL)** | Negative I-S regression uses the numeric pathway only; no visual morphology scorer or browser selection survives. |
| 53 | Known SRAX boundary/algorithm cases | **PASS (LOCAL + KNOWN IMAGE)** | Synthetic 20.0/>20/uncertain tests pass. Direct geometry on the supplied Four Maps images returned OD 2.0° and OS 1.1°, both negative under the strict threshold; no reverse-KISA path exists. |
| 54 | Complete archive cycle | **PASS (LOCAL)** | Automated route cycle covers save, visible identity/date, reopen, original PDF open, regeneration, immutable original, and attribution. |
| 55 | Retrospective research data | **PASS (LOCAL)** | Encrypted catalog search and pseudonymized research export support later queries outside the clinical engine; access controls are tested. |
| 56 | User/surgeon access and attribution | **PASS (LOCAL)** | OWNER/DOCTOR scope, authenticated reviewer binding, report/archive attribution, and job ownership are tested without clinical mutation. |
| 57 | Physical mobile/PWA test | **PARTIAL** | Manifest/share-target/service-worker/mobile layout, first-attempt retry, completion/report/archive flows pass automated browser/Node contracts. No physical phone installation/share/report/archive run was performed. |
| 58 | Current branding only | **PASS (LOCAL)** | The staging app/public site/title/footer use `CER-AI — Cornea Ectasia Risk Assessment Intelligence`; accepted branding is retained. No new branding change is authorized by this audit. |
| 59 | Surgeon responsibility notice | **PASS (LOCAL)** | Visible in application, reports, public site, and localization; remains presentation/legal content, separate from assessment findings. |
| 60 | Test retirement discipline | **PASS (LOCAL)** | `CERAI_STEP1_TEST_RETIREMENTS.md` records old rule → new owner/rule → reason, including the 2026-09-07 PTA clarification. |
| 61 | Complete local regression suite | **PASS (LOCAL, SHARED-PTA AMENDMENT)** | Accepted checkpoint: 697 tests and eight-page Word visual QA. After the approved PRK PTA amendment: 708 tests passed, with one dependency deprecation warning; static checks and startup invariants passed. Exact-commit GitHub Actions passed (Canonical Runtime Safety run 34220591929; brand run 34220591946). Fresh post-deployment audit reran 708 tests successfully on an identical source tree, plus static checks and startup invariants. |
| 62 | Architecture acceptance matrix | **PASS (LOCAL)** | `test_step14_architecture_acceptance.py` locks one runtime, no parallel engine, no browser clinical override, no report-side scoring, no reconciliation, PTA boundary, and current branding. |
| 63 | 30-target validation on real Pentacam screenshots | **PARTIAL** | Historical canonical-box transcription and bilateral geometric SRAX checks exist. Subsequent staging model extraction is evidenced by recovered responses and Railway logs. Complete field-by-field equality/sign-off for the exact release candidate is not established. Dedicated PS3 BAD flat axis is distinct from the historical unreadable Show 2 K1 axis. |
| 64 | Real-case end-to-end validation | **PARTIAL / ARCHIVE BLOCKED** | Accepted sample-report review and staging analysis/completion transport evidence exist; they do not establish complete clinical input sign-off or archive/reopen success. Staging rendered variable names contain no archive backend configuration. Complete source comparison, confirmed eligibility/treatment inputs, and deployed report/archive/reopen attribution still require evidence. |
| 65 | Merge/Railway deployment/SHA/version verification | **PARTIAL — STAGING VERIFIED** | Staging deployment 9741f77e-4c03-44ab-8773-925491068534 is SUCCESS at 4d068e06c02af8163d5f24a3cc7d6b79364a62d0 (2026-09-08 11:33:28 UTC). Post-deployment /app, service worker and manifest returned HTTP 200; app startup completed. Production remains 7b157014c507a83865d7d8332c71c324aa792456. Production promotion is pending validation and explicit authorization. Application label 0.7.71 alone does not identify the release; record SHA and policy version. |
| 66 | Production smoke test, including mobile repeat | **BLOCKED — NOT AUTHORIZED** | Requires approved production promotion, known-case source comparison, report/archive access and physical mobile repeat. Not performed. |
