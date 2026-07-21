/* localdb.js — browser-only backend for the static build.
 *
 * Overrides window.fetch for /api/* routes so the existing webreg.js runs
 * unchanged with no server: the FA26 catalog is loaded from data/catalog.json
 * and each visitor's schedule lives in their own browser (localStorage).
 * Mirrors the Flask app's search + schedule semantics.  Load BEFORE webreg.js.
 */
(function () {
  "use strict";

  const LS_KEY = "webreg_fa26_schedule_v1";
  const DATA = { loaded: null, courses: [], subjects: [], terms: [],
                 byCourse: new Map(), bySection: new Map(), subjSet: new Set() };

  /* -------------------------------------------------- data load (once) */
  function loadData() {
    if (DATA.loaded) return DATA.loaded;
    DATA.loaded = (async () => {
      const [catalog, subjects, terms] = await Promise.all([
        realFetch("data/catalog.json").then(r => r.json()),
        realFetch("data/subjects.json").then(r => r.json()),
        realFetch("data/terms.json").then(r => r.json()),
      ]);
      DATA.courses = catalog;
      DATA.subjects = subjects;
      DATA.terms = terms;
      DATA.subjSet = new Set(subjects.map(s => s.code.toUpperCase()));
      for (const c of catalog) {
        DATA.byCourse.set(c.id, c);
        for (const s of c.sections) DATA.bySection.set(s.id, { sec: s, course: c });
      }
    })();
    return DATA.loaded;
  }

  /* -------------------------------------------------- schedule storage */
  function loadSched() {
    try { return JSON.parse(localStorage.getItem(LS_KEY)) || { seq: 1, items: [] }; }
    catch (e) { return { seq: 1, items: [] }; }
  }
  function saveSched(s) { localStorage.setItem(LS_KEY, JSON.stringify(s)); }

  /* group meetings that travel with a chosen section (siblings + itself),
     finals last — matches app.py api_schedule */
  function groupMeetings(course, groupCode, sectionPk) {
    return course.sections
      .filter(s => s.group_code === groupCode && (!s.enrollable || s.id === sectionPk))
      .sort((a, b) => {
        const fa = a.meeting_type === "FI" ? 1 : 0, fb = b.meeting_type === "FI" ? 1 : 0;
        return fa - fb || String(a.section_code).localeCompare(String(b.section_code));
      });
  }

  function scheduleItems() {
    const s = loadSched();
    const out = [];
    for (const rec of s.items) {
      const hit = DATA.bySection.get(rec.section_pk);
      if (!hit) continue;                      // section vanished on a data refresh
      const { sec, course } = hit;
      out.push({
        item_id: rec.item_id, status: "planned",
        units: rec.units, grade_option: rec.grade_option, position: null,
        course_id: course.id, subject_code: course.subject_code,
        course_num: course.course_num, title: course.title,
        section_pk: sec.id, group_code: sec.group_code,
        section_code: sec.section_code, section_id: sec.section_id,
        meetings: groupMeetings(course, sec.group_code, sec.id),
      });
    }
    out.sort((a, b) => a.subject_code.localeCompare(b.subject_code)
      || String(a.course_num).localeCompare(String(b.course_num)));
    return out;
  }

  /* -------------------------------------------------- search (mirrors app.py) */
  function numClause(numText, courseNum) {
    const num = String(numText).toUpperCase();
    const cn = String(courseNum).toUpperCase();
    if (/^\d+$/.test(num)) return cn === num || new RegExp("^" + num + "[A-Z]").test(cn);
    return cn === num;
  }

  function applySimpleQ(qtext, c) {
    const toks = qtext.trim().split(/\s+/).filter(Boolean);
    if (!toks.length) return true;
    const numlike = t => /^\d+[A-Za-z]{0,2}$/.test(t);
    const subj = c.subject_code.toUpperCase();
    const title = c.title.toLowerCase();
    if (toks.length === 1) {
      const t = toks[0];
      if (DATA.subjSet.has(t.toUpperCase())) return subj === t.toUpperCase();
      if (numlike(t)) return numClause(t, c.course_num);
      return title.includes(t.toLowerCase());
    }
    if (toks.length === 2 && DATA.subjSet.has(toks[0].toUpperCase()) && numlike(toks[1])) {
      return subj === toks[0].toUpperCase() && numClause(toks[1], c.course_num);
    }
    if (numlike(toks[toks.length - 1])) {
      if (!numClause(toks[toks.length - 1], c.course_num)) return false;
      return toks.slice(0, -1).every(w => title.includes(w.toLowerCase()));
    }
    return title.includes(qtext.toLowerCase());
  }

  function search(params) {
    const q = (params.get("q") || "").trim();
    const subjects = (params.get("subjects") || "").split(",").filter(Boolean)
      .map(s => s.toUpperCase());
    const courseno = (params.get("courseno") || "").trim().toUpperCase();
    const title = (params.get("title") || "").trim().toLowerCase();
    const instructor = (params.get("instructor") || "").trim().toLowerCase();
    const sectionid = (params.get("sectionid") || "").trim();
    const openOnly = params.get("hidefull") === "1" || params.get("onlyopen") === "1";

    let list = DATA.courses.filter(c => {
      if (q && !applySimpleQ(q, c)) return false;
      if (subjects.length && !subjects.includes(c.subject_code.toUpperCase())) return false;
      if (courseno && c.course_num.toUpperCase() !== courseno) return false;
      if (title && !c.title.toLowerCase().includes(title)) return false;
      if (sectionid && !c.sections.some(s => s.section_id === sectionid)) return false;
      if (instructor && !c.sections.some(s =>
        (s.instructor || "").toLowerCase().includes(instructor))) return false;
      return true;
    });

    return list.map(c => {
      let sections = c.sections;
      if (openOnly) {
        const openGroups = new Set(sections
          .filter(s => s.enrollable && (s.seats_avail || 0) > 0)
          .map(s => s.group_code));
        sections = sections.filter(s => openGroups.has(s.group_code));
      }
      return { ...c, sections };
    }).filter(c => c.sections.length);
  }

  /* -------------------------------------------------- route table */
  function jsonResp(obj, status) {
    return new Response(JSON.stringify(obj),
      { status: status || 200, headers: { "Content-Type": "application/json" } });
  }

  async function route(url, opts) {
    await loadData();
    const u = new URL(url, location.origin);
    const path = u.pathname.replace(/.*(\/api\/)/, "/api/");
    const method = (opts && opts.method) || "GET";
    const body = opts && opts.body ? JSON.parse(opts.body) : {};

    if (path === "/api/terms") return jsonResp(DATA.terms);
    if (path === "/api/subjects") return jsonResp(DATA.subjects);
    if (path === "/api/appointment") {
      return jsonResp({ term: "FA26",
        first_pass: { start: "Planning tool — no appointment needed", end: "Plan any time" },
        second_pass: { start: "Planning tool — no appointment needed", end: "Plan any time" } });
    }
    if (path === "/api/search") return jsonResp(search(u.searchParams));
    if (path === "/api/schedule") return jsonResp(scheduleItems());

    if (path === "/api/schedule/add" && method === "POST") {
      const hit = DATA.bySection.get(body.section_pk);
      if (!hit || !hit.sec.enrollable || hit.sec.cancelled)
        return jsonResp({ error: "Invalid section." }, 400);
      const s = loadSched();
      if (s.items.some(it => it.section_pk === body.section_pk)) {
        const c = hit.course;
        return jsonResp({ error: c.subject_code + " " + c.course_num
          + " section is already in your plan." }, 409);
      }
      s.items.push({ item_id: s.seq++, section_pk: body.section_pk,
        units: body.units || "4", grade_option: body.grade_option || "L",
        status: "planned" });
      saveSched(s);
      // conflict flag (best-effort) so the UI can warn, like the server did
      const conflict = hasConflict(hit.course, hit.sec, null);
      return jsonResp(conflict ? { ok: true, conflict: true } : { ok: true });
    }

    if (path === "/api/schedule/drop" && method === "POST") {
      const s = loadSched();
      s.items = s.items.filter(it => it.item_id !== body.item_id);
      saveSched(s);
      return jsonResp({ ok: true });
    }

    if (path === "/api/schedule/change" && method === "POST") {
      const s = loadSched();
      const it = s.items.find(x => x.item_id === body.item_id);
      if (!it) return jsonResp({ error: "Invalid schedule item." }, 400);
      let out = { ok: true };
      if (body.section_pk != null && body.section_pk !== it.section_pk) {
        const hit = DATA.bySection.get(body.section_pk);
        const cur = DATA.bySection.get(it.section_pk);
        if (!hit || !hit.sec.enrollable || hit.sec.cancelled
            || !cur || hit.course.id !== cur.course.id)
          return jsonResp({ error: "Invalid section." }, 400);
        if (s.items.some(x => x !== it && x.section_pk === body.section_pk))
          return jsonResp({ error: hit.course.subject_code + " "
            + hit.course.course_num + " section is already in your plan." }, 409);
        if (hasConflict(hit.course, hit.sec, it.item_id)) out.conflict = true;
        it.section_pk = body.section_pk;
      }
      if (body.units != null) it.units = body.units;
      if (body.grade_option != null) it.grade_option = body.grade_option;
      saveSched(s);
      return jsonResp(out);
    }

    return jsonResp({ error: "Not found." }, 404);
  }

  /* time-conflict check across the current schedule (weekly meetings only) */
  function toMin(t) {
    const m = /^(\d{1,2}):(\d{2})\s*([ap])m?$/i.exec(String(t || "").trim());
    if (!m) return null;
    let h = (+m[1]) % 12; if (m[3].toLowerCase() === "p") h += 12;
    return h * 60 + (+m[2]);
  }
  function daysOf(d) {
    const toks = []; const s = String(d || ""); let i = 0;
    const T = ["Su", "Sa", "Th", "Tu", "M", "W", "F"];
    while (i < s.length) { let hit = false;
      for (const t of T) if (s.substr(i, t.length).toLowerCase() === t.toLowerCase()) {
        toks.push(t); i += t.length; hit = true; break; }
      if (!hit) i++; }
    return toks;
  }
  function overlap(a, b) {
    if (!a.days || !b.days) return false;
    const da = daysOf(a.days), db = new Set(daysOf(b.days));
    if (!da.some(d => db.has(d))) return false;
    const a1 = toMin(a.time_start), a2 = toMin(a.time_end);
    const b1 = toMin(b.time_start), b2 = toMin(b.time_end);
    if ([a1, a2, b1, b2].some(x => x == null)) return false;
    return a1 < b2 && b1 < a2;
  }
  function hasConflict(course, sec, excludeItemId) {
    const mine = groupMeetings(course, sec.group_code, sec.id).filter(m => m.meeting_type !== "FI");
    for (const it of scheduleItems()) {
      if (excludeItemId != null && it.item_id === excludeItemId) continue;
      for (const om of it.meetings.filter(m => m.meeting_type !== "FI"))
        for (const m of mine) if (overlap(m, om)) return true;
    }
    return false;
  }

  /* -------------------------------------------------- fetch override */
  const realFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || "";
    if (/\/api\//.test(url)) return route(url, init || (typeof input === "object" ? input : {}));
    return realFetch(input, init);
  };
})();
