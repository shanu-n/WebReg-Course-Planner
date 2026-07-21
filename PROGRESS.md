# Progress Log

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
