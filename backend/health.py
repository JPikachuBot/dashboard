from __future__ import annotations

import time
from typing import Dict, Optional, TypedDict

try:
    from .cache import Cache
except ImportError:  # pragma: no cover - fallback for script execution
    from cache import Cache


START_TIME = time.time()


class SourceHealth(TypedDict):
    last_update: str
    status: str
    fetch_count: int
    error_count: int


class HealthStatus(TypedDict):
    status: str
    uptime_seconds: int
    subway: SourceHealth
    citibike: SourceHealth


def _format_age(last_updated: Optional[int], now: int) -> str:
    if not last_updated:
        return "never"
    delta = max(0, now - last_updated)
    return f"{delta}s ago"


def _source_status(
    last_updated: Optional[int],
    last_error_at: Optional[int],
    now: int,
    staleness_warning_sec: int,
    staleness_critical_sec: int,
) -> str:
    if last_error_at and (last_updated is None or last_error_at >= last_updated):
        return "error"
    if last_updated is None:
        return "error"
    age = now - last_updated
    if age >= staleness_critical_sec:
        return "error"
    if age >= staleness_warning_sec:
        return "stale"
    return "healthy"


def get_health_status(
    cache: Cache,
    staleness_warning_sec: int,
    staleness_critical_sec: int,
) -> HealthStatus:
    now = int(time.time())
    metadata = cache.get_all_metadata()

    def build_source(name: str) -> SourceHealth:
        entry = metadata.get(name, {})
        last_updated = entry.get("last_updated")
        last_error_at = entry.get("last_error_at")
        status = _source_status(
            last_updated=last_updated,
            last_error_at=last_error_at,
            now=now,
            staleness_warning_sec=staleness_warning_sec,
            staleness_critical_sec=staleness_critical_sec,
        )
        return {
            "last_update": _format_age(last_updated, now),
            "status": status,
            "fetch_count": int(entry.get("fetch_count", 0)),
            "error_count": int(entry.get("error_count", 0)),
        }

    subway = build_source("subway")
    citibike = build_source("citibike")

    overall_status = "healthy"
    if "error" in (subway["status"], citibike["status"]):
        overall_status = "down"
    elif "stale" in (subway["status"], citibike["status"]):
        overall_status = "degraded"

    return {
        "status": overall_status,
        "uptime_seconds": int(now - START_TIME),
        "subway": subway,
        "citibike": citibike,
    }
