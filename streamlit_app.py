"""Medelite Facility Assessment Report Generator - Streamlit UI (entry point)."""
from __future__ import annotations

import html

import streamlit as st

from medelite import config, presentation
from medelite.cms_client import CMSClientError, get_provider
from medelite.export.pdf import build_pdf
from medelite.models import ManualInputs
from medelite.report import assemble_report

st.set_page_config(page_title="Facility Assessment Snapshot", page_icon="🏥", layout="centered")


@st.cache_data(show_spinner="Fetching CMS data...")
def fetch_provider(ccn: str):
    """Cached CMS lookup so editing manual fields never refetches. Returns a row dict or None."""
    return get_provider(ccn)


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


def render_report_table(rows: list[tuple[str, str]]) -> None:
    body = "".join(
        f"<tr><td class='lbl'>{html.escape(label)}</td>"
        f"<td class='val'>{html.escape(value)}</td></tr>"
        for label, value in rows
    )
    st.markdown(
        f"""
        <style>
          table.fas {{ width:100%; border-collapse:collapse; font-size:0.95rem; margin-top:0.25rem; }}
          table.fas td {{ border:1px solid #d9d9e3; padding:8px 12px; vertical-align:top; }}
          table.fas td.lbl {{ background:#F5F6FA; font-weight:600; width:55%; }}
          table.fas td.val {{ width:45%; }}
        </style>
        <table class="fas">{body}</table>
        """,
        unsafe_allow_html=True,
    )


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


def main() -> None:
    render_header()
    ccn, manual = sidebar_inputs()

    if not ccn:
        st.info("Enter a facility CCN in the sidebar to generate a snapshot.")
        return

    try:
        provider_raw = fetch_provider(ccn)
    except CMSClientError as exc:
        st.error(f"Could not reach the CMS Provider Data API: {exc}")
        return

    rep = assemble_report(ccn, provider_raw, manual)

    if not rep.cms_record_found:
        st.warning(f"No CMS record found for CCN '{ccn}'. Showing a report built from your manual inputs.")

    st.markdown(f"#### {html.escape(rep.facility_name)}")
    render_report_table(presentation.mvp_rows(rep))

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download PDF",
            data=build_pdf(rep),
            file_name=f"{rep.ccn or 'facility'}_assessment_snapshot.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with col2:
        st.link_button("View on Medicare Care Compare \u2197", rep.medicare_url, use_container_width=True)

    render_qa(rep)


if __name__ == "__main__":
    main()
