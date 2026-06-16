from hypothesis import given, strategies as st

from medelite import qa as qa_tools
from medelite import report
from medelite.models import ManualInputs, QAReport


@given(st.text())
def test_coerce_rating_never_crashes_and_stays_in_range(value):
    qa = QAReport(ccn="x")
    result = qa_tools.coerce_rating({"r": value}, "r", "R", qa)
    assert result is None or 1 <= result <= 5


@given(st.dictionaries(st.text(), st.text()))
def test_assemble_never_crashes_on_arbitrary_payload(raw):
    rep = report.assemble_report("686123", raw, ManualInputs())
    assert rep.facility_name           # always a non-empty resolved name
    assert isinstance(rep.cms_record_found, bool)
