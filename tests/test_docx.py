from medelite import report
from medelite.export.docx import build_docx


def test_build_docx_returns_docx_bytes(kendall_raw, full_manual, kendall_claims, state_averages_rows):
    rep = report.assemble_report("686123", kendall_raw, full_manual, kendall_claims, state_averages_rows)
    data = build_docx(rep)
    assert isinstance(data, (bytes, bytearray))
    assert data[:2] == b"PK"  # .docx is a zip archive
    assert len(data) > 1000


def test_build_docx_handles_not_found(blank_manual):
    rep = report.assemble_report("999999", None, blank_manual)
    data = build_docx(rep)
    assert data[:2] == b"PK"
