"""Field-mapping registry - the single source of truth.

One declarative list maps every row of the Medelite Facility Assessment Snapshot to its source
(CMS dataset slug, manual input, or derived) and its clean display label. Fetch, normalization,
rendering, and export all read from this so the report layout is defined in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Source(str, Enum):
    CMS_PROVIDER = "cms_provider"      # Provider Information      (4pq5-n9py)
    CMS_CLAIMS = "cms_claims"          # Claims Quality Measures   (ijh5-nb2v)   [bonus]
    CMS_STATE_AVG = "cms_state_avg"    # State US Averages         (xcdc-v8bm)   [bonus]
    MANUAL = "manual"                  # entered by the user
    DERIVED = "derived"                # computed (resolved name, medicare url, ...)


@dataclass(frozen=True)
class FieldSpec:
    key: str                          # internal key
    label: str                        # clean label shown on the report (matches the Kendall layout)
    source: Source
    api_slug: Optional[str] = None    # CMS field slug, for provider-sourced fields
    bonus: bool = False


# Order mirrors the rows of the Kendall Lakes "Facility Assessment Snapshot".
REPORT_FIELDS: list[FieldSpec] = [
    FieldSpec("facility_name", "Name of Facility", Source.DERIVED),                 # override > provider_name
    FieldSpec("location", "Location", Source.CMS_PROVIDER, "location"),
    FieldSpec("emr", "EMR", Source.MANUAL),
    FieldSpec("census_capacity", "Census Capacity", Source.CMS_PROVIDER, "number_of_certified_beds"),
    FieldSpec("current_census", "Current Census", Source.MANUAL),
    FieldSpec("patient_type", "Type of Patient", Source.MANUAL),
    FieldSpec("previous_coverage", "Previous Coverage from Medelite", Source.MANUAL),
    FieldSpec("previous_provider_performance", "Previous Provider Performance from Medelite", Source.MANUAL),
    FieldSpec("medical_coverage", "Medical Coverage", Source.MANUAL),
    FieldSpec("overall", "Overall Star Rating", Source.CMS_PROVIDER, "overall_rating"),
    FieldSpec("health_inspection", "Health Inspection", Source.CMS_PROVIDER, "health_inspection_rating"),
    FieldSpec("staffing", "Staffing", Source.CMS_PROVIDER, "staffing_rating"),
    FieldSpec("quality_of_resident_care", "Quality of Resident Care", Source.CMS_PROVIDER, "qm_rating"),
    # --- [bonus] 12 hospitalization / ED metrics ---
    # Facility values come from the Claims QM dataset (long format, matched by measure description);
    # *_national / *_state come from the State US Averages dataset (NATION row + the facility's state
    # row). The exact slugs/columns are confirmed by scripts/verify.py before wiring normalize.py.
    FieldSpec("str_hospitalization", "Short Term Hospitalization", Source.CMS_CLAIMS, bonus=True),
    FieldSpec("str_hospitalization_national", "STR National Avg. for Hospitalization", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("str_hospitalization_state", "STR State National Avg. for Hospitalization", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("str_ed_visit", "STR ED Visit", Source.CMS_CLAIMS, bonus=True),
    FieldSpec("str_ed_visit_national", "STR ED Visits National Avg.", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("str_ed_visit_state", "STR ED Visits State Avg.", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("lt_hospitalization", "LT Hospitalization", Source.CMS_CLAIMS, bonus=True),
    FieldSpec("lt_hospitalization_national", "LT National Avg. for Hospitalization", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("lt_hospitalization_state", "LT State National Avg. for Hospitalization", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("lt_ed_visit", "ED Visit", Source.CMS_CLAIMS, bonus=True),
    FieldSpec("lt_ed_visit_national", "LT ED Visits National Avg.", Source.CMS_STATE_AVG, bonus=True),
    FieldSpec("lt_ed_visit_state", "LT ED Visits State Avg.", Source.CMS_STATE_AVG, bonus=True),
]

# Provider-info slugs the MVP depends on; qa.py asserts these are present (schema-drift guard).
REQUIRED_PROVIDER_SLUGS: tuple[str, ...] = (
    "cms_certification_number_ccn",
    "provider_name",
    "location",
    "state",
    "number_of_certified_beds",
    "overall_rating",
    "health_inspection_rating",
    "staffing_rating",
    "qm_rating",
)

# Convenience lookups.
FIELDS_BY_KEY: dict[str, FieldSpec] = {f.key: f for f in REPORT_FIELDS}
MVP_FIELDS: list[FieldSpec] = [f for f in REPORT_FIELDS if not f.bonus]
BONUS_FIELDS: list[FieldSpec] = [f for f in REPORT_FIELDS if f.bonus]
