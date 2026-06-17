from medelite import qa as qa_tools
from medelite.models import QAReport, QAStatus


def _qa() -> QAReport:
    return QAReport(ccn="686123")


def test_coerce_rating_valid():
    qa = _qa()
    assert qa_tools.coerce_rating({"overall_rating": "4"}, "overall_rating", "Overall", qa) == 4
    assert qa.ok


def test_coerce_rating_empty_with_footnote():
    qa = _qa()
    raw = {"staffing_rating": "", "staffing_rating_footnote": "23"}
    result = qa_tools.coerce_rating(raw, "staffing_rating", "Staffing", qa, "staffing_rating_footnote")
    assert result is None
    assert any(i.status == QAStatus.FOOTNOTE for i in qa.issues)
    assert qa.ok  # a footnote is informational, not a structural failure


def test_coerce_rating_out_of_range():
    qa = _qa()
    assert qa_tools.coerce_rating({"overall_rating": "9"}, "overall_rating", "Overall", qa) is None
    assert any(i.status == QAStatus.OUT_OF_RANGE for i in qa.issues)
    assert not qa.ok


def test_coerce_rating_unparseable():
    qa = _qa()
    assert qa_tools.coerce_rating({"overall_rating": "N/A"}, "overall_rating", "Overall", qa) is None
    assert not qa.ok


def test_coerce_rating_rejects_non_finite():
    # regression: float("INF")/("nan")/("1e999") must not crash int(); they become OUT_OF_RANGE -> None
    for bad in ("INF", "inf", "-inf", "nan", "1e999"):
        qa = _qa()
        assert qa_tools.coerce_rating({"overall_rating": bad}, "overall_rating", "Overall", qa) is None
        assert not qa.ok


def test_coerce_int_tolerates_float_string():
    qa = _qa()
    assert qa_tools.coerce_int({"number_of_certified_beds": "120"}, "number_of_certified_beds", "Beds", qa) == 120
    assert qa_tools.coerce_int({"number_of_certified_beds": "120.0"}, "number_of_certified_beds", "Beds", qa) == 120


def test_coerce_int_rejects_non_finite():
    qa = _qa()
    assert qa_tools.coerce_int({"number_of_certified_beds": "INF"}, "number_of_certified_beds", "Beds", qa) is None
    assert any(i.status == QAStatus.OUT_OF_RANGE for i in qa.issues)


def test_coerce_int_missing():
    qa = _qa()
    assert qa_tools.coerce_int({}, "number_of_certified_beds", "Beds", qa) is None
    assert any(i.status == QAStatus.MISSING for i in qa.issues)


def test_assert_schema_flags_drift():
    qa = _qa()
    qa_tools.assert_schema({"provider_name": "X"}, ("provider_name", "overall_rating"), qa)
    assert any(i.status == QAStatus.SCHEMA_DRIFT and i.field == "overall_rating" for i in qa.issues)
    assert not qa.ok
