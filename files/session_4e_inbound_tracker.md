# Milestone 4E — Inbound 4/5 Pickup Tracker

Date: 2026-02-09

## High-level summary
Inbound 4E adds a “Pickup Mode” panel that shows **southbound 4/5 trains between 59th St and Brooklyn Bridge** and their ETA to **Wall St** and **Fulton St**, plus a “leave in X min” number based on a 2-minute walk from 15 Broad St. It reuses the existing GTFS-RT polling cycle and MTA backend infrastructure, without new feeds, persistence, alerts, or input UI.

---

## Proposed data model + API + UI states

### Data model (backend payload)
- `InboundTrain`
  - `trip_id: str`
  - `route_id: Literal["4","5"]`
  - `current_position: str`
  - `wall_st_eta: int` (minutes, floor)
  - `fulton_st_eta: int` (minutes, floor)
  - `leave_by: int` (minutes, floor at 0; `wall_st_eta - 2`)
- `InboundTrackerResponse`
  - `trains: list[InboundTrain]` (sorted by `wall_st_eta`, max 5)
  - `last_updated: str` (ISO UTC)
  - `tracking_window: str` (e.g., `59th St → Brooklyn Bridge`)

### API endpoints
- `GET /api/inbound`
  - Returns `InboundTrackerResponse` as specified in `docs/INBOUND_TRACKER_SPEC.md`.
- (No new fetch cadence; same 30s poll as existing MTA feed.)

### UI states
- **Normal list** (1–5 trains): each row shows route badge, `current_position`, `Wall X min`, and **Leave in Y min** (largest emphasis, urgency colors).
- **Empty state**: `No inbound 4/5 trains between 59th and Brooklyn Bridge`.
- **Stale data**: reuse existing subway staleness indicator; no new UI logic.

---

## Implementation plan (milestones/steps)
1. **Stop ID resolution**
   - Confirm GTFS stop IDs for `59th St`, `Grand Central`, `14th St–Union Square`, `Brooklyn Bridge`, plus destination stops `Wall St` and `Fulton St` (southbound).
   - Add resolved IDs to config or a small constant map in the MTA fetcher.
2. **Backend: inbound tracker module**
   - Reuse existing GTFS-RT feed data and scan active trips for routes `4`/`5` with southbound `direction_id`.
   - Filter to trips that include stop_time_updates within the tracking window and **include Wall/Fulton ETA**; exclude trips missing either destination.
   - Compute `current_position`, `wall_st_eta`, `fulton_st_eta`, `leave_by`; sort and cap to 5.
3. **API: `/api/inbound`**
   - Add endpoint and response schema; wire to inbound tracker module.
4. **Frontend panel**
   - New section under existing subway block or toggleable panel (dev discretion).
   - Render rows with urgency color rules from existing subway ETAs.
   - Empty state and staleness indicator integration.
5. **Config**
   - Add `inbound_tracker` block in `config.yaml` as per spec; include `enabled` and station names.
6. **Verification**
   - Compare ETAs vs MTA app within ±1 minute.
   - Confirm sorting, cap, and `leave_by` logic.

---

## Risks / edge cases + open questions

### Risks / edge cases
- **Stop ID mismatches** (southbound suffixes or nyct-gtfs ID formatting) could silently drop trains.
- **Trips skipping Wall/Fulton** (express patterns) must be excluded; otherwise ETAs are misleading.
- **Current position derivation** may be ambiguous when stop_time_updates are sparse or delayed.

### Open questions
- Where should stop ID mapping live: `config.yaml` vs hardcoded map in `backend/fetchers/mta.py`?
- Should `current_position` use “Approaching X” vs “At X” based on time deltas or `current_stop_sequence` if available?

---

## Files likely to change
- `backend/fetchers/mta.py`
- `backend/app.py`
- `backend/fetchers/resolve_stop_ids.py` (if adding helpers)
- `config.yaml`
- `frontend/app.js`
- `frontend/index.html`
- `frontend/style.css`
- `docs/INBOUND_TRACKER_SPEC.md` (only if clarifying stop IDs or schema)

---

## Implementation notes
- Inbound tracker resolves stop IDs at runtime by normalizing station names from `config.yaml` against `data/mta-static/stops.txt`, so name-only config stays human-friendly while still matching GTFS stop IDs.
- Inbound trains are computed during the existing subway fetch cycle, reusing the same GTFS-RT feed pull and cache timestamp to avoid extra polling.
- Trip inclusion in the tracking window is based on stop sequence indices between the configured north/south boundary stops, ensuring only trains currently between 59th St and Brooklyn Bridge are shown.
- `/api/inbound` uses the cached fetch timestamp (ISO UTC) and the config-defined tracking window label in its response payload.
