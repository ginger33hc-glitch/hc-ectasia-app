# CER-AI Monday Step 2 — Pentacam Extraction Flattening Inventory

Status: **SUPERSEDED HISTORICAL INVENTORY — migration completed 2026-09-07**

The wrapper chain below records the pre-flattening state. It is not a description of the current
runtime. Current acceptance evidence is in `CERAI_MASTER_ORDER_66_ITEM_EVIDENCE_MATRIX.md` and
`tests/test_step14_architecture_acceptance.py`.

Governing invariant:

`SOURCE IMAGE -> ONE CANONICAL EXTRACTION -> ONE CANONICAL VALUE + PROVENANCE`

No replacement wrapper is permitted. Accepted behavior must move into the direct canonical extraction/merge/source location, callers must migrate, and the superseded wrapper must then be deleted.

## 1. Canonical source authority

`pentacam_canonical_source_lock.py` is the sole field/source registry specification.

Locked fields are direct-read only. Wrong-screen observations are ignored/audited, not reconciled. Missing canonical values remain unreadable; no reverse calculation or substitute source is allowed.

`pentacam_provenance.py` is already pure and side-effect free and matches the Monday conflict semantics:
- same eye + same exam + same canonical source disagreement -> CONFLICT;
- different screens/wrong source -> ignored as wrong-source audit evidence, not conflict;
- different exams -> explicit exam selection required;
- surgeon correction -> SURGEON_CONFIRMED with original automatic observations retained.

These two modules are canonical authorities and should survive Step 2.

## 2. Current production mutation chain

### Merge path

Current effective chain is layered:

1. `app.py::merge_extractions`
2. `merge_policy_base.py` replaces `core.merge_extractions` at import time.
3. `extraction_guard.py` wraps the current merge at import time.
4. `pentacam_canonical_source_enforcement.install()` wraps merge again.
5. `ps3_extraction_policy.install()` wraps merge again.
6. `mandatory_source_set_policy.install()` wraps merge again.

This is not accepted final architecture.

### Per-image extraction path

Current effective chain is layered:

1. `app.py::extract_one_image`
2. `pentacam_targeted_reread.install()` wraps `core.extract_one_image`.
3. `rmin_front_source_policy.install()` wraps it again, clears Rmin and performs a second dedicated Rmin reread.
4. `geometric_srax_policy.install()` wraps it again to add deterministic SRAX geometry.

This is not accepted final architecture.

### Prompt/schema mutation

The base `app.py` schema/prompt are subsequently modified by:
- `erss_numeric_extraction_policy.install()` — rewrites the ERSS morphology/SRAX prompt section.
- `pentacam_canonical_source_enforcement.install()` — appends the source registry prompt and patches targeted-reread labels/apply behavior.
- `ps3_extraction_policy.install()` — adds schema fields and source prompt text.
- `mandatory_source_set_policy.install()` — appends BAD-page recognition prompt text.
- `rmin_front_source_policy.install()` — appends Rmin source-lock prompt text.
- `bad_display_source_policy.install()` — appends BAD source-lock prompt text.

One extraction contract must own these rules directly after flattening.

## 3. Module disposition

### KEEP AS CANONICAL / PURE

- `pentacam_canonical_source_lock.py`
  - sole locked-field source registry.
- `pentacam_provenance.py`
  - sole canonical observation/provenance/conflict resolver.
- `geometric_srax_policy.py` **algorithm only**
  - keep deterministic `measure_srax()` and its helpers;
  - delete installer/extract-one-image replacement after direct integration.
- `pentacam_targeted_reread.py` **pure reread/crop/label helpers only**
  - keep image crop/render and structured targeted-reread helpers;
  - delete installer/extract-one-image replacement after direct integration.
- `mandatory_source_set_policy.py` **pure classification/validation helpers only if still needed**
  - source-set validation is workflow/readiness behavior, not a merge mutation;
  - delete merge and `_run_image_assessment` wrappers after direct workflow integration.

### MIGRATE THEN DELETE WRAPPER MODULE

#### `pentacam_canonical_source_enforcement.py`
Accepted behavior:
- registry-derived source-family rejection;
- no map fallback for locked fields;
- source-aware reread rejection;
- TKC/topometric-RMin/F.Ele.Th label validation.

Canonical destination:
- direct extraction/reread validation using `pentacam_canonical_source_lock.py`;
- direct merge/provenance resolution using `pentacam_provenance.py`.

Delete installer after callers migrate.

#### `merge_policy_base.py`
Accepted behavior:
- preserve EX500 `laser_plans` and EX500 source handling.

Canonical destination:
- direct `app.merge_extractions` / later canonical merge module.

Delete import-time replacement after migration.

#### `extraction_guard.py`
Accepted behavior:
- plausibility audit;
- PPI internal consistency audit;
- extraction-validation payload.

Retire/replace behavior:
- string-based conflict parsing and <=1% reconciliation must not govern locked fields;
- canonical locked-field conflict semantics belong to `pentacam_provenance.py`.

