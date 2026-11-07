"""Parser and tools for OFAC's "Changes to the SDN list" text archives (sdnnewYY.txt).

Source (verified to exist, text format 1994-2023): https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/archive-of-changes-to-the-sdn-list
Format as observed in sdnnew22.txt: a long preamble, then date blocks `MM/DD/YY:`; inside a block, header paragraphs
("The following [PROGRAM] entries have been added to OFAC's SDN List:", "... have been removed:", "... have been changed:",
"resulting in the following new ... entries:") each followed by wrapped entry text; changed entries read `OLD -to- NEW`.

What this module produces: a normalised event list (date, action add|remove, key, programs, kind) plus renames.
Entry identity is a HEURISTIC (the archive has no stable id): see `entry_key`. Diagnostics report anything unparsed.
"""
from __future__ import annotations

import csv
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

DATE_LINE = re.compile(r"^(\d{2})/(\d{2})/(\d{2}):\s*$")
AKA = re.compile(r" \((?:a|f|n)\.k\.a\. ")
ACTION = re.compile(r"\b(added|removed|deleted|changed|amended|updated)\b", re.I)
_END = re.compile(r"(?<=[\]\)]\.)\s+")          # an entry ends with `].` or `).` (programs, optionally "(Linked To: ...)")
TAGS = re.compile(r"\[([A-Z0-9][A-Z0-9\-]*)\]")


@dataclass(frozen=True)
class Event:
    date: str          # ISO yyyy-mm-dd
    action: str        # add | remove
    key: str
    programs: str
    kind: str          # individual | vessel | aircraft | entity
    seq: int           # order of appearance in the source, to order events on the same date


def _iso(mm: str, dd: str, yy: str) -> str:
    y = int(yy)
    return f"{1900 + y if y >= 90 else 2000 + y}-{mm}-{dd}"


def _join(lines: list[str]) -> str:
    out = ""
    for ln in (x.strip() for x in lines):
        if not ln:
            continue
        out = out + ln if out.endswith("-") else (out + " " + ln if out else ln)
    return out


def entry_key(text: str) -> str:
    """Heuristic identity: the primary name. Aliases listed as separate entries get their own key."""
    t = " ".join(text.split())
    m = AKA.search(t)
    if m and ";" not in t[:m.start()]:
        k = t[:m.start()]
    elif "(individual)" in t:
        k = ",".join(t.split(",")[:2])
    else:
        k = re.split(r"[;,]", t, maxsplit=1)[0]
    return k.strip().strip('"').strip().upper()


def _kind(t: str) -> str:
    return "individual" if "(individual)" in t else "vessel" if "(vessel)" in t else "aircraft" if "(aircraft)" in t else "entity"


def parse_text(text: str) -> dict:
    """Returns dict(events=[Event], renames=[(date, old_key, new_key)], diag={...})."""
    events: list[Event] = []
    renames: list[tuple[str, str, str]] = []
    diag = dict(date_blocks=0, headers=defaultdict(int), unrecognised_headers=[], long_entries=0, entries=0)
    state = dict(date=None, mode=None, seq=0)
    para: list[str] = []

    def entries_of(txt: str) -> list[str]:
        out = [p.strip() for p in _END.split(txt.strip()) if p.strip()]
        diag["long_entries"] += sum(len(p) > 3000 for p in out)
        return out

    def handle(txt: str) -> None:
        low = txt.lower()
        if low.startswith("resulting in the following") or txt.startswith("The following"):
            if low.startswith("resulting in"):
                state["mode"] = "resulting"
            else:
                m = ACTION.search(txt.split(":")[0])
                if not m:
                    diag["unrecognised_headers"].append(txt[:120])
                    state["mode"] = None
                else:
                    w = m.group(1).lower()
                    state["mode"] = "add" if w == "added" else "remove" if w in ("removed", "deleted") else "change"
            diag["headers"][state["mode"] or "unrecognised"] += 1
            rest = txt.split(":", 1)[1].strip() if ":" in txt else ""
            if len(rest) > 20 and state["mode"] in ("add", "remove", "change"):
                handle_entries(rest)
            return
        handle_entries(txt)

    def handle_entries(txt: str) -> None:
        mode, d = state["mode"], state["date"]
        if mode in ("add", "remove"):
            for e in entries_of(txt):
                diag["entries"] += 1
                state["seq"] += 1
                events.append(Event(d, mode, entry_key(e), "|".join(TAGS.findall(e)), _kind(e), state["seq"]))
        elif mode == "change":
            parts = re.split(r"\s*-to-\s*", txt)
            for j in range(len(parts) - 1):
                old, new = entries_of(parts[j])[-1], entries_of(parts[j + 1])[0]
                ko, kn = entry_key(old), entry_key(new)
                if ko != kn:
                    renames.append((d, ko, kn))

    def flush() -> None:
        if para and state["date"]:
            handle(_join(para))
        para.clear()

    for ln in text.splitlines():
        m = DATE_LINE.match(ln)
        if m:
            flush()
            state.update(date=_iso(m.group(1), m.group(2), m.group(3)), mode=None)
            diag["date_blocks"] += 1
        elif not ln.strip():
            flush()
        elif state["date"]:
            para.append(ln)
    flush()
    diag["headers"] = dict(diag["headers"])
    return dict(events=events, renames=renames, diag=diag)


