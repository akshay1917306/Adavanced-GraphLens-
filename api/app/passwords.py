"""Secrets for sign-in: password hashing, the password rules, recovery codes and random tokens.

Passwords and recovery codes are hashed with argon2id (memory 19 MiB, 2 passes, 1 lane: the OWASP
minimum for argon2id). Random session secrets and reset tokens have 256 bits, so a plain SHA-256 is
enough to store them. Nothing here logs a secret. See docs/phases/phase-8-v1-5/THREATS.md.
"""

import hashlib
import hmac
import secrets
import threading
from contextlib import contextmanager

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MIN_PASSWORD = 10
MAX_PASSWORD = 128
CODES_PER_SET = 8
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I
CODE_CHARS = 12  # 12 characters of a 32-letter alphabet = 60 bits
HASH_SLOTS = 2  # at most this many hashes run at once; others wait a little, then get "busy"
HASH_WAIT_SECONDS = 2.0

_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
_slots = threading.BoundedSemaphore(HASH_SLOTS)

# A hash of a random value, checked when the account does not exist, so the time looks the same.
_DUMMY = _hasher.hash(secrets.token_urlsafe(16))


class Busy(Exception):
    """Every hashing slot stayed taken for too long."""


@contextmanager
def _slot():
    if not _slots.acquire(timeout=HASH_WAIT_SECONDS):
        raise Busy
    try:
        yield
    finally:
        _slots.release()


def hash_secret(value: str) -> str:
    with _slot():
        return _hasher.hash(value)


def verify_secret(stored: str | None, value: str) -> bool:
    """True when `value` matches `stored`. With no stored hash the work is still done."""
    with _slot():
        try:
            _hasher.verify(stored or _DUMMY, value)
        except (VerificationError, InvalidHashError):
            return False
    return stored is not None


def needs_rehash(stored: str) -> bool:
    return _hasher.check_needs_rehash(stored)


COMMON = frozenset(
    """password passw0rd p@ssw0rd p@ssword password1 password12 password123 password1234 1234567890
    12345678 123456789 1234567 qwertyuiop qwerty123 qwerty1234 1q2w3e4r5t 1qaz2wsx qazwsxedc
    iloveyou1 iloveyou123 letmein123 welcome123 welcome1234 admin12345 administrator abc123456
    abcd123456 abcdefghij 0123456789 9876543210 1111111111 0000000000 1234512345 monkey1234
    dragon1234 football1 baseball1 superman1 sunshine1 princess1 trustno1 changeme123 changeme
    letmein1234 master1234 shadow1234 michael123 jennifer1 computer1 internet1 starwars1 whatever1
    freedom123 passpass12 qwertyui12 asdfghjkl1 asdfghjkl12 zxcvbnm123 zaq12wsxcde 123qweasd
    qweasdzxc1 pa55word12 pa55w0rd12 test123456 testtest12 testing123 guest12345 default123
    root123456 hello12345 helloworld1 lovelove12 987654321 1029384756 147258369 159753456
    graphlens1 graphlens12 graphlens123""".split()
)


def check_password(password: str, email: str) -> str | None:
    """A short reason (for the screen) when the password is not acceptable, else None."""
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return f"Use at most {MAX_PASSWORD} characters."
    lowered = password.casefold()
    local = email.casefold().split("@")[0]
    if lowered in COMMON or lowered == email.casefold() or (len(local) >= 4 and lowered == local):
        return "That password is too common or too close to your email. Choose another."
    if len(set(password)) < 4:
        return "Use a password with more different characters."
    return None


def new_recovery_codes() -> list[str]:
    """Eight codes like `ABCD-EFGH-JKLM`."""
    codes = []
    for _ in range(CODES_PER_SET):
        raw = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHARS))
        codes.append("-".join(raw[i : i + 4] for i in range(0, CODE_CHARS, 4)))
    return codes


def normalise_code(value: str) -> str:
    """What a person may type (lower case, spaces, missing dashes) turned into the stored form."""
    raw = "".join(ch for ch in value.upper() if ch.isalnum())
    return raw


def code_for_hash(code: str) -> str:
    return normalise_code(code)


def new_secret() -> str:
    return secrets.token_urlsafe(32)


def fast_hash(value: str) -> str:
    """For 256-bit random values only (never for a password or a recovery code)."""
    return hashlib.sha256(value.encode()).hexdigest()


def same(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
