#!/usr/bin/env python3
"""Build data/webreg.db from parsed course data.

Inputs (produced by scraper/soc_scraper.py and tss/import_tss.py):
  data/terms.json               [{code, name, source?, is_default?}]
  data/subjects.json            [{code, name}]
  data/parsed/<TERM>/<SUBJ>.json  list of course dicts:
    {subject, number, title, units, restriction, sections: [
       {section_id, group, type, code, days, time_start, time_end,
        building, room, instructor, avail, limit, waitlist,
        enrollable, cancelled, note}]}

Idempotent: re-seeding a term replaces that term's catalog but keeps schedules
(schedule items pointing at vanished sections are pruned).
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DB = ROOT / "data" / "webreg.db"


def main():
    conn = sqlite3.connect(DB)
    conn.executescript((ROOT / "schema.sql").read_text())

    terms = json.loads((ROOT / "data" / "terms.json").read_text())
    for i, t in enumerate(terms):
        conn.execute(
            "INSERT OR REPLACE INTO terms (code,name,sort_key,source,is_default)"
            " VALUES (?,?,?,?,?)",
            (t["code"], t["name"], t.get("sort_key", len(terms) - i),
             t.get("source", "soc"), int(t.get("is_default", 0))))

    for s in json.loads((ROOT / "data" / "subjects.json").read_text()):
        conn.execute("INSERT OR REPLACE INTO subjects (code,name) VALUES (?,?)",
                     (s["code"], s["name"]))

    parsed_root = ROOT / "data" / "parsed"
    term_dirs = sorted(parsed_root.iterdir()) if parsed_root.exists() else []
    for term_dir in term_dirs:
        term = term_dir.name
        old = [r[0] for r in conn.execute(
            "SELECT id FROM courses WHERE term_code=?", (term,))]
        if old:
            ph = ",".join("?" * len(old))
            conn.execute(f"DELETE FROM sections WHERE course_id IN ({ph})", old)
            conn.execute(f"DELETE FROM courses WHERE id IN ({ph})", old)
        n_courses = n_sections = 0
        for f in sorted(term_dir.glob("*.json")):
            for c in json.loads(f.read_text()):
                cur = conn.execute(
                    "INSERT OR IGNORE INTO courses (term_code,subject_code,"
                    "course_num,title,units,restriction) VALUES (?,?,?,?,?,?)",
                    (term, c["subject"], c["number"], c["title"],
                     str(c.get("units", "")), c.get("restriction", "")))
                if not cur.lastrowid or not cur.rowcount:
                    continue
                cid = cur.lastrowid
                n_courses += 1
                for s in c.get("sections", []):
                    conn.execute(
                        "INSERT INTO sections (course_id,section_id,group_code,"
                        "meeting_type,section_code,days,time_start,time_end,"
                        "building,room,instructor,seats_avail,seats_limit,"
                        "waitlist_ct,enrollable,cancelled,note)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (cid, s.get("section_id", ""), s.get("group", "A"),
                         s.get("type", "LE"), s.get("code", ""),
                         s.get("days", ""), s.get("time_start", ""),
                         s.get("time_end", ""), s.get("building", ""),
                         s.get("room", ""), s.get("instructor", ""),
                         s.get("avail"), s.get("limit"),
                         s.get("waitlist", 0), int(s.get("enrollable", 0)),
                         int(s.get("cancelled", 0)), s.get("note", "")))
                    n_sections += 1
        print(f"{term}: {n_courses} courses, {n_sections} section rows")

    conn.execute("""DELETE FROM schedule_items WHERE section_pk NOT IN
                    (SELECT id FROM sections)""")
    conn.commit()
    conn.close()
    print(f"OK → {DB}")


if __name__ == "__main__":
    sys.exit(main())
