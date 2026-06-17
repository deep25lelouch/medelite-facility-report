"""Input validation helpers (framework-agnostic, no Streamlit imports)."""
from __future__ import annotations

import re
from typing import Optional

CCN_LENGTH = 6


def validate_ccn(ccn: str) -> Optional[str]:
    """Return a human-readable error message if the CCN is malformed, else None.

    CMS Certification Numbers are 6-character alphanumeric facility identifiers (nursing-home CCNs
    are typically 6 digits, e.g. 686123). Catching obvious entry mistakes here avoids a pointless
    API round-trip and gives the user immediate, specific feedback.
    """
    cleaned = ccn.strip()
    if not cleaned:
        return "Please enter a CMS Certification Number."
    if len(cleaned) != CCN_LENGTH:
        return (
            f"A CMS Certification Number is exactly {CCN_LENGTH} characters "
            f"(e.g. 686123); you entered {len(cleaned)}."
        )
    if not cleaned.isalnum():
        return "A CMS Certification Number should contain only letters and digits — no spaces or symbols."
    return None


def parse_ccn_list(raw: str) -> list[str]:
    """Split a free-text blob of CCNs into a de-duplicated, order-preserving list.

    Accepts any mix of commas, spaces, and newlines as separators. Does not validate the CCNs
    themselves -- pair each result with validate_ccn(). Used by the compare-facilities mode.
    """
    tokens = [token.strip() for token in re.split(r"[\s,]+", raw or "") if token.strip()]
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            ordered.append(token)
    return ordered
