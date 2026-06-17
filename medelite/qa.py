"""Validation + QA recording primitives.

These helpers do the "validated coercion" work: turn raw CMS string values into typed values,
record what happened (coerced / missing / footnote / out-of-range) on a QAReport, and assert that
expected field slugs are present (schema-drift guard). The PDC API can rename/truncate columns, so
the schema check fails loud rather than silently producing nulls.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional

from medelite.models import QAReport, QAStatus

# Footnote code -> plain meaning (CMS Nursing Home data dictionary, Table 15). Explains why a value
# is shown as N/A instead of a number.
FOOTNOTE_MEANINGS: dict[str, str] = {
    "1": "Newly certified facility / less than 12-15 months of data.",
    "2": "Not enough data available to calculate a star rating.",
    "6": "Submitted data did not meet criteria to calculate a staffing measure.",
    "7": "CMS determined the value was not accurate, or data was suppressed.",
    "9": "Too few residents/stays to report.",
    "10": "Data missing or not submitted.",
    "13": "Based on a shorter time period than required.",
    "18": "Not rated due to serious quality issues (special focus facility).",
    "20": "Accuracy of the rating data could not be validated by CMS.",
    "21": "Accuracy of the measure data could not be validated by CMS.",
    "22": "Address could not be geocoded; coordinates are based on ZIP.",
    "23": "Facility did not submit staffing data.",
    "24": "High number of days without a registered nurse onsite.",
    "25": "Accuracy of staffing data could not be validated by CMS.",
    "26": "Did not submit valid staffing data for turnover; minimum points assigned.",
    "27": "Turnover data did not meet criteria; excluded and rescaled.",
    "28": "Annual measure; quarterly data not available.",
}


def assert_schema(raw: dict[str, Any], required_slugs: Iterable[str], qa: QAReport) -> None:
    """Record a SCHEMA_DRIFT issue for any required slug missing from the payload."""
    for slug in required_slugs:
        if slug not in raw:
            qa.add(
                slug,
                QAStatus.SCHEMA_DRIFT,
                f"Expected CMS field '{slug}' was not in the payload (column may have been renamed).",
            )


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _to_float(text: str) -> Optional[float]:
    """Parse a cleaned string into a FINITE float, or None.

    Rejects inf / -inf / nan and overflow (e.g. "INF", "1e999", "nan"), which otherwise blow up a
    later int() with OverflowError. CMS never sends these, but the parser must not crash on them.
    """
    try:
        value = float(text)
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def parse_float(value: Any) -> Optional[float]:
    """Best-effort finite-float parse with NO QA recording (for adjusted->observed fallback chains)."""
    s = _clean(value)
    return _to_float(s) if s is not None else None


def coerce_int(raw: dict[str, Any], slug: str, label: str, qa: QAReport) -> Optional[int]:
    """Parse an integer field; record MISSING / OUT_OF_RANGE as appropriate."""
    s = _clean(raw.get(slug))
    if s is None:
        qa.add(label, QAStatus.MISSING, f"{label}: no value supplied by CMS.")
        return None
    value = _to_float(s)  # tolerate "120" and "120.0"; rejects inf/nan
    if value is None:
        qa.add(label, QAStatus.OUT_OF_RANGE, f"{label}: could not parse '{s}' as a finite number.")
        return None
    return int(value)


def coerce_float(raw: dict[str, Any], slug: str, label: str, qa: QAReport) -> Optional[float]:
    """Parse a float field; record MISSING / OUT_OF_RANGE as appropriate."""
    s = _clean(raw.get(slug))
    if s is None:
        qa.add(label, QAStatus.MISSING, f"{label}: no value supplied by CMS.")
        return None
    value = _to_float(s)
    if value is None:
        qa.add(label, QAStatus.OUT_OF_RANGE, f"{label}: could not parse '{s}' as a finite number.")
        return None
    return value


def coerce_rating(
    raw: dict[str, Any],
    slug: str,
    label: str,
    qa: QAReport,
    footnote_slug: Optional[str] = None,
) -> Optional[int]:
    """Parse a 1-5 star rating.

    Empty value + footnote -> N/A with the footnote meaning recorded. Out-of-range, non-finite, or
    unparseable values are rejected (OUT_OF_RANGE).
    """
    s = _clean(raw.get(slug))
    if s is None:
        fn = _clean(raw.get(footnote_slug)) if footnote_slug else None
        if fn:
            meaning = FOOTNOTE_MEANINGS.get(fn, f"footnote {fn}")
            qa.add(label, QAStatus.FOOTNOTE, f"{label}: not rated ({meaning}).")
        else:
            qa.add(label, QAStatus.MISSING, f"{label}: no rating supplied by CMS.")
        return None
    value = _to_float(s)
    if value is None:
        qa.add(label, QAStatus.OUT_OF_RANGE, f"{label}: could not parse rating '{s}'.")
        return None
    rating = int(value)
    if not 1 <= rating <= 5:
        qa.add(label, QAStatus.OUT_OF_RANGE, f"{label}: rating {rating} is outside the valid 1-5 range.")
        return None
    return rating