Canonical destination:
- pure post-resolution extraction audit called directly by canonical merge/workflow.

Delete import-time merge replacement after migration.

#### `ps3_extraction_policy.py`
Accepted behavior:
- schema fields: `topographic_astig_D`, `topographic_steep_axis_deg`, `posterior_Kmean_D`, `F_Ele_Th_um`;
- exact source requirements for those fields;
- exam-date separation requirement.

Retire/replace behavior:
- PS3-specific merge must disappear;
- `nice_readings` must not be a second storage path for `B_Ele_Th_um` or central pachymetry;
- those values must live once on the canonical eye payload with canonical provenance.

Canonical destination:
- base canonical extraction schema/prompt + canonical merge/provenance.

Delete module after migration.

#### `rmin_front_source_policy.py`
Accepted behavior:
- `Rmin_mm` only from Show 2 Exams Topometric -> Cornea Back -> Rmin;
- no map fallback.

Retire behavior:
- clearing the first-pass Rmin and performing a separate Rmin-specific wrapper reread.

Canonical destination:
- base extraction/reread contract using the canonical source registry.

Delete module after migration. Rename-free deletion is preferred; do not preserve misleading legacy symbol names.

#### `erss_numeric_extraction_policy.py`
Accepted behavior:
- model-based general ERSS morphology disabled;
- model SRAX estimation disabled;
- signed I-S remains a direct numeric read;
- geometric SRAX owns SRAX when measurable.

Canonical destination:
- base extraction prompt.

Delete prompt-patch installer after migration.

#### `bad_display_source_policy.py`
Accepted behavior:
- Df/Db/Dp/Dt/Da/Final D are direct BAD-strip transcriptions with signs preserved;
- no reconstruction.

Canonical destination:
- base extraction prompt/registry.

Delete prompt-patch installer after migration.

## 4. Targeted reread normalization defect to remove

`pentacam_targeted_reread.py` still has a legacy `nice_readings` side channel for:
- `central_pachy_um`
- `B_Ele_Th_um`

This violates one normalized value/one downstream path. Step 2 must make these ordinary canonical eye fields with source provenance, just like other locked fields. NICE and PS3 must consume the same eye value; neither may own a separate extraction copy.

## 5. Mandatory source-set gate disposition

The mandatory five-image source-set requirement is a pre-assessment workflow/readiness gate. It should not be implemented by wrapping `merge_extractions` and `_run_image_assessment` with a `ContextVar`.

Target:
- classify/validate the extracted source set directly in the image-assessment workflow before canonical clinical evaluation;
- attach the source-set summary to the extraction payload;
- keep the pure source-set classifier if useful;
- delete runtime monkey/wrapper installation.

## 6. First safe flattening sequence

Step 2A — canonical schema/prompt ownership:
1. Move all accepted PS3/source-lock/BAD/Rmin/ERSS extraction fields and prompt rules into one direct extraction contract.
2. Ensure `SCHEMA`, table field enums and prompt contain every canonical locked field exactly once.
3. Remove prompt/schema installer dependencies one by one with regression tests.

Step 2B — targeted reread direct integration:
1. Make targeted reread consult `pentacam_canonical_source_lock` directly.
2. Store central pachymetry and B.Ele.Th directly on eye payload, not `nice_readings`.
3. Integrate Rmin Cornea-Back validation into normal targeted reread; remove Rmin-specific wrapper.
4. Call targeted reread directly from the single per-image extraction function.

Step 2C — deterministic SRAX direct integration:
1. Keep `measure_srax()` pure.
2. Call it directly after the base extraction only for the correct Four Maps eye/image.
3. Store one SRAX value/provenance.
4. Remove SRAX extractor installer.

Step 2D — canonical merge/provenance:
1. Replace wrapper merge chain with one direct merge.
2. Convert locked-field observations to `pentacam_provenance.Observation` and resolve with `resolve_field()`.
3. Ignore wrong-source duplicates; only same-eye/same-exam/same-source disagreement creates conflict.
4. Never merge different exam dates.
5. Preserve EX500 aggregation explicitly.
6. Run the extraction audit directly after resolution.

Step 2E — mandatory source set direct workflow gate:
1. Call the pure source-set validator directly in the assessment workflow.
2. Delete merge/request wrapper installation.

Step 2F — delete superseded wrappers and composition entries.

## 7. Step 2 closure criteria

Step 2 is not complete until:
- one direct extraction function owns the model extraction + targeted reread + deterministic SRAX sequence;
- one direct merge/provenance path owns locked-field resolution;
- central pachymetry and B.Ele.Th have no `nice_readings` duplicate storage path;
- Rmin has no dedicated wrapper or fallback path;
- prompt/schema source rules exist once;
- wrong-screen values cannot create conflicts;
- different exams cannot merge;
- no extraction behavior depends on installer/import order;
- every superseded extraction wrapper is physically deleted;
- full regression suite and independent test-file/import-order checks pass.

PR #75 remains draft. Step 2 work does not authorize merge or deployment.
