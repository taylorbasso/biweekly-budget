"""Account rules: email/password validation and password hashing.

Plain Python, no Flask imports (Constitution Principle II). Hashing uses Werkzeug's
salted, slow scrypt; the library's check function compares in constant time.
"""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from budget.models import ValidationError

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128
MAX_EMAIL_LENGTH = 254


def normalize_email(raw: str) -> str:
    """Emails are case-insensitive and stored trimmed and lowercased."""
    return raw.strip().lower()


def validate_email(email: str) -> None:
    """Validate an already-normalized email; raises ValidationError."""
    if len(email) > MAX_EMAIL_LENGTH:
        raise ValidationError("Email address is too long")
    local, separator, domain = email.partition("@")
    if (
        not separator
        or not local
        or "@" in domain
        or "." not in domain
        or domain.startswith(".")
        or domain.endswith(".")
        or any(ch.isspace() for ch in email)
    ):
        raise ValidationError("Enter a valid email address")


def validate_password(password: str) -> None:
    """Length-only policy (NIST SP 800-63B); raises ValidationError."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValidationError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters"
        )


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """False for oversized input without hashing it (keeps huge inputs cheap)."""
    if len(password) > MAX_PASSWORD_LENGTH:
        return False
    return check_password_hash(password_hash, password)
