# 🚇 Inbound Train Tracker — Feature Spec for FiDi Dash (4/5 “Pickup Mode”)

**Feature Name:** Inbound 4/5 Train Tracker ("Pickup Mode")
**Priority:** v1.1 — builds on existing Milestone 1 MTA backend work
**Context:** Read `DASHBOARD_PLAN.md` first for full project architecture and conventions.

---

## Purpose

When Jackson’s girlfriend is on the **4 or 5 train heading downtown**, Jackson needs to quickly understand:

1) **The next 2 trains arriving at Grand Central–42nd St (southbound)**, including where they are right now and how soon they arrive at 42nd.
2) **All trains currently “in-flight” after 42nd St and before Wall St**, including where they are right now and their predicted arrivals at **Fulton St** and **Wall St**.

This allows him to time leaving 15 Broad St to meet her.

---

## What to Build

### A) New Backend Module: Inbound Trip Tracker

Add a module/function to the existing MTA fetcher infrastructure that:

1. **Reads the same GTFS-RT feed** already being polled (`gtfs-1234567`). No new feed needed.

2. **Scans all active 4 and 5 train trips** heading **southbound** (direction_id corresponding to downtown-bound service).

3. **Resolves and uses specific stop IDs** from the static GTFS `stops.txt` (do not guess). Stop IDs below are illustrative only.

#### Stations (north → south order)

We care about these stations (southbound platforms):

- **Grand Central–42nd St** (GCT 42)
- **14th St–Union Square**
- **Brooklyn Bridge–City Hall**
- **Fulton St**
- **Wall St**

**Important ordering note:** **Fulton is north of Wall**, so for a given train when both are still ahead, **ETA(Wall) should be greater than ETA(Fulton)**.

4. **Compute per-trip “where is it now?” (`current_position`)**

Derive a human-readable `current_position` from stop_time_updates, e.g.:
- `Approaching 14th St`
- `At 42nd St`
- `Departed 42nd St`
- `Between 14th St and Brooklyn Bridge`

Keep this concise and stable.

---

### B) Two Output Sections (Required)

#### Section 1: “Next 2 trains arriving at 42nd St”

Goal: show the **next 2** southbound 4/5 trains that will arrive at **Grand Central–42nd St**, and help Jackson understand what they are doing right now.

**Selection rules:**
- Include only trips that have a stop_time_update for **42nd St (southbound)** with an arrival time in the future.
- Sort by `gct_42_eta_minutes` ascending.
- **Cap at 2 trains**.

**Per-train fields:**
- `trip_id`
- `route_id` ("4" or "5")
- `current_position`
- `gct_42_eta_minutes`
- `fulton_eta_minutes` (optional; see “blanking rules”)
- `wall_eta_minutes` (optional; see “blanking rules”)

#### Section 2: “In-flight (post‑42nd → pre‑Wall)”

Goal: show **all trains in-flight after 42nd St and before Wall St**.

**Selection rules (the tracking window):**
- Include only trips that have **already passed/departed 42nd St** (i.e., 42nd St is behind them).
- Include only trips that have **not yet arrived at Wall St** (i.e., Wall St is still ahead of them).

**Sorting/capping:**
- Sort by `wall_eta_minutes` ascending (soonest Wall arrival first).
- Default cap: **max 8 trains** (to keep the panel readable). Make this configurable.

**Per-train fields:**
- `trip_id`
- `route_id`
- `current_position`
- `fulton_eta_minutes` (optional)
- `wall_eta_minutes` (optional)

---

### C) ETA / Blanking Rules (Critical)

We display **Fulton then Wall** (in that order) everywhere.

- If a train **has already passed Fulton** (e.g., it is approaching Wall), then **Fulton ETA must be blank/null**.
- If a train **has already reached Wall**, it should **not appear** in the in-flight section.
- If a trip does not have a stop_time_update for a station that we’re trying to display, treat that ETA as **blank/null**.

---

## API Endpoint

```
GET /api/inbound
```

