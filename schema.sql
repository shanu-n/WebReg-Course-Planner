-- WebReg Revival — SQLite schema
-- Data model mirrors how the legacy Schedule of Classes presents data:
-- course header rows, then per-meeting section rows grouped into letter groups
-- (A00 lecture + A01/A02 discussions + one final). The enrollable unit is the
-- row WebReg put the button on; everything else in the group tags along.

PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS terms (
  code        TEXT PRIMARY KEY,   -- e.g. FA26, SP26
  name        TEXT NOT NULL,      -- e.g. Fall 2026
  sort_key    INTEGER NOT NULL,   -- descending recency
  source      TEXT NOT NULL DEFAULT 'soc',  -- soc | tss
  is_default  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subjects (
  code TEXT PRIMARY KEY,          -- CSE
  name TEXT NOT NULL              -- Computer Science & Engineering
);

CREATE TABLE IF NOT EXISTS courses (
  id           INTEGER PRIMARY KEY,
  term_code    TEXT NOT NULL REFERENCES terms(code),
  subject_code TEXT NOT NULL,
  course_num   TEXT NOT NULL,     -- "100", "15L", "199"
  title        TEXT NOT NULL,
  units        TEXT NOT NULL,     -- "4" or "2/4 by 2" ranges, kept as display text
  restriction  TEXT DEFAULT '',   -- restriction codes shown by SOC (e.g. "SI")
  UNIQUE(term_code, subject_code, course_num)
);

CREATE TABLE IF NOT EXISTS sections (
  id           INTEGER PRIMARY KEY,
  course_id    INTEGER NOT NULL REFERENCES courses(id),
  section_id   TEXT DEFAULT '',   -- 6-digit WebReg section ID; '' for FI/non-enrollable rows
  group_code   TEXT NOT NULL,     -- letter group: "A", "B" (from A00/A01...)
  meeting_type TEXT NOT NULL,     -- LE DI LA ST SE FI MI TU PR RE ...
  section_code TEXT NOT NULL,     -- A00, A01, B00... ('' for finals: date shown instead)
  days         TEXT DEFAULT '',   -- "MWF", "TuTh"; final rows use date "SA 12/12/2026"
  time_start   TEXT DEFAULT '',   -- "9:30a" display style; '' = TBA
  time_end     TEXT DEFAULT '',
  building     TEXT DEFAULT '',
  room         TEXT DEFAULT '',
  instructor   TEXT DEFAULT '',   -- "Last, First" comma style as SOC prints
  seats_avail  INTEGER,           -- NULL = n/a (FI rows, non-enrollable)
  seats_limit  INTEGER,
  waitlist_ct  INTEGER DEFAULT 0,
  enrollable   INTEGER NOT NULL DEFAULT 0,  -- 1 = this row carries the Enroll/Plan button
  cancelled    INTEGER NOT NULL DEFAULT 0,
  note         TEXT DEFAULT ''    -- nonenrtxt / special notes
);
CREATE INDEX IF NOT EXISTS idx_sections_course ON sections(course_id);

-- User-side: schedules per term. status mirrors WebReg semantics but is planning-only.
CREATE TABLE IF NOT EXISTS schedules (
  id        INTEGER PRIMARY KEY,
  term_code TEXT NOT NULL REFERENCES terms(code),
  name      TEXT NOT NULL DEFAULT 'My Schedule',
  UNIQUE(term_code, name)
);

CREATE TABLE IF NOT EXISTS schedule_items (
  id            INTEGER PRIMARY KEY,
  schedule_id   INTEGER NOT NULL REFERENCES schedules(id),
  course_id     INTEGER NOT NULL REFERENCES courses(id),
  section_pk    INTEGER NOT NULL REFERENCES sections(id), -- the enrollable row chosen
  status        TEXT NOT NULL DEFAULT 'planned',          -- planning-only tool: always 'planned'
  units         TEXT NOT NULL,
  grade_option  TEXT NOT NULL DEFAULT 'L',                -- L | P (P/NP) | S (S/U)
  waitlist_pos  INTEGER,                                  -- legacy column, unused in planning-only mode
  added_at      TEXT NOT NULL DEFAULT (datetime('now'))
  -- no uniqueness: a planner may add the same course/section multiple times
);
