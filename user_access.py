"""Named-user authentication and role identity for CER-AI.

This module contains no clinical rules. Accounts are supplied as a Railway secret containing only
password hashes; raw passwords are never stored. Sessions are opaque, bounded, in-memory tokens in a
Secure/HttpOnly/SameSite=Strict cookie. A process restart intentionally requires users to sign in again.
"""

from __future__ import annotations

from collections import OrderedDict, defaultdict, deque
from contextvars import ContextVar, Token
from dataclasses import dataclass
import hashlib
import json
import os
import re
import secrets
import unicodedata
from threading import RLock
from time import monotonic
from typing import Any, Dict, Optional

from fastapi import Body, HTTPException, Request
from fastapi.responses import JSONResponse


ROLE_OWNER = "OWNER"
ROLE_DOCTOR = "DOCTOR"
ALLOWED_ROLES = frozenset({ROLE_OWNER, ROLE_DOCTOR})
SESSION_COOKIE = "cer_ai_session"
NAMED_USERS_ENABLED = os.getenv("CERAI_NAMED_USERS_ENABLED", "0").strip() == "1"
# Temporary supervised trial mode. Existing named-user deployments enter the trial flow unless
# they explicitly opt out; deployments without named users remain unchanged. Set this to 0 to
# restore the password-backed registry without changing or deleting the stored account hashes.
TRIAL_NAME_LOGIN_ENABLED = os.getenv(
    "CERAI_TRIAL_NAME_LOGIN_ENABLED",
    "1" if NAMED_USERS_ENABLED else "0",
).strip() == "1"
SESSION_TTL_SECONDS = max(
    900,
    min(int(os.getenv("CERAI_SESSION_TTL_SECONDS", "43200")), 86400),
)
MAX_SESSIONS = max(16, min(int(os.getenv("CERAI_MAX_USER_SESSIONS", "256")), 2048))
COOKIE_SECURE = os.getenv("CERAI_SESSION_COOKIE_SECURE", "1").strip() != "0"
LOGIN_FAILURE_LIMIT = max(3, min(int(os.getenv("CERAI_LOGIN_FAILURE_LIMIT", "10")), 50))
LOGIN_FAILURE_WINDOW_SECONDS = max(
    60,
    min(int(os.getenv("CERAI_LOGIN_FAILURE_WINDOW_SECONDS", "900")), 86400),
)
_USER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class UserConfigurationError(RuntimeError):
    """Named-user configuration is unsafe or malformed."""


@dataclass(frozen=True)
class Principal:
    user_id: str
    username: str
    display_name: str
    role: str

    def public(self) -> Dict[str, str]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
        }


@dataclass(frozen=True)
class UserAccount:
    principal: Principal
    password_hash: str
    enabled: bool = True


_lock = RLock()
_users_by_username: Dict[str, UserAccount] = {}
_sessions: "OrderedDict[str, tuple[Principal, float]]" = OrderedDict()
_failed_logins: Dict[str, deque[float]] = defaultdict(deque)
_current_principal: ContextVar[Optional[Principal]] = ContextVar(
    "cer_ai_current_principal",
    default=None,
)


def normalize_username(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def hash_password(
    password: str,
    *,
    salt: Optional[bytes] = None,
    n: int = 16384,
    r: int = 8,
    p: int = 1,
) -> str:
    """Create a portable scrypt verifier. Intended for the offline helper script, not login."""
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("CER-AI account passwords must contain at least 12 characters.")
    salt = salt or os.urandom(16)
    if len(salt) < 16:
        raise ValueError("Password-hash salt must contain at least 16 bytes.")
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=32,
    )
    return f"scrypt${n}${r}${p}${salt.hex()}${digest.hex()}"


def _parse_password_hash(value: str) -> tuple[int, int, int, bytes, bytes]:
    try:
        scheme, n_text, r_text, p_text, salt_hex, digest_hex = str(value).split("$", 5)
        n, r, p = int(n_text), int(r_text), int(p_text)
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(digest_hex)
    except (TypeError, ValueError) as exc:
        raise UserConfigurationError("Malformed CER-AI user password hash.") from exc
    if scheme != "scrypt":
        raise UserConfigurationError("Only scrypt CER-AI user password hashes are accepted.")
    if n < 16384 or n > 131072 or n & (n - 1):
        raise UserConfigurationError("Unsafe scrypt N parameter in CER-AI user registry.")
    if r < 1 or r > 16 or p < 1 or p > 8:
        raise UserConfigurationError("Unsafe scrypt r/p parameter in CER-AI user registry.")
    if len(salt) < 16 or len(digest) != 32:
        raise UserConfigurationError("Unsafe scrypt salt/digest length in CER-AI user registry.")
    return n, r, p, salt, digest


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        n, r, p, salt, expected = _parse_password_hash(encoded_hash)
        actual = hashlib.scrypt(
            str(password).encode("utf-8"),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=len(expected),
        )
    except (UserConfigurationError, ValueError, TypeError):
        return False
    return secrets.compare_digest(actual, expected)


