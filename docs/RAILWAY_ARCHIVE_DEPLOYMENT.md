# CER-AI Railway Archive Deployment Runbook

This runbook activates the encrypted CER-AI case archive without changing clinical scoring or decision logic.

## Safety rule

Do not place patient data in the Railway bucket until the configuration preflight and the non-PHI encrypted canary both pass. Keep `CERAI_ARCHIVE_ENABLED=0` and `CERAI_ARCHIVE_REQUIRED=0` during provisioning.

## 1. Create the Railway Storage Bucket

In the existing CER-AI Railway project:

1. Create a new **Bucket** resource.
2. Choose the temporary region deliberately; Railway does not allow changing a bucket region after creation.
3. Give the bucket a clear display name such as `cer-ai-archive`.
4. Do not make the bucket public. CER-AI expects private S3-compatible access.

Railway exposes the actual S3 credentials from the bucket resource. The S3 API bucket name is `BUCKET`; `RAILWAY_BUCKET_NAME` is only the display name and must not be substituted for `BUCKET`.

## 2. Inject bucket variables into the CER-AI service

Use Railway variable references from the bucket resource to the CER-AI service for:

- `BUCKET`
- `ACCESS_KEY_ID`
- `SECRET_ACCESS_KEY`
- `REGION`
- `ENDPOINT`

Use `AWS_S3_URL_STYLE=virtual` unless the bucket Credentials tab explicitly says the bucket requires path style.

Never commit real bucket credentials to GitHub.

## 3. Create the archive encryption key

Generate one random 32-byte secret and store only its base64 representation as:

`CERAI_ARCHIVE_MASTER_KEY_B64`

Back up this key separately from Railway. Loss of this key makes the encrypted clinical archive unreadable. Do not reuse it as the research pseudonym key.

Keep:

- `CERAI_ARCHIVE_ENABLED=0`
- `CERAI_ARCHIVE_REQUIRED=0`

at this stage.

## 4. Run configuration preflight

Run inside an environment that has the same Railway variables as the CER-AI service:

```bash
python scripts/verify_railway_archive_config.py
```

The preflight checks configuration only and does not contact the bucket or upload data. It verifies, among other things:

- required Railway S3 variables are present,
- `BUCKET` was not confused with `RAILWAY_BUCKET_NAME`,
- the Railway endpoint is HTTPS,
- URL style is valid,
- archive key decodes to exactly 32 bytes,
- research and archive keys are different,
- named-user configuration contains an OWNER when enabled,
- raw password fields are not placed in `CERAI_USERS_JSON`.

It must finish with:

`CER-AI Railway archive configuration preflight passed.`

## 5. Run the non-PHI encrypted canary

Only after the preflight passes, run:

```bash
python scripts/verify_case_archive.py
```

The canary contains no patient information. It verifies the real S3 path end to end:

1. client-side AES-GCM encryption,
2. upload to the configured bucket,
3. object listing,
4. read-back,
5. authenticated decryption,
6. plaintext SHA-256 verification.

The canary object is intentionally retained as a non-PHI verification artifact.

Do not proceed if this step fails.

## 6. Configure named users

Generate each account password hash without putting the password in shell history:

```bash
python scripts/generate_user_password_hash.py
```

Store only the resulting scrypt hash in `CERAI_USERS_JSON`. At least one enabled `OWNER` account is required. Normal clinical users should use the `DOCTOR` role.

Then set:

`CERAI_NAMED_USERS_ENABLED=1`

Verify sign-in before enabling the clinical archive.

## 7. Enable the archive in non-required mode

Set:

`CERAI_ARCHIVE_ENABLED=1`

Keep:

`CERAI_ARCHIVE_REQUIRED=0`

for the first controlled verification. Use only non-PHI or an explicitly approved test case. Confirm that the Case Archive UI can search the archived revision and retrieve the exact original PDF/DOCX.

## 8. Enable fail-closed production behavior

Only after the real bucket has passed the canary and controlled archive verification, set:

`CERAI_ARCHIVE_REQUIRED=1`

In REQUIRED mode, CER-AI must not release a clinical report if required archive/audit persistence fails.

## 9. Optional research export

Research export is OWNER-only and should remain disabled until required.

Generate a different random 32-byte key and store it as:

`CERAI_RESEARCH_PSEUDONYM_KEY_B64`

Then set:

`CERAI_RESEARCH_EXPORT_ENABLED=1`

The research key must never equal the archive encryption key.

## 10. Future migration to a Turkish S3-compatible provider

CER-AI includes a ciphertext-preserving migration utility. It does not decrypt patient content during migration.

Default dry run:

```bash
python scripts/migrate_case_archive.py
```

Apply mode requires explicit:

`CERAI_MIGRATION_APPLY=1`

Existing matching objects are retained. Any conflicting destination object aborts migration rather than being overwritten.

## Release gate

Do not merge/deploy the archive PR unless all repository safety gates are green and the real Railway preflight + non-PHI canary have both passed.

The archive master key must be backed up outside Railway before real patient data is stored.
