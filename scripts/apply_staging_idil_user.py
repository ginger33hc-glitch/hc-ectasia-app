"""Apply the "idil" staging user to Railway's CERAI_USERS_JSON variable.

STAGING-ONLY. This script must only ever be pointed at the cer-ai-staging service in the
staging environment. It never touches production, and it will refuse to run unless the
operator explicitly confirms the target via CERAI_STAGING_APPLY_CONFIRM=1 (see below).

It delegates all account-generation logic to ensure_staging_idil_user.py so the two scripts
stay in lockstep and the update is idempotent: if "idil" already exists, nothing is changed.

Two ways to apply the update, controlled by RAILWAY_API_TOKEN:

1. Railway API (preferred): if RAILWAY_API_TOKEN, RAILWAY_PROJECT_ID, RAILWAY_ENVIRONMENT_ID,
   and RAILWAY_SERVICE_ID are all set, this script calls the Railway public GraphQL API
   (variableUpsert) to set CERAI_USERS_JSON on the cer-ai-staging service in the staging
   environment, then exits. Railway is responsible for triggering a redeploy.

2. Local/manual mode (fallback): if the Railway API variables are not set, this script only
   prints the new CERAI_USERS_JSON value and instructions for setting it by hand via the
   Railway dashboard or `railway variables --set`. It never writes to a local .env file
   automatically, to avoid accidentally leaking the staging registry into a committed file.

Safety rails:
  * Refuses to run unless CERAI_STAGING_APPLY_CONFIRM=1 is set, forcing an explicit,
    deliberate invocation rather than an accidental one from a shared shell history.
  * Never runs against anything other than the service/environment named by
    RAILWAY_SERVICE_NAME / RAILWAY_ENVIRONMENT_NAME if those are present, guarding against
    a stale token pointed at the wrong project.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import urllib.request


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.ensure_staging_idil_user import EnsureUserError, ensure_idil_user  # noqa: E402

RAILWAY_GRAPHQL_ENDPOINT = "https://backboard.railway.app/graphql/v2"
EXPECTED_ENVIRONMENT_NAME = "staging"
EXPECTED_SERVICE_NAME = "cer-ai-staging"


class ApplyGuardError(RuntimeError):
    """The staging-only safety checks failed; refusing to apply anything."""


def _assert_staging_target() -> None:
    if os.environ.get("CERAI_STAGING_APPLY_CONFIRM", "").strip() != "1":
        raise ApplyGuardError(
            "Refusing to run: set CERAI_STAGING_APPLY_CONFIRM=1 to confirm this is being "
            "run deliberately against staging."
        )
    environment_name = os.environ.get("RAILWAY_ENVIRONMENT_NAME", "").strip().lower()
    if environment_name and environment_name != EXPECTED_ENVIRONMENT_NAME:
        raise ApplyGuardError(
            f"Refusing to run: RAILWAY_ENVIRONMENT_NAME={environment_name!r}, expected "
            f"{EXPECTED_ENVIRONMENT_NAME!r}. This script must never target production."
        )
    service_name = os.environ.get("RAILWAY_SERVICE_NAME", "").strip().lower()
    if service_name and service_name != EXPECTED_SERVICE_NAME:
        raise ApplyGuardError(
            f"Refusing to run: RAILWAY_SERVICE_NAME={service_name!r}, expected "
            f"{EXPECTED_SERVICE_NAME!r}."
        )


def _railway_api_credentials() -> dict[str, str] | None:
    token = os.environ.get("RAILWAY_API_TOKEN", "").strip()
    project_id = os.environ.get("RAILWAY_PROJECT_ID", "").strip()
    environment_id = os.environ.get("RAILWAY_ENVIRONMENT_ID", "").strip()
    service_id = os.environ.get("RAILWAY_SERVICE_ID", "").strip()
    if not (token and project_id and environment_id and service_id):
        return None
    return {
        "token": token,
        "project_id": project_id,
        "environment_id": environment_id,
        "service_id": service_id,
    }


def _set_variable_via_api(credentials: dict[str, str], value: str) -> None:
    mutation = """
        mutation VariableUpsert($input: VariableUpsertInput!) {
            variableUpsert(input: $input)
        }
    """
    variables = {
        "input": {
            "projectId": credentials["project_id"],
            "environmentId": credentials["environment_id"],
            "serviceId": credentials["service_id"],
            "name": "CERAI_USERS_JSON",
            "value": value,
        }
    }
    body = json.dumps({"query": mutation, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        RAILWAY_GRAPHQL_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {credentials['token']}",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise ApplyGuardError(f"Railway API rejected the update: {payload['errors']}")


def main() -> None:
    _assert_staging_target()

    raw = os.environ.get("CERAI_USERS_JSON", "")
    try:
        report = ensure_idil_user(raw)
    except EnsureUserError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, sort_keys=True))
        raise SystemExit(1)

    if report["status"] == "already_present":
        print(json.dumps(report, sort_keys=True))
        return

    credentials = _railway_api_credentials()
    if credentials is None:
        print(
            "RAILWAY_API_TOKEN/RAILWAY_PROJECT_ID/RAILWAY_ENVIRONMENT_ID/RAILWAY_SERVICE_ID "
            "not fully set. Not calling the Railway API. Apply the new CERAI_USERS_JSON "
            "value below to the cer-ai-staging service in the staging environment manually "
            "(e.g. via the Railway dashboard or `railway variables --set`)."
        )
        print(
            json.dumps(
                {k: v for k, v in report.items() if k != "cerai_users_json"},
                sort_keys=True,
            )
        )
        print(report["cerai_users_json"])
        return

    _set_variable_via_api(credentials, report["cerai_users_json"])
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "cerai_users_json"},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except ApplyGuardError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, sort_keys=True))
        raise SystemExit(1)
