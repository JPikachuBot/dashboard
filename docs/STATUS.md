# STATUS — FiDi Transit Dashboard

Last updated: 2026-02-07

## Current State
- ✅ Session 1A: MTA stop_id resolver complete
- ✅ Session 1B: MTA realtime fetcher complete (using api-endpoint.mta.info)
- ✅ Session 2: Citi Bike fetcher complete (4 stations configured)
- ✅ Session 3A: Flask API + cache + health + scheduler complete
- ✅ Session 4A: Static HTML/CSS dashboard served via Flask complete
- ✅ Session 4B: Live JS polling + DOM updates complete

## Running Prototype (Mac mini)
```bash
cd ~/Projects/dashboard
source venv/bin/activate
git checkout milestone-4b-javascript
python backend/app.py
# Open: http://127.0.0.1:5000
```

## Open Work (next)
### Milestone 4C — UX / Information Architecture fixes (from live prototype feedback)
1. **Split Wall St into two distinct groups**
   - Wall St (4/5) should be its own group
   - Wall St (2/3) should be its own group
   - Root cause: frontend grouping currently uses `arrival.station` only; needs to group by configured stop/station block (e.g., by stop_id or a config key).

2. **Show direction/destination prominently**
   - Each station block should include a clear label like:
     - "Uptown → Van Cortlandt Park" (1)
     - "Uptown → Harlem-148" (2/3) or appropriate
     - "Uptown → Eastchester-Dyre / Nereid" (4/5) or similar
     - "J → Jamaica Center" (J)
   - Goal: at-a-glance confidence about what you’re looking at.

3. **Show next train in each direction (where relevant)**
   - For 4/5 and 2/3: show two columns/rows: Uptown + Downtown, each with next 2 arrivals.
   - J at Broad St: one direction is fine (terminus).
   - Implementation likely requires adding direction-aware station definitions in config + returning arrivals tagged by direction.

### Future Enhancement (not implementing now)
- **Track a specific train through the system** (e.g., girlfriend commute monitoring)
  - Idea: identify a unique trip/train from GTFS-RT (trip_id + route_id) at one station, then predict/track its subsequent stops (e.g., Fulton → Wall St).
  - Feasibility: likely possible with GTFS-RT trip updates (same trip_id appears at multiple stops), but needs careful handling of service changes and direction.

## Next Major Milestone
- Session 5: manual commute testing (multi-day)
- Session 6A: Raspberry Pi deployment scripts
