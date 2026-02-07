# Session 3A: Flask API Server with Background Scheduling

## Context
You are working on Milestone 3 of the FiDi Transit Dashboard project. Both fetchers (MTA and Citibike) are complete and tested. This session integrates them into a Flask web server with automatic background polling.

## Files You Need Access To
- `~/Projects/dashboard/backend/app.py` (create - main deliverable)
- `~/Projects/dashboard/backend/cache.py` (create - in-memory data store)
- `~/Projects/dashboard/backend/health.py` (create - health monitoring)
- `~/Projects/dashboard/backend/fetchers/mta.py` (read only - already complete)
- `~/Projects/dashboard/backend/fetchers/citibike.py` (read only - already complete)
- `~/Projects/dashboard/config.yaml` (read only)

## Background
The dashboard needs:
1. **Background workers** that poll MTA (30s) and Citibike (60s) continuously
2. **In-memory cache** storing latest results (no database needed)
3. **REST API** for frontend to fetch cached data
4. **Health monitoring** to detect stale/failed fetches

Architecture:
```
APScheduler (background)
    ├─> MTA Fetcher (every 30s) ──> Cache
    └─> Citibike Fetcher (every 60s) ──> Cache
                                          │
Flask API (HTTP)                          │
    ├─> GET /api/subway ────────────> Read Cache
    ├─> GET /api/citibike ──────────> Read Cache
    └─> GET /api/health ────────────> Health Stats
```

## Your Task

### 1. Create `backend/cache.py` - In-Memory Data Store
A simple thread-safe cache for storing fetcher results:

```python
{
    "subway": {
        "data": [...],           # List of arrival dicts
        "last_updated": 1707234567,
        "last_error": None,
        "fetch_count": 42
    },
    "citibike": {
        "data": [...],           # List of station status dicts
        "last_updated": 1707234567,
        "last_error": None,
        "fetch_count": 21
    }
}
```

**Required methods:**
- `set(key, data)` - Store data with automatic timestamp
- `get(key)` - Retrieve data with metadata
- `record_error(key, error)` - Log fetch errors
- `get_all_metadata()` - Return stats for health endpoint

**Thread safety:** Use `threading.Lock()` for concurrent access

---

### 2. Create `backend/health.py` - Health Monitoring
Tracks system health and data freshness:

```python
def get_health_status(cache):
    """Return health status dict"""
    return {
        "status": "healthy",        # healthy | degraded | down
        "uptime_seconds": 3600,
        "subway": {
            "last_update": "30s ago",
            "status": "healthy",    # healthy | stale | error
            "fetch_count": 42,
            "error_count": 0
        },
        "citibike": {
            "last_update": "45s ago",
            "status": "healthy",
            "fetch_count": 21,
            "error_count": 1
        }
    }
```

**Status logic:**
- `healthy` - Last update < 90s ago
- `stale` - Last update 90-180s ago
- `error` - Last update > 180s ago OR recent fetch error

---

### 3. Create `backend/app.py` - Flask Server + Scheduler

#### API Endpoints

**`GET /api/subway`**
Returns cached subway arrivals:
```json
{
    "success": true,
    "data": [
        {
            "line": "4",
            "station": "Wall St",
            "direction": "N",
            "minutes_until": 3,
            "route_id": "4",
            "stop_id": "140N",
            "timestamp": 1707234567
        },
        // ... more arrivals
    ],
    "last_updated": 1707234567,
    "staleness_seconds": 12
}
```

**`GET /api/citibike`**
Returns cached Citibike status:
```json
{
    "success": true,
    "data": [
        {
            "station_id": "66db237e...",
            "name": "Broadway & Exchange Pl",
            "bikes_available": 8,
            "ebikes_available": 3,
            "docks_available": 4,
            "total_capacity": 15,
            "is_renting": true,
            "is_returning": true,
            "last_reported": 1707234567,
            "percent_full": 73
        },
        // ... more stations
    ],
    "last_updated": 1707234560,
    "staleness_seconds": 35
}
```

**`GET /api/health`**
Returns system health:
```json
{
    "status": "healthy",
    "uptime_seconds": 3600,
    "subway": {
        "last_update": "30s ago",
        "status": "healthy",
        "fetch_count": 42,
        "error_count": 0
    },
    "citibike": {
        "last_update": "45s ago",
        "status": "healthy",
        "fetch_count": 21,
        "error_count": 1
    }
}
```

**`GET /` (root)**
Returns a simple HTML page:
```html
<!DOCTYPE html>
<html>
<head><title>FiDi Dash API</title></head>
<body>
    <h1>FiDi Transit Dashboard API</h1>
    <p>Endpoints:</p>
    <ul>
        <li><a href="/api/subway">/api/subway</a> - Subway arrivals</li>
        <li><a href="/api/citibike">/api/citibike</a> - Citibike status</li>
        <li><a href="/api/health">/api/health</a> - System health</li>
    </ul>
</body>
</html>
```

