from medelite import report
from medelite.export.pdf import build_pdf
from medelite.models import ManualInputs


def test_build_pdf_returns_pdf_bytes(kendall_raw, full_manual):
    rep = report.assemble_report("686123", kendall_raw, full_manual)
    pdf = build_pdf(rep)
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000


def test_build_pdf_handles_not_found(blank_manual):
    rep = report.assemble_report("999999", None, blank_manual)
    pdf = build_pdf(rep)
    assert pdf[:4] == b"%PDF"
