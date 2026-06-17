"""Domain-level normalization.

Turns raw CMS rows into the structured values the report needs:
- Provider Information -> name, composed location, state, certified beds, star ratings.
- Claims QM + State US Averages -> the 12 hospitalization/ED metrics (facility + national + state).
"""
from __future__ import annotations

from typing import Any, Optional

from medelite import mapping
from medelite import qa as qa_tools
from medelite.models import HospEDMetrics, QAReport, QAStatus, StarRatings


def find_by_prefix(raw: dict[str, Any], prefix: str) -> Optional[Any]:
    """Return the value of the first key starting with `prefix`.

    The PDC API truncates long column names and appends a hash (e.g.
    'number_of_outpatient_emergency_department_visits_per_1000_l_de9d'); matching on the stable
    prefix survives a refresh that changes the hash.
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


# --- Bonus: the 12 hospitalization / ED metrics -------------------------------------------------

def _find_avg_row(rows: list[dict[str, Any]], key: Optional[str]) -> Optional[dict[str, Any]]:
    """Find the State-US-Averages row whose `state_or_nation` matches (e.g. 'NATION' or 'FL')."""
    if not key:
        return None
    target = str(key).strip().upper()
    for r in rows:
        if str(r.get("state_or_nation", "")).strip().upper() == target:
            return r
    return None


def _facility_score(row: Optional[dict[str, Any]], spec: "mapping.MetricSpec", qa: QAReport) -> Optional[float]:
    """Facility measure value: prefer the risk-adjusted score, fall back to observed."""
    label = mapping.FIELDS_BY_KEY[spec.key].label
    if row is None:
        qa.add(spec.key, QAStatus.MISSING, f"{label}: measure not reported for this facility.")
        return None
    adjusted = qa_tools.parse_float(row.get("adjusted_score"))
    if adjusted is not None:
        return adjusted
    observed = qa_tools.parse_float(row.get("observed_score"))
    if observed is not None:
        qa.add(spec.key, QAStatus.COERCED, f"{label}: used observed score (adjusted was empty).")
        return observed
    qa.add(spec.key, QAStatus.MISSING, f"{label}: no adjusted or observed score available.")
    return None


def _avg_value(row: Optional[dict[str, Any]], prefix: str, label: str, qa: QAReport) -> Optional[float]:
    if row is None:
        qa.add(label, QAStatus.MISSING, f"{label}: averages row not found.")
        return None
    value = qa_tools.parse_float(find_by_prefix(row, prefix))
    if value is None:
        qa.add(label, QAStatus.MISSING, f"{label}: value missing in averages row.")
    return value


def build_metrics(
    claims_rows: list[dict[str, Any]],
    state_avg_rows: list[dict[str, Any]],
    state: Optional[str],
    qa: QAReport,
) -> HospEDMetrics:
    """Assemble the 12-metric model from the Claims QM rows (facility) and State US Averages rows."""
    by_measure = {str(r.get("measure_description", "")).strip(): r for r in claims_rows}
    nation_row = _find_avg_row(state_avg_rows, "NATION")
    state_row = _find_avg_row(state_avg_rows, state)

    values: dict[str, Optional[float]] = {}
    for spec in mapping.METRIC_SPECS:
        label = mapping.FIELDS_BY_KEY[spec.key].label
        values[spec.key] = _facility_score(by_measure.get(spec.claims_measure), spec, qa)
        values[f"{spec.key}_national"] = _avg_value(nation_row, spec.avg_prefix, f"{label} (national avg)", qa)
        values[f"{spec.key}_state"] = _avg_value(state_row, spec.avg_prefix, f"{label} (state avg)", qa)
    return HospEDMetrics(**values)
