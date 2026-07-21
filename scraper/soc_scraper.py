#!/usr/bin/env python3
"""Scrape UCSD's legacy Schedule of Classes into data/parsed/<TERM>/<SUBJ>.json.

The legacy server (act.ucsd.edu/scheduleOfClasses) is still public but
overloaded in enrollment season: it hangs on curl's default User-Agent and
intermittently throws HTTP 500 "Max Sessions Exceeded". Rules of engagement:
  - Always send a real Chrome User-Agent.
  - Establish a session (GET the form page) before requesting results.
  - Retry each page with exponential-ish backoff; re-establish the session on 500.
  - Cache every fetched page under data/samples/<TERM>/ so parsing is offline-
    repeatable (run with --parse-only to rebuild JSON from cache).

Usage:
  python3 soc_scraper.py --term SP26 --subjects CSE,MATH     # scrape + parse
  python3 soc_scraper.py --term SP26 --all-subjects
  python3 soc_scraper.py --term SP26 --parse-only            # from cache
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://act.ucsd.edu/scheduleOfClasses"
FORM_URL = f"{BASE}/scheduleOfClassesStudent.htm"
RESULT_URL = f"{BASE}/scheduleOfClassesStudentResult.htm"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

session = None


def new_session():
    global session
    session = requests.Session()
    session.headers.update({"User-Agent": UA,
                            "Accept": "text/html,application/xhtml+xml"})
    session.get(FORM_URL, timeout=45)


def fetch_page(term, subject, page, max_tries=8):
    """Fetch one results page, patiently. Returns HTML or raises."""
    params = {
        "selectedTerm": term, "xsoc_term": "", "loggedIn": "false",
        "tabNum": "tabs-crs", "selectedSubjects": subject, "courseNo": "",
        "sectionTypes": "all", "instructorType": "begin", "instructor": "",
        "titleType": "contain", "title": "", "_hideFullSec": "on",
        "_showPopup": "on", "_openSec": "on", "schedOption1": "true",
        "schedOption2": "true", "page": str(page),
    }
    delay = 5
    for attempt in range(1, max_tries + 1):
        try:
            if session is None:
                new_session()
            r = session.get(RESULT_URL, params=params, timeout=60)
            if r.status_code == 200 and ("sectxt" in r.text
                                         or "No Result Found" in r.text
                                         or "crsheader" in r.text):
                return r.text
            reason = f"HTTP {r.status_code}"
            if "Max Sessions Exceeded" in r.text:
                reason = "Max Sessions Exceeded"
        except requests.RequestException as e:
            reason = type(e).__name__
        print(f"    {subject} p{page}: {reason} (attempt {attempt}/{max_tries}),"
              f" retrying in {delay}s", flush=True)
        time.sleep(delay)
        delay = min(delay * 2, 60)
        new_session()
    raise RuntimeError(f"{subject} page {page}: server never yielded")


CLEAN = re.compile(r"\s+")


def txt(el):
    return CLEAN.sub(" ", el.get_text(" ", strip=True)).strip()


def parse_pages(pages):
    """Parse SOC result pages (one subject) into course dicts."""
    from bs4 import BeautifulSoup
    courses = []
    cur = None
    group = "A"
    for html in pages:
        soup = BeautifulSoup(html, "html.parser")
        for tr in soup.select("tr"):
            klass = tr.get("class") or []
            cells = tr.find_all("td")
            if "crsheader" in klass and len(cells) >= 4:
                # td[1]=number, td[2]=title cell with units, td[0]=subject col
                num = txt(cells[1])
                title_cell = txt(cells[2])
                m = re.match(r"(.*?)\s*\(\s*([\d./\-–to ]+)\s*Units?\)", title_cell)
                title, units = (m.group(1), m.group(2).strip()) if m else (title_cell, "")
                subj = txt(cells[0]) or (cur["subject"] if cur else "")
                cur = {"subject": subj, "number": num, "title": title,
                       "units": units, "restriction": "", "sections": []}
                courses.append(cur)
                group = "A"
            elif ("sectxt" in klass or "nonenrtxt" in klass) and cur and len(cells) >= 10:
                v = [txt(c) for c in cells]
                # layout: [pad, id, type, code, days, time, bldg, room, instructor,
                #          avail, limit] — verified against cached samples
                row = dict(zip(
                    ["_", "section_id", "type", "code", "days", "time",
                     "building", "room", "instructor", "avail", "limit"],
                    v + [""] * 11))
                t0, t1 = ("", "")
                if "-" in row["time"]:
                    t0, t1 = [p.strip() for p in row["time"].split("-", 1)]
                code = row["code"]
                if re.match(r"^[A-Z]\d\d$", code):
                    group = code[0]
                avail_raw = row["avail"]
                wl = 0
                mwl = re.search(r"FULL\s*Waitlist\((\d+)\)", avail_raw) or \
                    re.search(r"\((\d+)\)", avail_raw) if "FULL" in avail_raw.upper() else None
                if mwl:
                    wl = int(mwl.group(1))
                avail = None
                if avail_raw.isdigit():
                    avail = int(avail_raw)
                elif "FULL" in avail_raw.upper():
                    avail = 0
                limit = int(row["limit"]) if row["limit"].isdigit() else None
                cancelled = "cancel" in " ".join(v).lower()
                enrollable = bool(row["section_id"].strip().isdigit()) and not cancelled
                cur["sections"].append({
                    "section_id": row["section_id"] if row["section_id"].isdigit() else "",
                    "group": group, "type": row["type"], "code": code,
                    "days": row["days"], "time_start": t0, "time_end": t1,
                    "building": row["building"], "room": row["room"],
                    "instructor": row["instructor"], "avail": avail,
                    "limit": limit, "waitlist": wl,
                    "enrollable": enrollable, "cancelled": cancelled,
                    "note": "" if "sectxt" in klass else " ".join(v).strip(),
                })
    return [c for c in courses if c["sections"]]


def page_count(html):
    m = re.search(r"Page\s*(?:&nbsp;)?\(?\s*\d+\s*of\s*(\d+)", html)
    return int(m.group(1)) if m else 1


def scrape_subject(term, subject, cache_dir, parse_only=False):
    pages = []
    p = 1
    while True:
        cache = cache_dir / f"{subject}_p{p}.html"
        if cache.exists():
            html = cache.read_text()
        elif parse_only:
            break
        else:
            html = fetch_page(term, subject, p)
            cache.write_text(html)
            time.sleep(2)
        pages.append(html)
        if p >= page_count(html):
            break
        p += 1
    return parse_pages(pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--term", required=True)
    ap.add_argument("--subjects", default="")
    ap.add_argument("--all-subjects", action="store_true")
    ap.add_argument("--parse-only", action="store_true")
    args = ap.parse_args()

    if args.all_subjects:
        subs = [s["code"] for s in
                json.loads((ROOT / "data" / "subjects.json").read_text())]
    else:
        subs = [s for s in args.subjects.split(",") if s]
    if not subs:
        ap.error("give --subjects or --all-subjects")

    cache_dir = ROOT / "data" / "samples" / args.term
    out_dir = ROOT / "data" / "parsed" / args.term
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    failed = []
    for sub in subs:
        print(f"[{args.term}] {sub} ...", flush=True)
        try:
            courses = scrape_subject(args.term, sub, cache_dir, args.parse_only)
        except Exception as e:
            print(f"    FAILED: {e}", flush=True)
            failed.append(sub)
            continue
        if courses:
            (out_dir / f"{sub}.json").write_text(json.dumps(courses, indent=1))
        print(f"    {len(courses)} courses", flush=True)
    if failed:
        print("FAILED subjects:", ",".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
