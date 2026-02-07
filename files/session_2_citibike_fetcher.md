# Session 2: Citibike Dock Status Fetcher

## Context
You are working on Milestone 2 of the FiDi Transit Dashboard project. MTA fetcher is complete. This session builds the Citibike dock availability fetcher.

## Files You Need Access To
- `~/Projects/dashboard/config.yaml` (read/write - need to update station_ids)
- `~/Projects/dashboard/backend/fetchers/citibike.py` (create - main deliverable)

## Background
Citibike publishes free, open GBFS (General Bikeshare Feed Specification) JSON endpoints:

**Station Information** (static, rarely changes):
- URL: https://gbfs.citibikenyc.com/gbfs/en/station_information.json
- Contains: station_id, name, lat, lon, capacity
- Use: Resolve station names to station_ids

**Station Status** (live, updates ~60s):
- URL: https://gbfs.citibikenyc.com/gbfs/en/station_status.json
- Contains: num_bikes_available, num_ebikes_available, num_docks_available, is_renting, is_returning, last_reported
- Use: Get real-time dock levels

## Your Task
Create `backend/fetchers/citibike.py` with the following:

### 1. Station ID Resolution (run once, update config)
Write a function: `resolve_station_ids(station_names)`
- Fetches station_information.json
- Searches for stations matching the names from config.yaml
- Finds closest matches by name (fuzzy matching recommended)
- Returns: `{name: station_id}` mapping
- Updates config.yaml with resolved station_ids

