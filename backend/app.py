from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, send_from_directory

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover - optional dependency
    CORS = None

try:
    from backend.cache import Cache
    from backend.fetchers.citibike import fetch_citibike_status
    from backend.fetchers.inbound import fetch_inbound_trains
    from backend.fetchers.mta import fetch_mta_feeds, fetch_subway_arrivals, get_required_feeds_from_config
    from backend.health import get_health_status
except ImportError:  # pragma: no cover - fallback for script execution
    from cache import Cache
    from fetchers.citibike import fetch_citibike_status
    from fetchers.inbound import fetch_inbound_trains
    from fetchers.mta import fetch_mta_feeds, fetch_subway_arrivals, get_required_feeds_from_config
    from health import get_health_status


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.yaml"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
if CORS is not None:
    CORS(app)
else:
    logger.warning("flask-cors not installed; CORS headers disabled.")

cache = Cache()


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_PATH}")
    logger.info("Loading config from %s", CONFIG_PATH)
    with CONFIG_PATH.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping.")
    return data


def _safe_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _get_display_thresholds(config: Dict[str, Any]) -> Tuple[int, int]:
    display = config.get("display", {}) if isinstance(config.get("display"), dict) else {}
    warning = max(0, _safe_int(display.get("staleness_warning_sec", 60), 60))
    critical = max(0, _safe_int(display.get("staleness_critical_sec", 120), 120))
    if critical < warning:
        critical = warning
    return warning, critical


def _get_poll_intervals(config: Dict[str, Any]) -> Tuple[int, int]:
    subway = config.get("subway", {}) if isinstance(config.get("subway"), dict) else {}
    citibike = config.get("citibike", {}) if isinstance(config.get("citibike"), dict) else {}
    subway_interval = _safe_int(subway.get("poll_interval_seconds", 30), 30)
    citibike_interval = _safe_int(citibike.get("poll_interval_seconds", 60), 60)
    return subway_interval, citibike_interval


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return straight-line distance in miles between two coordinates."""

    import math

    radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def _walk_minutes_from_miles(distance_miles: float, walking_speed_mps: float = 1.4) -> Optional[int]:
    import math

    if not math.isfinite(distance_miles):
        return None
    if distance_miles <= 0:
        return 0
    meters_per_mile = 1609.34
    minutes_per_mile = meters_per_mile / (walking_speed_mps * 60)
    return max(1, int(round(distance_miles * minutes_per_mile)))


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_frontend_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a small, read-only subset of config.yaml for the frontend.

    This keeps the frontend rendering deterministic (always renders the configured blocks,
    even if there are currently no arrivals for a given station).
    """

    display = config.get("display", {}) if isinstance(config.get("display"), dict) else {}
    location = config.get("location", {}) if isinstance(config.get("location"), dict) else {}
    subway = config.get("subway", {}) if isinstance(config.get("subway"), dict) else {}
    citibike = config.get("citibike", {}) if isinstance(config.get("citibike"), dict) else {}

    home_lat = _safe_float(location.get("lat"))
    home_lng = _safe_float(location.get("lng"))

    stations = subway.get("stations", []) if isinstance(subway.get("stations"), list) else []
    citibike_stations = (
        citibike.get("stations", []) if isinstance(citibike.get("stations"), list) else []
    )

    subway_blocks: list[dict[str, Any]] = []
    for st in stations:
        if not isinstance(st, dict):
            continue
        directions = st.get("directions", []) if isinstance(st.get("directions"), list) else []

        st_lat = _safe_float(st.get("lat"))
        st_lng = _safe_float(st.get("lng"))
        distance_miles: Optional[float] = None
        walk_minutes: Optional[int] = None
        if home_lat is not None and home_lng is not None and st_lat is not None and st_lng is not None:
            distance_miles = _haversine_miles(home_lat, home_lng, st_lat, st_lng)
            walk_minutes = _walk_minutes_from_miles(distance_miles)

        subway_blocks.append(
            {
                "id": st.get("id"),
                "name": st.get("name"),
                "lines": st.get("lines"),
                "distance_miles": distance_miles,
                "walk_minutes": walk_minutes,
                "directions": [
                    {
                        "code": d.get("code"),
                        "label": d.get("label"),
                        "destination": d.get("destination"),
                        "stop_id": d.get("stop_id"),
                    }
                    for d in directions
                    if isinstance(d, dict)
                ],
            }
        )

    return {
        "display": {
            "refresh_interval_ms": max(1000, _safe_int(display.get("refresh_interval_ms", 15000), 15000)),
            "staleness_warning_sec": max(0, _safe_int(display.get("staleness_warning_sec", 60), 60)),
            "staleness_critical_sec": max(0, _safe_int(display.get("staleness_critical_sec", 120), 120)),
            "theme": display.get("theme"),
            "orientation": display.get("orientation"),
        },
        "location": {
            "name": location.get("name"),
            "lat": home_lat,
            "lng": home_lng,
        },
        "subway": {
            "stations": subway_blocks,
        },
        "citibike": {
            "stations": [
                {"name": s.get("name"), "station_id": s.get("station_id")}
                for s in citibike_stations
                if isinstance(s, dict)
            ]
        },
    }


