"""Static configuration: CMS dataset identifiers, API endpoint, and Medelite branding constants."""
from __future__ import annotations

# --- CMS Provider Data Catalog (PDC) datastore query API ---
# No API key required, no rate limits. Each response page is capped at 1500 rows.
PDC_API_BASE = "https://data.cms.gov/provider-data/api/1/datastore/query"

# Dataset identifiers (resolved against the live catalog). Re-confirm the field slugs inside each
# dataset with scripts/verify.py before relying on them - the API truncates long column names.
DATASET_PROVIDER_INFO = "4pq5-n9py"    # name, location, certified beds, star ratings   (MVP)
DATASET_CLAIMS_QM = "ijh5-nb2v"        # facility-level hospitalization / ED measures    (bonus)
DATASET_STATE_AVERAGES = "xcdc-v8bm"   # national + per-state averages                   (bonus)

PDC_PAGE_LIMIT = 1500
REQUEST_TIMEOUT_SECONDS = 15
REQUEST_MAX_RETRIES = 3

# --- Medelite branding (STATIC - never overwritten by CMS data or the name override) ---
BRAND_PLATFORM = "INFINITE"
BRAND_TAGLINE = "Managed by MEDELITE"
REPORT_TITLE = "FACILITY ASSESSMENT SNAPSHOT"
BRAND_COLOR = "#E6007E"  # Medelite magenta (matches .streamlit/config.toml primaryColor)

# --- Medicare Care Compare public profile (CCN + state injected dynamically) ---
MEDICARE_PROFILE_TEMPLATE = (
    "https://www.medicare.gov/care-compare/details/nursing-home/{ccn}/view-all?state={state}"
)


def medicare_profile_url(ccn: str, state: str | None) -> str:
    """Build the dynamic Medicare Care Compare profile URL for a facility."""
    return MEDICARE_PROFILE_TEMPLATE.format(ccn=(ccn or "").strip(), state=(state or "").strip().upper())
