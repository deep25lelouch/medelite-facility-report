"""Medelite Facility Assessment Report Generator - Streamlit UI (entry point)."""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from medelite import config, presentation
from medelite.cms_client import CMSClientError, get_claims, get_provider, get_state_averages
from medelite.export.compare_pdf import build_comparison_pdf
from medelite.export.docx import build_docx
from medelite.export.pdf import build_pdf
from medelite.models import ManualInputs
from medelite.report import assemble_report
from medelite.validation import parse_ccn_list, validate_ccn

st.set_page_config(page_title="Facility Assessment Snapshot", page_icon="🏥", layout="centered")

_SOURCE_ORDER = ["Facility", "U.S.", "State"]
_SOURCE_COLORS = ["#E6007E", "#9AA0B4", "#1A73E8"]
_RATING_LABELS = {"Overall Star Rating", "Health Inspection", "Staffing", "Quality of Resident Care"}
_COMPARE_PALETTE = ["#E6007E", "#1A73E8", "#F5A623", "#34A853", "#9C27B0", "#00ACC1"]
_CCN_LOOKUP_URL = "https://www.medicare.gov/care-compare/?providerType=NursingHome"

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
        st.plotly_chart(_benchmark_fig(short_stay, "Percent", True), width="stretch")
    with right:
        st.caption("Long-stay (per 1,000 resident days)")
        st.plotly_chart(_benchmark_fig(long_stay, "Rate", False), width="stretch")


def sidebar_inputs() -> tuple[str, ManualInputs]:
    st.sidebar.header("Facility lookup")
    st.sidebar.link_button(
        "Look up a CCN on Medicare \u2197",
        _CCN_LOOKUP_URL,
        width="stretch",
        help="Opens Medicare Care Compare — search any nursing home and its 6-digit CCN is in the profile.",
    )

    with st.sidebar.form("single_lookup"):
        ccn = st.text_input(
            "CMS Certification Number (CCN)", help="6-character CMS facility ID, e.g. 686123"
        ).strip()
        st.divider()
        st.markdown("**Manual details** _(optional)_")
        name_override = st.text_input("Facility name (override)", help="Leave blank to use the official CMS name.")
        emr = st.text_input("EMR", placeholder="e.g. PCC")
        current_census = st.number_input("Current census", min_value=0, max_value=100000, value=0, step=1)
        patient_type = st.text_input("Type of patient", placeholder="e.g. Long-term & Short-term")
        previous_coverage = st.selectbox("Previous coverage from Medelite", ["", "Yes", "No"])
        previous_performance = st.text_input(
            "Previous provider performance", placeholder="e.g. About 30 patients/day"
        )
        medical_coverage = st.text_input("Medical coverage", placeholder="e.g. Optometry, PCP, Podiatry")
        st.form_submit_button("Generate snapshot", type="primary", width="stretch")

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
        st.info("Enter a facility CCN in the sidebar and click **Generate snapshot** (or press Enter).")
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
            width="stretch",
        )
    with col2:
        st.download_button(
            "Download Word",
            data=build_docx(rep),
            file_name=f"{rep.ccn or 'facility'}_assessment_snapshot.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch",
        )
    with col3:
        st.link_button("Medicare Care Compare \u2197", rep.medicare_url, width="stretch")

    render_benchmarks(rep)
    render_qa(rep)


