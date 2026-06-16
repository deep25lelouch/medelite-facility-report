from medelite import normalize
from medelite.models import QAReport


def test_compose_location_from_parts():
    raw = {"provider_address": "5280 SW 157TH AVE", "citytown": "MIAMI", "state": "FL", "location": "ignored"}
    assert normalize.compose_location(raw) == "5280 SW 157TH AVE, MIAMI, FL"


def test_compose_location_fallback_to_location_field():
    raw = {"location": "260 WEST WALNUT STREET,SYLACAUGA,AL,35150"}
    assert normalize.compose_location(raw) == "260 WEST WALNUT STREET,SYLACAUGA,AL,35150"


def test_find_by_prefix_handles_hashed_slug():
    raw = {"number_of_outpatient_emergency_department_visits_per_1000_l_de9d": "1.21"}
    assert normalize.find_by_prefix(raw, "number_of_outpatient_emergency_department_visits_per_1000_l") == "1.21"
    assert normalize.find_by_prefix(raw, "nonexistent_prefix") is None


def test_normalize_ratings(kendall_raw):
    qa = QAReport(ccn="686123")
    r = normalize.normalize_ratings(kendall_raw, qa)
    assert (r.overall, r.health_inspection, r.staffing, r.quality_of_resident_care) == (1, 1, 2, 4)
    assert qa.ok
