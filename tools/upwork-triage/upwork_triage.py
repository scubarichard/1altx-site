#!/usr/bin/env python3
"""
Upwork application sheet I/O for the upwork-triage subagent.

Setup (one-time):
  1. Create a Google Cloud service account, enable Sheets API, download JSON key.
  2. Share the target sheet with the service account email (Editor).
  3. Set env vars:
       UPWORK_SHEET_ID=11cydvXB7zb38FGSqrLTXEnikIK5gec1FSe3nK3Hy_BY
       UPWORK_SA_KEY=/path/to/service-account.json
       UPWORK_SHEET_TAB=Sheet1   # optional, defaults to first sheet
  4. pip install -r requirements.txt

Usage:
  upwork_triage.py read 97-123                     # JSON of rows to stdout
  upwork_triage.py write < decisions.json          # write column W in batch
  upwork_triage.py write --dry-run < decisions.json

decisions.json format:
  [{"row": 97, "value": "ðŸ”¥ Hot"}, {"row": 98, "value": "skip"}, ...]
"""
import argparse
import json
import os
import re
import sys
from html import unescape

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

COLUMNS = {
    "A_title": 0,
    "N_status": 13,
    "O_notes": 14,
    "P_html": 15,
    "W_priority": 22,
    "X_jobfit": 23,
    "Y_clientq": 24,
    "Z_combined": 25,
    "AH_scoring": 33,
}
LAST_COL_LETTER = "AL"  # column index 37


def sheets_client():
    key_path = os.environ.get("UPWORK_SA_KEY")
    if not key_path:
        sys.exit("UPWORK_SA_KEY not set (path to service account JSON)")
    creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def sheet_id():
    sid = os.environ.get("UPWORK_SHEET_ID")
    if not sid:
        sys.exit("UPWORK_SHEET_ID not set")
    return sid


def sheet_tab():
    return os.environ.get("UPWORK_SHEET_TAB") or _first_tab_name()


def _first_tab_name():
    svc = sheets_client()
    meta = svc.spreadsheets().get(spreadsheetId=sheet_id(), fields="sheets.properties.title").execute()
    return meta["sheets"][0]["properties"]["title"]


def parse_range(s: str):
    m = re.match(r"^(\d+)-(\d+)$", s)
    if not m:
        sys.exit(f"row range must be N-M, got {s!r}")
    a, b = int(m.group(1)), int(m.group(2))
    if a > b or a < 2:
        sys.exit("row range must be ascending and start at 2 or higher")
    return a, b


def strip_html(s: str, max_chars: int = 4000) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_chars]


def cmd_read(args):
    start, end = parse_range(args.range)
    tab = sheet_tab()
    rng = f"{tab}!A{start}:{LAST_COL_LETTER}{end}"
    svc = sheets_client()
    resp = svc.spreadsheets().values().get(
        spreadsheetId=sheet_id(), range=rng
    ).execute()
    values = resp.get("values", [])
    out = []
    for i, row in enumerate(values):
        while len(row) < 38:
            row.append("")
        sheet_row = start + i
        rec = {"row": sheet_row}
        for name, idx in COLUMNS.items():
            v = row[idx]
            if name == "P_html":
                rec["P_text"] = strip_html(v, max_chars=args.html_chars)
            else:
                rec[name] = v
        out.append(rec)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")


def cmd_write(args):
    raw = sys.stdin.read()
    try:
        decisions = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"invalid JSON on stdin: {e}")
    if not isinstance(decisions, list):
        sys.exit("expected a JSON array of {row, value}")
    tab = sheet_tab()
    data = []
    for d in decisions:
        row = d["row"]
        value = d["value"]
        data.append({
            "range": f"{tab}!W{row}",
            "values": [[value]],
        })
    if args.dry_run:
        json.dump({"would_write": data}, sys.stdout, ensure_ascii=False, indent=1)
        sys.stdout.write("\n")
        return
    svc = sheets_client()
    body = {"valueInputOption": "USER_ENTERED", "data": data}
    resp = svc.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id(), body=body
    ).execute()
    json.dump({
        "updated_cells": resp.get("totalUpdatedCells", 0),
        "updated_ranges": resp.get("totalUpdatedRanges", 0),
    }, sys.stdout)
    sys.stdout.write("\n")


def main():
    p = argparse.ArgumentParser(description="Upwork sheet I/O")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="read rows in N-M range")
    p_read.add_argument("range", help="row range, e.g. 97-123")
    p_read.add_argument("--html-chars", type=int, default=4000,
                        help="max chars of stripped job description (default 4000)")
    p_read.set_defaults(func=cmd_read)

    p_write = sub.add_parser("write", help="batch update column W from stdin JSON")
    p_write.add_argument("--dry-run", action="store_true",
                         help="print payload instead of writing")
    p_write.set_defaults(func=cmd_write)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
