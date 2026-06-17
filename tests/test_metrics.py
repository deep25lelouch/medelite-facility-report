from medelite import normalize, presentation, report
from medelite.models import ManualInputs, QAReport


def test_build_metrics_maps_all_twelve(kendall_claims, state_averages_rows):
    qa = QAReport(ccn="686123")
    m = normalize.build_metrics(kendall_claims, state_averages_rows, "FL", qa)
    assert m.str_hospitalization == 18.7
    assert m.str_hospitalization_national == 21.5
    assert m.str_hospitalization_state == 23.8
    assert m.str_ed_visit == 13.9
    assert m.lt_hospitalization == 1.86
    assert m.lt_hospitalization_national == 1.65
    assert m.lt_ed_visit == 6.94
    assert m.lt_ed_visit_state == 1.21


def test_build_metrics_resolves_hashed_average_columns(kendall_claims, state_averages_rows):
    qa = QAReport(ccn="686123")
    m = normalize.build_metrics(kendall_claims, state_averages_rows, "FL", qa)
    # this value lives behind a truncated+hashed slug (..._who_had_an_outpatient_em_d911)
    assert m.str_ed_visit_national == 11.6


def test_build_metrics_missing_claims_is_na_but_averages_resolve(state_averages_rows):
    qa = QAReport(ccn="686123")
    m = normalize.build_metrics([], state_averages_rows, "FL", qa)
    assert m.str_hospitalization is None
    assert m.str_hospitalization_national == 21.5


def test_report_includes_25_rows_with_metrics(kendall_raw, kendall_claims, state_averages_rows, blank_manual):
    rep = report.assemble_report("686123", kendall_raw, blank_manual, kendall_claims, state_averages_rows)
    assert rep.metrics is not None
    rows = presentation.all_rows(rep)
    assert len(rows) == 25  # 13 MVP + 12 metrics
    d = dict(rows)
    assert d["Short Term Hospitalization"] == "18.7%"
    assert d["LT Hospitalization"] == "1.86"
    assert d["STR ED Visits State Avg."] == "9.3%"


def test_report_without_claims_has_13_rows(kendall_raw, blank_manual):
    rep = report.assemble_report("686123", kendall_raw, blank_manual)
    assert rep.metrics is None
    assert len(presentation.all_rows(rep)) == 13
