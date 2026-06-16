"""Typed domain models - the contract between the data layer and the UI / exporters."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QAStatus(str, Enum):
    OK = "ok"
    COERCED = "coerced"            # value was parsed/converted (e.g. "5" -> 5)
    MISSING = "missing"           # field empty / not supplied by CMS
    OUT_OF_RANGE = "out_of_range"  # value failed a validation rule (e.g. rating not in 1..5)
    FOOTNOTE = "footnote"         # CMS suppressed the value and gave a footnote code
    SCHEMA_DRIFT = "schema_drift"  # an expected CMS field slug was absent from the payload


class QAIssue(BaseModel):
    field: str
    status: QAStatus
    message: str


class QAReport(BaseModel):
    """A structured record of everything the normalization/validation layer observed."""
    ccn: str
    issues: list[QAIssue] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if nothing structurally wrong was found (drift / out-of-range)."""
        bad = {QAStatus.OUT_OF_RANGE, QAStatus.SCHEMA_DRIFT}
        return not any(i.status in bad for i in self.issues)

    def add(self, field: str, status: QAStatus, message: str) -> None:
        self.issues.append(QAIssue(field=field, status=status, message=message))


class StarRatings(BaseModel):
    """CMS Five-Star ratings. None means not rated / unavailable."""
    overall: Optional[int] = None
    health_inspection: Optional[int] = None
    staffing: Optional[int] = None
    quality_of_resident_care: Optional[int] = None


class HospEDMetrics(BaseModel):
    """[Bonus] The 12 hospitalization / ED metrics. None means unavailable.

    Short-stay (STR) values are percentages; long-stay (LT) values are rates per 1000
    resident days.
    """
    str_hospitalization: Optional[float] = None
    str_hospitalization_national: Optional[float] = None
    str_hospitalization_state: Optional[float] = None
    str_ed_visit: Optional[float] = None
    str_ed_visit_national: Optional[float] = None
    str_ed_visit_state: Optional[float] = None
    lt_hospitalization: Optional[float] = None
    lt_hospitalization_national: Optional[float] = None
    lt_hospitalization_state: Optional[float] = None
    lt_ed_visit: Optional[float] = None
    lt_ed_visit_national: Optional[float] = None
    lt_ed_visit_state: Optional[float] = None


class ManualInputs(BaseModel):
    """Operational fields that do not live in the public CMS data - entered by the user."""
    facility_name_override: str = ""
    emr: str = ""
    current_census: Optional[int] = None
    patient_type: str = ""
    previous_coverage: str = ""              # "Yes" / "No" / ""
    previous_provider_performance: str = ""
    medical_coverage: str = ""


class ReportModel(BaseModel):
    """The fully assembled report - the single object every renderer consumes."""
    ccn: str
    facility_name: str                       # resolved: override > CMS legal name
    location: str = ""
    state: Optional[str] = None
    census_capacity: Optional[int] = None    # CMS number_of_certified_beds
    cms_record_found: bool = True
    ratings: StarRatings = Field(default_factory=StarRatings)
    metrics: Optional[HospEDMetrics] = None  # bonus; None until the 12 metrics are wired in
    manual: ManualInputs = Field(default_factory=ManualInputs)
    medicare_url: str = ""
    qa: QAReport
