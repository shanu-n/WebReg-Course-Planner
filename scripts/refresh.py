#!/usr/bin/env python3
"""One-command data refresh for the WebReg Course Planner.

Usage:  python3 scripts/refresh.py

Modern TSS opens the Schedule-of-Classes UI as a popup we can't drive, so we
DON'T browse it. Instead we log in once, then read the class data straight
from its backing OData v4 service with the session cookies. You just log in
and close the window — the script does the rest.

Steps:
  1. tss/connect.py — a REAL browser opens. Log in with UCSD SSO + Duo, then
     simply CLOSE the window. (You do NOT need to click into Schedule of
     Classes — ignore any tab that flickers open and shut.)
  2. tss/fetch_soc.py — pulls the full FA26 catalog + events directly from the
     yucsd_con_module OData service using the session you just created.
     -> data/tss_fa26/{modules,events}.json
  3. tss/import_fa26.py — maps the dumps into data/parsed/FA26/<DEPT>.json.
  4. Stamps today's date into data/refreshed_at.txt (the site's "Data as of").
  5. scripts/build_site.py — seed -> export -> rebuild site/.

It does NOT touch git. When Claude runs this for you it reviews the result,
commits it to the `staging` branch, and pushes the PREVIEW deploy — the live
site (main) is only updated when you say "ship".
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
PARSED = ROOT / "data" / "parsed" / "FA26"
STAMP = ROOT / "data" / "refreshed_at.txt"


def sh(*cmd, check=True):
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, cwd=ROOT, check=check)


def course_count():
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

    # 1. capture the session — browser opens; user logs in and CLOSES it.
    print("\n>>> A browser is opening. Log in (UCSD SSO + Duo), then just "
          "CLOSE the window.\n>>> You do NOT need to browse anywhere — ignore "
          "any tab that flickers.\n")
    r = sh(PY, ROOT / "tss" / "connect.py", check=False)
    if r.returncode != 0:
        print("\nLogin/capture step failed — aborting, nothing changed.")
        return 1

    # 2. pull the FA26 data straight from OData (no browsing needed)
    r = sh(PY, ROOT / "tss" / "fetch_soc.py", check=False)
    if r.returncode != 0:
        print("\nDirect OData pull failed (did you log in before closing the "
              "window?). Catalog left unchanged.")
        return 1

    # 3. map the dumps into the parsed catalog
    r = sh(PY, ROOT / "tss" / "import_fa26.py", check=False)
    if r.returncode != 0:
        print("\nImport failed — catalog left unchanged.")
        return 1

    after = course_count()
    print(f"\nCatalog after refresh: {after} courses ({after - before:+d}).")

    # 4. stamp the refresh date
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
