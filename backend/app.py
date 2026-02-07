from __future__ import annotations

import logging
import time
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
    from backend.fetchers.mta import fetch_subway_arrivals
    from backend.health import get_health_status
except ImportError:  # pragma: no cover - fallback for script execution
    from cache import Cache
    from fetchers.citibike import fetch_citibike_status
    from fetchers.mta import fetch_subway_arrivals
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


def _build_frontend_config(config: Dict[str, Any]) -> Dict[str, Any]:
    display = config.get("display", {}) if isinstance(config.get("display"), dict) else {}
    location = config.get("location", {}) if isinstance(config.get("location"), dict) else {}
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
        },
    }


def _compute_staleness_seconds(last_updated: Any, now: int) -> Optional[int]:
    if not isinstance(last_updated, int):
        return None
    return max(0, now - last_updated)


def fetch_subway_task() -> None:
    try:
        config = load_config()
        data = fetch_subway_arrivals(config)
        cache.set("subway", data)
        logger.info("Subway: Fetched %s arrivals", len(data))
    except Exception as exc:
        cache.record_error("subway", str(exc))
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

    logger.info("Flask server starting on http://localhost:5000")
    port = int(__import__("os").environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
