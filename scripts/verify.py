"""Phase 0 verification - run locally (needs network).

    poetry run python scripts/verify.py

Confirms whether the provided test CCN returns a live record and dumps the actual field slugs for
all three datasets so the bonus mapping (normalize.py) can be wired against real keys rather than
assumptions. The PDC API truncates long column names, so never trust a guessed slug.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running as `python scripts/verify.py` from the repo root (package-mode=false => not installed).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from medelite import cms_client, config  # noqa: E402

TEST_CCN = "686123"


def show(title: str, rows: list[dict]) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")
    print(f"rows returned: {len(rows)}")
    if rows:
        print("field slugs:")
        for k in rows[0].keys():
            print(f"  - {k}")


def main() -> None:
    print(f"CMS PDC base: {config.PDC_API_BASE}")
    print(f"Test CCN:     {TEST_CCN}")

    # --- Provider Information (MVP) ---
    try:
        provider = cms_client.get_provider(TEST_CCN)
    except cms_client.CMSClientError as exc:
        print(f"\n[provider] request failed: {exc}")
        provider = None

    if provider is None:
        print(
            f"\n[FINDING] CCN {TEST_CCN} returned NO Provider Information record.\n"
            f"          Double-check the CCN; the app treats this as a not-found case and still\n"
            f"          generates a report from manual inputs + the name override."
        )
    else:
        print(f"\n[FINDING] CCN {TEST_CCN} resolves to a live record: {provider.get('provider_name')!r}")
        show("Provider Information slugs (4pq5-n9py)", [provider])

    # --- Claims Quality Measures (bonus) ---
    try:
        claims = cms_client.get_claims(TEST_CCN)
        show(f"Claims QM slugs (ijh5-nb2v) for CCN {TEST_CCN}", claims)
        if claims:
            measures = sorted(
                {r.get("measure_description") or r.get("measure_code") or "?" for r in claims}
            )
            print("distinct measures present:")
            for m in measures:
                print(f"  * {m}")
    except cms_client.CMSClientError as exc:
        print(f"\n[claims] request failed: {exc}")

    # --- State US Averages (bonus) ---
    try:
        avgs = cms_client.get_state_averages()
        show("State US Averages slugs (xcdc-v8bm)", avgs)
        if avgs:
            key0 = next(iter(avgs[0].keys()))
            states = sorted({str(r.get(key0)) for r in avgs})
            print(f"distinct values in first column ('{key0}'): {len(states)} (expect NATION + states)")
    except cms_client.CMSClientError as exc:
        print(f"\n[averages] request failed: {exc}")


if __name__ == "__main__":
    main()
