# Session 1B: MTA Real-Time Fetcher Implementation

## Context
You are working on Milestone 1 of the FiDi Transit Dashboard project. Session 1A has already resolved stop IDs. This session builds the real-time MTA subway data fetcher.

## Files You Need Access To
- `~/Projects/dashboard/config.yaml` (read only - now has stop_ids filled in)
- `~/Projects/dashboard/backend/fetchers/__init__.py` (create if needed)
- `~/Projects/dashboard/backend/fetchers/mta.py` (create - main deliverable)

## Background
The MTA publishes 4 different GTFS-Realtime feeds (protobuf format) that update every 30 seconds:
- **1-7 lines feed:** https://api.mta.info/api/subway/gtfs/gtfs-1234567
- **ACE lines feed:** https://api.mta.info/api/subway/gtfs/gtfs-ace
- **NQRW lines feed:** https://api.mta.info/api/subway/gtfs/gtfs-nqrw
- **JZ lines feed:** https://api.mta.info/api/subway/gtfs/gtfs-jz

Your stations span all 4 feeds:
- Wall St (4/5), Wall St (2/3), Rector St (1) → 1234567 feed
- Fulton St (A/C) → ACE feed
- Rector St (R/W) → NQRW feed
- Broad St (J) → JZ feed

## Your Task
Create `backend/fetchers/mta.py` with the following:

### 1. Core Function: `fetch_subway_arrivals(config)`
**Input:** config dict (from parsed config.yaml)  
**Output:** List of arrival dictionaries

**Each arrival dict should contain:**
```python
{
    "line": "4",                    # Train line (4, 5, 2, 3, J, 1, R, W, A, C)
    "station": "Wall St",           # Station name
    "direction": "N",               # N, S, E, W (from config)
    "minutes_until": 3,             # Minutes until arrival (integer)
    "route_id": "4",                # MTA route ID (usually same as line)
    "stop_id": "140N",              # The platform stop ID
    "timestamp": 1707234567         # Unix timestamp when this data was fetched
}
```

### 2. Requirements
**Use the `nyct-gtfs` library** (already installed):
```python
from nyct_gtfs import NYCTFeed
```

**Fetch strategy:**
- Load config.yaml to get all configured stations and stop_ids
- Determine which feeds to fetch based on which lines are configured
- For each feed, get stop time updates for your stop_ids only
- Filter to next 2 arrivals per station
- Convert arrival times to "minutes from now"
- Return sorted by station priority (from config)

**Error handling:**
- Feed fetch timeout (30s limit)
- Feed returns stale data (timestamp > 2 minutes old)
- No trains scheduled (return empty list, don't crash)
- Invalid stop_id in feed (log warning, skip)
- Network errors (log error, return cached/empty data)

**Edge cases:**
- Train is "arriving now" → show as 0 minutes, not negative
- Train arrival time is in the past → exclude it
- Duplicate trains in feed → deduplicate by route + arrival time

### 3. Helper Functions (suggested structure)
```python
def load_config(config_path="config.yaml"):
    """Load and parse config.yaml"""
    pass

def get_required_feeds(stations):
    """Determine which GTFS-RT feeds to fetch based on configured lines"""
    # Returns: ["gtfs-1234567", "gtfs-ace", "gtfs-nqrw", "gtfs-jz"]
    pass

def parse_feed(feed_url, stop_ids):
    """Fetch and parse a single GTFS-RT feed for specific stop_ids"""
    pass

def minutes_until(timestamp):
    """Convert Unix timestamp to minutes from now"""
    pass
```

### 4. Test Function
Include a `if __name__ == "__main__":` block that:
- Loads config
- Fetches arrivals
- Prints results in a readable format
- Compares to what the MTA app shows (you'll verify manually)

## Example Output (Test Run)
```bash
$ python backend/fetchers/mta.py

Fetching MTA subway arrivals...
Loaded 6 stations from config.yaml
Fetching feeds: 1234567, ACE, NQRW, JZ

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WALL ST (4/5)
  4 train → 2 min
  5 train → 6 min

WALL ST (2/3)
  2 train → 5 min
  3 train → 9 min

BROAD ST (J)
  J train → 3 min
  J train → 11 min

RECTOR ST (1)
  1 train → 4 min
  1 train → 8 min

RECTOR ST (R/W)
  R train → 7 min
  W train → 14 min

FULTON ST (A/C)
  A train → 3 min
  C train → 5 min
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fetched 12 arrivals in 1.2s
Last updated: 2026-02-06 14:32:15
```

## Acceptance Criteria
- [ ] Script runs without errors
- [ ] Returns next 2 arrivals for each of the 6 configured stations
- [ ] Arrival times match the MTA app (within 1 minute)
- [ ] Gracefully handles: no trains, feed errors, network issues
- [ ] Returns structured data (list of dicts) for API consumption
- [ ] Runs in < 3 seconds for all 4 feeds combined

## Implementation Tips
- **nyct-gtfs usage:**
  ```python
  feed = NYCTFeed("1234567")  # Feed name without "gtfs-" prefix
  for stop_id in your_stop_ids:
      trains = feed.filter_trip_updates(stop_id=stop_id)
  ```
- **Time conversion:** `minutes = (arrival_timestamp - time.time()) // 60`
- **Feed deduplication:** Some trains appear in multiple feeds; use route_id + stop_id + time as unique key
- **Config structure:** Use `yaml.safe_load()` to parse config.yaml

## Testing Checklist
After implementing, test these scenarios:

1. **Normal operation:**
   ```bash
   python backend/fetchers/mta.py
   # Compare output to MTA app
   ```

2. **No trains scenario:**
   ```bash
   # Run at 2am when service is light
   # Should return empty lists, not crash
   ```

3. **Feed staleness:**
   ```python
   # Mock a feed with old timestamp
   # Should log warning and handle gracefully
   ```

4. **Network failure:**
   ```bash
   # Disconnect WiFi during fetch
   # Should timeout and return error, not hang
   ```

## Next Session
Once complete, Session 2 will implement the Citibike fetcher using a similar pattern.

## Reference Links
- nyct-gtfs docs: https://github.com/Andrew-Dickinson/nyct-gtfs
- MTA Developer Portal: https://www.mta.info/developers
- GTFS-RT spec: https://gtfs.org/realtime/
