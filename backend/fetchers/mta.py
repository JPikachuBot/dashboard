from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple, TypedDict

import requests
import yaml
from nyct_gtfs import NYCTFeed


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"

FEED_URLS: Dict[str, str] = {
    "gtfs-1234567": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs",
    "gtfs-ace": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace",
    "gtfs-nqrw": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw",
    "gtfs-jz": "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz",
}

LINE_TO_FEED: Dict[str, str] = {
    "1": "gtfs-1234567",
    "2": "gtfs-1234567",
    "3": "gtfs-1234567",
    "4": "gtfs-1234567",
    "5": "gtfs-1234567",
    "6": "gtfs-1234567",
    "7": "gtfs-1234567",
    "A": "gtfs-ace",
    "C": "gtfs-ace",
    "E": "gtfs-ace",
    "J": "gtfs-jz",
    "Z": "gtfs-jz",
    "N": "gtfs-nqrw",
    "Q": "gtfs-nqrw",
    "R": "gtfs-nqrw",
    "W": "gtfs-nqrw",
}

FEED_TIMEOUT_SECONDS = 30
STALE_THRESHOLD_SECONDS = 120

logger = logging.getLogger(__name__)


class Arrival(TypedDict):
    line: str
    station: str
    direction: str
    minutes_until: int
    route_id: str
    stop_id: str
    timestamp: int


class StationConfig(TypedDict):
    name: str
    lines: List[str]
    stop_id: str
    direction: str


@dataclass
class ArrivalCandidate:
    arrival_timestamp: int
    line: str
    station: str
    direction: str
    route_id: str
    stop_id: str


@dataclass
class CacheState:
    timestamp: Optional[int]
    arrivals: List[Arrival]


_CACHE = CacheState(timestamp=None, arrivals=[])


class FeedStaleError(RuntimeError):
    pass


def load_config(config_path: Path = CONFIG_PATH) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping.")
    return data


def get_required_feeds(stations: Sequence[StationConfig]) -> List[str]:
    required: Set[str] = set()
    for station in stations:
        for line in station["lines"]:
            feed = LINE_TO_FEED.get(line)
            if feed is None:
                logger.warning("Unknown line '%s' in config; skipping feed mapping.", line)
                continue
            required.add(feed)
    ordered = [feed for feed in FEED_URLS.keys() if feed in required]
    return ordered


