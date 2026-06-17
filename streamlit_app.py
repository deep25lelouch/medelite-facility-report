"""Medelite Facility Assessment Report Generator - Streamlit UI (entry point)."""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from medelite import config, presentation
from medelite.cms_client import CMSClientError, get_claims, get_provider, get_state_averages
from medelite.export.pdf import build_pdf
from medelite.export.docx import build_docx
from medelite.models import ManualInputs
from medelite.report import assemble_report
from medelite.validation import parse_ccn_list, validate_ccn

st.set_page_config(page_title="Facility Assessment Snapshot", page_icon="🏥", layout="centered")

_SOURCE_ORDER = ["Facility", "U.S.", "State"]
_SOURCE_COLORS = ["#E6007E", "#9AA0B4", "#1A73E8"]
_RATING_LABELS = {"Overall Star Rating", "Health Inspection", "Staffing", "Quality of Resident Care"}

# Rows shown in the side-by-side compare view (must match labels produced by presentation.all_rows).
_COMPARE_LABELS = [
    "Location",
    "Census Capacity",
    "Overall Star Rating",
    "Health Inspection",
    "Staffing",
    "Quality of Resident Care",
    "Short Term Hospitalization",
    "STR ED Visit",
    "LT Hospitalization",
    "ED Visit",
]

_TABLE_CSS = """
<style>
  table.fas { width:100%; border-collapse:collapse; font-size:0.95rem; margin-top:0.25rem; }
  table.fas td { border:1px solid #d9d9e3; padding:8px 12px; vertical-align:top; }
  table.fas td.lbl { background:#F5F6FA; font-weight:600; width:55%; }
  table.fas td.val { width:45%; }
  table.fas td.sec { background:#FCE7F3; color:#9D174D; font-weight:700; text-align:left;
                     letter-spacing:0.5px; font-size:0.78rem; text-transform:uppercase; padding:7px 12px; }
</style>
"""


@st.cache_data(show_spinner="Fetching CMS data...")
def fetch_provider(ccn: str):
    """Cached Provider Information lookup. Returns a row dict or None."""
    return get_provider(ccn)


@st.cache_data(show_spinner=False)
def fetch_claims(ccn: str):
    """Cached Claims QM lookup (for the 12 metrics). Returns a list of rows."""
    return get_claims(ccn)


@st.cache_data(show_spinner=False)
def fetch_state_averages():
    """Cached State US Averages (national + per-state rows). Fetched once per session."""
    return get_state_averages()


