from __future__ import annotations

import pytest

from budget.accounts import (
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    hash_password,
    normalize_email,
    validate_email,
    validate_password,
    verify_password,
)
from budget.models import ValidationError


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email("  Taylor@Example.COM \n") == "taylor@example.com"


@pytest.mark.parametrize("email", ["a@b.co", "first.last+tag@sub.example.com"])
def test_validate_email_accepts_valid(email: str) -> None:
    validate_email(email)


@pytest.mark.parametrize(
    "email",
    ["", "plain", "@example.com", "a@", "a@b", "a@@b.co", "a b@c.co", "a@.co", "a@b."],
)
def test_validate_email_rejects_invalid(email: str) -> None:
    with pytest.raises(ValidationError):
        validate_email(email)


def test_validate_email_rejects_too_long() -> None:
    with pytest.raises(ValidationError):
        validate_email("a" * 250 + "@b.co")


def test_password_length_boundaries() -> None:
    validate_password("x" * MIN_PASSWORD_LENGTH)
    validate_password("x" * MAX_PASSWORD_LENGTH)
    with pytest.raises(ValidationError):
        validate_password("x" * (MIN_PASSWORD_LENGTH - 1))
    with pytest.raises(ValidationError):
        validate_password("x" * (MAX_PASSWORD_LENGTH + 1))


def test_password_has_no_composition_rules() -> None:
    validate_password("alllowercaseletters")
    validate_password("            ")  # spaces count


def test_hash_is_not_the_password_and_is_salted() -> None:
    first = hash_password("correct horse battery")
    second = hash_password("correct horse battery")
    assert "correct horse battery" not in first
    assert first != second


def test_verify_password() -> None:
    password_hash = hash_password("correct horse battery")
    assert verify_password(password_hash, "correct horse battery")
    assert not verify_password(password_hash, "wrong horse battery")


def test_verify_password_rejects_oversized_input_quickly() -> None:
    password_hash = hash_password("correct horse battery")
    assert not verify_password(password_hash, "x" * 500_000)
