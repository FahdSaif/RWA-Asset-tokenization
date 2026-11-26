"""Build the Q1 sample from saved Etherscan label pages.

Usage:
  python tools/build_sample.py page1.mhtml page2.mhtml page3.mhtml

Reads the pages (saved in Chrome as "Webpage, Single File"), applies the rule
(the 25 census tokens plus the first 75 other tokens in page order) and writes:
  data/sample_tokens.txt                     the 100 tokens
  data/etherscan_rwa_snapshot_<date>.txt     every row read, with the SHA-256 of each page
"""
import email
import hashlib
import html
import re
import sys
from email import policy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT.parent / "rwa-threatlab" / "docs" / "data" / "exploratory" / "census_tokens.txt"
N_NEW = 75


def read_page(path: Path) -> dict:
    """Rows of one saved page: rank, address, name (symbol), market cap, holders."""
    raw = path.read_bytes()
    msg = email.message_from_bytes(raw, policy=policy.default)
    page = next(p.get_content() for p in msg.walk() if p.get_content_type() == "text/html")
    body = re.search(r'id="table-subcatid-0".*?<tbody[^>]*>(.*?)</tbody>', page, re.S)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body.group(1) if body else "", re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        addr = re.search(r"/token/(0x[0-9a-fA-F]{40})", tr)
        if not addr or len(cells) < 5:
            continue
        name = re.sub(r"\(\s*(.*?)\s*\)\s*$", r"(\1)", cells[2])   # "( X )" -> "(X)"
        rows.append(dict(rank=int(cells[0]), address=addr.group(1).lower(), name=name,
                         cap=cells[3].replace("$", "").split(".")[0], holders=cells[4]))
    return dict(rows=rows, sha256=hashlib.sha256(raw).hexdigest(),
                saved=msg.get("Date", ""), url=msg.get("Snapshot-Content-Location", ""))


def main(paths: list[str]) -> None:
    pages = [read_page(Path(p)) for p in paths]
    rows = sorted((r for p in pages for r in p["rows"]), key=lambda r: r["rank"])
    addrs = [r["address"] for r in rows]
    if len(set(addrs)) != len(addrs):
        raise SystemExit("a token appears twice across pages: save the pages again")
    census = [l.split()[0].lower() for l in CENSUS.read_text().splitlines() if l.strip() and not l.startswith("#")]
    missing = [c for c in census if c not in addrs]
    new = [r for r in rows if r["address"] not in census][:N_NEW]
    if len(new) < N_NEW:
        raise SystemExit("not enough rows: save more pages")
    chosen = set(census) | {r["address"] for r in new}
    last = max(r["rank"] for r in rows if r["address"] in chosen)
    date = "2026-11-26"
    hdr = [
        "# QAMP Q1 sample: 100 tokens, fixed BEFORE any Q1 data were fetched.",
        "# Rule: the 25 tokens of the rwa-threatlab census (census_tokens.txt, seen 2026-11-08), plus the first 75 other tokens",
        f"#   in the order displayed on the page below on {date}. No exclusions, no replacements.",
        "# Source: https://etherscan.io/tokens/label/real-world-assets?subcatid=0&size=50&start=0&col=3&order=desc (and start=50, start=100)",
        f"# Seen on {date}, 10:20-10:21 AWST (UTC+08:00): Etherscan 'Token Tracker: Real World Assets', 844 records, sorted by market cap.",
        (f"# Result: all 25 census tokens were found; the 100 tokens are exactly that day's rows 1-{last}." if last == 100 and not missing
         else f"# Result: census tokens not found: {len(missing)}; the 100 tokens come from that day's rows 1-{last}."),
        f"# Columns: address, rank on {date}, name and symbol as shown, market cap shown on {date} (USD).",
        f"# Full snapshot: etherscan_rwa_snapshot_{date}.txt (built by tools/build_sample.py). Data: Etherscan.io (label source).",
    ]
    lines = [f"{r['address']}  {r['rank']}  {r['name']}  {r['cap']}" for r in rows if r["address"] in chosen]
    (ROOT / "data" / "sample_tokens.txt").write_text("\n".join(hdr + lines) + "\n")
    snap = [f"# Etherscan 'Token Tracker: Real World Assets' (label source: Etherscan.io), rows 1-{len(rows)}, sorted by market cap.",
            f"# Saved in Chrome as 'Webpage, Single File' (MHTML) on {date}; converted by tools/build_sample.py.",
            "# SHA-256 of the saved pages (kept by the author):"]
    for i, p in enumerate(pages, 1):
        snap.append(f"#   page {i}: {p['sha256']}  saved {p['saved']}  {p['url']}")
    snap.append("# Columns: rank | address | name (symbol) | market cap (USD) | holders | in census (2026-11-08) | in sample")
    snap += [f"{r['rank']} | {r['address']} | {r['name']} | {r['cap']} | {r['holders']} | "
             f"{'yes' if r['address'] in census else 'no'} | {'yes' if r['address'] in chosen else 'no'}" for r in rows]
    (ROOT / "data" / f"etherscan_rwa_snapshot_{date}.txt").write_text("\n".join(snap) + "\n")
    print(f"{len(rows)} rows read; {len(lines)} tokens in the sample; census tokens missing: {len(missing)}")


if __name__ == "__main__":
    main(sys.argv[1:])