#### Background Scheduler Setup
Use `APScheduler` to run fetchers:

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def fetch_subway_task():
    """Background job for MTA data"""
    try:
        config = load_config()
        data = fetch_subway_arrivals(config)
        cache.set('subway', data)
    except Exception as e:
        cache.record_error('subway', str(e))
        logger.error(f"Subway fetch failed: {e}")

def fetch_citibike_task():
    """Background job for Citibike data"""
    try:
        config = load_config()
        data = fetch_citibike_status(config)
        cache.set('citibike', data)
    except Exception as e:
        cache.record_error('citibike', str(e))
        logger.error(f"Citibike fetch failed: {e}")

# Schedule jobs
scheduler.add_job(fetch_subway_task, 'interval', seconds=30)
scheduler.add_job(fetch_citibike_task, 'interval', seconds=60)
scheduler.start()

# Run immediately on startup
fetch_subway_task()
fetch_citibike_task()
```

---

## Requirements

### Error Handling
- Catch ALL exceptions in background jobs (don't crash the scheduler)
- Log errors to stdout/stderr
- Return last known good data if current fetch fails
- Track error count per data source

### Logging
Use Python's `logging` module:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)
```

### CORS Headers
Enable for local development:
```python
from flask import Flask
from flask_cors import CORS  # Add to requirements.txt if needed

app = Flask(__name__)
CORS(app)  # Allow all origins (fine for local use)
```

### Startup Behavior
- Fetch initial data immediately (don't wait 30s/60s)
- Log successful startup
- Show health status on console

---

## Example Console Output (Startup)
```bash
$ python backend/app.py

2026-02-06 14:30:00 [INFO] Loading config from config.yaml
2026-02-06 14:30:00 [INFO] Starting background scheduler...
2026-02-06 14:30:00 [INFO] Fetching initial subway data...
2026-02-06 14:30:01 [INFO] Subway: Fetched 12 arrivals from 6 stations
2026-02-06 14:30:01 [INFO] Fetching initial Citibike data...
2026-02-06 14:30:02 [INFO] Citibike: Fetched 2 stations
2026-02-06 14:30:02 [INFO] Scheduler started: MTA every 30s, Citibike every 60s
2026-02-06 14:30:02 [INFO] Flask server starting on http://localhost:5000
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit

2026-02-06 14:30:32 [INFO] Subway: Fetched 12 arrivals from 6 stations
2026-02-06 14:31:02 [INFO] Citibike: Fetched 2 stations
2026-02-06 14:31:02 [INFO] Subway: Fetched 12 arrivals from 6 stations
```

---

## Acceptance Criteria
- [ ] Flask server starts successfully on port 5000
- [ ] Background scheduler runs MTA fetcher every 30s
- [ ] Background scheduler runs Citibike fetcher every 60s
- [ ] Initial data fetched immediately on startup
- [ ] All 3 API endpoints return valid JSON
- [ ] Data in cache matches fetcher output
- [ ] Health endpoint shows accurate staleness
- [ ] Server logs all fetch activity
- [ ] Crashes in fetchers don't crash the server
- [ ] Can test with: `curl http://localhost:5000/api/subway`

---

## Testing Checklist

### 1. Basic functionality
```bash
cd ~/Projects/dashboard
source venv/bin/activate
python backend/app.py

# In another terminal:
curl http://localhost:5000/api/subway | jq
curl http://localhost:5000/api/citibike | jq
curl http://localhost:5000/api/health | jq
```

### 2. Background polling
```bash
# Watch logs for 2 minutes
# Should see subway fetch every 30s, citibike every 60s
```

### 3. Error recovery
```python
# Temporarily break one fetcher (e.g., invalid URL)
# Server should continue running
# Health endpoint should show error status
# Last good data should still be served
```

### 4. Staleness detection
```bash
# Stop the background scheduler (comment out scheduler.start())
# Wait 90 seconds
# Check health endpoint - should show "stale" status
```

---

## Project Structure After This Session
```
dashboard/
├── backend/
│   ├── app.py              ← Main Flask server (NEW)
│   ├── cache.py            ← In-memory data store (NEW)
│   ├── health.py           ← Health monitoring (NEW)
│   └── fetchers/
│       ├── __init__.py
│       ├── mta.py          (existing)
│       └── citibike.py     (existing)
├── config.yaml             (existing)
└── requirements.txt        (update if needed)
```

---

## Additional Dependencies
Add to `requirements.txt` if not present:
```
flask==3.0.0
APScheduler==3.10.4
flask-cors==4.0.0
```

Then: `pip install -r requirements.txt`

---

## Next Session
Once complete, Session 4A will build the HTML/CSS frontend that consumes these API endpoints.

---

## Reference Links
- Flask docs: https://flask.palletsprojects.com/
- APScheduler docs: https://apscheduler.readthedocs.io/
- Python threading: https://docs.python.org/3/library/threading.html
