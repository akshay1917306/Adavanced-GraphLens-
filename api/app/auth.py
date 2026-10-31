"""Sign-in routes (Phase 8, Part B). Threats and measures: docs/phases/phase-8-v1-5/THREATS.md.

Rules that hold in every route here:
- a request body is never logged and never echoed; errors name no email, password or code;
- unknown email and wrong password give the same answer, after the same amount of hashing work;
- every attempt counts toward a limit per address and a limit per account name (known or not);
- a password or a recovery code is checked with argon2id; nothing secret is stored in plain text.
"""

import hashlib
import hmac
import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.accounts import (
    ABSOLUTE_DAYS,
    Accounts,
    EmailTaken,
    SessionUser,
    UserCapReached,
    get_accounts,
)
from app.config import get_settings
from app.passwords import (
    Busy,
    check_password,
    hash_secret,
    needs_rehash,
    new_recovery_codes,
    normalise_code,
    verify_secret,
)
from app.ratelimit import Limiter, admin_limit, client_ip, get_limiter
from app.schemas import ErrorResponse
from app.visitor import VisitorRequired, verify_token

router = APIRouter()

EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,189}\.[^@\s]{2,63}$")
LOGIN_WINDOW = 15 * 60
HOUR = 3600
SESSION_SECONDS = ABSOLUTE_DAYS * 86400


def _fail(code: str, message: str, http_status: int) -> JSONResponse:
    body = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=http_status, content=body.model_dump())


def _account_key(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()[:32]


def _email(value: str) -> str:
    value = value.strip().casefold()
    if len(value) > 254 or not EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


class EmailBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return _email(value)


class SignupBody(EmailBody):
    password: str = Field(max_length=200)


class LoginBody(EmailBody):
    password: str = Field(max_length=200)


class ResetBody(EmailBody):
    recovery_code: str = Field(min_length=1, max_length=40)
    new_password: str = Field(max_length=200)


class LinkResetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=20, max_length=100)
    new_password: str = Field(max_length=200)


class PasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(max_length=200)


class ClaimBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(max_length=200)
    anonymous_token: str = Field(max_length=200)


class AdminLinkBody(EmailBody):
    pass


class SessionResponse(BaseModel):
    token: str
    max_age_seconds: int
    email: str
    recovery_codes: list[str] | None = None  # only at sign-up, shown once


class MeResponse(BaseModel):
    email: str
    unused_recovery_codes: int


class CodesResponse(BaseModel):
    recovery_codes: list[str]


class DoneResponse(BaseModel):
    ok: bool = True
    detail: dict | None = None


class LinkResponse(BaseModel):
    path: str
    url: str
    expires_in_minutes: int


def current_session(
    accounts: Annotated[Accounts, Depends(get_accounts)],
    x_visitor_token: Annotated[str | None, Header()] = None,
) -> SessionUser:
    user = accounts.resolve_session(x_visitor_token or "")
    if user is None:
        raise VisitorRequired
    return user


def _session_reply(token: str, email: str, codes: list[str] | None = None) -> SessionResponse:
    return SessionResponse(
        token=token, max_age_seconds=SESSION_SECONDS, email=email, recovery_codes=codes
    )


def _count_attempt(limiter: Limiter, ip: str, email: str, scope: str, limit: int, window: int):
    limiter.hit(f"{scope}-ip", ip, limit, window)
    limiter.hit(f"{scope}-acct", _account_key(email), limit, window)


# --------------------------------------------------------------------------- sign up and in


