# Milestone 4E — Inbound 4/5 Pickup Tracker

Date: 2026-02-10

## Summary
- Added inbound 4/5 tracker backend and `/api/inbound` endpoint using the existing MTA GTFS-RT feed.
- Frontend now renders an “INBOUND 4/5” panel after Citi Bike and refreshes on the same cadence.
- Config updated with `inbound_tracker` (name-only station config + destinations + max trains).
- Fixed a bug where in-flight trains (already past start) were dropped when the start stop_time_update was missing.
- Made the in-flight classifier more robust using both last/next stop parent-station ordering.

---

## Data Model / API / UI

### API: `GET /api/inbound`
Response shape:
- `trains[]`: `{ trip_id, route_id, current_position, wall_st_eta, fulton_st_eta, leave_by }`
- `last_updated`: ISO UTC timestamp
- `tracking_window`: `"<north> → <south>"`

### UI
- New “INBOUND 4/5” panel placed below Citi Bike.
- Rows show line badge, current position, Wall/Fulton ETAs, and a large “Leave in X min” emphasis.
- Empty state: “No inbound 4/5 trains between 59th St → Brooklyn Bridge.”
- Inbound rows are grouped into two sections: “Next @ 42” (approaching_start) and “In flight (42 → Wall/Fulton)” (inflight). Empty state only appears if both groups are empty.


---

## Implementation Notes
- **Station-name → stop-id resolution** is done at runtime using `data/mta-static/stops.txt`.
- Names are normalized (dash/ordinal handling + prefix matching) so config values like “Grand Central–42nd St” and “Brooklyn Bridge” resolve correctly.
- Ambiguous station names (Wall St, Fulton St, Grand Central, Union Sq) are disambiguated via preferred parent station IDs in code to ensure the 4/5 platform is selected.
- The inbound tracker requires Wall/Fulton ETAs and end-station stop_time_updates. Start-station stop_time_updates are optional; if missing, we infer “in-flight” using the next stop’s parent station between start/end parents. Sorting is by Wall St ETA, capped to 5.
- The inflight heuristic now checks both the last stop <= now and the next stop >= now against start/end parent stations to handle sparse or inconsistent stop_time_updates.

### UI/Implementation Notes
- `end_station` is now Wall St so the window includes the Fulton → Wall segment.
- Trains that have already passed Fulton omit Fulton ETA/leave-by, but still show Wall.
- Verify by watching `/api/inbound` as a train passes Fulton; `fulton_st_eta`/`leave_by_fulton` should drop to `null` while Wall remains.

### Bug / Root Cause / Fix
- **Bug:** Trains that had already passed the start station could disappear from the inbound list.
- **Root cause:** The filter required a start-station stop_time_update, which can be omitted once a train passes that stop.
- **Fix:** Keep Wall/Fulton + end-station requirements, but allow missing start_time. Classify in-flight if either the last stop or next stop parent station falls between the start/end parents (with debug logging); also use the next stop as the “approaching start” time when it equals the start parent.
- **Bug:** Trains north of Grand Central (e.g., 86 St) could be misclassified as “inflight.”
- **Root cause:** Parent-station “between” check used numeric min/max, but Lex parent IDs are not monotonic southbound (e.g., 631 → 640 → 419 → 418), so unrelated parents could appear “between.”
- **Fix:** Added an ordered Lex corridor parent list (42 → Fulton) and index-based corridor membership checks that respect direction; fallback remains numeric for non-corridor parents. Strictly require corridor membership when start/end are in the corridor, and emit `INBOUND_DEBUG=1` logs if inflight classification involves north-of-42 stops (86 St/138 St) or parents outside the corridor index.

### Verification Steps
1. Start the server: `PORT=5050 INBOUND_DEBUG=1 venv/bin/python backend/app.py`
2. Query `GET /api/inbound` using python urllib: `python3 - <<'PY'\nimport json,urllib.request;print(json.load(urllib.request.urlopen("http://127.0.0.1:5050/api/inbound")))\nPY`
3. Confirm no trains with next stop names containing “86 St” or “138 St” are classified as `window_bucket: "inflight"`.
4. If `INBOUND_DEBUG=1`, confirm debug logs appear only for inflight trains that match the north-of-42 check or have parents outside the corridor index.

---

## Risks / Open Questions
- Stop-id disambiguation depends on preferred parent-station mappings; if MTA changes static IDs, the resolver may need updates.
- Current position uses the next scheduled stop; if stop_time_updates are sparse, “Approaching” may feel less precise.
- We currently treat the tracker as enabled whenever config is present; if we want the UI hidden when disabled, we should add a frontend toggle flag.

---

## Files Changed
- `backend/app.py`
- `backend/fetchers/mta.py`
- `backend/fetchers/inbound.py`
- `frontend/index.html`
- `frontend/app.js`
- `frontend/style.css`
- `config.yaml`
- `files/session_4e_inbound_tracker.md`
