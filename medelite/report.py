"""Assemble a ReportModel from CMS data + manual operational inputs.

build_report() is the convenience entry point (fetches, then assembles); assemble_report() is the
pure function the UI and tests use when the raw payload is already in hand (no network).
"""
from __future__ import annotations

from typing import Any, Optional

from medelite import cms_client, config, mapping, normalize
from medelite import qa as qa_tools
from medelite.models import ManualInputs, QAReport, QAStatus, ReportModel


def resolve_facility_name(override: str, provider_raw: Optional[dict[str, Any]]) -> str:
    """Override wins; else the CMS legal name; else a neutral placeholder.

    The INFINITE brand banner is a separate constant and is never derived from this value.
    """
    override = (override or "").strip()
    if override:
        return override
    if provider_raw:
        name = str(provider_raw.get("provider_name", "")).strip()
        if name:
            return name
    return "Unknown Facility"


def assemble_report(
    ccn: str,
    provider_raw: Optional[dict[str, Any]],
    manual: ManualInputs,
) -> ReportModel:
    """Build the report from an already-fetched provider row (or None if not found)."""
    ccn = (ccn or "").strip()
    qa = QAReport(ccn=ccn)

    if provider_raw is None:
        qa.add(
            "cms_record",
            QAStatus.MISSING,
            f"No CMS Provider Information record found for CCN '{ccn}'. "
            "Report built from manual inputs only.",
        )
        return ReportModel(
            ccn=ccn,
            facility_name=resolve_facility_name(manual.facility_name_override, None),
            cms_record_found=False,
            manual=manual,
            medicare_url=config.medicare_profile_url(ccn, None),
            qa=qa,
        )

    qa_tools.assert_schema(provider_raw, mapping.REQUIRED_PROVIDER_SLUGS, qa)
    state = str(provider_raw.get("state", "")).strip() or None

    return ReportModel(
        ccn=ccn,
        facility_name=resolve_facility_name(manual.facility_name_override, provider_raw),
        location=normalize.compose_location(provider_raw),
        state=state,
        census_capacity=qa_tools.coerce_int(
            provider_raw, "number_of_certified_beds", "Census Capacity", qa
        ),
        cms_record_found=True,
        ratings=normalize.normalize_ratings(provider_raw, qa),
        manual=manual,
        medicare_url=config.medicare_profile_url(ccn, state),
        qa=qa,
    )


def build_report(ccn: str, manual: ManualInputs) -> ReportModel:
    """Fetch the CMS record then assemble the report. Raises CMSClientError on API failure."""
    provider_raw = cms_client.get_provider(ccn)
    return assemble_report(ccn, provider_raw, manual)
