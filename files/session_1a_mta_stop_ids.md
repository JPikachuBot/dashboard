# Session 1A: MTA Stop ID Resolution

## Context
You are working on Milestone 1 of the FiDi Transit Dashboard project. This session focuses on resolving MTA subway stop IDs for 6 stations.

## Files You Need Access To
- `~/Projects/dashboard/config.yaml` (read and write)
- `~/Projects/dashboard/data/mta-static/stops.txt` (read only)

## Background
The MTA's GTFS static data includes a `stops.txt` file that maps station names to unique stop IDs. Each platform (northbound/southbound) has a different stop ID. We need the northbound (or westbound/uptown) platform IDs for our 6 stations.

## Your Task
Write a Python script (`backend/fetchers/resolve_stop_ids.py`) that:

1. **Reads `data/mta-static/stops.txt`** (CSV format with columns: stop_id, stop_name, stop_lat, stop_lon, parent_station)

2. **Finds the correct stop_id for each of these 6 stations:**
   - Wall St (4/5 trains) - Northbound (N) platform
   - Wall St (2/3 trains) - Northbound (N) platform  
   - Broad St (J train) - Westbound (W) platform
   - Rector St (1 train) - Northbound (N) platform
   - Rector St (R/W trains) - Northbound (N) platform
   - Fulton St (A/C trains) - Northbound/Uptown (N) platform

3. **Important notes:**
   - These are separate physical stations that happen to share names
   - Stop IDs typically end with direction suffix: `N` (north), `S` (south)
   - Wall St has TWO different stations: one for 4/5, one for 2/3
   - Rector St also has TWO different stations: one for 1, one for R/W
   - Use `stop_name` and geographic coordinates to disambiguate

4. **Updates `config.yaml`** by replacing all `"TBD"` stop_id values with the resolved IDs

5. **Prints a summary** showing:
   - Station name
   - Lines served
   - Resolved stop_id
   - Latitude/Longitude (for verification)

## Acceptance Criteria
- [ ] Script runs without errors
- [ ] All 6 stop_ids in config.yaml are replaced with real values (no "TBD" remaining)
- [ ] Stop IDs are for the correct direction (northbound/westbound/uptown)
- [ ] Output clearly shows which stop_id corresponds to which station/lines

## Implementation Tips
- CSV parsing: Use Python's `csv` module or `pandas`
- YAML editing: Use `pyyaml` library (already in requirements.txt)
- Direction suffix: Stop IDs typically look like `140N`, `232S`, etc.
- Disambiguation: Use lat/lon coordinates to distinguish between stations with the same name

## Example Output
```
Resolving MTA Stop IDs...

✓ Wall St (4/5) → Stop ID: 140N (40.7076, -74.0119)
✓ Wall St (2/3) → Stop ID: 232N (40.7068, -74.0091)
✓ Broad St (J) → Stop ID: 624W (40.7064, -74.0107)
✓ Rector St (1) → Stop ID: 134N (40.7073, -74.0134)
✓ Rector St (R/W) → Stop ID: R31N (40.7072, -74.0131)
✓ Fulton St (A/C) → Stop ID: A38N (40.7104, -74.0071)

Config file updated: config.yaml
All stop IDs resolved successfully!
```

## Files to Create
- `backend/fetchers/resolve_stop_ids.py` (main script)

## Files to Modify
- `config.yaml` (replace TBD values)

## Testing
After running the script:
```bash
cd ~/Projects/dashboard
source venv/bin/activate
python backend/fetchers/resolve_stop_ids.py

# Verify config.yaml has no "TBD" values
grep -i "tbd" config.yaml  # Should return nothing
```

## Next Session
Once complete, Session 1B will use these stop_ids to fetch real-time train arrivals from MTA's GTFS-RT feeds.
