# WebReg Revival — Design

## Goal
Pixel-faithful rebuild of classic UCSD WebReg as a localhost **planning** tool (no live registration), backed by real UCSD course data. Users: Sahir first, then friends fed up with TSS.

## Architecture
- **Flask + SQLite** (`app.py` + `data/webreg.db`, port 5060). No build step, no framework — vanilla JS/CSS replicating WebReg's classic look.
- **Data layer**: everything imported into SQLite by `seed.py`; the app never calls UCSD live.
  - `scraper/soc_scraper.py` — legacy public Schedule of Classes (terms ≤ SU26). Chrome UA mandatory; patient retry/backoff around "Max Sessions Exceeded" 500s; raw HTML cached in `data/samples/` so parsing is re-runnable offline.
  - `tss/connect.py` — headed Playwright window → Sahir does SSO+Duo → storage_state saved to `tss/state.json` (git-ignored) → sniff JSON XHRs from TSS class search → dump `data/tss_raw/` → import FA26.
- **Schedule model**: WebReg semantics, local-only. `enrolled | waitlisted | planned` statuses; units + grading option per item; one "My Schedule" per term.

## Pages
1. `/` — term selector ("Go") → main app, single page, two tabs like WebReg: **My Schedule** (calendar/list/finals views) and **Enroll (Add Classes)** (search → results grid → Enroll/Plan dialogs).

## Fidelity source of truth
`docs/research/UI_SPEC.md` (built from real screenshots in `docs/research/refs/`) + `docs/research/FEATURES.md`. Where sources conflict, screenshots win.

## Key constraints
- Cookies/PII never committed (`tss/state.json`, `data/` git-ignored).
- Planning-only: every WebReg write-action maps to local DB; wording preserved ("Enroll", confirm dialogs) with a subtle planner banner so nobody thinks it registered them for real.
- Verify UI at 1336 / 1600 / 2560 px widths (Sahir's screen is wide).
