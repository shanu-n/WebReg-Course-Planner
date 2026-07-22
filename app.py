#!/usr/bin/env python3
"""WebReg Revival — Flask server + JSON API.

Serves the classic-WebReg UI and a small API over data/webreg.db.
Planning tool only: 'enroll' writes to local schedule tables, never to UCSD.
"""
import os
import re
import sqlite3
from pathlib import Path

from flask import Flask, g, jsonify, render_template, request

DB_PATH = Path(os.environ.get("WEBREG_DB", Path(__file__).parent / "data" / "webreg.db"))
# 5070, not 5060: browsers hard-block port 5060 (SIP) with ERR_UNSAFE_PORT.
PORT = int(os.environ.get("WEBREG_PORT", 5070))

app = Flask(__name__)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def rows(cursor):
    return [dict(r) for r in cursor.fetchall()]


# ---------------------------------------------------------------- pages

def _data_asof():
    """The 'Data as of' date, written by scripts/refresh.py."""
    f = Path(__file__).resolve().parent / "data" / "refreshed_at.txt"
    return f.read_text().strip() if f.exists() else "—"


@app.route("/")
def page_term_select():
    """Classic WebReg landing: pick a term, hit Go."""
    return render_template("index.html", data_asof=_data_asof())


# ---------------------------------------------------------------- api: catalog

@app.route("/api/terms")
def api_terms():
    return jsonify(rows(db().execute(
        "SELECT code, name, source, is_default FROM terms ORDER BY sort_key DESC")))


@app.route("/api/subjects")
def api_subjects():
    return jsonify(rows(db().execute(
        "SELECT code, name FROM subjects ORDER BY code")))


_NUMLIKE = re.compile(r"\d+[A-Za-z]{0,2}$")


def _q_number_clause(where, args, num):
    """Match a course number. Pure digits also match letter-suffixed
    variants (searching '3' finds '3' and '3L', like WebReg's simple box)."""
    num = num.upper()
    if num.isdigit():
        where.append("(UPPER(c.course_num) = ? OR UPPER(c.course_num) GLOB ?)")
        args += [num, num + "[A-Z]*"]
    else:
        where.append("UPPER(c.course_num) = ?")
        args.append(num)


def _apply_simple_q(q_text, where, args, conn):
    """WebReg simple-search box: 'BILD', 'BILD 3', or 'computer 3'."""
    toks = q_text.split()
    if not toks:
        return
    subjects = {r["code"].upper() for r in conn.execute("SELECT code FROM subjects")}
    # split a glued subject+number, "CSE11" -> ["CSE","11"], when the letters
    # are a real subject (so title words like "data" are left alone)
    if len(toks) == 1:
        m = re.match(r"^([A-Za-z]{2,6})(\d+[A-Za-z]{0,2})$", toks[0])
        if m and m.group(1).upper() in subjects:
            toks = [m.group(1), m.group(2)]
    if len(toks) == 1:
        t = toks[0]
        if t.upper() in subjects:
            where.append("UPPER(c.subject_code) = ?")
            args.append(t.upper())
        elif _NUMLIKE.fullmatch(t):
            _q_number_clause(where, args, t)
        else:
            where.append("c.title LIKE ?")
            args.append(f"%{t}%")
    elif len(toks) == 2 and toks[0].upper() in subjects and _NUMLIKE.fullmatch(toks[1]):
        where.append("UPPER(c.subject_code) = ?")
        args.append(toks[0].upper())
        _q_number_clause(where, args, toks[1])
    elif _NUMLIKE.fullmatch(toks[-1]):
        _q_number_clause(where, args, toks[-1])
        for w in toks[:-1]:
            where.append("c.title LIKE ?")
            args.append(f"%{w}%")
    else:
        where.append("c.title LIKE ?")
        args.append(f"%{q_text}%")