def render_header() -> None:
    st.markdown(
        f"""
        <div style="text-align:center; margin-bottom:0.75rem;">
          <div>
            <span style="font-size:2rem; font-weight:800; color:{config.BRAND_COLOR};">{config.BRAND_PLATFORM}</span>
            <span style="font-size:1rem; color:#666; margin-left:0.4rem;">{config.BRAND_TAGLINE}</span>
          </div>
          <div style="font-size:1.05rem; font-weight:700; letter-spacing:3px; margin-top:0.35rem; color:#1A1A2E;">
            {config.REPORT_TITLE}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _stars_html(n: int) -> str:
    filled = '<span style="color:#F5A623;">★</span>' * n
    empty = '<span style="color:#D9D9E3;">★</span>' * (5 - n)
    return f"{filled}{empty} <span style='color:#777; font-size:0.85em;'>({n})</span>"


def render_report_table(mvp_rows, metric_rows) -> None:
    def cell_value(label: str, value: str) -> str:
        if label in _RATING_LABELS and value.isdigit() and 1 <= int(value) <= 5:
            return _stars_html(int(value))
        return html.escape(value)

    def row(label: str, value: str) -> str:
        return (
            f"<tr><td class='lbl'>{html.escape(label)}</td>"
            f"<td class='val'>{cell_value(label, value)}</td></tr>"
        )

    parts = [row(label, value) for label, value in mvp_rows]
    if metric_rows:
        parts.append("<tr><td class='sec' colspan='2'>Hospitalization &amp; ED Metrics</td></tr>")
        parts.extend(row(label, value) for label, value in metric_rows)
    st.markdown(_TABLE_CSS + f"<table class='fas'>{''.join(parts)}</table>", unsafe_allow_html=True)


def _benchmark_fig(measures, y_title: str, is_pct: bool) -> go.Figure:
    names = [row[0] for row in measures]
    fig = go.Figure()
    for offset, (source, color) in enumerate(zip(_SOURCE_ORDER, _SOURCE_COLORS)):
        vals = [row[offset + 1] for row in measures]
        labels = ["" if v is None else (f"{v:.1f}%" if is_pct else f"{v:.2f}") for v in vals]
        fig.add_bar(
            name=source,
            x=names,
            y=vals,
            marker_color=color,
            text=labels,
            textposition="outside",
            cliponaxis=False,
        )
    fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=24, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
        yaxis_title=y_title,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def render_benchmarks(rep) -> None:
    """Data cards (facility vs U.S. delta) + grouped Plotly bar charts for the 12 metrics."""
    m = rep.metrics
    if m is None:
        return

    st.divider()
    st.markdown("##### Hospitalization & ED benchmarks")
    st.caption("Facility value with the change vs the U.S. average — green means better (lower).")

    cards = [
        ("Short-stay rehospitalization", m.str_hospitalization, m.str_hospitalization_national, True),
        ("Short-stay ED visit", m.str_ed_visit, m.str_ed_visit_national, True),
        ("Long-stay hospitalization / 1k", m.lt_hospitalization, m.lt_hospitalization_national, False),
        ("Long-stay ED visit / 1k", m.lt_ed_visit, m.lt_ed_visit_national, False),
    ]
    for col, (label, fac, nat, is_pct) in zip(st.columns(4), cards):
        with col:
            if fac is None:
                st.metric(label, "N/A")
                continue
            value = f"{fac:.1f}%" if is_pct else f"{fac:.2f}"
            delta = None
            if nat is not None:
                diff = fac - nat
                delta = f"{diff:+.1f}%" if is_pct else f"{diff:+.2f}"
            st.metric(label, value, delta=delta, delta_color="inverse")

    short_stay = [
        ("Rehospitalization", m.str_hospitalization, m.str_hospitalization_national, m.str_hospitalization_state),
        ("ED visit", m.str_ed_visit, m.str_ed_visit_national, m.str_ed_visit_state),
    ]
    long_stay = [
        ("Hospitalization", m.lt_hospitalization, m.lt_hospitalization_national, m.lt_hospitalization_state),
        ("ED visit", m.lt_ed_visit, m.lt_ed_visit_national, m.lt_ed_visit_state),
    ]

    left, right = st.columns(2)
    with left:
        st.caption("Short-stay (% of residents)")
        st.plotly_chart(_benchmark_fig(short_stay, "Percent", True), use_container_width=True)
    with right:
        st.caption("Long-stay (per 1,000 resident days)")
        st.plotly_chart(_benchmark_fig(long_stay, "Rate", False), use_container_width=True)


def sidebar_inputs() -> tuple[str, ManualInputs]:
    st.sidebar.header("Facility lookup")
    ccn = st.sidebar.text_input(
        "CMS Certification Number (CCN)", help="6-character CMS facility ID, e.g. 686123"
    ).strip()

    st.sidebar.divider()
    st.sidebar.subheader("Manual details")
    name_override = st.sidebar.text_input(
        "Facility name (override)", help="Leave blank to use the official CMS name."
    )
    emr = st.sidebar.text_input("EMR", placeholder="e.g. PCC")
    current_census = st.sidebar.number_input("Current census", min_value=0, max_value=100000, value=0, step=1)
    patient_type = st.sidebar.text_input("Type of patient", placeholder="e.g. Long-term & Short-term")
    previous_coverage = st.sidebar.selectbox("Previous coverage from Medelite", ["", "Yes", "No"])
    previous_performance = st.sidebar.text_input(
        "Previous provider performance", placeholder="e.g. About 30 patients/day"
    )
    medical_coverage = st.sidebar.text_input("Medical coverage", placeholder="e.g. Optometry, PCP, Podiatry")

    manual = ManualInputs(
        facility_name_override=name_override,
        emr=emr,
        current_census=int(current_census) if current_census else None,
        patient_type=patient_type,
        previous_coverage=previous_coverage,
        previous_provider_performance=previous_performance,
        medical_coverage=medical_coverage,
    )
    return ccn, manual


def render_qa(rep) -> None:
    issues = rep.qa.issues
    if not issues:
        st.caption("Data quality: all checks passed.")
        return
    label = f"Data quality report ({len(issues)} note{'s' if len(issues) != 1 else ''})"
    with st.expander(label):
        for i in issues:
            st.markdown(f"- **{i.field}** — _{i.status.value}_: {i.message}")


def _load_report(ccn: str, manual: ManualInputs):
    """Fetch + assemble one facility. Raises CMSClientError only on the provider call."""
    provider_raw = fetch_provider(ccn)
    claims_rows: list = []
    state_avg_rows: list = []
    if provider_raw is not None:
        try:
            claims_rows = fetch_claims(ccn)
            state_avg_rows = fetch_state_averages()
        except CMSClientError:
            pass
    return assemble_report(ccn, provider_raw, manual, claims_rows, state_avg_rows)


def render_single() -> None:
    ccn, manual = sidebar_inputs()

    if not ccn:
        st.info("Enter a facility CCN in the sidebar to generate a snapshot.")
        return

    ccn_error = validate_ccn(ccn)
    if ccn_error:
        st.error(ccn_error)
        return

    try:
        provider_raw = fetch_provider(ccn)
    except CMSClientError as exc:
        st.error(
            "Couldn't reach the CMS Provider Data API right now — this is usually a temporary "
            "network issue. Please try again in a moment."
        )
        st.caption(f"Technical detail: {exc}")
        return

    claims_rows: list = []
    state_avg_rows: list = []
    if provider_raw is not None:
        try:
            claims_rows = fetch_claims(ccn)
            state_avg_rows = fetch_state_averages()
        except CMSClientError:
            st.info(
                "The facility profile loaded, but the hospitalization/ED metrics couldn't be "
                "fetched right now — the rest of the snapshot is complete."
            )

    rep = assemble_report(ccn, provider_raw, manual, claims_rows, state_avg_rows)

    if not rep.cms_record_found:
        st.warning(
            f"No CMS nursing-home record matched CCN **{ccn}**. Double-check the number on "
            "Medicare Care Compare — or, if it's correct, the snapshot below uses your manual inputs."
        )

    st.markdown(f"#### {html.escape(rep.facility_name)}")
    render_report_table(presentation.mvp_rows(rep), presentation.metric_rows(rep))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Download PDF",
            data=build_pdf(rep),
            file_name=f"{rep.ccn or 'facility'}_assessment_snapshot.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download Word",
            data=build_docx(rep),
            file_name=f"{rep.ccn or 'facility'}_assessment_snapshot.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    with col3:
        st.link_button("Medicare Care Compare \u2197", rep.medicare_url, use_container_width=True)

    render_benchmarks(rep)
    render_qa(rep)


def _render_comparison(reports) -> None:
    rowmaps = [(rep, dict(presentation.all_rows(rep))) for rep in reports]

    st.markdown(f"#### Comparing {len(reports)} facilities")

    columns = {}
    for rep, rowmap in rowmaps:
        header = f"{rep.facility_name} ({rep.ccn})"
        columns[header] = [rowmap.get(label, "N/A") for label in _COMPARE_LABELS]
    df = pd.DataFrame(columns, index=_COMPARE_LABELS)
    st.dataframe(df, use_container_width=True)

    names = []
    overall = []
    for rep, rowmap in rowmaps:
        name = rep.facility_name
        names.append(name if len(name) <= 24 else name[:23] + "…")
        value = rowmap.get("Overall Star Rating", "")
        overall.append(int(value) if value.isdigit() else None)

    fig = go.Figure(
        go.Bar(
            x=names,
            y=overall,
            marker_color="#E6007E",
            text=["" if o is None else str(o) for o in overall],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=24, b=10),
        yaxis_title="Overall star rating",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
    fig.update_yaxes(range=[0, 5], showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Pulled live from CMS. Higher star ratings are better; lower hospitalization/ED figures are better.")


def render_compare() -> None:
    st.sidebar.header("Compare facilities")
    raw = st.sidebar.text_area(
        "CCNs to compare",
        placeholder="One per line or comma-separated:\n686123\n105007\n245001",
        height=150,
        help="Enter 2 or more CMS Certification Numbers.",
    )
    ccns = parse_ccn_list(raw)
    if len(ccns) < 2:
        st.info("Enter two or more CCNs in the sidebar to compare facilities side by side.")
        return

    max_facilities = 6
    if len(ccns) > max_facilities:
        st.info(f"Showing the first {max_facilities} of {len(ccns)} CCNs for readability.")
        ccns = ccns[:max_facilities]

    reports = []
    for ccn in ccns:
        error = validate_ccn(ccn)
        if error:
            st.warning(f"Skipping `{ccn}` — {error}")
            continue
        try:
            reports.append(_load_report(ccn, ManualInputs()))
        except CMSClientError:
            st.warning(f"Skipping `{ccn}` — couldn't reach the CMS API.")

    if not reports:
        st.warning("No facilities could be loaded. Check the CCNs and try again.")
        return

    _render_comparison(reports)


def main() -> None:
    render_header()
    mode = st.sidebar.radio("Mode", ["Single facility", "Compare facilities"], index=0)
    st.sidebar.divider()
    if mode == "Single facility":
        render_single()
    else:
        render_compare()


if __name__ == "__main__":
    main()
