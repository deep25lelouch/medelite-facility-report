from medelite.validation import validate_ccn


def test_valid_ccn_returns_none():
    assert validate_ccn("686123") is None


def test_surrounding_whitespace_is_tolerated():
    assert validate_ccn("  686123  ") is None


def test_empty_or_blank_is_rejected():
    assert validate_ccn("") is not None
    assert validate_ccn("   ") is not None


def test_wrong_length_is_rejected():
    assert validate_ccn("12345") is not None
    assert validate_ccn("1234567") is not None


def test_non_alphanumeric_is_rejected():
    assert validate_ccn("68-123") is not None
    assert validate_ccn("68 123") is not None
