# 🚇 Inbound Train Tracker — Feature Spec for FiDi Dash

**Feature Name:** Inbound 4/5 Train Tracker ("Pickup Mode")
**Priority:** v1.1 — builds on existing Milestone 1 MTA backend work
**Context:** Read `DASHBOARD_PLAN.md` first for full project architecture and conventions.

---

## Purpose

The user's girlfriend commutes home on the **4 or 5 train**, boarding at either **Grand Central–42nd St** or **14th St–Union Square**. When she texts that she's on the subway, the user needs to see all southbound 4/5 trains currently between **59th St and Brooklyn Bridge** with their predicted arrival times at **Wall St** and **Fulton St**, so he knows when to leave 15 Broad St to meet her.

---

## What to Build

### New Backend: Inbound Trip Tracker

Add a new module/function to the existing MTA fetcher infrastructure that:

1. **Reads the same GTFS-RT feed** already being polled (`gtfs-1234567`). No new feed needed.

2. **Scans all active 4 and 5 train trips** heading southbound (direction = South / direction_id that corresponds to downtown-bound service).

3. **Filters to trips that have upcoming stop_time_updates at stations in the tracking window.** The 4/5 is an **express** line — it does NOT stop at 51st, 28th, 23rd, or Astor Place. The tracking window is the following stations only, ordered north to south:

   | Station Name | Approximate GTFS Stop ID (Southbound) |
   |---|---|
   | 59th St | `631S` |
   | Grand Central–42nd St | `629S` |
   | 14th St–Union Square | `626S` |
   | Brooklyn Bridge–City Hall | `624S` |

   **Important:** These stop IDs are approximate and must be verified against the MTA's static GTFS `stops.txt` file. The `S` suffix indicates southbound platform. The `nyct-gtfs` library may use a different ID format — confirm during implementation. The developer should resolve and hardcode (or put in config) the correct stop IDs for these 4 stations.

4. **For each matching trip, extract:**
   - `trip_id` — unique identifier for this specific train run
   - `route_id` — "4" or "5"
   - `current_position` — the *last station the train has departed* or the *next station it will arrive at*, derived from the stop_time_updates. Essentially: what's the southernmost station that has a past timestamp, or the northernmost station with a future timestamp. Present this as a human-readable station name (e.g., "Approaching 14th St" or "At 23rd St").
   - `wall_st_eta_minutes` — predicted minutes until arrival at Wall St (southbound platform). This is the stop_time_update arrival time for the Wall St stop on this trip, minus current time, converted to minutes. Round down to nearest integer.
   - `fulton_st_eta_minutes` — same calculation for Fulton St stop.
   - If a trip does not have a stop_time_update for Wall St or Fulton (meaning it may not stop there — e.g., an express skipping it), **exclude it**.

5. **Sort results by `wall_st_eta_minutes` ascending** (soonest arrival first).

6. **Cap at 5 trains.** More than that is noise.

### New API Endpoint

```
GET /api/inbound
```

**Response schema:**

```json
{
  "trains": [
    {
      "trip_id": "string",
      "route_id": "4",
      "current_position": "Approaching 14th St",
      "wall_st_eta": 6,
      "fulton_st_eta": 5,
      "leave_by": 3
    }
  ],
  "last_updated": "2026-02-10T08:15:30Z",
  "tracking_window": "59th St → Brooklyn Bridge"
}
```

**`leave_by` calculation:** `wall_st_eta - 2` (it's a 2-minute walk from 15 Broad to Wall St station). Floor at 0. This is the number the user actually cares about — "leave in X minutes."

### New Frontend Panel

Add a new section to the dashboard below the existing subway arrivals (or as a toggleable panel — developer's discretion on layout).

**Header:** `INBOUND 4/5` (or `PICKUP TRACKER`)

**For each train, display one row:**

```
④  Approaching 14th St     Wall 6 min  │  Leave in 3 min
⑤  At 42nd St              Wall 12 min │  Leave in 10 min
④  Departing 59th St       Wall 18 min │  Leave in 16 min
```

**Design rules:**
- Use the existing MTA color scheme: **4 = green circle, 5 = green circle** (they share the Lexington Ave color).
- The `leave_by` value is the most important number. Make it the largest/most prominent element in each row. Use the same urgency color coding as existing arrivals: green (≥5 min), yellow (2–4 min), red (≤1 min or 0).
- `current_position` gives the user a mental map of where the train is. Keep it concise.
- When no trains are in the window, display: `No inbound 4/5 trains between 59th and Brooklyn Bridge`
- This section uses the same staleness indicator as the rest of the subway data (it comes from the same feed).

### Configuration

Add to `config.yaml`:

```yaml
inbound_tracker:
  enabled: true
  label: "INBOUND 4/5"
  routes: ["4", "5"]
  direction: "S"
  tracking_window:
    north_boundary: "59th St"        # Stop ID resolved at startup
    south_boundary: "Brooklyn Bridge" # Stop ID resolved at startup
  destination_stations:
    - name: "Wall St"
      walk_time_minutes: 2           # From 15 Broad St
    - name: "Fulton St"
      walk_time_minutes: 4           # From 15 Broad St
  max_trains: 5
```

---

## What NOT to Build

- **No input mechanism.** This is not Approach 1 (pin a specific train). This is purely a passive display of all inbound trains in the window. No buttons, no text parsing, no phone integration.
- **No new feeds.** The `gtfs-1234567` feed already contains all 4/5 data.
- **No trip persistence.** Don't store or remember trip IDs across refreshes. Each poll is a fresh snapshot.
- **No alerts or notifications.** This is a glanceable display, not a push notification system.

---

## Acceptance Criteria

1. When a southbound 4 or 5 train is between 59th St and Brooklyn Bridge, it appears in the inbound tracker panel with correct position and ETA.
2. ETAs match the MTA app's predicted arrivals within ±1 minute.
3. `leave_by` = `wall_st_eta - 2`, floored at 0.
4. Trains are sorted soonest-first.
5. The panel auto-refreshes with the same 30-second backend poll cycle — no extra fetching needed.
6. When no trains are in the window (late night, service disruption), the panel shows an appropriate empty state.
7. The feature can be disabled via `config.yaml` by setting `enabled: false`.

---

## Implementation Notes

- This feature **reuses the existing MTA feed polling**. The `gtfs-1234567` feed is already being fetched every 30 seconds for the main subway arrivals panel. The inbound tracker just processes the same feed data differently — scanning for trips on routes 4/5 heading south, filtering to the tracking window, and extracting position + downstream ETAs.
- The `nyct-gtfs` library provides trip-level access to stop_time_updates, which is exactly what's needed to get per-stop arrival predictions for a given trip.
- The developer should verify stop IDs from `stops.txt` before hardcoding. Run `grep "Wall St" stops.txt` etc. to find the exact IDs with directional suffixes.
