# CER-AI production promotion review — 8 September 2026

Status: **DRAFT — release gates remain open; production deployment is not authorized**.

## Scope and preserved checkpoint

This documentation follow-up reconciles evidence relative to the accepted staging checkpoint. It changes no executable
code, clinical threshold, model setting, report renderer, credential, deployment configuration,
or patient data. The working staging branch/service remains separate from production.

| Target | Branch / commit | Railway deployment | Verified state |
|---|---|---|---|
| Staging | `staging/canonical-validation-2026-09-08` / `0d36e06981b48d1147eb2123c2b46a0df077f70a` | `a4fa9194-f66f-4f6b-ae6b-2ea053457bf7` | SUCCESS; service `cer-ai-staging`, environment `staging` |
| Production | `main` / `7b157014c507a83865d7d8332c71c324aa792456` | `1581f239-cce7-410a-9c20-892fff1bbc4f` | SUCCESS since September 6; service `hc-ectasia-app`, environment `production` |

The original local checkout at `8c86378960a17102179e2dc98b13257272b38bc6` has the same tree as
GitHub staging: `4628b13bc6ec02c796b8cc55d9016665cc149c11`. Different local/remote commit
identifiers therefore do not indicate different source files. The review branch must descend
from the actual GitHub staging commit, not replace staging with the local history.

Application label: `0.7.71`. Clinical policy: `CER-AI-2026-09-08-PRK-ERSS-SHARED-ABLATION`.
The label alone is insufficient to identify a deployment; retain commit and policy identifiers.

## Evidence already accepted

- Stages 1–14 local canonical architecture, workflow, planning, reporting, access and regression work.
- Latest checkpoint: 697 tests passed. Earlier Stage 14 counts describe earlier snapshots.
- Approved Word/PDF presentation alignment: all eight sample Word pages visually checked and accepted by the surgeon. No repeat visual approval is requested.
- Exact staging GitHub head and Railway deployment metadata match. Staging and production have different service IDs, environment IDs, branches and domains.
- Subsequent clinical/source amendments are summarized in the 66-item matrix and recorded in the owning protocol/test-retirement documentation. They take precedence over the original freeze.

## Newly recovered staging evidence and its limits

Railway runtime/HTTP logs for the verified staging deployment show:

| Time (UTC), September 8 | Observation | What it establishes |
|---|---|---|
| 10:51:31 | `/app` returned 200 | Application page was served |
| 10:54:19 | `POST /analysis/jobs` returned 202 | An analysis request was accepted |
| 10:54–10:55 | Model-completion messages and job polling | Extraction work ran on staging |
| 10:55:49 | Analysis-job polling returned 200 | Job endpoint returned a completed response |
| 10:55:59 | `POST /assessment/complete` returned 200 | Completion endpoint processed a request |

HTTP 200 does not prove READY, correct extracted values, full scoring completion, report
generation, or archive success. No patient identifiers, session tokens or raw logs are copied
into this review.

Two recovered extraction-response artifacts from the previous workspace have
`CONTACT_LENS_WASHOUT_REQUIRED`, no report token, and no effective treatment plans. They
demonstrate extraction/completion behavior, not a complete clinical assessment. Their exact
deployment provenance is not established, so they cannot close exact-candidate acceptance.

The rendered staging variable-name inventory contains model and access settings, but no archive
bucket/endpoint/master-key markers or required-archive setting. The owning
`case_archive.runtime_from_environment` consequently has no configured persistent archive backend.
Production lists archive configuration names, but values and live archive operation have not
been validated here. Do not copy production patient storage or keys into staging.

## Remaining acceptance gates

| Matrix item | Required evidence | Current limitation |
|---|---|---|
| Policy reconciliation | Explicit disposition of the old standalone PRK PTA >35.28% CAUTION | Historical compliance text and current runtime disagree; no specific resolving approval was recovered |
| 57 | Physical phone: install/share, first upload, completion, PDF/Word access and archive reopen | Automated tests and HTTP logs are not a physical-device run |
| 63 | Compare every canonical target against labeled source boxes for the exact candidate; include BAD flat axis, dedicated ML7 K1/K2, bilateral geometric SRAX and unreadable/conflict behavior | Historical transcription and extracted responses do not establish complete equality/sign-off |
| 64 | Surgeon-confirmed eligibility and treatment inputs; complete case through report, durable save, search, reopen, original artifact and attribution | Incomplete recovered responses; staging archive is unconfigured |
| 65 | Required CI on the proposed promotion revision, explicit approval, production deployment/SHA verification | Staging is verified; production promotion is pending |
| 66 | Production desktop and physical-mobile smoke test after authorized deployment | Not performed; production action is not authorized |