def parse_registry(raw: str) -> Dict[str, UserAccount]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise UserConfigurationError("CERAI_USERS_JSON must be valid JSON.") from exc
    if not isinstance(payload, list) or not payload:
        raise UserConfigurationError("CERAI_USERS_JSON must contain a non-empty account list.")

    result: Dict[str, UserAccount] = {}
    user_ids: set[str] = set()
    owner_count = 0
    for item in payload:
        if not isinstance(item, dict):
            raise UserConfigurationError("Each CER-AI user entry must be an object.")
        user_id = str(item.get("user_id") or "").strip()
        username_display = " ".join(str(item.get("username") or "").strip().split())
        username = normalize_username(username_display)
        display_name = " ".join(str(item.get("display_name") or "").strip().split())
        role = str(item.get("role") or "").strip().upper()
        password_hash = str(item.get("password_hash") or "").strip()
        enabled = item.get("enabled", True) is not False

        if not _USER_ID_RE.fullmatch(user_id):
            raise UserConfigurationError("CER-AI user_id must be a stable 1-64 character token.")
        if not username or len(username) > 128:
            raise UserConfigurationError("CER-AI username is missing or too long.")
        if not display_name or len(display_name) > 160:
            raise UserConfigurationError("CER-AI display_name is missing or too long.")
        if role not in ALLOWED_ROLES:
            raise UserConfigurationError("CER-AI user role must be OWNER or DOCTOR.")
        _parse_password_hash(password_hash)
        if username in result:
            raise UserConfigurationError("Duplicate CER-AI username in user registry.")
        if user_id in user_ids:
            raise UserConfigurationError("Duplicate CER-AI user_id in user registry.")

        principal = Principal(user_id, username_display, display_name, role)
        result[username] = UserAccount(principal, password_hash, enabled)
        user_ids.add(user_id)
        if enabled and role == ROLE_OWNER:
            owner_count += 1

    if owner_count < 1:
        raise UserConfigurationError("At least one enabled OWNER account is required.")
    return result


def configure_from_environment() -> None:
    global _users_by_username
    if not NAMED_USERS_ENABLED:
        _users_by_username = {}
        return
    if TRIAL_NAME_LOGIN_ENABLED:
        _users_by_username = {}
        return
    raw = os.getenv("CERAI_USERS_JSON", "").strip()
    if not raw:
        raise UserConfigurationError(
            "CERAI_NAMED_USERS_ENABLED=1 requires CERAI_USERS_JSON with hashed accounts."
        )
    _users_by_username = parse_registry(raw)


def _prune_sessions(now: Optional[float] = None) -> None:
    now = monotonic() if now is None else now
    for token in list(_sessions):
        if _sessions[token][1] <= now:
            del _sessions[token]
    while len(_sessions) > MAX_SESSIONS:
        _sessions.popitem(last=False)


def _prune_failures(username: str, now: float) -> deque[float]:
    failures = _failed_logins[username]
    cutoff = now - LOGIN_FAILURE_WINDOW_SECONDS
    while failures and failures[0] <= cutoff:
        failures.popleft()
    return failures


def _login_allowed(username: str) -> bool:
    now = monotonic()
    with _lock:
        return len(_prune_failures(username, now)) < LOGIN_FAILURE_LIMIT


def _record_login_failure(username: str) -> None:
    now = monotonic()
    with _lock:
        failures = _prune_failures(username, now)
        failures.append(now)


def _clear_login_failures(username: str) -> None:
    with _lock:
        _failed_logins.pop(username, None)


def authenticate_credentials(username: Any, password: Any) -> Principal:
    normalized = normalize_username(username)
    if not normalized or not _login_allowed(normalized):
        if normalized and not _login_allowed(normalized):
            raise HTTPException(
                429,
                "Too many failed sign-in attempts. Try again later.",
                headers={"Retry-After": str(LOGIN_FAILURE_WINDOW_SECONDS)},
            )
        raise HTTPException(401, "Invalid username or password.")
    account = _users_by_username.get(normalized)
    if not account or not account.enabled or not verify_password(str(password or ""), account.password_hash):
        _record_login_failure(normalized)
        raise HTTPException(401, "Invalid username or password.")
    _clear_login_failures(normalized)
    return account.principal


def authenticate_trial_name(value: Any) -> Principal:
    """Create a stable DOCTOR identity from a displayed name during supervised trial use."""
    display_name = " ".join(str(value or "").strip().split())
    if not 2 <= len(display_name) <= 160:
        raise HTTPException(422, "Doctor name must contain 2 to 160 characters.")
    if not any(character.isalpha() for character in display_name):
        raise HTTPException(422, "Doctor name must contain letters.")
    if any(unicodedata.category(character).startswith("C") for character in display_name):
        raise HTTPException(422, "Doctor name contains unsupported characters.")
    normalized = unicodedata.normalize("NFKC", display_name).casefold()
    identity_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return Principal(
        user_id=f"trial-{identity_digest}",
        username=display_name,
        display_name=display_name,
        role=ROLE_DOCTOR,
    )


