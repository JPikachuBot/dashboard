# Milestone 4D — Directional Station Layout + Citi Bike Walk-Time Ordering

Date: 2026-02-07

## Decision: 4D vs edits to 4C
**Recommend: make this Milestone 4D.**
- 4C is already merged to `main` and represents a coherent baseline.
- 4D is a UX/layout refactor + a few behavior changes (row-capping, abbreviations, stable Citi Bike ordering) and should be easy to review/roll back independently.

---

## Constraints / ops notes
- **Leave port 5050 open** (do not bind anything new to 5050).
- **Do not touch port 5000** (it’s occupied by macOS ControlCenter; we’re not changing that).

---

## Scope

### A) Subway UI: 3-column station block (Uptown | Station | Downtown)
For each station block:
- Single header row: `Uptown | <route pills + station name> | Downtown`
- Rows below (cap **2** per direction), row-aligned with blanks:
  - Left side: `<ETA> | <train + destination>`
  - Thick divider in the middle
  - Right side: `<train + destination> | <ETA>`

Acceptance criteria:
- Minutes appear on the *outside* edges.
- Strong visual divider between uptown/downtown.
- Capped to 2 rows per direction; blanks used to preserve alignment.


### B) Destination shortening
- Implement curated abbreviation map for long/ambiguous destinations.
- Apply before rendering text (so layout is stable).

Acceptance criteria:
- No ugly truncation for common long destinations.
- Abbreviations are consistent across the UI.


### C) Bug fix: station header route pills completeness
- Ensure station header shows all expected route pills (e.g., `4 5 Wall St`, not just `4`).

Acceptance criteria:
- Route pills rendered are consistent with configured routes/station mapping.


### D) Citi Bike: walk time + stable distance ordering
- Use a fixed “home” location = **15 Broad St** (store lat/lon in config).
- Add header format:
  - `<Station Name> — 5 min (0.3 mi) away`
- Sort Citi Bike stations once by computed distance (closest→farthest) and **freeze order** until explicitly asked to re-sort.

Implementation approach (v1, no external APIs):
- Compute straight-line (Haversine) distance.
- Convert to walk-time estimate (e.g., 1.4 m/s).
- Persist the computed ordering (and/or distances) in a local cache file so live availability changes don’t reorder the list.

Acceptance criteria:
- Walk time appears in the header line.
- Ordering remains stable across refreshes.
- E-bike lightning + status bar behavior remains unchanged.

---

## Files likely to change
- `frontend/index.html`
- `frontend/style.css`
- `frontend/app.js`
- `backend/app.py` (only if API needs to expose direction-grouped arrivals or extra station metadata)
- `backend/fetchers/mta.py` (if direction tagging/route pills source needs adjustment)
- `backend/fetchers/citibike.py` (if we compute/store walk distances server-side)
- `config.yaml` (add home lat/lon; optional abbreviations config)

---

## Suggested implementation order
1) Frontend layout prototype for one station block (static HTML/CSS).
2) Wire dynamic data → direction arrays (uptown[], downtown[]) and row-align + cap to 2.
3) Add divider + spacing + typography tweaks.
4) Add abbreviation map (start small, expand).
5) Fix route pill completeness.
6) Citi Bike: compute distance + stable ordering + header format.

---

## Open questions (only if needed)
- Do we compute walk distance client-side (JS) or server-side (Python)?
  - Server-side is easier to keep ordering stable and consistent.
- Should abbreviations live in code or `config.yaml`?

---

## Related docs
- UX diagram/spec: `docs/ux-proposal-directional-stations-3col.md`