**Target stations from config:**
- "Broadway & Exchange Pl" (near 15 Broad St)
- A second station TBD (you'll help identify the closest one)

### 2. Core Function: `fetch_citibike_status(config)`
**Input:** config dict (from parsed config.yaml)  
**Output:** List of station status dictionaries

**Each status dict should contain:**
```python
{
    "station_id": "66db237e-0aca-11e7-82f6-3863bb44ef7c",
    "name": "Broadway & Exchange Pl",
    "bikes_available": 8,           # Regular bikes
    "ebikes_available": 3,          # Electric bikes
    "docks_available": 4,           # Empty docks
    "total_capacity": 15,           # Total docks at this station
    "is_renting": True,             # Station accepting rentals?
    "is_returning": True,           # Station accepting returns?
    "last_reported": 1707234567,    # Unix timestamp of last update
    "percent_full": 73              # (bikes / capacity) * 100
}
```

### 3. Requirements
**Libraries:** Use `requests` (already installed)

**Fetch strategy:**
- Load config.yaml to get configured station_ids
- Fetch station_status.json
- Filter to only your configured stations
- Calculate derived fields (percent_full, total bikes)
- Return list sorted by name

**Error handling:**
- API timeout (10s limit)
- Station offline (is_renting/is_returning = False)
- Invalid station_id (not found in response)
- Network errors
- Malformed JSON

**Edge cases:**
- Station out of service → flag with "OUT OF SERVICE" status
- All docks full → highlight in output
- All bikes taken → highlight in output
- Stale data (last_reported > 5 minutes old) → show warning

### 4. Helper Functions (suggested structure)
```python
def load_config(config_path="config.yaml"):
    """Load and parse config.yaml"""
    pass

def fetch_station_information():
    """Get static station data (for ID resolution)"""
    pass

def fetch_station_status():
    """Get live dock/bike counts"""
    pass

def resolve_station_ids(station_names):
    """Find station_ids for given names, update config.yaml"""
    # Uses fuzzy matching (e.g., "Broadway & Exchange" matches "Broadway & Exchange Pl")
    pass

def calculate_percent_full(bikes, capacity):
    """Calculate percentage fullness"""
    pass
```

### 5. Test Function
Include a `if __name__ == "__main__":` block that:
- First resolves station_ids (if any "TBD" in config)
- Then fetches live status
- Prints results with visual indicators
- Suggests nearby stations if needed

## Example Output (Station ID Resolution)
```bash
$ python backend/fetchers/citibike.py --resolve

Fetching Citibike station information...
Found 2000+ stations in NYC

Searching for: "Broadway & Exchange Pl"
  ✓ Match found: "Broadway & Exchange Pl" (ID: 66db237e-0aca-11e7-82f6-3863bb44ef7c)
    Location: 40.7092, -74.0100
    Capacity: 15 docks

Searching for: "Second Station TBD"
  ⚠ No match found. Nearby stations:
    1. "Broad St & Water St" (0.1 mi away, 19 docks)
    2. "Stone St & Mill Ln" (0.2 mi away, 15 docks)
    3. "Pearl St & Hanover Square" (0.3 mi away, 27 docks)

Which station would you like to use? Enter station name or number [1-3]: 1

  ✓ Selected: "Broad St & Water St" (ID: 66db2676-0aca-11e7-82f6-3863bb44ef7c)

Updated config.yaml with resolved station_ids.
```

## Example Output (Live Status Fetch)
```bash
$ python backend/fetchers/citibike.py

Fetching Citibike dock status...
Loaded 2 stations from config.yaml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BROADWAY & EXCHANGE PL
  ████████████░░░  73% full
  🚲 Regular bikes:  8
  ⚡ E-bikes:        3
  🅿 Empty docks:    4
  Status: ✓ Renting | ✓ Returning
  Updated: 12s ago

BROAD ST & WATER ST
  █████░░░░░░░░░░  32% full
  🚲 Regular bikes:  4
  ⚡ E-bikes:        2
  🅿 Empty docks:   13
  Status: ✓ Renting | ✓ Returning
  Updated: 8s ago
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fetched 2 stations in 0.3s
```

## Acceptance Criteria
- [ ] Script resolves station_ids from station names
- [ ] Updates config.yaml with resolved IDs
- [ ] Fetches live status for configured stations
- [ ] Returns structured data (list of dicts) for API consumption
- [ ] Gracefully handles: station offline, API errors, network issues
- [ ] Status matches the Citibike app
- [ ] Runs in < 2 seconds

## Implementation Tips
- **Fuzzy name matching:** Use `difflib.get_close_matches()` for station name search
- **Nearby stations:** Calculate distance using haversine formula (or simple lat/lon diff)
- **GBFS structure:**
  ```python
  response = requests.get(url, timeout=10).json()
  stations = response['data']['stations']  # List of station objects
  ```
- **Interactive station selection:** Use `input()` for CLI interaction during resolution
- **Config update:** Use `yaml.safe_dump()` to write back to config.yaml

## Testing Checklist
After implementing, test these scenarios:

1. **Station ID resolution:**
   ```bash
   # Reset config.yaml station_ids to "TBD"
   python backend/fetchers/citibike.py --resolve
   # Verify config.yaml updated correctly
   grep station_id config.yaml
   ```

2. **Live status fetch:**
   ```bash
   python backend/fetchers/citibike.py
   # Compare to Citibike app
   ```

3. **Station out of service:**
   ```python
   # Mock a station with is_renting=False
   # Should display "OUT OF SERVICE" warning
   ```

4. **All docks full/empty:**
   ```bash
   # Wait for natural occurrence or find a busy station
   # Should highlight critical state
   ```

## Configuration Update
After running station resolution, your config.yaml should look like:
```yaml
citibike:
  poll_interval_seconds: 60
  stations:
    - name: "Broadway & Exchange Pl"
      station_id: "66db237e-0aca-11e7-82f6-3863bb44ef7c"
    - name: "Broad St & Water St"  # Example - you'll choose this
      station_id: "66db2676-0aca-11e7-82f6-3863bb44ef7c"
```

## Next Session
Once complete, Session 3A will integrate both fetchers into a Flask API server with background scheduling.

## Reference Links
- GBFS Specification: https://github.com/MobilityData/gbfs
- Citibike System Data: https://citibikenyc.com/system-data
- Haversine formula: https://en.wikipedia.org/wiki/Haversine_formula
