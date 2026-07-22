# Progress Log

## 2026-07-21 — Manual "Add Event" on the schedule
- New **Add Event** link in the schedule tab bar (returns the classic-WebReg chrome link removed in feedback round 1 — now as a real feature): add any weekly block (work, clubs, gym) with name, days, start/end (15-min ticks, 7am–10pm), optional location.
- Events are full citizens of the schedule: gold blocks in Calendar, own rows in List (status "Event"), counted by the conflict engine (banner + red borders + the same warn-then-allow confirm flow as planning a class), Remove/Change buttons everywhere classes have them.
- Implemented 100% client-side in `webreg.js` (localStorage `webreg_fa26_events_v1`, negative ids so they never collide with section pks) — zero backend changes, so Flask dev and the static GitHub Pages build behave identically. Events are stored **per named schedule** and follow it through copy/rename/delete (migration hooks in `onSchedNameChange`).
- Verified: 12-step Playwright E2E (validation, conflict warn, list/calendar render, persistence across reload, edit, remove) green on both Flask :5070 and the static build, plus a 6-step schedule-migration suite; screenshots at 1336/1440/2560 (`scratchpad ev_*.png` during dev).
- Wrote `docs/DISTRIBUTION.md`: full channel-by-channel plan (Reddit follow-up + mod sidebar ask, class-year Discords, YikYak timing, org emails — CSES/ACM/TESC/AS, Guardian + Triton media pitches, advisor outreach, faculty of mega-courses), email templates, enrollment-window timing calendar, analytics-before-outreach step, and the caution to keep Registrar/ITS out of the loop while data comes from scraping. Launch post ("I brought WebReg Back!!!") sits at ~376 upvotes but is archived — follow-up post is the top action.

## 2026-07-21 — Integration pass (all builders merged, E2E green)
- Seeded `data/webreg.db` (DEMO term = real SP15 CSE data, 4 courses / 39 sections; FA26 placeholder awaits TSS import).
- Fixed 5 integration bugs: default port 5060→**5070** (browsers block 5060/SIP as unsafe), `/api/appointment` response shape, final-exam dates lost between scraper format and UI (seed.py now normalizes FI rows into `days`), waitlist position display (queue length vs your position), DI-before-LE row ordering in results/confirm.
- Verified every API endpoint incl. error paths via curl; 19-step headless-Playwright E2E all passing (enroll → list/calendar → conflict banner + red blocks → waitlist → change → drop → finals → advanced search → term switch → appointment).
- Screenshots of all 5 views at 1336/1600/2560 in `docs/research/verify/final_*.png`, no horizontal scroll at any width. Full detail: `docs/research/INTEGRATION_REPORT.md`.

## 2026-07-21 — FA26 LIVE (real data landed) 🎉
- **Cracked the TSS data source.** The new system is SAP; its "Schedule of Classes" Fiori app is served by OData v4 service `yucsd_con_module_sb/…/yucsd_con_module_servicedef/0001`. The crashy TSS search UI is bypassed entirely — with Sahir's captured session I query the backend directly.
- Key entity sets: `YUCSD_CON_MODULE` (course list, defaults to current term = FA26), `YUCSD_CON_EVENTS` (sections: teaching method, instructor, seats/limit/waitlist, human `Sched` string with days/times/room + Final Examination line), `YUCSD_CON_MODULE_SCHED` (structured meeting times). Term keys: `Peryr=2026, Perid=2`.
- Dumped the full FA26 term to `data/tss_fa26/` (git-ignored): **1,768 courses, 8,431 events, 7,408 meetings, 7,107 instructors**.
- `tss/import_fa26.py` maps it into WebReg's format: courses → lecture groups (A/B/C…) → discussion rows (A01..) + lab rows (A50..) + final-exam FI rows, real rooms/instructors/seats. → `data/parsed/FA26/<DEPT>.json` (153 subjects, committed) and FA26 set as default term.
- Seeded: **FA26 = 1,766 courses / 8,061 rows**, FA25 = 570/3,778 (legacy scrape), DEMO. Verified live at http://localhost:5070: CSE 100 shows Paul Cao, Galbraith Hall 242, 100 seats, 12/09/2026 final.
- Data-source recipe for re-runs: `tss/connect.py` (SSO capture) → session in `tss/state.json` → the dump+`import_fa26.py`+`seed.py`. Note `tss/import_tss.py` was the generic first-pass importer; `import_fa26.py` is the working one built against the real service.