def minutes_until(arrival_timestamp: int, now_timestamp: int) -> int:
    if arrival_timestamp <= now_timestamp:
        return 0
    return max(0, int((arrival_timestamp - now_timestamp) // 60))


def _fetch_feed(feed_name: str, api_key: Optional[str], timeout_seconds: int) -> NYCTFeed:
    feed_url = FEED_URLS[feed_name]
    feed = NYCTFeed(feed_url, fetch_immediately=False)
    headers = {"x-api-key": api_key} if api_key else None
    response = requests.get(
        feed_url,
        headers=headers,
        timeout=timeout_seconds,
    )
    if response.status_code in {401, 403}:
        logger.error(
            "MTA feed request unauthorized for %s (HTTP %s).",
            feed_name,
            response.status_code,
        )
    response.raise_for_status()
    feed.load_gtfs_bytes(response.content)
    return feed


def _is_stop_id_valid(feed: NYCTFeed, stop_id: str) -> bool:
    try:
        feed._stops.get_station_name(stop_id)
    except ValueError:
        return False
    return True


def _collect_candidates(
    feed: NYCTFeed,
    stations: Sequence[StationConfig],
    now_timestamp: int,
) -> Dict[int, List[ArrivalCandidate]]:
    candidates_by_station: Dict[int, List[ArrivalCandidate]] = {
        idx: [] for idx in range(len(stations))
    }

    for idx, station in enumerate(stations):
        stop_id = station["stop_id"]
        if not _is_stop_id_valid(feed, stop_id):
            logger.warning("Invalid stop_id '%s' in feed; skipping station %s.", stop_id, station["name"])
            continue

        station_lines = station["lines"]
        trips = feed.filter_trips(line_id=station_lines)
        for trip in trips:
            for update in trip.stop_time_updates:
                if update.stop_id != stop_id:
                    continue
                arrival_dt = update.arrival or update.departure
                if arrival_dt is None:
                    continue
                arrival_ts = int(arrival_dt.timestamp())
                if arrival_ts < now_timestamp:
                    continue
                candidates_by_station[idx].append(
                    ArrivalCandidate(
                        arrival_timestamp=arrival_ts,
                        line=trip.route_id,
                        station=station["name"],
                        direction=station["direction"],
                        route_id=trip.route_id,
                        stop_id=stop_id,
                    )
                )

    return candidates_by_station


def _select_arrivals(
    candidates_by_station: Dict[int, List[ArrivalCandidate]],
    now_timestamp: int,
    fetched_timestamp: int,
) -> List[Arrival]:
    results: List[Arrival] = []
    for idx in sorted(candidates_by_station.keys()):
        candidates = candidates_by_station[idx]
        candidates.sort(key=lambda candidate: candidate.arrival_timestamp)

        seen: Set[Tuple[str, str, int]] = set()
        kept: List[ArrivalCandidate] = []
        for candidate in candidates:
            key = (candidate.route_id, candidate.stop_id, candidate.arrival_timestamp)
            if key in seen:
                continue
            seen.add(key)
            kept.append(candidate)
            if len(kept) >= 2:
                break

        for candidate in kept:
            results.append(
                Arrival(
                    line=candidate.line,
                    station=candidate.station,
                    direction=candidate.direction,
                    minutes_until=minutes_until(candidate.arrival_timestamp, now_timestamp),
                    route_id=candidate.route_id,
                    stop_id=candidate.stop_id,
                    timestamp=fetched_timestamp,
                )
            )
    return results


def _extract_stations(config: dict) -> List[StationConfig]:
    subway = config.get("subway")
    if not isinstance(subway, dict):
        raise ValueError("Config missing subway section.")
    stations = subway.get("stations")
    if not isinstance(stations, list):
        raise ValueError("Config subway.stations must be a list.")
    normalized: List[StationConfig] = []
    for station in stations:
        if not isinstance(station, dict):
            raise ValueError("Each station entry must be a mapping.")
        name = station.get("name")
        lines = station.get("lines")
        stop_id = station.get("stop_id")
        direction = station.get("direction")
        if not isinstance(name, str) or not isinstance(lines, list):
            raise ValueError("Station entry missing name or lines.")
        if not isinstance(stop_id, str) or not stop_id:
            raise ValueError(f"Station {name} missing stop_id.")
        if not isinstance(direction, str) or not direction:
            raise ValueError(f"Station {name} missing direction.")
        normalized.append(
            StationConfig(
                name=name,
                lines=[str(line).strip() for line in lines],
                stop_id=stop_id.strip(),
                direction=direction.strip(),
            )
        )
    return normalized


def fetch_subway_arrivals(config: dict) -> List[Arrival]:
    stations = _extract_stations(config)
    feed_names = get_required_feeds(stations)
    api_key = os.environ.get("MTA_API_KEY")

    if not api_key:
        logger.info("MTA_API_KEY is not set; fetching feeds without authentication.")

    now_timestamp = int(time.time())
    fetched_timestamp = now_timestamp
    candidates_by_station: Dict[int, List[ArrivalCandidate]] = {
        idx: [] for idx in range(len(stations))
    }

    try:
        for feed_name in feed_names:
            feed = _fetch_feed(feed_name, api_key, FEED_TIMEOUT_SECONDS)
            feed_timestamp = int(feed.last_generated.timestamp())
            if now_timestamp - feed_timestamp > STALE_THRESHOLD_SECONDS:
                raise FeedStaleError(
                    f"Feed {feed_name} is stale: generated at {feed.last_generated}."
                )

            feed_candidates = _collect_candidates(feed, stations, now_timestamp)
            for idx, candidates in feed_candidates.items():
                candidates_by_station[idx].extend(candidates)
    except requests.RequestException as exc:
        logger.error("Network error while fetching MTA feed: %s", exc)
        return list(_CACHE.arrivals) if _CACHE.arrivals else []
    except FeedStaleError as exc:
        logger.warning("%s Returning cached data if available.", exc)
        return list(_CACHE.arrivals) if _CACHE.arrivals else []
    except Exception as exc:  # Explicit catch to keep fetcher resilient
        logger.error("Unexpected error while fetching MTA feed: %s", exc)
        return list(_CACHE.arrivals) if _CACHE.arrivals else []

    arrivals = _select_arrivals(candidates_by_station, now_timestamp, fetched_timestamp)
    _CACHE.timestamp = fetched_timestamp
    _CACHE.arrivals = arrivals
    return arrivals


def _format_station_header(station: StationConfig) -> str:
    lines_display = "/".join(station["lines"])
    return f"{station['name'].upper()} ({lines_display})"


def _render_output(stations: Sequence[StationConfig], arrivals: Sequence[Arrival]) -> str:
    arrivals_by_station: Dict[str, List[Arrival]] = {}
    for arrival in arrivals:
        arrivals_by_station.setdefault(arrival["stop_id"], []).append(arrival)

    output_lines: List[str] = []
    output_lines.append("Fetching MTA subway arrivals...")
    output_lines.append(f"Loaded {len(stations)} stations from config.yaml")

    required_feeds = get_required_feeds(stations)
    display_feeds = ", ".join(feed.replace("gtfs-", "").upper() for feed in required_feeds) or "NONE"
    output_lines.append(f"Fetching feeds: {display_feeds}")
    output_lines.append("")
    output_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for station in stations:
        output_lines.append(_format_station_header(station))
        station_arrivals = arrivals_by_station.get(station["stop_id"], [])
        if not station_arrivals:
            output_lines.append("  (no upcoming trains)")
            output_lines.append("")
            continue
        for arrival in station_arrivals:
            output_lines.append(
                f"  {arrival['line']} train → {arrival['minutes_until']} min"
            )
        output_lines.append("")

    output_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    output_lines.append(f"Fetched {len(arrivals)} arrivals")
    if arrivals:
        last_updated = datetime.fromtimestamp(arrivals[0]["timestamp"])
        output_lines.append(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
    return "\n".join(output_lines)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        config = load_config(CONFIG_PATH)
    except Exception as exc:
        logger.error("Failed to load config: %s", exc)
        return

    stations = _extract_stations(config)
    arrivals = fetch_subway_arrivals(config)
    output = _render_output(stations, arrivals)
    print(output)


if __name__ == "__main__":
    main()
