"""Presentation helpers shared by the UI and the exporters.

Turns a ReportModel into the ordered (label, value) rows of the Facility Assessment Snapshot,
driven by the mapping registry so the layout is defined in exactly one place. Blank/None values
render as 'N/A'. The 12 bonus metrics are formatted as percentages (short-stay) or rates (long-stay).
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


def format_metric(key: str, value: Any) -> str:
    """Short-stay (str_*) metrics are percentages; long-stay (lt_*) are rates per 1000 days."""
    if value is None:
        return NA
    if key.startswith("str_"):
        return f"{value:.1f}%"
    return f"{value:.2f}"


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


def metric_rows(rep: ReportModel) -> list[tuple[str, str]]:
    """The 12 hospitalization/ED rows (empty list if metrics were not built)."""
    if rep.metrics is None:
        return []
    return [
        (spec.label, format_metric(spec.key, getattr(rep.metrics, spec.key, None)))
        for spec in mapping.BONUS_FIELDS
    ]


def all_rows(rep: ReportModel) -> list[tuple[str, str]]:
    """Full snapshot: 13 MVP rows followed by the 12 metric rows (when present)."""
    return mvp_rows(rep) + metric_rows(rep)