## 2026-07-21 — Project start (ultracode build)
- Recon: legacy Schedule of Classes still live (browser UA required; terms end at SU26/S326 — **FA26 exists only in TSS**). Server intermittently 500s "Max Sessions Exceeded" (enrollment-season load) → scraper needs retry/backoff.
- Scaffold: Flask app (`app.py`, port 5070 — moved off 5060 during integration: Chrome/Firefox block 5060 as an unsafe SIP port), SQLite schema (`schema.sql`), repo `SahirSSharma/webreg-revival` (private) created and pushed.
- Research workflow launched: WebReg UI spec from real screenshots, SOC HTML format, TSS recon, feature inventory → `docs/research/`.

### Data-quality sweep (FA26)
1,766 courses · 153 subjects · 8,061 section rows · 5,888 enrollable rows with seat counts · 1,216 finals. ~2,422 rows have no meeting day/time — verified these are legitimately-TBA sections (grad tutorials, independent study, research), exactly as WebReg displays them.

## 2026-07-21 — Feedback round 1 (Feedback (1).pdf)
All 8 items implemented:
1. Removed the fake MY TRITONLINK nav tab strip (Current Students / Advising & Grades / …).
2. Term selector shows **only Fall 2026** (client filters `/api/terms` to FA26).
3. Removed the external-link ↗ glyphs next to Catalog / Prerequisites / Resources / Evaluations (and everywhere else) — `.popout` now `display:none`.
4. **Bug fixed:** calendar-block Remove/Change buttons were cut off — raised min block height to 92px and blocks expand on hover (`height:auto`, overflow visible) so buttons are always reachable.
5. Removed the email ✉ glyph next to instructor names.
6. **Can now plan multiple of the same class** (the key scheduling feature): dropped the "already enrolled" duplicate-course block and the section UNIQUE constraint; any course/section can be planned repeatedly to compare options.
7. Removed the Enroll/Waitlist actions everywhere — planning-only. Results action is a single **Plan**; schedule rows/blocks use Remove + Change; status is always "Planned"; wording updated.
8. Removed the Add Event button.
DB rebuilt (schema change), verified live at :5070 (screenshots in docs/research/verify/fb_*.png).

## 2026-07-21 — Feedback: planned-state button
Once a section is planned it can't be planned again — its Plan button turns into a dark, non-interactive "Planned" chip (`.planned-chip`, #0A4A65). Backend rejects a duplicate of the same section (409); the results grid re-renders on any schedule change so Plan↔Planned stays in sync (removing the class reverts it to Plan). Different sections of the same course can still be planned to compare.

## 2026-07-21 — Distribution: static site on GitHub Pages 🚀
**LIVE: https://sahirssharma.github.io/WebReg-Course-Planner/** — shareable link, nothing to install.
- Converted to a browser-only build under `site/`: `scripts/export_static.py` bakes the FA26 catalog to `site/data/catalog.json` (2.8 MB), and `site/js/localdb.js` overrides `window.fetch` for `/api/*` so the existing `webreg.js` runs unchanged — client-side search + each visitor's schedule in their own browser (localStorage, key `webreg_fa26_schedule_v1`). No server, no shared-schedule clobbering.
- Deployed via a `gh-pages` branch (root); repo made public (Pages free tier). Repo canonical name is now **WebReg-Course-Planner**.
- Redeploy after a data/UI change: `python3 scripts/export_static.py` → copy `static/*` into `site/` if the app JS/CSS changed → push `site/` contents to the `gh-pages` branch.
- Caveat: seats/waitlists are a snapshot (baked at export). Refresh = re-run the TSS capture + import + export.