@app.route("/api/search")
def api_search():
    """Search courses like WebReg's Enroll tab.

    Params: term (required), q (simple-search box), subjects (CSV), courseno,
    instructor, title, sectionid, hidefull (1/0), onlyopen (1/0).
    Returns courses with nested section rows.
    """
    conn = db()
    term = request.args.get("term", "")
    q = ["c.term_code = ?"]
    args = [term]

    simple = request.args.get("q", "").strip()
    if simple:
        _apply_simple_q(simple, q, args, conn)

    subjects = [s for s in request.args.get("subjects", "").split(",") if s]
    if subjects:
        q.append("c.subject_code IN (%s)" % ",".join("?" * len(subjects)))
        args += subjects
    courseno = request.args.get("courseno", "").strip()
    if courseno:
        q.append("UPPER(c.course_num) = UPPER(?)")
        args.append(courseno)
    title = request.args.get("title", "").strip()
    if title:
        q.append("c.title LIKE ?")
        args.append(f"%{title}%")
    instructor = request.args.get("instructor", "").strip()
    sectionid = request.args.get("sectionid", "").strip()
    if sectionid:
        q.append("c.id IN (SELECT course_id FROM sections WHERE section_id = ?)")
        args.append(sectionid)
    if instructor:
        q.append("c.id IN (SELECT course_id FROM sections WHERE instructor LIKE ?)")
        args.append(f"%{instructor}%")

    courses = rows(conn.execute(
        "SELECT c.* FROM courses c WHERE %s ORDER BY c.subject_code, "
        "CAST(REPLACE(REPLACE(c.course_num,'L',''),'R','') AS INTEGER), c.course_num"
        % " AND ".join(q), args))

    # Both filters keep only letter-groups with an open enrollable section
    # (hidefull = results-grid checkbox; onlyopen = advanced-search
    # "Only show sections with seats available").
    open_only = request.args.get("hidefull") == "1" or request.args.get("onlyopen") == "1"
    for c in courses:
        secs = rows(conn.execute(
            "SELECT * FROM sections WHERE course_id = ? ORDER BY group_code, "
            "CASE meeting_type WHEN 'FI' THEN 1 ELSE 0 END, section_code", (c["id"],)))
        if open_only:
            groups_open = {s["group_code"] for s in secs
                           if s["enrollable"] and (s["seats_avail"] or 0) > 0}
            secs = [s for s in secs if s["group_code"] in groups_open]
        c["sections"] = secs
    return jsonify([c for c in courses if c["sections"]])


# ---------------------------------------------------------------- api: appointment

@app.route("/api/appointment")
def api_appointment():
    """Enrollment-appointment stub for the 'Appointment time' modal.

    Static, plausible pass windows for the default term (planning-only —
    there is no real appointment; Enroll is always active)."""
    row = db().execute(
        "SELECT code FROM terms WHERE is_default=1 ORDER BY sort_key DESC").fetchone()
    return jsonify({
        "term": row["code"] if row else "FA25",
        "first_pass": {"start": "Saturday, 05/17/2025 8:00 a.m. PT",
                       "end": "Monday, 05/19/2025 11:59 p.m. PT"},
        "second_pass": {"start": "Thursday, 05/29/2025 5:20 p.m. PT",
                        "end": "Friday, 09/26/2025 11:59 p.m. PT"},
    })


# ---------------------------------------------------------------- schedule helpers

_DAY_TOKENS = re.compile(r"Su|Sa|Tu|Th|M|W|F")
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})([ap])$")


def _time_mins(t):
    m = _TIME_RE.fullmatch((t or "").strip().lower())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return h * 60 + mi


def _meetings_overlap(a, b):
    """True if two section rows meet on a common day at overlapping times."""
    days_a = set(_DAY_TOKENS.findall(a["days"] or ""))
    days_b = set(_DAY_TOKENS.findall(b["days"] or ""))
    if not (days_a & days_b):
        return False
    s1, e1 = _time_mins(a["time_start"]), _time_mins(a["time_end"])
    s2, e2 = _time_mins(b["time_start"]), _time_mins(b["time_end"])
    if None in (s1, e1, s2, e2):
        return False  # TBA rows can't conflict
    return s1 < e2 and s2 < e1


def _group_meetings(conn, course_id, group_code, section_pk):
    """All class meetings that travel with an enrollable choice: the chosen
    row plus its non-enrollable siblings (LE etc.), finals excluded."""
    return rows(conn.execute(
        "SELECT * FROM sections WHERE course_id=? AND group_code=? "
        "AND (enrollable=0 OR id=?) AND meeting_type != 'FI'",
        (course_id, group_code, section_pk)))


def _has_conflict(conn, schedule_id, sec, exclude_item_id=None):
    """Does the section (with its group siblings) collide with anything
    already on the schedule?"""
    new_meetings = _group_meetings(conn, sec["course_id"], sec["group_code"], sec["id"])
    items = conn.execute(
        "SELECT si.id, si.course_id, si.section_pk, s.group_code "
        "FROM schedule_items si JOIN sections s ON s.id = si.section_pk "
        "WHERE si.schedule_id = ?", (schedule_id,)).fetchall()
    for it in items:
        if exclude_item_id is not None and it["id"] == exclude_item_id:
            continue
        for m1 in _group_meetings(conn, it["course_id"], it["group_code"],
                                  it["section_pk"]):
            for m2 in new_meetings:
                if _meetings_overlap(m1, m2):
                    return True
    return False


def _course_label(conn, course_id):
    c = conn.execute("SELECT subject_code, course_num FROM courses WHERE id=?",
                     (course_id,)).fetchone()
    return f"{c['subject_code']} {c['course_num']}" if c else "this class"


