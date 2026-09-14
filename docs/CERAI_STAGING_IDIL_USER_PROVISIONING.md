# Staging-only provisioning: the "idil" test account

This document describes how to idempotently provision a named-user test account
(`username=idil`, `display_name=Idil`, `role=DOCTOR`, `password=idil`) in
**cer-ai-staging (staging environment) only**. It must never be run against production.

## Why

The named-user authentication system (`user_access.py`) stores accounts as
`CERAI_USERS_JSON`, a Railway secret containing scrypt password hashes (never raw
passwords). Testing the login flow in staging requires a known account, but manually
editing the JSON secret by hand is error-prone and risks either duplicating the account
(if a previous attempt already applied it) or leaving the registry without an enabled
`OWNER` account, which `user_access.parse_registry()` rejects outright.

## How it works

* `scripts/ensure_staging_idil_user.py` reads `CERAI_USERS_JSON` (from the environment,
  or an empty list if unset), checks whether a user normalizes to username `idil`
  (case-folded, whitespace-collapsed, matching `user_access.normalize_username`), and:
  * If found: reports `status: already_present` and makes no changes.
  * If not found: generates a scrypt hash for the password `idil` using the exact same
    parameters as `hash_password()` in `user_access.py` (`n=16384, r=8, p=1`, 16-byte
    random salt, 32-byte digest, `scrypt$N$r$p$salt_hex$digest_hex` encoding), appends
    a new user object, verifies at least one enabled `OWNER` account still exists, and
    reports `status: changed` along with the new `CERAI_USERS_JSON` value and the
    before/after user counts.
* `scripts/apply_staging_idil_user.py` calls the ensure script and, if the registry
  changed, updates the Railway variable via the Railway public GraphQL API
  (`variableUpsert`), using `RAILWAY_API_TOKEN`, `RAILWAY_PROJECT_ID`,
  `RAILWAY_ENVIRONMENT_ID`, and `RAILWAY_SERVICE_ID`. If those are not set, it prints the
  new JSON value instead of writing anywhere, so it can be applied by hand via the
  Railway dashboard or `railway variables --set`.

## Safety rails

* `apply_staging_idil_user.py` refuses to run unless `CERAI_STAGING_APPLY_CONFIRM=1` is
  explicitly set, and additionally refuses to run if `RAILWAY_ENVIRONMENT_NAME` or
  `RAILWAY_SERVICE_NAME` are set and do not match `staging` / `cer-ai-staging`.
* Both scripts are read/report-only against the *local* environment variable unless the
  Railway API credentials are supplied; there is no automatic build/deploy hook that runs
  this against every deploy, since account provisioning is a one-off, explicit, operator
  action rather than something that should happen implicitly on every staging deploy.

## Usage

```
# Preview only, no changes applied anywhere:
python scripts/ensure_staging_idil_user.py

# Apply to Railway staging (requires the Railway API env vars and explicit confirmation):
CERAI_STAGING_APPLY_CONFIRM=1 \
RAILWAY_ENVIRONMENT_NAME=staging \
RAILWAY_SERVICE_NAME=cer-ai-staging \
RAILWAY_API_TOKEN=... RAILWAY_PROJECT_ID=... RAILWAY_ENVIRONMENT_ID=... RAILWAY_SERVICE_ID=... \
python scripts/apply_staging_idil_user.py
```

Re-running either script after the account has been created is a no-op
(`status: already_present`), which makes both scripts safe to retry after a timeout.