def parse_files(paths: list[str | Path]) -> dict:
    ev, rn, diags = [], [], {}
    off = 0
    for p in paths:
        r = parse_text(Path(p).read_text(encoding="utf-8", errors="replace"))
        ev += [Event(e.date, e.action, e.key, e.programs, e.kind, e.seq + off) for e in r["events"]]
        off += len(r["events"]) + 1
        rn += r["renames"]
        diags[str(p)] = r["diag"]
    return dict(events=ev, renames=rn, diag=diags)


FIELDS = ["date", "action", "key", "programs", "kind", "seq"]


def write_events_csv(path: str | Path, events: list[Event], renames: list[tuple[str, str, str]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FIELDS)
        for e in events:
            w.writerow([e.date, e.action, e.key, e.programs, e.kind, e.seq])
        for d, o, n in renames:
            w.writerow([d, "rename", o, n, "", 0])


def load_events_csv(path: str | Path) -> tuple[list[Event], list[tuple[str, str, str]]]:
    ev, rn = [], []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["action"] == "rename":
                rn.append((r["date"], r["key"], r["programs"]))
            elif r["action"] in ("add", "remove"):
                ev.append(Event(r["date"], r["action"], r["key"], r["programs"], r["kind"], int(r["seq"])))
            else:
                raise ValueError(f"unknown action {r['action']!r}")
    return ev, rn


# ---- identity, histories, pool ------------------------------------------------------------------------------
def canonical_map(renames: list[tuple[str, str, str]]) -> dict[str, str]:
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for _, o, n in sorted(renames):
        parent[find(o)] = find(n)          # the newest name is the representative
    return {k: find(k) for k in list(parent)}


def build_histories(events: list[Event], renames: list[tuple[str, str, str]], start: str, end: str) -> dict[str, list[str]]:
    """key -> alternating list of 'add'/'remove' inside [start, end] (ISO dates, inclusive), consecutive duplicates removed."""
    cm = canonical_map(renames)
    per: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if start <= e.date <= end:
            per[cm.get(e.key, e.key)].append(e)
    hist = {}
    for k, evs in per.items():
        seq: list[str] = []
        for e in sorted(evs, key=lambda x: (x.date, x.seq)):
            if not seq or seq[-1] != e.action:
                seq.append(e.action)
        hist[k] = seq
    return hist


def dated_histories(events, renames, start, end) -> dict[str, list[tuple[str, str]]]:
    cm = canonical_map(renames)
    per: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if start <= e.date <= end:
            per[cm.get(e.key, e.key)].append(e)
    out = {}
    for k, evs in per.items():
        seq: list[tuple[str, str]] = []
        for e in sorted(evs, key=lambda x: (x.date, x.seq)):
            if not seq or seq[-1][1] != e.action:
                seq.append((e.date, e.action))
        out[k] = seq
    return out


def volatile_pool(hist: dict[str, list[str]]) -> list[str]:
    """Pre-registered rule (addendum A3): the first in-window event is an add and at least one remove follows."""
    return sorted(k for k, s in hist.items() if s and s[0] == "add" and "remove" in s)


def relisted(hist: dict[str, list[str]]) -> list[str]:
    """H16: entries that were removed and later added again inside the window."""
    return sorted(k for k, s in hist.items() if any(a == "remove" and "add" in s[i + 1:] for i, a in enumerate(s)))


def by_year(events: list[Event], start: str, end: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = defaultdict(lambda: dict(add=0, remove=0))
    for e in events:
        if start <= e.date <= end:
            out[e.date[:4]][e.action] += 1
    return dict(sorted(out.items()))


PARTICIPANTS = ("u", "a1", "a2")     # the accredited, non-permanently-sanctioned participants of the fuzzer fixture


def sample_entries(pool: list[str], seed: int, k: int = len(PARTICIPANTS)) -> list[str]:
    if len(pool) < k:
        raise ValueError(f"volatile pool has {len(pool)} entries, need {k}")
    return random.Random(seed).sample(pool, k)


def make_schedule(entries: list[str], dated: dict[str, list[tuple[str, str]]], variant: str, steps: int) -> dict[int, tuple[str, str]]:
    """step -> ('sanction'|'delist', participant). Order of real events is kept; real gaps are not (addendum A3).
    variant 'spread': events evenly spaced from step 2; 'burst': consecutive steps from step 2."""
    seq = []
    for idx, k in enumerate(entries):
        for d, a in dated.get(k, []):
            seq.append((d, idx, a))
    seq.sort()
    seq = seq[: max(0, steps - 5)]
    if not seq:
        return {}
    stride = 1 if variant == "burst" else max(1, (steps - 4) // len(seq))
    return {2 + i * stride: ("sanction" if a == "add" else "delist", PARTICIPANTS[idx])
            for i, (_, idx, a) in enumerate(seq) if 2 + i * stride < steps - 1}
