from medelite import presentation, report
from medelite.models import ManualInputs


def test_mvp_rows_count_and_first_row(kendall_raw, blank_manual):
    rep = report.assemble_report("686123", kendall_raw, blank_manual)
    rows = presentation.mvp_rows(rep)
    assert len(rows) == 13
    assert rows[0] == ("Name of Facility", "KENDALL LAKES HEALTHCARE AND REHAB CENTER")
    labels = [label for label, _ in rows]
    assert "Overall Star Rating" in labels
    assert "Medical Coverage" in labels


def test_mvp_rows_blanks_become_na(blank_manual):
    rep = report.assemble_report("999999", None, blank_manual)
    rows = dict(presentation.mvp_rows(rep))
    assert rows["EMR"] == "N/A"
    assert rows["Overall Star Rating"] == "N/A"
    assert rows["Name of Facility"] == "Unknown Facility"
