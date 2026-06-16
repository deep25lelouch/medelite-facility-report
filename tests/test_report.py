from medelite import config, report
from medelite.models import ManualInputs


def test_assemble_happy_path(kendall_raw, blank_manual):
    rep = report.assemble_report("686123", kendall_raw, blank_manual)
    assert rep.cms_record_found
    assert rep.facility_name == "KENDALL LAKES HEALTHCARE AND REHAB CENTER"
    assert rep.location == "5280 SW 157TH AVE, MIAMI, FL"
    assert rep.state == "FL"
    assert rep.census_capacity == 120
    assert (rep.ratings.overall, rep.ratings.staffing, rep.ratings.quality_of_resident_care) == (1, 2, 4)
    assert rep.medicare_url == config.medicare_profile_url("686123", "FL")
    assert rep.qa.ok


def test_override_wins(kendall_raw, blank_manual):
    m = ManualInputs(facility_name_override="Kendall Lakes SNF")
    rep = report.assemble_report("686123", kendall_raw, m)
    assert rep.facility_name == "Kendall Lakes SNF"


def test_name_falls_back_to_cms_when_override_blank(kendall_raw):
    rep = report.assemble_report("686123", kendall_raw, ManualInputs(facility_name_override="   "))
    assert rep.facility_name == "KENDALL LAKES HEALTHCARE AND REHAB CENTER"


def test_not_found_uses_override(blank_manual):
    rep = report.assemble_report("999999", None, ManualInputs(facility_name_override="Some Facility"))
    assert not rep.cms_record_found
    assert rep.facility_name == "Some Facility"
    assert rep.medicare_url == config.medicare_profile_url("999999", None)


def test_not_found_placeholder(blank_manual):
    rep = report.assemble_report("999999", None, blank_manual)
    assert not rep.cms_record_found
    assert rep.facility_name == "Unknown Facility"


def test_schema_drift_recorded(kendall_raw, blank_manual):
    bad = dict(kendall_raw)
    del bad["qm_rating"]
    rep = report.assemble_report("686123", bad, blank_manual)
    assert not rep.qa.ok