def _get_schedule(term):
    conn = db()
    row = conn.execute(
        "SELECT id FROM schedules WHERE term_code=? AND name='My Schedule'",
        (term,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO schedules (term_code, name) VALUES (?, 'My Schedule')", (term,))
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------- api: schedule

@app.route("/api/schedule")
def api_schedule():
    term = request.args.get("term", "")
    sid = _get_schedule(term)
    items = rows(db().execute("""
        SELECT si.id AS item_id, si.status, si.units, si.grade_option,
               si.waitlist_pos AS position,
               c.id AS course_id, c.subject_code, c.course_num, c.title,
               s.id AS section_pk, s.group_code, s.section_code, s.section_id
        FROM schedule_items si
        JOIN courses c ON c.id = si.course_id
        JOIN sections s ON s.id = si.section_pk
        WHERE si.schedule_id = ?
        ORDER BY c.subject_code, c.course_num""", (sid,)))
    for it in items:
        if it["status"] != "waitlisted":
            it["position"] = None
        it["meetings"] = rows(db().execute(
            "SELECT * FROM sections WHERE course_id=? AND group_code=? "
            "AND (enrollable=0 OR id=?) ORDER BY "
            "CASE meeting_type WHEN 'FI' THEN 1 ELSE 0 END, section_code",
            (it["course_id"], it["group_code"], it["section_pk"])))
    return jsonify(items)


@app.route("/api/schedule/add", methods=["POST"])
def api_schedule_add():
    d = request.get_json(force=True)
    term, section_pk = d["term"], d["section_pk"]
    status = d.get("status", "enrolled")
    conn = db()
    sec = conn.execute("SELECT * FROM sections WHERE id=?", (section_pk,)).fetchone()
    if not sec or sec["cancelled"] or sec["meeting_type"] == "FI":
        return jsonify({"error": "Invalid section."}), 400
    sid = _get_schedule(term)
    # You may plan the same COURSE several times (compare lecture options), but
    # not the exact same SECTION twice — once planned it's already on the grid.
    dup = conn.execute(
        "SELECT 1 FROM schedule_items WHERE schedule_id=? AND section_pk=?",
        (sid, section_pk)).fetchone()
    if dup:
        return jsonify({"error": f"{_course_label(conn, sec['course_id'])} "
                                 "section is already in your plan."}), 409
    position = None
    if status == "waitlisted":
        position = (sec["waitlist_ct"] or 0) + 1
    conflict = _has_conflict(conn, sid, sec)
    conn.execute(
        "INSERT INTO schedule_items (schedule_id, course_id, section_pk, status,"
        " units, grade_option, waitlist_pos) VALUES (?,?,?,?,?,?,?)",
        (sid, sec["course_id"], section_pk, status,
         d.get("units", "4"), d.get("grade_option", "L"), position))
    conn.commit()
    out = {"ok": True}
    if position is not None:
        out["position"] = position
    if conflict:
        out["conflict"] = True  # WebReg allows the add; frontend shows the warning
    return jsonify(out)


@app.route("/api/schedule/drop", methods=["POST"])
def api_schedule_drop():
    d = request.get_json(force=True)
    conn = db()
    conn.execute("DELETE FROM schedule_items WHERE id=?", (d["item_id"],))
    conn.commit()
    return jsonify({"ok": True})


@app.route("/api/schedule/change", methods=["POST"])
def api_schedule_change():
    """WebReg 'Change' flow: units / grading option / switch section within
    the same course."""
    d = request.get_json(force=True)
    conn = db()
    item = conn.execute("SELECT * FROM schedule_items WHERE id=?",
                        (d["item_id"],)).fetchone()
    if not item:
        return jsonify({"error": "Invalid schedule item."}), 400

    out = {"ok": True}
    new_pk = d.get("section_pk")
    position = item["waitlist_pos"]
    if new_pk is not None and new_pk != item["section_pk"]:
        sec = conn.execute("SELECT * FROM sections WHERE id=?", (new_pk,)).fetchone()
        if (not sec or sec["cancelled"] or sec["meeting_type"] == "FI"
                or sec["course_id"] != item["course_id"]):
            return jsonify({"error": "Invalid section."}), 400
        label = _course_label(conn, sec["course_id"])
        if item["status"] == "enrolled" and (sec["seats_avail"] or 0) <= 0:
            return jsonify({"error": f"There are no seats available for {label}. "
                                     "You may add yourself to the waitlist."}), 409
        if item["status"] == "waitlisted":
            position = (sec["waitlist_ct"] or 0) + 1
            out["position"] = position
        if _has_conflict(conn, item["schedule_id"], sec,
                         exclude_item_id=item["id"]):
            out["conflict"] = True
    else:
        new_pk = None

    conn.execute(
        "UPDATE schedule_items SET units=COALESCE(?,units),"
        " grade_option=COALESCE(?,grade_option),"
        " section_pk=COALESCE(?,section_pk), waitlist_pos=? WHERE id=?",
        (d.get("units"), d.get("grade_option"), new_pk, position, d["item_id"]))
    conn.commit()
    return jsonify(out)


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} missing — run: python3 seed.py")
    app.run(host="127.0.0.1", port=PORT, debug=False)
