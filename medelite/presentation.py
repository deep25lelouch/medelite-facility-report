"""Presentation helpers shared by the UI and the exporters.

Turns a ReportModel into the ordered (label, value) rows of the Facility Assessment Snapshot,
driven by the mapping registry so the layout is defined in exactly one place. Blank/None values
render as 'N/A'.
"""
from __future__ import annotations

from typing import Any

from medelite import mapping
from medelite.models import ReportModel

NA = "N/A"


def format_value(value: Any) -> str:
    if value is None:
        return NA
    s = str(value).strip()
    return s if s else NA


def mvp_rows(rep: ReportModel) -> list[tuple[str, str]]:
    """Ordered (label, formatted_value) pairs for the 13 MVP rows, in Kendall-snapshot order."""
    values: dict[str, Any] = {
        "facility_name": rep.facility_name,
        "location": rep.location,
        "emr": rep.manual.emr,
        "census_capacity": rep.census_capacity,
        "current_census": rep.manual.current_census,
        "patient_type": rep.manual.patient_type,
        "previous_coverage": rep.manual.previous_coverage,
        "previous_provider_performance": rep.manual.previous_provider_performance,
        "medical_coverage": rep.manual.medical_coverage,
        "overall": rep.ratings.overall,
        "health_inspection": rep.ratings.health_inspection,
        "staffing": rep.ratings.staffing,
        "quality_of_resident_care": rep.ratings.quality_of_resident_care,
    }
    return [(spec.label, format_value(values.get(spec.key))) for spec in mapping.MVP_FIELDS]