@router.post("/api/v1/auth/signup", response_model=SessionResponse)
def signup(
    body: SignupBody,
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    settings = get_settings()
    limiter.hit("signup-ip", ip, settings.rate_signup_ip_per_hour, HOUR)
    problem = check_password(body.password, body.email)
    if problem:
        return _fail("weak_password", problem, 422)
    codes = new_recovery_codes()
    try:
        password_hash = hash_secret(body.password)
        code_hashes = [hash_secret(normalise_code(c)) for c in codes]
    except Busy:
        return _fail("busy", "The server is busy. Please try again shortly.", 503)
    try:
        user_id, _ = accounts.create_account(
            body.email, password_hash, code_hashes, settings.max_users
        )
    except EmailTaken:
        return _fail("email_unavailable", "This email cannot be used. Try signing in.", 409)
    except UserCapReached:
        return _fail("signups_closed", "New accounts are closed on this installation.", 403)
    return _session_reply(accounts.create_session(user_id), body.email, codes)


@router.post("/api/v1/auth/login", response_model=SessionResponse)
def login(
    body: LoginBody,
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    _count_attempt(limiter, ip, body.email, "login", 10, LOGIN_WINDOW)
    user = accounts.find_user(body.email)
    try:
        correct = verify_secret(user["password_hash"] if user else None, body.password)
    except Busy:
        return _fail("busy", "The server is busy. Please try again shortly.", 503)
    if not (user and correct):
        accounts.audit(user["id"] if user else None, "login_failed")
        return _fail("invalid_credentials", "Email or password is wrong.", 401)
    if needs_rehash(user["password_hash"]):
        accounts.set_password_hash(user["id"], hash_secret(body.password))
    return _session_reply(accounts.create_session(user["id"]), user["email"])


@router.post("/api/v1/auth/logout", response_model=DoneResponse)
def logout(
    session: Annotated[SessionUser, Depends(current_session)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    accounts.revoke_session(session.session_id)
    return DoneResponse()


@router.get("/api/v1/auth/me", response_model=MeResponse)
def me(
    session: Annotated[SessionUser, Depends(current_session)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    row = accounts.get_user(session.user_id)
    return MeResponse(email=session.email, unused_recovery_codes=int(row["unused_codes"]))


# --------------------------------------------------------------------------- password needed


def _confirm(
    session: SessionUser,
    password: str,
    ip: str,
    limiter: Limiter,
    accounts: Accounts,
) -> JSONResponse | None:
    """None when the password is right, else the error answer. Counts like a sign-in."""
    _count_attempt(limiter, ip, session.email, "login", 10, LOGIN_WINDOW)
    row = accounts.get_user(session.user_id)
    try:
        correct = verify_secret(row["password_hash"] if row else None, password)
    except Busy:
        return _fail("busy", "The server is busy. Please try again shortly.", 503)
    if not (row and correct):
        return _fail("invalid_credentials", "Password is wrong.", 401)
    return None


@router.post("/api/v1/auth/logout-all", response_model=DoneResponse)
def logout_all(
    body: PasswordBody,
    session: Annotated[SessionUser, Depends(current_session)],
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    refused = _confirm(session, body.password, ip, limiter, accounts)
    if refused:
        return refused
    accounts.revoke_all_sessions(session.user_id)
    accounts.audit(session.user_id, "logout_all")
    return DoneResponse()


@router.post("/api/v1/auth/recovery-codes", response_model=CodesResponse)
def new_codes(
    body: PasswordBody,
    session: Annotated[SessionUser, Depends(current_session)],
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    refused = _confirm(session, body.password, ip, limiter, accounts)
    if refused:
        return refused
    codes = new_recovery_codes()
    try:
        hashes = [hash_secret(normalise_code(c)) for c in codes]
    except Busy:
        return _fail("busy", "The server is busy. Please try again shortly.", 503)
    accounts.replace_codes(session.user_id, hashes)
    return CodesResponse(recovery_codes=codes)


@router.delete("/api/v1/auth/account", response_model=DoneResponse)
def delete_account(
    body: PasswordBody,
    session: Annotated[SessionUser, Depends(current_session)],
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    refused = _confirm(session, body.password, ip, limiter, accounts)
    if refused:
        return refused
    return DoneResponse(detail=accounts.delete_account(session.user_id))


@router.post("/api/v1/auth/claim", response_model=DoneResponse)
def claim(
    body: ClaimBody,
    session: Annotated[SessionUser, Depends(current_session)],
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    """Move the anonymous history of this browser into the account. Once per anonymous visitor."""
    refused = _confirm(session, body.password, ip, limiter, accounts)
    if refused:
        return refused
    secret = get_settings().visitor_token_secret.get_secret_value()
    anonymous = verify_token(body.anonymous_token, secret)
    moved = (
        accounts.claim(session.user_id, session.home_visitor_id, anonymous) if anonymous else None
    )
    if moved is None:
        return _fail("nothing_to_claim", "There is no unclaimed history in this browser.", 404)
    return DoneResponse(detail=moved)


# --------------------------------------------------------------------------- reset


@router.post("/api/v1/auth/reset", response_model=SessionResponse)
def reset_with_code(
    body: ResetBody,
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    _count_attempt(limiter, ip, body.email, "reset", 10, HOUR)
    problem = check_password(body.new_password, body.email)
    if problem:
        return _fail("weak_password", problem, 422)
    failed = _fail("reset_failed", "The email or the recovery code is not right.", 400)
    user = accounts.find_user(body.email)
    wanted = normalise_code(body.recovery_code)
    match: UUID | None = None
    try:
        codes = accounts.unused_codes(user["id"]) if user else []
        if not codes:
            verify_secret(None, wanted)  # the same work as one real check
        for code_id, code_hash in codes:
            if verify_secret(code_hash, wanted):
                match = code_id
                break
        if user is None or match is None:
            if user is not None:
                accounts.audit(user["id"], "reset_code_failed")
            return failed
        token = accounts.finish_reset(user["id"], hash_secret(body.new_password), "code", match)
    except Busy:
        return _fail("busy", "The server is busy. Please try again shortly.", 503)
    except LookupError:
        return failed
    return _session_reply(token, user["email"])


@router.post("/api/v1/auth/reset-with-link", response_model=SessionResponse)
def reset_with_link(
    body: LinkResetBody,
    ip: Annotated[str, Depends(client_ip)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
    accounts: Annotated[Accounts, Depends(get_accounts)],
):
    limiter.hit("reset-link-ip", ip, 10, HOUR)
    failed = _fail("reset_failed", "This link is not valid any more.", 400)
    user_id = accounts.take_reset_token(body.token)
    if user_id is None:
        return failed
    row = accounts.get_user(user_id)
    if row is None:
        return failed
    problem = check_password(body.new_password, row["email"])
    if problem:
        return _fail("weak_password", problem, 422)
    try:
        token = accounts.finish_reset(user_id, hash_secret(body.new_password), "link")
    except Busy:
        return _fail("busy", "The server is busy. Please try again shortly.", 503)
    return _session_reply(token, row["email"])


@router.post(
    "/api/v1/admin/reset-link",
    response_model=LinkResponse,
    dependencies=[Depends(admin_limit)],
)
def admin_reset_link(
    body: AdminLinkBody,
    accounts: Annotated[Accounts, Depends(get_accounts)],
    x_admin_key: Annotated[str | None, Header()] = None,
):
    """For the owner: a one-time link (30 minutes) for an account that lost its way in."""
    key = get_settings().admin_api_key.get_secret_value()
    if not key:
        return _fail("admin_disabled", "Admin routes are switched off.", 403)
    if x_admin_key is None or not hmac.compare_digest(x_admin_key, key):
        return _fail("unauthorized", "Missing or wrong admin key.", 401)
    user = accounts.find_user(body.email)
    if user is None:
        return _fail("not_found", "No account with this email.", 404)
    token = accounts.issue_reset_token(user["id"])
    path = f"/reset#token={token}"
    origin = get_settings().web_origin.rstrip("/")
    return LinkResponse(path=path, url=origin + path, expires_in_minutes=30)
