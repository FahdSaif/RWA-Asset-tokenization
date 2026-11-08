"""Ethereum-format (0x + 40 hex) addresses in OFAC 'added' entries, with the date of first listing.

Reads the same sdnnewYY.txt files as the sanctions replay (docs/data/raw). Only 'added' paragraphs count; the first date wins.
Addresses in 0x format may belong to any EVM chain; the analysis uses Ethereum mainnet events only (stated limitation).
"""
from __future__ import annotations

import re
from pathlib import Path

DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{2}):\s*$")
ADDR = re.compile(r"0x[0-9a-fA-F]{40}")
ACTION = re.compile(r"\b(added|removed|deleted|changed)\b", re.I)


def extract_text(text: str, first: dict[str, str] | None = None) -> dict[str, str]:
    first = {} if first is None else first
    mode, date, para = None, None, []

    def flush() -> None:
        nonlocal mode
        t = " ".join(x.strip() for x in para).strip()
        para.clear()
        if not t:
            return
        if t.startswith("The following") or t.lower().startswith("resulting"):
            m = ACTION.search(t.split(":")[0])
            mode = {"added": "add", "removed": "remove", "deleted": "remove", "changed": "change"}.get(m.group(1).lower()) if m else None
        elif mode == "add" and date:
            for a in ADDR.findall(t):
                first.setdefault(a.lower(), date)

    for ln in text.splitlines():
        m = DATE.match(ln)
        if m:
            flush()
            mode = None
            yy = int(m.group(3))
            date = f"{1900 + yy if yy >= 90 else 2000 + yy}-{m.group(1)}-{m.group(2)}"
        elif not ln.strip():
            flush()
        elif date:
            para.append(ln)
    flush()
    return first


def extract(raw_dir: str | Path) -> dict[str, str]:
    first: dict[str, str] = {}
    for f in sorted(Path(raw_dir).glob("sdnnew*.txt")):          # chronological: sdnnew19 ... sdnnew23
        extract_text(f.read_text(encoding="utf-8", errors="replace"), first)
    return dict(sorted(first.items(), key=lambda kv: (kv[1], kv[0])))