def create_session(principal: Principal) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        _prune_sessions()
        _sessions[token] = (principal, monotonic() + SESSION_TTL_SECONDS)
        _sessions.move_to_end(token)
        _prune_sessions()
    return token


def remove_session(token: str) -> None:
    with _lock:
        _sessions.pop(str(token or ""), None)


def principal_for_token(token: str) -> Optional[Principal]:
    with _lock:
        _prune_sessions()
        record = _sessions.get(str(token or ""))
        if not record:
            return None
        principal, _expires = record
        _sessions[str(token)] = (principal, monotonic() + SESSION_TTL_SECONDS)
        _sessions.move_to_end(str(token))
        return principal


def authenticate_request(request: Request) -> Optional[Principal]:
    if not NAMED_USERS_ENABLED:
        return None
    return principal_for_token(request.cookies.get(SESSION_COOKIE, ""))


def bind_current_principal(principal: Principal) -> Token:
    return _current_principal.set(principal)


def reset_current_principal(token: Token) -> None:
    _current_principal.reset(token)


def current_principal() -> Optional[Principal]:
    return _current_principal.get()


def require_current_principal() -> Principal:
    principal = current_principal()
    if principal is None:
        raise HTTPException(401, "CER-AI sign-in required.")
    return principal


def install(core: Any) -> None:
    """Install authentication endpoints and expose request-auth hooks to the security boundary."""
    if getattr(core, "_cerai_named_user_access_installed", False):
        return
    configure_from_environment()

    core._cerai_named_users_enabled = NAMED_USERS_ENABLED
    core._cerai_trial_name_login_enabled = TRIAL_NAME_LOGIN_ENABLED
    core._cerai_authenticate_request = authenticate_request
    core._cerai_bind_principal = bind_current_principal
    core._cerai_reset_principal = reset_current_principal
    core._cerai_current_principal = current_principal

    def audit(event_type: str, **kwargs) -> None:
        callback = getattr(core, "_cerai_audit_event", None)
        if callback is not None:
            callback(event_type, **kwargs)

    if NAMED_USERS_ENABLED:
        @core.app.post("/auth/login")
        def login(payload: Dict[str, Any] = Body(...)):
            if TRIAL_NAME_LOGIN_ENABLED:
                principal = authenticate_trial_name(
                    payload.get("display_name", payload.get("username"))
                )
                auth_mode = "TRIAL_NAME"
            else:
                principal = authenticate_credentials(payload.get("username"), payload.get("password"))
                auth_mode = "PASSWORD"
            token = create_session(principal)
            try:
                audit(
                    "LOGIN_SUCCESS",
                    actor=principal,
                    details={"role": principal.role, "authentication_mode": auth_mode},
                )
            except Exception:
                remove_session(token)
                raise
            response = JSONResponse({"user": principal.public()})
            response.set_cookie(
                SESSION_COOKIE,
                token,
                max_age=SESSION_TTL_SECONDS,
                httponly=True,
                secure=COOKIE_SECURE,
                samesite="strict",
                path="/",
            )
            return response

        @core.app.post("/auth/logout")
        def logout(request: Request):
            token = request.cookies.get(SESSION_COOKIE, "")
            principal = principal_for_token(token)
            remove_session(token)
            if principal is not None:
                audit("LOGOUT", actor=principal)
            response = JSONResponse({"status": "SIGNED_OUT"})
            response.delete_cookie(SESSION_COOKIE, path="/")
            return response

        @core.app.get("/auth/me")
        def me(request: Request):
            principal = authenticate_request(request)
            if principal is None:
                raise HTTPException(401, "CER-AI sign-in required.")
            return {"user": principal.public()}

    core._cerai_named_user_access_installed = True


def _configure_for_tests(
    users: Dict[str, UserAccount], *, enabled: bool = True, trial: bool = False
) -> None:
    global _users_by_username, NAMED_USERS_ENABLED, TRIAL_NAME_LOGIN_ENABLED
    with _lock:
        _users_by_username = dict(users)
        _sessions.clear()
        _failed_logins.clear()
    NAMED_USERS_ENABLED = enabled
    TRIAL_NAME_LOGIN_ENABLED = trial


def _reset_for_tests() -> None:
    global _users_by_username, NAMED_USERS_ENABLED, TRIAL_NAME_LOGIN_ENABLED
    with _lock:
        _users_by_username = {}
        _sessions.clear()
        _failed_logins.clear()
    NAMED_USERS_ENABLED = False
    TRIAL_NAME_LOGIN_ENABLED = False
