from medelite.validation import parse_ccn_list, validate_ccn


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


def test_parse_ccn_list_splits_dedupes_and_preserves_order():
    assert parse_ccn_list("686123, 105007\n686123  245001") == ["686123", "105007", "245001"]


def test_parse_ccn_list_blank_returns_empty():
    assert parse_ccn_list("") == []
    assert parse_ccn_list("   \n  ") == []