def _compute_staleness_seconds(last_updated: Any, now: int) -> Optional[int]:
    if not isinstance(last_updated, int):
        return None
    return max(0, now - last_updated)


def fetch_subway_task() -> None:
    try:
        config = load_config()
        now_timestamp = int(time.time())
        feed_names = get_required_feeds_from_config(config)
        api_key = __import__("os").environ.get("MTA_API_KEY")
        feeds = fetch_mta_feeds(feed_names, api_key, now_timestamp)

        data = fetch_subway_arrivals(config, feeds_by_name=feeds, now_timestamp=now_timestamp)
        cache.set("subway", data)
        logger.info("Subway: Fetched %s arrivals", len(data))

        inbound = fetch_inbound_trains(config, feeds_by_name=feeds, now_timestamp=now_timestamp)
        cache.set("inbound", inbound)
        logger.info("Inbound: Fetched %s trains", len(inbound))
    except Exception as exc:
        cache.record_error("subway", str(exc))
        cache.record_error("inbound", str(exc))
        logger.error("Subway fetch failed: %s", exc)


def fetch_citibike_task() -> None:
    try:
        config = load_config()
        data = fetch_citibike_status(config)
        cache.set("citibike", data)
        logger.info("Citibike: Fetched %s stations", len(data))
    except Exception as exc:
        cache.record_error("citibike", str(exc))
        logger.error("Citibike fetch failed: %s", exc)


@app.route("/")
def index() -> Any:
    return send_from_directory("../frontend", "index.html")


@app.route("/<path:path>")
def static_files(path: str) -> Any:
    return send_from_directory("../frontend", path)


@app.route("/api/subway")
def api_subway() -> Any:
    entry = cache.get("subway")
    now = int(time.time())
    staleness_seconds = _compute_staleness_seconds(entry["last_updated"], now)
    return jsonify(
        {
            "success": True,
            "data": entry["data"],
            "last_updated": entry["last_updated"],
            "staleness_seconds": staleness_seconds,
        }
    )


@app.route("/api/citibike")
def api_citibike() -> Any:
    entry = cache.get("citibike")
    now = int(time.time())
    staleness_seconds = _compute_staleness_seconds(entry["last_updated"], now)
    return jsonify(
        {
            "success": True,
            "data": entry["data"],
            "last_updated": entry["last_updated"],
            "staleness_seconds": staleness_seconds,
        }
    )


def _format_iso_utc(timestamp: Optional[int]) -> Optional[str]:
    if not isinstance(timestamp, int):
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_tracking_window(config: Dict[str, Any]) -> str:
    inbound = config.get("inbound_tracker", {})
    if not isinstance(inbound, dict):
        return "Inbound"
    tracking = inbound.get("tracking_window", {})
    if not isinstance(tracking, dict):
        return "Inbound"

    start = tracking.get("start_station") or tracking.get("north_boundary")
    end = tracking.get("end_station") or tracking.get("south_boundary")
    include_next = tracking.get("include_next_at_start")

    if isinstance(start, str) and isinstance(end, str):
        suffix = ""
        try:
            include_next_int = int(include_next)
        except (TypeError, ValueError):
            include_next_int = 0
        if include_next_int > 0:
            suffix = f" (+{include_next_int} @ start)"
        return f"{start} → {end}{suffix}"

    return "Inbound"


@app.route("/api/inbound")
def api_inbound() -> Any:
    entry = cache.get("inbound")
    config = load_config()
    return jsonify(
        {
            "trains": entry["data"],
            "last_updated": _format_iso_utc(entry["last_updated"]),
            "tracking_window": _format_tracking_window(config),
        }
    )


@app.route("/health")
def health_alias() -> Any:
    return api_health()


@app.route("/api/health")
def api_health() -> Any:
    config = load_config()
    warning, critical = _get_display_thresholds(config)
    status = get_health_status(cache, warning, critical)
    return jsonify(status)


@app.route("/api/config")
def api_config() -> Any:
    config = load_config()
    return jsonify({"success": True, "data": _build_frontend_config(config)})


def _log_startup_health(config: Dict[str, Any]) -> None:
    warning, critical = _get_display_thresholds(config)
    status = get_health_status(cache, warning, critical)
    logger.info("Health status at startup: %s", status["status"])


def main() -> None:
    try:
        config = load_config()
    except Exception as exc:
        logger.error("Failed to load config: %s", exc)
        return

    subway_interval, citibike_interval = _get_poll_intervals(config)

    logger.info("Starting background scheduler...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_subway_task, "interval", seconds=subway_interval)
    scheduler.add_job(fetch_citibike_task, "interval", seconds=citibike_interval)
    scheduler.start()

    logger.info("Fetching initial subway data...")
    fetch_subway_task()
    logger.info("Fetching initial Citibike data...")
    fetch_citibike_task()

    logger.info(
        "Scheduler started: MTA every %ss, Citibike every %ss",
        subway_interval,
        citibike_interval,
    )

    _log_startup_health(config)

    environ = __import__("os").environ
    host = environ.get("HOST", "0.0.0.0")
    port = int(environ.get("PORT", "5000"))
    logger.info("Flask server starting on http://%s:%s", host, port)
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
