"""Shared pytest fixtures.

`kendall_raw` is a representative Provider Information payload that mirrors the *live* 686123
response shape (confirmed via scripts/verify.py) and uses the sample snapshot's published values
(ratings 1/1/2/4, 120 certified beds, Miami FL). It is fixture data for unit tests, not a claim
about any real record beyond what the snapshot states.
"""
import pytest

from medelite.models import ManualInputs


@pytest.fixture
def kendall_raw() -> dict:
    return {
        "cms_certification_number_ccn": "686123",
        "provider_name": "KENDALL LAKES HEALTHCARE AND REHAB CENTER",
        "provider_address": "5280 SW 157TH AVE",
        "citytown": "MIAMI",
        "state": "FL",
        "zip_code": "33193",
        "number_of_certified_beds": "120",
        "average_number_of_residents_per_day": "112.0",
        "overall_rating": "1",
        "overall_rating_footnote": "",
        "health_inspection_rating": "1",
        "health_inspection_rating_footnote": "",
        "staffing_rating": "2",
        "staffing_rating_footnote": "",
        "qm_rating": "4",
        "qm_rating_footnote": "",
        "location": "5280 SW 157TH AVE,MIAMI,FL,33193",
    }


@pytest.fixture
def blank_manual() -> ManualInputs:
    return ManualInputs()


@pytest.fixture
def full_manual() -> ManualInputs:
    return ManualInputs(
        emr="PCC",
        current_census=112,
        patient_type="Long-term & Short-term",
        previous_coverage="Yes",
        previous_provider_performance="About 30 patients/day",
        medical_coverage="Optometry, PCP, Podiatry",
    )
