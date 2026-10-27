"""Anonymous visitors with signed tokens (no sign-in; see D11, D51).

A token is `v1.<visitor id>.<expiry>.<HMAC>`. Only the API can make one, so a visitor id that
someone copies or guesses is useless without the signature. A missing, forged, expired or
unknown token never gives access to anyone's data: the caller gets "visitor_required".
"""

import hashlib
import hmac
import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header

from app.config import get_settings
from app.store import Store, get_store

VERSION = "v1"
MAX_TOKEN_CHARS = 200


class VisitorRequired(Exception):
    """The request has no valid visitor token."""


class VisitorNotConfigured(Exception):
    """No signing secret is set, so no token can be issued or trusted."""


def _sign(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(visitor_id: UUID, secret: str, ttl_seconds: int, now: float | None = None) -> str:
    expires = int((time.time() if now is None else now) + ttl_seconds)
    payload = f"{VERSION}.{visitor_id}.{expires}"
    return f"{payload}.{_sign(secret, payload)}"


def verify_token(token: str, secret: str, now: float | None = None) -> UUID | None:
    """The visitor id inside a genuine, unexpired token, else None."""
    if not secret or not token or len(token) > MAX_TOKEN_CHARS:
        return None
    parts = token.split(".")
    if len(parts) != 4 or parts[0] != VERSION:
        return None
    _, raw_id, raw_expiry, signature = parts
    expected = _sign(secret, f"{VERSION}.{raw_id}.{raw_expiry}")
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        visitor_id = UUID(raw_id)
        expires = int(raw_expiry)
    except ValueError:
        return None
    if (time.time() if now is None else now) > expires:
        return None
    return visitor_id


def signing_secret() -> str:
    secret = get_settings().visitor_token_secret.get_secret_value()
    if not secret:
        raise VisitorNotConfigured
    return secret


def get_visitor(
    store: Annotated[Store, Depends(get_store)],
    x_visitor_token: Annotated[str | None, Header()] = None,
) -> UUID:
    """The visitor of this request. Deny by default."""
    secret = get_settings().visitor_token_secret.get_secret_value()
    visitor_id = verify_token(x_visitor_token or "", secret)
    if visitor_id is None or not store.visitor_exists(visitor_id):
        raise VisitorRequired
    return visitor_id