## Documentation corrections in this review

- Replace reverse-KISA, inclusive-20 and PS3-22 SRAX instructions with shared geometric >20 evidence.
- Replace anterior Rmin and tolerance/minimum/maximum reconciliation instructions with canonical source/conflict ownership.
- Include PRK ERSS/shared ablation, automatic per-eye LASIK→PRK evaluation, PS3 >3 D activation/BAD flat axis, and ML7 dedicated BAD K fields.
- Replace obsolete soft-lens 14-day operational text with the existing canonical 10-day readiness gate.
- Correct matrix item 45 and distinguish earlier local audit evidence from later staging deployment and accepted report QA.

### Open policy decision: standalone PRK PTA >35.28% flag

The earlier compliance audit says this value independently causes CAUTION. The current canonical
core/runtime contains no such gate. Searches of repository history, the master-order text and
prior-session context did not recover explicit approval retaining or retiring this isolated flag.
Retirement of the PRK-EWSS scorer alone is not assumed to resolve it. The surgeon must decide
whether the flag is retired or is an intended independent caution before policy acceptance closes.
Clinical code remains unchanged. This is separate from the approved LASIK PTA >=40% plan-failure rule.

## Concrete promotion sequence

1. Keep the documentation/release review on `review/production-readiness-2026-09-08`, descended
   from the exact staging checkpoint. Open a draft PR to `main`; do not merge it or enable auto-merge.
2. Inspect the existing Canonical Runtime Safety workflow on that PR. Record actual results;
   a missing, queued or failed workflow is not a pass. The initial staging head had no Actions
   runs because the workflow triggers on `main` pushes and PRs targeting `main`.
3. Resolve the isolated PRK PTA policy conflict with the surgeon, then close items 63–64 with verified source values and surgeon-confirmed case inputs. Provision
   an isolated staging archive only after its storage destination and access configuration are
   known; never substitute production patient storage. Record the actual persistent cycle.
4. Complete the physical-device portions of item 57. Preserve the already accepted Word sample.
5. Present the exact PR revision, CI outcomes, case/phone/archive evidence and release diff for
   explicit production authorization. Railway source settings currently have `checkSuites=false`;
   do not rely on Railway to block an unverified `main` merge. A merge to `main` may auto-deploy.
6. Only after authorization, promote the approved revision and verify its actual production
   deployment SHA/status. Complete item 66 and preserve staging's separate branch/service.

Rollback reference is production commit `7b157014c507a83865d7d8332c71c324aa792456` and successful
deployment `1581f239-cce7-410a-9c20-892fff1bbc4f`. These are reference identifiers, not a claim
that rollback or archive compatibility has been exercised. No archive migration is proposed here.

## Source references

- [Staging checkpoint](https://github.com/ginger33hc-glitch/hc-ectasia-app/commit/0d36e06981b48d1147eb2123c2b46a0df077f70a)
- [Production baseline](https://github.com/ginger33hc-glitch/hc-ectasia-app/commit/7b157014c507a83865d7d8332c71c324aa792456)
- [Verified staging deployment](https://railway.com/project/7684f33d-d931-469c-ad1c-a5b7fd4c506e/service/7a90cee1-b5b9-46fe-854f-4018f1e73175?id=a4fa9194-f66f-4f6b-ae6b-2ea053457bf7&environmentId=8361baab-5c69-4ab7-869b-3ba4213e444b)
- Repository: `CERAI_MASTER_ORDER_66_ITEM_EVIDENCE_MATRIX.md`, `CERAI_STEP1_TEST_RETIREMENTS.md`,
  `CER-AI_PROTOCOL_v0.7.md`, canonical source registry and owning clinical modules.
