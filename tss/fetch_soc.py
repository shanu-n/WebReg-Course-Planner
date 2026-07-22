#!/usr/bin/env python3
"""Fetch FA26 Schedule-of-Classes data straight from TSS OData v4.

Modern TSS opens the Schedule-of-Classes UI as a popup our headed capture
can't drive — but the app's backing OData v4 service is fully readable with
the login cookies connect.py already saved. So we skip the browsing entirely
and read the data directly.

Service : /sap/opu/odata4/sap/yucsd_con_module_sb/.../yucsd_con_module_servicedef/0001/
          (term-scoped to the current Schedule of Classes = FA26)
Reads   : tss/state.json   (session cookies from connect.py)
Writes  : data/tss_fa26/{modules,events}.json  (bare row lists, the exact
          shape import_fa26.py consumes)

Usage:  python3 tss/fetch_soc.py
"""
import json
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "tss" / "state.json"
OUT = ROOT / "data" / "tss_fa26"
BASE = ("https://tss.ucsd.edu/sap/opu/odata4/sap/yucsd_con_module_sb/"
        "srvd/sap/yucsd_con_module_servicedef/0001/")
# entity set -> output file. import_fa26.py only needs these two; events
# carries the Sched text, seat counts, and instructor inline.
SETS = {"modules": "YUCSD_CON_MODULE", "events": "YUCSD_CON_EVENTS"}
PAGE = 5000                 # rows per request ($skip/$top paging)
MIN_MODULES = 500           # sanity floor — refuse to write a short pull

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")


def cookies():
    st = json.loads(STATE.read_text())
    return "; ".join(f"{c['name']}={c['value']}" for c in st["cookies"]
                     if c["domain"].endswith("tss.ucsd.edu"))


def get(url, cook):
    req = urllib.request.Request(url, headers={
        "Cookie": cook, "Accept": "application/json", "User-Agent": _UA})
    with urllib.request.urlopen(req, context=_CTX, timeout=90) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_set(es, cook):
    """Pull an entire entity set via $skip/$top paging."""
    rows, skip = [], 0
    while True:
        d = get(f"{BASE}{es}?sap-client=500&$top={PAGE}&$skip={skip}", cook)
        batch = d.get("value", [])
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        skip += len(batch)
    return rows


def main():
    cook = cookies()
    if "SAP_SESSIONID" not in cook:
        print("No live TSS session in tss/state.json — run connect.py and log "
              "in (SSO + Duo) first, then re-run this.")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    pulled = {}
    for name, es in SETS.items():
        try:
            rows = fetch_set(es, cook)
        except Exception as e:
            print(f"  {name} ({es}): FAILED — {e}")
            print("Session may have expired (SAP dies after ~30-60 min idle) "
                  "— run connect.py again to re-login.")
            return 1
        pulled[name] = rows
        print(f"  {name}: {len(rows)} rows")

    if len(pulled.get("modules", [])) < MIN_MODULES:
        print(f"Only {len(pulled.get('modules', []))} modules — that looks "
              "wrong (session issue?). Refusing to overwrite the good dumps.")
        return 1

    for name, rows in pulled.items():
        (OUT / f"{name}.json").write_text(json.dumps(rows))
        print(f"  wrote data/tss_fa26/{name}.json ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
