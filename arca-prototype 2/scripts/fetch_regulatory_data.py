"""
Fetches live regulatory reference data from the real, official sources
the paper's Regulatory Oracle Network (Sec. V-F) is designed to consume.

This script is NOT run as part of the test suite or CI — tests should
not depend on live third-party network calls, and the sandbox this
repository was originally built in restricts egress to a small domain
allowlist that does not include these government hosts. Run it yourself
from an environment with normal internet access:

    python scripts/fetch_regulatory_data.py --which ofac
    python scripts/fetch_regulatory_data.py --which fatf

See data/README.md for why fatf_lists.json is checked in as a dated
snapshot rather than being treated as a live source, and why we did not
bundle an OFAC snapshot at all.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import requests  # not in requirements.txt on purpose: this script is optional tooling

# Official OFAC Sanctions List Service exports (U.S. Treasury; public-domain
# US federal government work, see 17 U.S.C. 105). Confirmed as the current
# canonical endpoints as of 2026; the older treasury.gov/ofac/downloads/*.csv
# paths are legacy courtesy redirects to the same service.
OFAC_ENDPOINTS = {
    "sdn": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
    "sdn_alt_names": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ALT.CSV",
    "consolidated_primary": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONS_PRIM.CSV",
}

# FATF publishes grey/black list updates as HTML pages after each Plenary
# (Feb / June / Oct); there is no machine-readable feed at the time of
# writing, so this fetches the page for a human (or a follow-up parser
# tailored to FATF's current HTML structure, which does change) to read,
# rather than attempting brittle HTML scraping here.
FATF_PAGES = {
    "increased_monitoring": "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html",
}

OUT_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "live_fetch"
USER_AGENT = (
    "Mozilla/5.0 (compatible; ARCA-prototype-oracle-fetcher/0.1; "
    "+https://github.com/) research-prototype-data-fetch"
)


def fetch_ofac(which: str = "sdn") -> pathlib.Path:
    url = OFAC_ENDPOINTS[which]
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"ofac_{which}.csv"
    out_path.write_bytes(resp.content)
    print(f"Wrote {len(resp.content)} bytes to {out_path}")
    return out_path


def fetch_fatf(which: str = "increased_monitoring") -> pathlib.Path:
    url = FATF_PAGES[which]
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"fatf_{which}.html"
    out_path.write_text(resp.text)
    print(f"Wrote {len(resp.text)} chars of HTML to {out_path}")
    print("NOTE: this is the raw page, not a parsed list — FATF's markup "
          "changes between Plenaries, so update data/fatf_lists.json by hand "
          "after checking this against the current page structure.")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--which", choices=["ofac", "fatf"], required=True)
    args = parser.parse_args()

    try:
        if args.which == "ofac":
            fetch_ofac("sdn")
        else:
            fetch_fatf("increased_monitoring")
    except requests.exceptions.RequestException as exc:
        print(f"Fetch failed: {exc}", file=sys.stderr)
        print(
            "If this is bot-detection (HTTP 403) rather than a network "
            "issue: OFAC/FATF's edge protection sometimes blocks generic "
            "script user-agents even for legitimate public-data access. "
            "Try again from a normal (non-datacenter) IP, or use OFAC's "
            "Sanctions List Search UI / SLS API docs directly.",
            file=sys.stderr,
        )
        sys.exit(1)
