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


@pytest.fixture
def kendall_claims() -> list:
    """Four Claims QM rows mirroring the live ijh5-nb2v shape (representative scores)."""
    def row(desc: str, adjusted: str, observed: str) -> dict:
        return {
            "cms_certification_number_ccn": "686123",
            "measure_description": desc,
            "resident_type": "",
            "adjusted_score": adjusted,
            "observed_score": observed,
            "expected_score": "",
        }

    return [
        row("Percentage of short-stay residents who were rehospitalized after a nursing home admission", "18.7", "19.0"),
        row("Percentage of short-stay residents who had an outpatient emergency department visit", "13.9", "14.1"),
        row("Number of hospitalizations per 1000 long-stay resident days", "1.86", "1.90"),
        row("Number of outpatient emergency department visits per 1000 long-stay resident days", "6.94", "7.00"),
    ]


@pytest.fixture
def state_averages_rows() -> list:
    """NATION + two state rows mirroring State US Averages, using the API's truncated+hashed slugs."""
    def row(sn, str_hosp, str_ed, lt_hosp, lt_ed) -> dict:
        return {
            "state_or_nation": sn,
            "percentage_of_short_stay_residents_who_were_rehospitalized__1d02": str_hosp,
            "percentage_of_short_stay_residents_who_had_an_outpatient_em_d911": str_ed,
            "number_of_hospitalizations_per_1000_longstay_resident_days": lt_hosp,
            "number_of_outpatient_emergency_department_visits_per_1000_l_de9d": lt_ed,
        }

    return [
        row("NATION", "21.5", "11.6", "1.65", "1.70"),
        row("FL", "23.8", "9.3", "1.95", "1.21"),
        row("CA", "20.0", "10.0", "1.50", "1.30"),
    ]
