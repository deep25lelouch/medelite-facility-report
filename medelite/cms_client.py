"""Thin client for the CMS Provider Data Catalog datastore query API.

The API needs no key and has no rate limit. Responses are JSON of the form {"results": [...]}.
Each unique (dataset, conditions) result is cached for the life of the process so Streamlit reruns
do not refetch.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import requests

from medelite import config


class CMSClientError(RuntimeError):
    """Raised when the CMS API cannot be reached or returns an unexpected payload."""


_session = requests.Session()
_cache: dict[tuple, list[dict[str, Any]]] = {}


def _query(dataset_id: str, conditions: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Run a datastore query and return its `results` list (cached per dataset+conditions)."""
    cache_key = (dataset_id, tuple(tuple(sorted(c.items())) for c in conditions))
    if cache_key in _cache:
        return _cache[cache_key]

    url = f"{config.PDC_API_BASE}/{dataset_id}/0"
    params: dict[str, str] = {"limit": str(config.PDC_PAGE_LIMIT)}
    for i, cond in enumerate(conditions):
        params[f"conditions[{i}][property]"] = cond["property"]
        params[f"conditions[{i}][value]"] = cond["value"]
        params[f"conditions[{i}][operator]"] = cond.get("operator", "=")

    last_err: Optional[Exception] = None
    for attempt in range(config.REQUEST_MAX_RETRIES):
        try:
            resp = _session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)
            resp.raise_for_status()
            payload = resp.json()
            results = payload.get("results", [])
            if not isinstance(results, list):
                raise CMSClientError(
                    f"Unexpected payload from {dataset_id}: 'results' is not a list"
                )
            _cache[cache_key] = results
            return results
        except (requests.RequestException, ValueError) as exc:
            last_err = exc
            if attempt < config.REQUEST_MAX_RETRIES - 1:
                time.sleep(0.5 * (2 ** attempt))  # 0.5s, then 1.0s
    raise CMSClientError(
        f"CMS API request to {dataset_id} failed after {config.REQUEST_MAX_RETRIES} attempts: {last_err}"
    )


def get_provider(ccn: str) -> Optional[dict[str, Any]]:
    """Return the single Provider Information row for a CCN, or None if no record exists."""
    rows = _query(
        config.DATASET_PROVIDER_INFO,
        [{"property": "cms_certification_number_ccn", "value": (ccn or "").strip(), "operator": "="}],
    )
    return rows[0] if rows else None


def get_claims(ccn: str) -> list[dict[str, Any]]:
    """[Bonus] Return all Claims QM rows (one per measure) for a CCN."""
    return _query(
        config.DATASET_CLAIMS_QM,
        [{"property": "cms_certification_number_ccn", "value": (ccn or "").strip(), "operator": "="}],
    )


def get_state_averages() -> list[dict[str, Any]]:
    """[Bonus] Return all rows from State US Averages (includes the NATION row + one row per state)."""
    return _query(config.DATASET_STATE_AVERAGES, [])


def clear_cache() -> None:
    """Drop the in-process response cache (useful in tests)."""
    _cache.clear()
