#!/usr/bin/env python3
"""TSS session capture + API discovery.

Opens a REAL (headed) Chromium window on the new UCSD student system so Sahir
can log in with SSO + Duo himself. We never touch credentials. After login:
  1. storage_state (cookies) → tss/state.json   [git-ignored]
  2. Every JSON XHR the app makes while you browse class search is recorded to
     data/tss_raw/<n>_<host>_<path>.json with its URL, so we can map the API.

Usage:
  python3 tss/connect.py                  # capture session + record traffic
  python3 tss/connect.py --url <tss url>  # if the default entry URL is wrong

Leave the window open and browse: open class search, pick FA26, search a few
departments. Close the window (or Ctrl-C here) when done; everything is saved
as you go.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "tss" / "state.json"
RAW = ROOT / "data" / "tss_raw"

# Entry points to try, most specific first. TSS lives behind SSO; any of these
# should bounce through the login page. Adjust with --url if recon found better.
DEFAULT_URL = "https://tritonlink.ucsd.edu"

UCSD_HOSTS = re.compile(r"(ucsd\.edu|ucsd\.textbook|instructure)", re.I)
SKIP_CT = re.compile(r"image/|font/|text/css|javascript", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    counter = {"n": 0}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(
            storage_state=STATE if STATE.exists() else None,
            viewport={"width": 1500, "height": 950})

        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                if SKIP_CT.search(ct) or "json" not in ct:
                    return
                if not UCSD_HOSTS.search(resp.url):
                    return
                body = resp.json()
            except Exception:
                return
            counter["n"] += 1
            host = re.sub(r"https?://([^/]+).*", r"\1", resp.url)
            path = re.sub(r"[^A-Za-z0-9_.-]+", "_", resp.url.split(host, 1)[1])[:120]
            out = RAW / f"{counter['n']:04d}_{host}_{path}.json"
            out.write_text(json.dumps(
                {"url": resp.url, "status": resp.status, "body": body}, indent=1))
            print(f"  captured {out.name}")

        ctx.on("response", on_response)
        page = ctx.new_page()
        print(f"Opening {args.url} — log in with SSO + Duo, then browse class "
              f"search for FA26. Session + API traffic are saved live.")
        page.goto(args.url, timeout=120000)

        try:
            while True:
                page.wait_for_timeout(5000)
                ctx.storage_state(path=STATE)
                if not ctx.pages:
                    break
        except KeyboardInterrupt:
            pass
        except Exception:
            pass  # window closed
        try:
            ctx.storage_state(path=STATE)
        except Exception:
            pass
        browser.close()

    print(f"\nSaved session → {STATE}")
    print(f"Captured {counter['n']} JSON responses → {RAW}")
    print("Next: we inspect data/tss_raw/ to map the API, then build the FA26 importer.")


if __name__ == "__main__":
    sys.exit(main())
