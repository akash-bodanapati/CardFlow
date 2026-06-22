from typing import Any, Dict, List

import pytest

from app.agent.nodes import _extraction_looks_valid
# Import features to test
from app.services.dedup_service import (is_duplicate, normalize_email,
                                        normalize_phone)


def test_normalize_phone() -> None:
    """Tests the phone number normalization logic."""
    assert normalize_phone("+91 98765-43210") == "919876543210"
    assert normalize_phone("9876543210") == "9876543210"
    assert normalize_phone("") == ""
    assert normalize_phone("+1 (555) 123-4567") == "15551234567"


def test_normalize_email() -> None:
    """Tests the email address normalization logic."""
    assert normalize_email(" TEST@example.com ") == "test@example.com"
    assert normalize_email("") == ""
    assert normalize_email("john.doe+alias@gmail.com") == "john.doe+alias@gmail.com"


def test_is_duplicate() -> None:
    """Tests contact duplicate checking against mock rows."""
    mock_rows: List[Dict[str, Any]] = [
        {"Name": "Alice", "Phone": "+91 98765-43210", "Email": "alice@example.com"},
        {"Name": "Bob", "Phone": "1-555-123-4567", "Email": "bob@domain.org"},
    ]

    # Email match
    match_email = is_duplicate("0000000000", "ALICE@example.com", mock_rows)
    assert match_email is not None
    assert match_email["Name"] == "Alice"

    # Phone suffix match (without +91 vs with)
    match_phone = is_duplicate("9876543210", "other@example.com", mock_rows)
    assert match_phone is not None
    assert match_phone["Name"] == "Alice"

    # Phone mismatch but email mismatch
    no_match = is_duplicate("9999999999", "new@example.com", mock_rows)
    assert no_match is None


def test_extraction_looks_valid() -> None:
    """Tests validation of raw extraction structure."""
    # Valid extractions (at least one key field)
    assert (
        _extraction_looks_valid({"name": "Priya Sharma", "phone": "", "email": ""})
        is True
    )
    assert (
        _extraction_looks_valid({"name": "", "phone": "9876543210", "email": ""})
        is True
    )
    assert (
        _extraction_looks_valid({"name": "", "phone": "", "email": "p@sharma.com"})
        is True
    )

    # Invalid extractions (all empty or none)
    assert (
        _extraction_looks_valid(
            {"name": "", "phone": "", "email": "", "company": "NovaTech"}
        )
        is False
    )
    assert _extraction_looks_valid({}) is False
    assert _extraction_looks_valid(None) is False
