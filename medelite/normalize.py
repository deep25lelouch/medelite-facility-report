"""Domain-level normalization: turn a raw CMS Provider Information row into the structured values
the report needs (name, composed location, state, certified beds, star ratings)."""
from __future__ import annotations

from typing import Any, Optional

from medelite import qa as qa_tools
from medelite.models import QAReport, StarRatings


def find_by_prefix(raw: dict[str, Any], prefix: str) -> Optional[Any]:
    """Return the value of the first key starting with `prefix`.

    The PDC API truncates long column names and appends a hash (e.g.
    'number_of_outpatient_emergency_department_visits_per_1000_l_de9d'); matching on the stable
    prefix survives a refresh that changes the hash. Used by the bonus metric mapping.
    """
    for key, value in raw.items():
        if key.startswith(prefix):
            return value
    return None


def compose_location(raw: dict[str, Any]) -> str:
    """Build 'Address, City, ST' from the provider row, matching the snapshot format.

    Falls back to the API's single `location` field if the components are absent.
    """
    parts = [str(raw.get(k, "")).strip() for k in ("provider_address", "citytown", "state")]
    parts = [p for p in parts if p]
    if parts:
        return ", ".join(parts)
    return str(raw.get("location", "")).strip()


def normalize_ratings(raw: dict[str, Any], qa: QAReport) -> StarRatings:
    """Coerce the four CMS Five-Star ratings into a StarRatings model (footnote-aware)."""
    return StarRatings(
        overall=qa_tools.coerce_rating(
            raw, "overall_rating", "Overall Star Rating", qa, "overall_rating_footnote"
        ),
        health_inspection=qa_tools.coerce_rating(
            raw, "health_inspection_rating", "Health Inspection", qa, "health_inspection_rating_footnote"
        ),
        staffing=qa_tools.coerce_rating(
            raw, "staffing_rating", "Staffing", qa, "staffing_rating_footnote"
        ),
        quality_of_resident_care=qa_tools.coerce_rating(
            raw, "qm_rating", "Quality of Resident Care", qa, "qm_rating_footnote"
        ),
    )