def _compare_ratings_chart(rowmaps, names) -> go.Figure:
    rating_keys = [
        ("Overall", "Overall Star Rating"),
        ("Health", "Health Inspection"),
        ("Staffing", "Staffing"),
        ("Quality", "Quality of Resident Care"),
    ]
    fig = go.Figure()
    for (rating_label, key), color in zip(rating_keys, _COMPARE_PALETTE):
        y = []
        for rowmap in rowmaps:
            value = rowmap.get(key, "")
            y.append(int(value) if value.isdigit() else None)
        fig.add_bar(
            name=rating_label,
            x=names,
            y=y,
            marker_color=color,
            text=["" if t is None else str(t) for t in y],
            textposition="outside",
            cliponaxis=False,
        )
    fig.update_layout(
        barmode="group",
        height=340,
        margin=dict(l=10, r=10, t=24, b=10),
        yaxis_title="Star rating (1-5)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )
    fig.update_yaxes(range=[0, 5], showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def _compare_metric_chart(reports, names, is_short: bool) -> go.Figure:
    if is_short:
        measures = [
            ("Rehospitalization", "str_hospitalization", "str_hospitalization_national"),
            ("ED visit", "str_ed_visit", "str_ed_visit_national"),
        ]
        y_title = "Percent"
    else:
        measures = [
            ("Hospitalization", "lt_hospitalization", "lt_hospitalization_national"),
            ("ED visit", "lt_ed_visit", "lt_ed_visit_national"),
        ]
        y_title = "Rate"

    x = [m[0] for m in measures]
    fig = go.Figure()
    for idx, (rep, name) in enumerate(zip(reports, names)):
        y = [getattr(rep.metrics, m[1]) if rep.metrics is not None else None for m in measures]
        fig.add_bar(name=name, x=x, y=y, marker_color=_COMPARE_PALETTE[idx % len(_COMPARE_PALETTE)])

    nat_source = next((rep for rep in reports if rep.metrics is not None), None)
    if nat_source is not None:
        national = [getattr(nat_source.metrics, m[2]) for m in measures]
        fig.add_bar(name="U.S. avg", x=x, y=national, marker_color="#9AA0B4")

    fig.update_layout(
        barmode="group",
        height=300,
        margin=dict(l=10, r=10, t=24, b=10),
        yaxis_title=y_title,
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )
    fig.update_yaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    fig.update_xaxes(showgrid=False)
    return fig


def _render_comparison(reports) -> None:
    rowmaps = [dict(presentation.all_rows(rep)) for rep in reports]
    names = [rep.facility_name if len(rep.facility_name) <= 24 else rep.facility_name[:23] + "…" for rep in reports]

    st.markdown(f"#### Comparing {len(reports)} facilities")

    columns = {}
    for rep, rowmap in zip(reports, rowmaps):
        columns[f"{rep.facility_name} ({rep.ccn})"] = [rowmap.get(label, "N/A") for label in _COMPARE_LABELS]
    df = pd.DataFrame(columns, index=_COMPARE_LABELS)
    st.dataframe(df, width="stretch")

    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "Download comparison (CSV)",
            data=df.to_csv().encode("utf-8"),
            file_name="facility_comparison.csv",
            mime="text/csv",
            width="stretch",
        )
    with dl2:
        st.download_button(
            "Download comparison (PDF)",
            data=build_comparison_pdf(reports),
            file_name="facility_comparison.pdf",
            mime="application/pdf",
            width="stretch",
        )

    care_links = "  ·  ".join(f"[{rep.facility_name}]({rep.medicare_url})" for rep in reports)
    st.markdown("**View on Medicare Care Compare:** " + care_links)

    st.divider()
    st.markdown("##### Star ratings")
    st.plotly_chart(_compare_ratings_chart(rowmaps, names), width="stretch")

    st.markdown("##### Hospitalization & ED outcomes — lower is better")
    left, right = st.columns(2)
    with left:
        st.caption("Short-stay (% of residents)")
        st.plotly_chart(_compare_metric_chart(reports, names, is_short=True), width="stretch")
    with right:
        st.caption("Long-stay (per 1,000 resident days)")
        st.plotly_chart(_compare_metric_chart(reports, names, is_short=False), width="stretch")


def render_compare() -> None:
    st.sidebar.header("Compare facilities")
    st.sidebar.link_button(
        "Look up CCNs on Medicare \u2197",
        _CCN_LOOKUP_URL,
        width="stretch",
        help="Opens Medicare Care Compare — find each nursing home's 6-digit CCN in its profile.",
    )

    with st.sidebar.form("compare_lookup"):
        raw = st.text_area(
            "CCNs to compare",
            placeholder="One per line or comma-separated:\n686123\n105007\n245001",
            height=150,
            help="Enter 2 or more CMS Certification Numbers.",
        )
        st.form_submit_button("Compare facilities", type="primary", width="stretch")

    ccns = parse_ccn_list(raw)
    if len(ccns) < 2:
        st.info("Enter two or more CCNs in the sidebar and click **Compare facilities**.")
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
