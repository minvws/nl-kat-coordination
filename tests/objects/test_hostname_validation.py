"""Unit tests for hostname validation function (no database required)."""

import pytest
from django.core.exceptions import ValidationError

from objects.models import validate_hostname


def test_validate_hostname_valid_cases():
    """Test that valid hostnames pass validation."""
    # Single label
    validate_hostname("example")

    # Two labels
    validate_hostname("example.com")

    # Subdomain
    validate_hostname("sub.example.com")

    # Multi-level subdomain
    validate_hostname("a.b.c.example.com")

    # With hyphens
    validate_hostname("test-123.example-site.com")

    # With digits
    validate_hostname("server01.example.com")

    # Single character labels
    validate_hostname("a.b.c")

    # Mixed case (validation is case-insensitive)
    validate_hostname("Example.COM")

    # Max label length (63 characters)
    validate_hostname("a" * 63 + ".example.com")

    # Max total length (253 characters)
    label = "a" * 62
    validate_hostname(f"{label}.{label}.{label}.{label}")  # 251 chars


def test_validate_hostname_empty():
    """Test that empty hostname raises ValidationError."""
    with pytest.raises(ValidationError, match="Hostname cannot be empty"):
        validate_hostname("")


def test_validate_hostname_empty_labels():
    """Test that hostnames with empty labels raise ValidationError."""
    # Consecutive dots
    with pytest.raises(ValidationError, match="empty labels"):
        validate_hostname("example..com")

    # Leading dot
    with pytest.raises(ValidationError, match="empty labels"):
        validate_hostname(".example.com")

    # Single trailing dot creates empty label
    with pytest.raises(ValidationError, match="empty labels"):
        validate_hostname("example.com.")

    # Multiple trailing dots
    with pytest.raises(ValidationError, match="empty labels"):
        validate_hostname("example.com...")

    # Note: The Hostname model's clean() and save() methods normalize
    # a single trailing dot before validation, but the validator itself
    # treats any trailing dot as creating an empty label


def test_validate_hostname_label_too_long():
    """Test that labels longer than 63 characters raise ValidationError."""
    # Label with 64 characters (one too many)
    long_label = "a" * 64
    with pytest.raises(ValidationError, match="too long.*63 characters"):
        validate_hostname(f"{long_label}.example.com")


def test_validate_hostname_total_length_too_long():
    """Test that hostnames longer than 253 characters raise ValidationError."""
    # Create a hostname with 255 characters
    label = "a" * 63
    long_hostname = f"{label}.{label}.{label}.{label}"  # 255 characters
    with pytest.raises(ValidationError, match="too long.*253 characters"):
        validate_hostname(long_hostname)


def test_validate_hostname_hyphen_at_start():
    """Test that labels starting with hyphens raise ValidationError."""
    with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
        validate_hostname("-example.com")

    with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
        validate_hostname("sub.-example.com")


def test_validate_hostname_hyphen_at_end():
    """Test that labels ending with hyphens raise ValidationError."""
    with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
        validate_hostname("example-.com")

    with pytest.raises(ValidationError, match="cannot start or end with a hyphen"):
        validate_hostname("sub.example-.com")


def test_validate_hostname_hyphen_in_middle():
    """Test that hyphens in the middle of labels are valid."""
    validate_hostname("ex-ample.com")
    validate_hostname("test-site-123.example.com")


def test_validate_hostname_invalid_characters():
    """Test that hostnames with invalid characters raise ValidationError."""
    # Underscore
    with pytest.raises(ValidationError, match="invalid characters"):
        validate_hostname("example_test.com")

    # Space
    with pytest.raises(ValidationError, match="invalid characters"):
        validate_hostname("example test.com")

    # Special characters
    with pytest.raises(ValidationError, match="invalid characters"):
        validate_hostname("example@test.com")

    with pytest.raises(ValidationError, match="invalid characters"):
        validate_hostname("example!.com")

    with pytest.raises(ValidationError, match="invalid characters"):
        validate_hostname("example#test.com")

    with pytest.raises(ValidationError, match="invalid characters"):
        validate_hostname("example$.com")
