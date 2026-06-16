# Medelite — Facility Assessment Report Generator

A lightweight Streamlit app that looks up a skilled nursing facility by its **CMS Certification
Number (CCN)**, pulls public performance data from the CMS Provider Data Catalog, combines it with
the manual operational inputs Medelite tracks internally, and exports a polished, print-ready
**Facility Assessment Snapshot** (PDF / DOCX) with a live link back to the Medicare Care Compare
profile.

> Take-home case study for the Medelite *Healthcare Data Automation & QA Analytics* Internship.

## Architecture

UI (Streamlit) → core service layer (framework-agnostic Python) → CMS Provider Data Catalog API.
The fetch runs **server-side**, so there is no CORS to fight. There is **no database** — a lookup
reads CMS live and the report is assembled in-session.

```
streamlit_app.py                 UI layer only (entry point)
  └─ medelite/                   core service layer — no streamlit imports (testable, API-ready)
       config.py                 dataset IDs, API base, branding constants, Medicare URL template
       mapping.py                field-mapping registry — single source of truth
       models.py                 Pydantic: ReportModel, ManualInputs, StarRatings, Metrics, QAReport
       cms_client.py             PDC datastore client (+retry, +cache)
       normalize.py              raw payload -> typed values (coerce, footnotes, prefix-resolve)
       qa.py                     validated coercion + QA report (ranges, missing, schema drift)
       report.py                 assembles ReportModel from CMS + manual + name-override logic
       presentation.py           registry-driven (label, value) rows shared by UI + exporters
       export/  pdf.py docx.py   one ReportModel, many renderers                           [later]
  └─ CMS PDC API                 data.cms.gov/provider-data  ·  no key  ·  no rate limit
```

## Data sources (CMS Provider Data Catalog)

| Dataset | ID | Used for |
| --- | --- | --- |
| Provider Information | `4pq5-n9py` | name, location, certified beds, star ratings (MVP) |
| Medicare Claims Quality Measures | `ijh5-nb2v` | 4 facility hospitalization / ED values (bonus) |
| State US Averages | `xcdc-v8bm` | 8 national + state averages (bonus) |

Query pattern (no API key required):
`GET {base}/{datasetId}/0?conditions[0][property]=cms_certification_number_ccn&conditions[0][value]={ccn}&conditions[0][operator]==`

## Facility name override

"Name of Facility" defaults to the CMS legal name (`provider_name`); if the user types a custom
name it overrides the API value. The `INFINITE` platform banner is a hardcoded constant and is
**never** replaced by the facility name (per the brief's branding guardrail).

## QA strategy

Raw CMS payloads pass through one mapping registry: string→numeric coercion, range validation
(ratings 1–5), footnote-aware "N/A", and schema-drift detection. The PDC API truncates long column
names and appends a hash (e.g. `..._on_t_4a14`), so columns are resolved by stable prefix and
required field slugs are asserted, not assumed. Each lookup produces a structured QA report, and
the CMS→report mapping is exercised end-to-end by unit + Hypothesis property tests.

## Assumptions

- The test CCN `686123` resolves to a live CMS record — **Kendall Lakes Healthcare and Rehab
  Center** (Miami, FL), confirmed via `scripts/verify.py`.
- The app renders **current** CMS data. The sample snapshot's specific values (overall rating 1,
  120 beds) differ from the current live values (overall 5, 150 beds) because CMS refreshes ratings
  monthly — the sample is a **layout reference from an earlier refresh**, not a fixed data target.
  The app intentionally shows live data rather than reproducing the static sample; the match is on
  format, not numbers.
- A not-found CCN is handled gracefully (empty result → report built from manual inputs + the name
  override + the dynamic Medicare link).
- For the bonus hospitalization/ED metrics, facility values use the risk-adjusted score from the
  Claims dataset and national/state averages come from the `NATION` and state rows of State US
  Averages.

## Scale path (intentionally not built)

For a single on-demand lookup, an ingestion pipeline is overkill. If Medelite needed to evaluate
many facilities, pre-cache, or track trends across monthly CMS refreshes, the next step would be a
monthly Airflow DAG (triggered on the PDC refresh) landing into Postgres/Snowflake and served from
the warehouse. This MVP is the live-read slice of that design.

## Setup

```bash
poetry install
poetry run python scripts/verify.py        # Phase 0: confirm test CCN + lock field slugs
poetry run streamlit run streamlit_app.py  # run the app
poetry run pytest                          # run the test suite
```

## Deploy

Streamlit Community Cloud — point it at `streamlit_app.py`; dependencies are read from
`pyproject.toml` (`package-mode = false`). Free-tier apps sleep after inactivity, so open the URL
once to warm it before a demo.

## Tech stack

Python · Streamlit · Pydantic · pandas · requests · reportlab · python-docx · PyTest · Hypothesis · Poetry