### Response schema

```json
{
  "next_at_42": [
    {
      "trip_id": "string",
      "route_id": "4",
      "current_position": "Approaching 59th St",
      "gct_42_eta": 3,
      "fulton_eta": 18,
      "wall_eta": 21
    }
  ],
  "in_flight": [
    {
      "trip_id": "string",
      "route_id": "5",
      "current_position": "Between 14th St and Brooklyn Bridge",
      "fulton_eta": 6,
      "wall_eta": 9
    }
  ],
  "last_updated": "2026-02-10T08:15:30Z",
  "tracking_window": {
    "in_flight": "post-42nd St → pre-Wall St",
    "note": "Fulton is north of Wall; Fulton ETA should be shorter than Wall ETA when both are present."
  }
}
```

Notes:
- JSON field names in code can be `snake_case` or `camelCase`, but be consistent across the project. If the rest of the API uses `snake_case`, keep it.

---

## Frontend Panel

Add a new section to the dashboard below the existing subway arrivals.

### Header
- `INBOUND 4/5` (or `PICKUP TRACKER`)

### Subsection 1: “NEXT @ 42ND ST”
Render **2 rows max**, sorted soonest-first.

Suggested row format (exact typography/layout is flexible, but data must be present):

```
④  Approaching 59th St          42nd: 3m   Fulton: 18m   Wall: 21m
⑤  At 42nd St                  42nd: 6m   Fulton: 21m   Wall: 24m
```

### Subsection 2: “IN-FLIGHT (42ND → WALL)”
Render all in-flight rows (cap to max 8) sorted by Wall ETA.

Suggested row format:

```
④  Departed 42nd St             Fulton: 10m  Wall: 13m
⑤  Approaching Brooklyn Bridge  Fulton: 4m   Wall: 7m
④  Approaching Wall St          Fulton: —    Wall: 1m
```

**Blanking requirement:** When Fulton is not applicable (already passed), render it as blank/—.

---

## Configuration

Update `config.yaml`:

```yaml
inbound_tracker:
  enabled: true
  label: "INBOUND 4/5"
  routes: ["4", "5"]
  direction: "S"

  # Stops must be resolved from GTFS stops.txt at startup and stored as IDs
  stops:
    gct_42: "<STOP_ID>"
    union_sq_14: "<STOP_ID>"
    brooklyn_bridge: "<STOP_ID>"
    fulton: "<STOP_ID>"
    wall: "<STOP_ID>"

  next_at_42:
    max_trains: 2

  in_flight:
    max_trains: 8
    window: "post-42nd → pre-wall"

  destination_stations:
    - name: "Fulton St"
      walk_time_minutes: 4
    - name: "Wall St"
      walk_time_minutes: 2
```

---

## What NOT to Build

- No input mechanism (no pinning a specific train).
- No new feeds (reuse `gtfs-1234567`).
- No trip persistence across refreshes.
- No push alerts/notifications.

---

## Acceptance Criteria

1) **Next @ 42nd:** exactly **2** upcoming southbound trains shown (or fewer if fewer exist), with correct `gct_42_eta` and meaningful `current_position`.
2) **In-flight:** shows trains that have passed 42nd and have not yet arrived at Wall; excludes everything else.
3) **Fulton-before-Wall ordering:** when both ETAs are present, **Fulton ETA < Wall ETA** (within normal MTA noise).
4) **Blanking rule:** if the train is approaching Wall / Fulton is already behind it, Fulton is blank/null in API and renders blank/— in UI.
5) Sorting: `next_at_42` by `gct_42_eta`, `in_flight` by `wall_eta`.
6) Auto-refresh uses the same backend poll cycle; no extra fetching.
7) Empty states are clear and non-alarming.

---

## Implementation Notes

- Reuse existing polling/parsing via `nyct-gtfs`.
- Resolve stop IDs from `stops.txt` during implementation and store in config.
- Keep the backend logic deterministic: selection rules should match the acceptance criteria above.
