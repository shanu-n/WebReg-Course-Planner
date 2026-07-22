#!/usr/bin/env python3
"""One-command data refresh for the WebReg Course Planner.

Usage:  python3 scripts/refresh.py

What it does, in order:
  1. Archives the previous raw capture (data/tss_raw -> data/tss_raw.last) so
     this session is a clean snapshot with no stale-merge ambiguity.
  2. Runs tss/connect.py — a REAL browser opens. Log in with UCSD SSO + Duo,
     open Schedule of Classes, pick Fall 2026, and search the departments you
     want refreshed (search everything for a full refresh, or just the ones
     that changed). Close the window when done.
  3. Runs tss/import_tss.py — turns the capture into data/parsed/FA26/<SUBJ>.json.
     This only ADDS or UPDATES the subjects you searched; every other subject's
     data is kept, so a partial browse can never shrink the catalog.
  4. Stamps today's date into data/refreshed_at.txt (the "Data as of" line the
     site shows).
  5. Runs scripts/build_site.py (seed -> export -> rebuild site/).

It does NOT touch git. When Claude runs this for you it reviews the result,
commits it to the `staging` branch, and pushes the PREVIEW deploy — the live
site friends use (main) is only updated when you say "ship".
"""
import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
RAW = ROOT / "data" / "tss_raw"
RAW_LAST = ROOT / "data" / "tss_raw.last"
PARSED = ROOT / "data" / "parsed" / "FA26"
STAMP = ROOT / "data" / "refreshed_at.txt"


def sh(*cmd, check=True):
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=ROOT, check=check)


def course_count():
    """Total courses currently in the parsed FA26 catalog."""
    if not PARSED.is_dir():
        return 0
    n = 0
    for f in PARSED.glob("*.json"):
        try:
            n += len(json.loads(f.read_text()))
        except Exception:
            pass
    return n


def main():
    print("=" * 64)
    print("WebReg data refresh")
    print("=" * 64)

    before = course_count()
    print(f"Current catalog: {before} courses in data/parsed/FA26/")

    # 1. archive the previous raw capture so this session is self-contained
    if RAW.exists():
        if RAW_LAST.exists():
            shutil.rmtree(RAW_LAST)
        shutil.move(str(RAW), str(RAW_LAST))
        print(f"Archived previous capture -> data/{RAW_LAST.name}")
    RAW.mkdir(parents=True, exist_ok=True)

    # 2. capture — browser opens; user logs in (SSO + Duo) and browses
    print("\n>>> A browser is opening. Log in (SSO + Duo), open Schedule of "
          "Classes,\n>>> pick Fall 2026, search the departments you want, then "
          "CLOSE the window.\n")
    r = sh(PY, ROOT / "tss" / "connect.py", check=False)
    if r.returncode != 0:
        print("\nCapture step exited abnormally — aborting, nothing changed.")
        return 1

    # 3. import — adds/updates only the subjects captured this session
    r = sh(PY, ROOT / "tss" / "import_tss.py", check=False)
    if r.returncode != 0:
        print("\nNo new class data was captured (did you reach Schedule of "
              "Classes\nand run a search?). Catalog left unchanged — nothing "
              "to build.")
        return 1

    after = course_count()
    print(f"\nCatalog after import: {after} courses ({after - before:+d}).")

    # 4. stamp the refresh date (the site's "Data as of" line)
    today = datetime.date.today().strftime("%B %-d, %Y")
    STAMP.write_text(today + "\n")
    print(f"Stamped data/refreshed_at.txt = {today}")

    # 5. rebuild the static site
    sh(PY, ROOT / "scripts" / "build_site.py")

    print("\n" + "=" * 64)
    print(f"Refresh built locally — data as of {today}, {after} courses.")
    print("Changes are in your working tree (data/ + site/), not yet pushed.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
