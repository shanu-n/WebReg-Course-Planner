#!/usr/bin/env python3
"""Map the raw FA26 TSS dump into WebReg's parsed format.

Input  : data/tss_fa26/{modules,events}.json  (from the TSS OData dump)
Output : data/parsed/FA26/<DEPT>.json          (frozen seed.py schema)
         + FA26 entry (source=tss, is_default) in data/terms.json

TSS data model (SAP SLcM, service yucsd_con_module):
  YUCSD_CON_MODULE  = one row per course offering (CourseAbbr, title, credits,
                      department, ModuleID).
  YUCSD_CON_EVENTS  = one row per meeting-within-a-package. Events sharing an
                      EventPkgDisplayID (e.g. SE00154263 = "CSE-003 (P-001-001)")
                      form ONE enrollable section: a lecture (LE) plus its
                      discussion (DI) / lab (LA), and the package carries the
                      seats/limit/waitlist a student books against.
  The human-readable `Sched` string carries days, times, modality, room, and a
  "Final Examination …" line — parsed here into meeting + FI rows.

WebReg mapping:
  course  = module (subject+number from CourseAbbr like "CSE-003").
  group   = lecture number (EventKey "001" -> letter A, "002" -> B).
  rows    = deduped meetings under that group: lecture "A00", then each
            enrollable package as a sub-row "A01", "A02"… (the row that carries
            the Enroll button + seats), plus a final-exam FI row.
"""
import json
import re
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "tss_fa26"
OUT = ROOT / "data" / "parsed" / "FA26"

DAY_MAP = {"M": "M", "MO": "M", "TU": "Tu", "W": "W", "WE": "W",
           "TH": "Th", "F": "F", "FR": "F", "SA": "Sa", "SU": "Su"}
DAY_ORDER = ["M", "Tu", "W", "Th", "F", "Sa", "Su"]

# TSS truncates building names to 40 characters; restore the full names.
BUILDING_FIX = {
    "Computer Science and Engineering Buildin":
        "Computer Science and Engineering Building",
    "Structural and Materials Engineering Bui":
        "Structural and Materials Engineering Building",
    "Science and Engineering Research Facilit":
        "Science and Engineering Research Facility",
    "MCTF - Marine Conservation and Technolog":
        "MCTF - Marine Conservation and Technology",
    "Medical Education and Telemedicine Cente":
        "Medical Education and Telemedicine Center",
    # ambiguous truncated designator ("- G"/"- N") — drop to the base name
    "Extended Studies and Public Programs - G":
        "Extended Studies and Public Programs",
    "Extended Studies and Public Programs - N":
        "Extended Studies and Public Programs",
}


def fix_building(b):
    return BUILDING_FIX.get(b, b)


def course_parts(abbr):
    """'CSE-003' -> ('CSE','3'); '010R' keeps suffix -> '10R'."""
    if "-" in abbr:
        subj, num = abbr.split("-", 1)
    else:
        m = re.match(r"([A-Za-z]+)(.*)", abbr)
        subj, num = (m.group(1), m.group(2)) if m else (abbr, "")
    m = re.match(r"0*(\d+)([A-Za-z]*)$", num.strip())
    if m:
        num = m.group(1) + m.group(2).upper()
    else:
        num = num.strip().lstrip("0") or num.strip()
    return subj.strip().upper(), num


def to_wr_time(t):
    """'08:00 AM' -> '8:00a'; '05:00 PM' -> '5:00p'."""
    m = re.match(r"(\d{1,2}):(\d{2})\s*([AP])M", t.strip(), re.I)
    if not m:
        return ""
    h, mn, ap = int(m.group(1)), m.group(2), m.group(3).lower()
    return f"{h}:{mn}{ap}"


def norm_days(chunk):
    """'Tu, Th' / 'MWF' / 'M Tu W' -> 'TuTh' / 'MWF'."""
    toks = re.findall(r"Su|Sa|Tu|Th|Mo|We|Fr|M|W|F", chunk)
    out = []
    for t in toks:
        d = DAY_MAP.get(t.upper())
        if d and d not in out:
            out.append(d)
    return "".join(sorted(out, key=DAY_ORDER.index))


_LOC = re.compile(r"@\s*(.+?)\s+Room\s+(\S+)\s*$", re.I)
_MEET = re.compile(
    r"^([A-Za-z, ]+?)\s+(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)\s*(.*)$",
    re.I)


def parse_sched(sched):
    """Return (meetings, final) from the Sched string.

    meetings: list of {days,t0,t1,building,room}. final: same or None.
    """
    meetings, final = [], None
    for line in (sched or "").split("\n"):
        line = line.strip()
        if not line:
            continue
        fm = re.match(r"Final Exam\w*\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+"
                      r"(\d{1,2}:\d{2}\s*[AP]M)\s*-\s*(\d{1,2}:\d{2}\s*[AP]M)",
                      line, re.I)
        if fm:
            final = {"date": fm.group(1), "t0": to_wr_time(fm.group(2)),
                     "t1": to_wr_time(fm.group(3))}
            continue
        mm = _MEET.match(line)
        if not mm:
            continue
        days = norm_days(mm.group(1))
        tail = mm.group(4).strip()
        building, room = "", ""
        lm = _LOC.search(tail)
        if lm:
            building, room = fix_building(lm.group(1).strip()), lm.group(2).strip()
        elif "online" in tail.lower():
            building = "RCLAS" if "live" in tail.lower() else "ONLINE"
        meetings.append({"days": days, "t0": to_wr_time(mm.group(2)),
                         "t1": to_wr_time(mm.group(3)),
                         "building": building, "room": room})
    return meetings, final


