# Milestone 4C — Subway station blocks + directions + deterministic config

Date: 2026-02-07

## What shipped (summary)
Milestone 4C upgraded the dashboard from a simple arrivals list into a more structured, kiosk-friendly UI with:
- **Station blocks** (group arrivals under a station/line block)
- **Direction support** (incl. "downtown" labeling and per-arrival direction labels)
- **Deterministic rendering config** via `/api/config`
- **Reroute resilience** (don’t hide arrivals when the MTA temporarily reroutes lines)

This milestone is now merged to GitHub `main`.

---

## GitHub / code pointers
- Repo: `~/Projects/dashboard`
- Merged into `main` via merge commit: `d019cf9` ("Merge milestone-4c-rw-note (Milestone 4C)")
- Branch history that comprised 4C (key commits):
  - `e6ee1d7` — add `/api/config` and make `PORT` configurable
  - `38cdd63` — station blocks + downtown direction
  - `b1ce019` — inline direction labels per arrival
  - `90e7e9f` — include station blocks in `/api/config` for deterministic rendering
  - `244ffca` — always render subway blocks; note when N serves Rector R/W
  - `48a3939` — include rerouted lines by filtering only by stop_id

Files primarily changed from 4B → 4C:
- `backend/app.py`
- `backend/fetchers/mta.py`
- `backend/fetchers/resolve_stop_ids.py`
- `config.yaml`
- `frontend/app.js`
- `frontend/index.html`
- `frontend/style.css`

---

## Functional changes (details)

### 1) Station blocks + multi-direction config
- Added structured station-block representation in the MTA fetcher.
- Config now supports station blocks with multiple direction specs (label/destination/stop_id).

### 2) Direction labeling improvements
- Arrivals include:
  - `direction_label`
  - optional `direction_destination`
  - plus metadata tying the arrival back to a station block (`station_block_id`).

### 3) Deterministic frontend rendering
- Added `/api/config` endpoint so the frontend can render station blocks deterministically (rather than relying on whatever arrivals happen to show up first).

### 4) Robustness to MTA reroutes
- Candidate collection intentionally **does not filter by configured line_id** when scanning a stop.
- Instead, it filters by `stop_id` so that if e.g. **N temporarily serves the R/W local**, arrivals still appear.

### 5) UX polishing
- Always render subway blocks (even if empty), so the board layout doesn’t jump around.
- Inline direction labels between the badge and time in the subway rows.

---

## Acceptance criteria that 4C met
- Station blocks render consistently.
- Downtown/uptown labeling shows clearly per arrival.
- Frontend receives station structure via `/api/config`.
- Temporary reroutes don’t cause “missing” trains.

---

## Known follow-ons
- Milestone 4D is planned for a bigger UX refactor: 3-column station blocks (Uptown | Station | Downtown), two-row cap per direction, curated destination abbreviations, and Citi Bike walk-time + frozen ordering.

(See: `files/session_4d_directional_layout_and_walktime.md` and `docs/ux-proposal-directional-stations-3col.md`.)
