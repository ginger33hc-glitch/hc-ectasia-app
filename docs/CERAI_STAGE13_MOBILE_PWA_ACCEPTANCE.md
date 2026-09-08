# CER-AI Stage 13 — Mobile and PWA Acceptance

Status: **IMPLEMENTED / LOCAL VALIDATION COMPLETE — 2026-09-07**

## Surviving mobile workflow

`install/share -> /app -> authenticated share-token handoff -> retained source Files -> /analysis/jobs -> canonical /analyze -> surgeon completion -> canonical report -> archive`

Mobile and PWA code changes transport and presentation only. It does not extract clinical
values, score ERSS/NICE/PS3, set thresholds, calculate procedural safety, plan procedures, or
build report findings.

## First-attempt and connection recovery

- A browser assessment request identifier now maps deterministically to an actor-scoped UUID.
- The background job passes that UUID to canonical `/analyze`, whose assessment request key
  requires UUID syntax.
- Repeating an upload after an interrupted response recovers the same job and does not run a
  second clinical assessment.
- Jobs without a browser request identifier receive a random UUID.
- Existing ownership checks continue to prevent another authenticated user from polling a job.
- Temporary upload limits remain six images, 20 MB per image, and 80 MB total.

This retires the old behavior in which the background transport generated a non-UUID opaque
identifier and then passed it into the UUID-validated canonical analysis path. The resulting
first-attempt failure was a transport defect, not a clinical-engine rule.

## Gallery and share-target handoff

- The PWA manifest opens `/app` and exposes one multipart `image/*` share target.
- The service worker stores validated shared images and redirects with an absolute
  `/app?share_token=...` URL.
- Share errors also return to `/app` with an explicit bounded error code.
- If login is required, the named-user gate and both login pages preserve only a syntactically
  valid share token or recognized share error. Arbitrary query strings and external redirect
  destinations are discarded.
- Shared blobs become browser `File` objects and are adopted by the existing source-retention
  mechanism. Surgeon completion or source replacement therefore preserves the selected
  Pentacam source set.
- The application removes the token from browser history after loading it.

This retires the old root-page share redirect. The public homepage cannot consume shared-image
tokens; the protected clinical application is the authoritative consumer.

## Mobile report and archive behavior

- The PDF action opens a browser tab synchronously from the surgeon's tap, then directs that tab
  to the completed PDF blob. This preserves the mobile browser's user-gesture requirement.
- Blob URLs remain valid long enough for mobile viewing/download rather than being revoked
  immediately.
- DOCX remains a download, while PDF is labeled as open/download.
- Report controls, clinical tables, form controls, archive actions, and source-image controls
  have responsive overflow and touch-target behavior.
- Archive search, reopening, original report access, regeneration, source viewing, and
  attribution continue through the Stage 12 server routes without UI-side clinical logic.

## Architecture cleanup

Old implementation -> surviving implementation -> reason retired:

- `mobile_install_section.py` renderer replacement -> `public_site._render_public_home` -> the
  install section is public-page presentation and does not require an import-order wrapper.
- root share redirect -> service-worker `/app` redirect -> only the clinical page loads cached
  shared images.
- non-UUID background job identifier -> actor-scoped UUID job identifier -> canonical analysis
  requires a UUID request key and retries must be idempotent.
- shared-image metadata as a parallel upload collection -> normal retained browser `File`
  collection -> source replacement must preserve one source-image path.

No old clinical test was removed or weakened. Stage 13 adds a dedicated acceptance file and CI
step; the complete pre-existing suite remains green.

## Local evidence

- Stage 13 mobile/PWA acceptance: `10 passed`.
- Adjacent transport, access, public-site, readiness, archive, and composition regressions:
  `35 passed`.
- Complete application suite: `574 passed`.
- All `65` test files passed independently in fresh pytest processes.
- Service-worker success/error behavior executed in Node with cache and file mocks.
- All application, archive, login, and trial-login inline JavaScript parsed successfully.
- PWA manifest JSON and declared PNG dimensions validated.
- Critical Ruff checks, Python compilation, canonical startup invariants, and production
  dependency audit: passed.

No push, merge, deployment, Railway action, production upload, or mobile-device smoke test was
performed. Those actions remain separate stages and require the relevant environment and
authorization.