def clean_instr(name):
    return (name or "").strip()


def main():
    modules = json.load(open(SRC / "modules.json"))
    events = json.load(open(SRC / "events.json"))
    OUT.mkdir(parents=True, exist_ok=True)

    mod_by_id = {m["ModuleID"]: m for m in modules}
    ev_by_mod = defaultdict(list)
    for e in events:
        ev_by_mod[e["ModuleID"]].append(e)

    by_dept = defaultdict(list)
    n_courses = n_sections = 0

    for mid, m in mod_by_id.items():
        subj, num = course_parts(m["CourseAbbr"])
        evs = ev_by_mod.get(mid, [])
        course = {"subject": subj, "number": num,
                  "title": m.get("CourseTitle", ""),
                  "units": m.get("CreditsDisplay", ""),
                  "restriction": "" if m.get("DeptApprovalReq") == "Not Required"
                                 else "D", "sections": []}

        # group events by lecture number (EventKey) -> letter group
        groups = defaultdict(list)
        for e in evs:
            groups[e.get("EventKey", "001")].append(e)

        for gi, (key, gevs) in enumerate(sorted(groups.items())):
            letter = chr(ord("A") + gi)
            # A physical meeting can be reused across enrollment packages
            # (one lecture/discussion serving several lab combos) — dedupe by
            # EventID so each real meeting is emitted once, keeping the package
            # with the most seats for its seat display.
            phys = OrderedDict()
            for e in gevs:
                eid = e.get("EventID")
                cur = phys.get(eid)
                if cur is None or (e.get("EventPkgSeatsAvailable") or 0) > (
                        cur.get("EventPkgSeatsAvailable") or 0):
                    phys[eid] = e

            lectures = [e for e in phys.values()
                        if e.get("TeachingMethod") == "LE"]
            subs = [e for e in phys.values()
                    if e.get("TeachingMethod") != "LE"]
            final_row = None
            has_subs = bool(subs)

            def emit(e, code, mtype, enrollable):
                nonlocal n_sections, final_row
                meets, final = parse_sched(e.get("Sched", ""))
                if final and not final_row:
                    final_row = final
                first = True
                for mt in (meets or [{"days": "", "t0": "", "t1": "",
                                      "building": "", "room": ""}]):
                    course["sections"].append({
                        "section_id": str(e.get("EventPkgObjid", ""))
                                      if (enrollable and first) else "",
                        "group": letter, "type": mtype, "code": code,
                        "days": mt["days"], "time_start": mt["t0"],
                        "time_end": mt["t1"], "building": mt["building"],
                        "room": mt["room"],
                        "instructor": clean_instr(e.get("InstructorName", "")),
                        "avail": e.get("EventPkgSeatsAvailable")
                                 if (enrollable and first) else None,
                        "limit": e.get("EventPkgLimit")
                                 if (enrollable and first) else None,
                        "waitlist": e.get("EventPkgNumOnWaitl", 0)
                                    if (enrollable and first) else 0,
                        "enrollable": 1 if (enrollable and first
                                            and not e.get("EventPkgDisable")) else 0,
                        "cancelled": e.get("Status") == "Cancelled",
                        "note": ""})
                    n_sections += 1
                    first = False

            # lecture -> A00 (non-enrollable when sub-sections exist)
            for e in lectures:
                emit(e, f"{letter}00", "LE", enrollable=not has_subs)

            # sub-sections: discussions A01.. , labs A50.. , others A0x
            di = la = other = 0
            for e in sorted(subs, key=lambda x: x.get("EventAbbr", "")):
                tm = e.get("TeachingMethod", "DI")
                if tm == "LA":
                    la += 1
                    code = f"{letter}{49 + la:02d}"
                elif tm == "DI":
                    di += 1
                    code = f"{letter}{di:02d}"
                else:
                    other += 1
                    code = f"{letter}{80 + other:02d}"
                emit(e, code, tm, enrollable=True)

            if final_row:
                course["sections"].append({
                    "section_id": "", "group": letter, "type": "FI",
                    "code": final_row["date"], "days": "",
                    "time_start": final_row["t0"], "time_end": final_row["t1"],
                    "building": "", "room": "", "instructor": "",
                    "avail": None, "limit": None, "waitlist": 0,
                    "enrollable": 0, "cancelled": 0, "note": ""})
                n_sections += 1

        if course["sections"]:
            by_dept[subj].append(course)
            n_courses += 1

    for dept, courses in by_dept.items():
        courses.sort(key=lambda c: (
            re.sub(r"\D", "", c["number"]).zfill(4), c["number"]))
        (OUT / f"{dept}.json").write_text(json.dumps(courses, indent=1))

    # terms.json: FA26 default, keep others
    terms_path = ROOT / "data" / "terms.json"
    terms = json.loads(terms_path.read_text()) if terms_path.exists() else []
    terms = [t for t in terms if t["code"] != "FA26"]
    for t in terms:
        t["is_default"] = 0
    terms.insert(0, {"code": "FA26", "name": "Fall 2026", "source": "tss",
                     "is_default": 1, "sort_key": 100})
    terms_path.write_text(json.dumps(terms, indent=1))

    print(f"FA26: {n_courses} courses, {n_sections} section rows, "
          f"{len(by_dept)} departments -> {OUT}")


if __name__ == "__main__":
    main()
