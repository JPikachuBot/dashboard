from __future__ import annotations

import csv
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, TypedDict

import requests
import yaml
from nyct_gtfs import NYCTFeed


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"
STOPS_PATH = ROOT_DIR / "data" / "mta-static" / "stops.txt"

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

UPTOWN_LINES: Set[str] = {
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "A",
    "C",
    "E",
    "B",
    "D",
    "F",
    "M",
    "N",
    "Q",
    "R",
    "W",
}


class Arrival(TypedDict):
    line: str
    station: str
    station_block_id: str
    direction: str
    direction_label: str
    direction_destination: Optional[str]
    minutes_until: int
    route_id: str
    stop_id: str
    timestamp: int


class InboundTrain(TypedDict):
    trip_id: str
    route_id: str
    current_position: str
    wall_st_eta: int
    fulton_st_eta: int
    leave_by: int


class DirectionConfig(TypedDict, total=False):
    code: str
    label: str
    destination: str
    stop_id: str


class StationBlockConfig(TypedDict, total=False):
    id: str
    name: str
    lines: List[str]
    directions: List[DirectionConfig]
    stop_id: str
    direction: str


@dataclass
class ArrivalCandidate:
    arrival_timestamp: int
    line: str
    station: str
    station_block_id: str
    direction: str
    direction_label: str
    direction_destination: Optional[str]
    route_id: str
    stop_id: str


@dataclass(frozen=True)
class DirectionSpec:
    code: str
    label: str
    destination: Optional[str]
    stop_id: str


@dataclass(frozen=True)
class StationBlock:
    id: str
    name: str
    lines: List[str]
    directions: List[DirectionSpec]


@dataclass(frozen=True)
class StationDirection:
    station_block_id: str
    station_name: str
    lines: List[str]
    direction_code: str
    direction_label: str
    direction_destination: Optional[str]
    stop_id: str


@dataclass(frozen=True)
class StopRow:
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    location_type: str
    parent_station: str


@dataclass(frozen=True)
class DestinationSpec:
    name: str
    walk_time_minutes: int


@dataclass(frozen=True)
class InboundTrackerConfig:
    label: str
    routes: Tuple[str, ...]
    direction: str
    north_boundary: str
    south_boundary: str
    destination_stations: Tuple[DestinationSpec, ...]
    max_trains: int


@dataclass
class CacheState:
    timestamp: Optional[int]
    arrivals: List[Arrival]


_CACHE = CacheState(timestamp=None, arrivals=[])


@dataclass
class InboundCacheState:
    timestamp: Optional[int]
    trains: List[InboundTrain]


_INBOUND_CACHE = InboundCacheState(timestamp=None, trains=[])

_STOPS_CACHE: Optional[Dict[str, StopRow]] = None


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


def get_required_feeds(stations: Sequence[StationBlock]) -> List[str]:
    required: Set[str] = set()
    for station in stations:
        for line in station.lines:
            feed = LINE_TO_FEED.get(line)
            if feed is None:
                logger.warning("Unknown line '%s' in config; skipping feed mapping.", line)
                continue
            required.add(feed)
    ordered = [feed for feed in FEED_URLS.keys() if feed in required]
    return ordered


def _get_inbound_required_feeds(
    inbound_config: Optional[InboundTrackerConfig],
) -> List[str]:
    if inbound_config is None:
        return []
    required: Set[str] = set()
    for route in inbound_config.routes:
        feed = LINE_TO_FEED.get(route)
        if feed:
            required.add(feed)
    return [feed for feed in FEED_URLS.keys() if feed in required]


def minutes_until(arrival_timestamp: int, now_timestamp: int) -> int:
    if arrival_timestamp <= now_timestamp:
        return 0
    return max(0, int((arrival_timestamp - now_timestamp) // 60))


def _normalize_station_name(name: str) -> str:
    value = name.strip().lower()
    value = value.replace("–", "-")
    value = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", value)
    replacements = {
        "street": "st",
        "st.": "st",
        "avenue": "av",
        "av.": "av",
        "boulevard": "blvd",
        "road": "rd",
        "square": "sq",
        "center": "ctr",
        "terminal": "term",
        "junction": "jct",
    }
    for word, replacement in replacements.items():
        value = re.sub(rf"\b{re.escape(word)}\b", replacement, value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _load_stops() -> Dict[str, StopRow]:
    global _STOPS_CACHE
    if _STOPS_CACHE is not None:
        return _STOPS_CACHE
    if not STOPS_PATH.exists():
        raise FileNotFoundError(f"Stops file not found: {STOPS_PATH}")
    stops: Dict[str, StopRow] = {}
    with STOPS_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stop_id = row.get("stop_id", "").strip()
            if not stop_id:
                continue
            stops[stop_id] = StopRow(
                stop_id=stop_id,
                stop_name=row.get("stop_name", "").strip(),
                stop_lat=float(row.get("stop_lat", "0") or 0.0),
                stop_lon=float(row.get("stop_lon", "0") or 0.0),
                location_type=row.get("location_type", "").strip(),
                parent_station=row.get("parent_station", "").strip(),
            )
    _STOPS_CACHE = stops
    return stops


def _resolve_stop_ids_by_name(
    stops: Dict[str, StopRow],
    name: str,
    direction: str,
) -> List[str]:
    normalized_target = _normalize_station_name(name)
    suffix = direction.strip().upper()
    if suffix not in {"N", "S"}:
        raise ValueError(f"Unsupported direction suffix: {direction}")
    resolved = [
        stop.stop_id
        for stop in stops.values()
        if stop.location_type != "1"
        and stop.stop_id.endswith(suffix)
        and _normalize_station_name(stop.stop_name) == normalized_target
    ]
    return sorted(resolved)


def _resolve_stop_name(stops: Dict[str, StopRow], stop_id: str) -> Optional[str]:
    stop = stops.get(stop_id)
    return stop.stop_name if stop else None


def _parse_inbound_config(config: dict) -> Optional[InboundTrackerConfig]:
    inbound = config.get("inbound_tracker")
    if not isinstance(inbound, dict):
        return None
    enabled = inbound.get("enabled", True)
    if enabled is False:
        return None
    label = inbound.get("label")
    label_value = label.strip() if isinstance(label, str) and label.strip() else "INBOUND 4/5"
    routes_raw = inbound.get("routes", [])
    if not isinstance(routes_raw, list):
        raise ValueError("Inbound tracker routes must be a list.")
    routes = tuple(
        str(route).strip().upper() for route in routes_raw if str(route).strip()
    )
    if not routes:
        raise ValueError("Inbound tracker routes cannot be empty.")
    direction = str(inbound.get("direction", "S")).strip().upper()
    if direction not in {"N", "S"}:
        raise ValueError("Inbound tracker direction must be 'N' or 'S'.")
    window = inbound.get("tracking_window", {})
    if not isinstance(window, dict):
        raise ValueError("Inbound tracker tracking_window must be a mapping.")
    north = window.get("north_boundary")
    south = window.get("south_boundary")
    if not isinstance(north, str) or not north.strip():
        raise ValueError("Inbound tracker north_boundary must be a string.")
    if not isinstance(south, str) or not south.strip():
        raise ValueError("Inbound tracker south_boundary must be a string.")

    destinations_raw = inbound.get("destination_stations", [])
    if not isinstance(destinations_raw, list):
        raise ValueError("Inbound tracker destination_stations must be a list.")
    destinations: List[DestinationSpec] = []
    for dest in destinations_raw:
        if not isinstance(dest, dict):
            continue
        name = dest.get("name")
        walk_time = dest.get("walk_time_minutes")
        if not isinstance(name, str) or not name.strip():
            continue
        try:
            walk_time_int = int(walk_time)
        except (TypeError, ValueError):
            walk_time_int = 0
        destinations.append(
            DestinationSpec(name=name.strip(), walk_time_minutes=max(0, walk_time_int))
        )

    max_trains = 5
    try:
        max_trains = int(inbound.get("max_trains", 5))
    except (TypeError, ValueError):
        max_trains = 5
    max_trains = max(1, max_trains)

    return InboundTrackerConfig(
        label=label_value,
        routes=routes,
        direction=direction,
        north_boundary=north.strip(),
        south_boundary=south.strip(),
        destination_stations=tuple(destinations),
        max_trains=max_trains,
    )


def _resolve_trip_direction(trip: NYCTFeed.Trip) -> Optional[str]:
    direction = getattr(trip, "direction", None)
    if isinstance(direction, str) and direction.strip():
        return direction.strip().upper()
    direction_id = getattr(trip, "direction_id", None)
    if direction_id in (0, "0"):
        return "N"
    if direction_id in (1, "1"):
        return "S"
    counts = {"N": 0, "S": 0}
    for update in trip.stop_time_updates:
        stop_id = getattr(update, "stop_id", None)
        if not stop_id:
            continue
        suffix = stop_id[-1].upper()
        if suffix in counts:
            counts[suffix] += 1
    if counts["N"] == counts["S"]:
        return None
    return "N" if counts["N"] > counts["S"] else "S"


def _extract_stop_updates(trip: NYCTFeed.Trip) -> List[Tuple[str, int]]:
    updates: List[Tuple[str, int]] = []
    for update in trip.stop_time_updates:
        stop_id = getattr(update, "stop_id", None)
        if not stop_id:
            continue
        arrival_dt = update.arrival or update.departure
        if arrival_dt is None:
            continue
        arrival_ts = int(arrival_dt.timestamp())
        updates.append((stop_id, arrival_ts))
    return updates


def _find_arrival_timestamp(
    stop_updates: Sequence[Tuple[str, int]],
    stop_ids: Set[str],
) -> Optional[int]:
    matched = [arrival_ts for stop_id, arrival_ts in stop_updates if stop_id in stop_ids]
    return min(matched) if matched else None


def _resolve_current_position(
    stops: Dict[str, StopRow],
    stop_updates: Sequence[Tuple[str, int]],
    now_timestamp: int,
) -> str:
    last_stop: Optional[str] = None
    next_stop: Optional[str] = None
    for stop_id, arrival_ts in stop_updates:
        if arrival_ts <= now_timestamp:
            last_stop = stop_id
            continue
        next_stop = stop_id
        break
    if next_stop:
        name = _resolve_stop_name(stops, next_stop) or next_stop
        return f"Approaching {name}"
    if last_stop:
        name = _resolve_stop_name(stops, last_stop) or last_stop
        return f"At {name}"
    return "In transit"


def _is_trip_in_window(
    stop_updates: Sequence[Tuple[str, int]],
    north_ids: Set[str],
    south_ids: Set[str],
    now_timestamp: int,
) -> bool:
    stop_ids = [stop_id for stop_id, _ in stop_updates]
    north_indices = [idx for idx, stop_id in enumerate(stop_ids) if stop_id in north_ids]
    south_indices = [idx for idx, stop_id in enumerate(stop_ids) if stop_id in south_ids]
    if not north_indices or not south_indices:
        return False
    north_index = min(north_indices)
    south_index = max(south_indices)
    if north_index >= south_index:
        return False
    next_index = None
    for idx, (_, arrival_ts) in enumerate(stop_updates):
        if arrival_ts >= now_timestamp:
            next_index = idx
            break
    if next_index is None:
        return False
    return north_index <= next_index <= south_index


def _get_inbound_walk_time(destinations: Iterable[DestinationSpec], name: str) -> int:
    target = _normalize_station_name(name)
    for dest in destinations:
        if _normalize_station_name(dest.name) == target:
            return max(0, dest.walk_time_minutes)
    return 0


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
    stations: Sequence[StationDirection],
    now_timestamp: int,
) -> Dict[int, List[ArrivalCandidate]]:
    candidates_by_station: Dict[int, List[ArrivalCandidate]] = {
        idx: [] for idx in range(len(stations))
    }

    for idx, station in enumerate(stations):
        stop_id = station.stop_id
        if not _is_stop_id_valid(feed, stop_id):
            logger.warning(
                "Invalid stop_id '%s' in feed; skipping station %s.",
                stop_id,
                station.station_name,
            )
            continue

        # NOTE: Do NOT filter by line_id here. Service changes can temporarily route
        # other lines over this stop (e.g., N serving the R/W local). Filtering only
        # by configured lines would hide valid arrivals.
        trips = feed.filter_trips()
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
                        station=station.station_name,
                        station_block_id=station.station_block_id,
                        direction=station.direction_code,
                        direction_label=station.direction_label,
                        direction_destination=station.direction_destination,
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
                    station_block_id=candidate.station_block_id,
                    direction=candidate.direction,
                    direction_label=candidate.direction_label,
                    direction_destination=candidate.direction_destination,
                    minutes_until=minutes_until(candidate.arrival_timestamp, now_timestamp),
                    route_id=candidate.route_id,
                    stop_id=candidate.stop_id,
                    timestamp=fetched_timestamp,
                )
            )
    return results


def _collect_inbound_trains(
    feeds: Dict[str, NYCTFeed],
    inbound_config: InboundTrackerConfig,
    now_timestamp: int,
) -> List[InboundTrain]:
    stops = _load_stops()

    north_ids = set(
        _resolve_stop_ids_by_name(
            stops, inbound_config.north_boundary, inbound_config.direction
        )
    )
    south_ids = set(
        _resolve_stop_ids_by_name(
            stops, inbound_config.south_boundary, inbound_config.direction
        )
    )
    if not north_ids or not south_ids:
        logger.warning("Inbound tracker boundaries could not be resolved.")
        return []

    destination_ids: Dict[str, Set[str]] = {}
    for dest in inbound_config.destination_stations:
        resolved = _resolve_stop_ids_by_name(stops, dest.name, inbound_config.direction)
        if resolved:
            destination_ids[_normalize_station_name(dest.name)] = set(resolved)

    wall_key = _normalize_station_name("Wall St")
    fulton_key = _normalize_station_name("Fulton St")
    wall_ids = destination_ids.get(
        wall_key, set(_resolve_stop_ids_by_name(stops, "Wall St", inbound_config.direction))
    )
    fulton_ids = destination_ids.get(
        fulton_key, set(_resolve_stop_ids_by_name(stops, "Fulton St", inbound_config.direction))
    )
    if not wall_ids or not fulton_ids:
        logger.warning("Inbound tracker destination stops could not be resolved.")
        return []

    wall_walk_time = _get_inbound_walk_time(inbound_config.destination_stations, "Wall St")
    if wall_walk_time <= 0:
        wall_walk_time = 2

    inbound_trains: List[InboundTrain] = []
    seen: Set[Tuple[str, str, int]] = set()

    inbound_feeds = _get_inbound_required_feeds(inbound_config)
    for feed_name in inbound_feeds:
        feed = feeds.get(feed_name)
        if feed is None:
            continue
        for trip in feed.filter_trips():
            route_id = str(getattr(trip, "route_id", "") or "").strip().upper()
            if route_id not in inbound_config.routes:
                continue
            direction = _resolve_trip_direction(trip)
            if direction != inbound_config.direction:
                continue

            stop_updates = _extract_stop_updates(trip)
            if not stop_updates:
                continue
            if not _is_trip_in_window(stop_updates, north_ids, south_ids, now_timestamp):
                continue

            wall_ts = _find_arrival_timestamp(stop_updates, wall_ids)
            fulton_ts = _find_arrival_timestamp(stop_updates, fulton_ids)
            if wall_ts is None or fulton_ts is None:
                continue

            wall_eta = minutes_until(wall_ts, now_timestamp)
            fulton_eta = minutes_until(fulton_ts, now_timestamp)
            trip_id = str(getattr(trip, "trip_id", "") or "").strip()
            if not trip_id:
                continue
            dedupe_key = (trip_id, route_id, wall_ts)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            inbound_trains.append(
                InboundTrain(
                    trip_id=trip_id,
                    route_id=route_id,
                    current_position=_resolve_current_position(
                        stops, stop_updates, now_timestamp
                    ),
                    wall_st_eta=wall_eta,
                    fulton_st_eta=fulton_eta,
                    leave_by=max(0, wall_eta - wall_walk_time),
                )
            )

    inbound_trains.sort(key=lambda train: train["wall_st_eta"])
    return inbound_trains[: inbound_config.max_trains]


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return cleaned.strip("_") or "station"


def _normalize_station_block_id(name: str, lines: List[str], provided: Optional[str]) -> str:
    if isinstance(provided, str) and provided.strip():
        return provided.strip()
    line_key = "_".join(sorted(_slugify(line) for line in lines if line))
    return f"{_slugify(name)}_{line_key}".strip("_")


def _resolve_direction_label(lines: List[str], code: str, provided: Optional[str]) -> str:
    if isinstance(provided, str) and provided.strip():
        return provided.strip()
    direction_code = code.strip().upper()
    normalized_lines = {str(line).strip().upper() for line in lines if str(line).strip()}
    is_uptown = any(line in UPTOWN_LINES for line in normalized_lines)
    if direction_code in {"N", "S"} and is_uptown:
        return "Uptown" if direction_code == "N" else "Downtown"
    if direction_code == "N":
        return "Northbound"
    if direction_code == "S":
        return "Southbound"
    if direction_code == "E":
        return "Eastbound"
    if direction_code == "W":
        return "Westbound"
    return "Unknown direction"


def _extract_station_blocks(config: dict) -> List[StationBlock]:
    subway = config.get("subway")
    if not isinstance(subway, dict):
        raise ValueError("Config missing subway section.")
    stations = subway.get("stations")
    if not isinstance(stations, list):
        raise ValueError("Config subway.stations must be a list.")
    normalized: List[StationBlock] = []
    for station_raw in stations:
        if not isinstance(station_raw, dict):
            raise ValueError("Each station entry must be a mapping.")
        name = station_raw.get("name")
        lines = station_raw.get("lines")
        stop_id = station_raw.get("stop_id")
        direction = station_raw.get("direction")
        directions = station_raw.get("directions")
        if not isinstance(name, str) or not isinstance(lines, list):
            raise ValueError("Station entry missing name or lines.")
        normalized_lines = [str(line).strip() for line in lines if str(line).strip()]
        if not normalized_lines:
            raise ValueError(f"Station {name} missing lines.")

        direction_specs: List[DirectionSpec] = []
        if isinstance(directions, list) and directions:
            for direction_raw in directions:
                if not isinstance(direction_raw, dict):
                    raise ValueError(f"Station {name} has invalid directions entry.")
                code = direction_raw.get("code")
                dir_stop_id = direction_raw.get("stop_id")
                label = direction_raw.get("label")
                destination = direction_raw.get("destination")
                if not isinstance(code, str) or not code.strip():
                    raise ValueError(f"Station {name} direction missing code.")
                if not isinstance(dir_stop_id, str) or not dir_stop_id.strip():
                    raise ValueError(f"Station {name} direction {code} missing stop_id.")
                resolved_label = _resolve_direction_label(normalized_lines, code, label)
                resolved_destination = (
                    destination.strip()
                    if isinstance(destination, str) and destination.strip()
                    else None
                )
                direction_specs.append(
                    DirectionSpec(
                        code=code.strip().upper(),
                        label=resolved_label,
                        destination=resolved_destination,
                        stop_id=dir_stop_id.strip(),
                    )
                )
        elif isinstance(stop_id, str) and stop_id.strip() and isinstance(direction, str) and direction.strip():
            resolved_label = _resolve_direction_label(normalized_lines, direction, None)
            direction_specs.append(
                DirectionSpec(
                    code=direction.strip().upper(),
                    label=resolved_label,
                    destination=None,
                    stop_id=stop_id.strip(),
                )
            )
        else:
            raise ValueError(f"Station {name} missing directions/stop_id configuration.")

        station_block_id = _normalize_station_block_id(
            name,
            normalized_lines,
            station_raw.get("id"),
        )
        normalized.append(
            StationBlock(
                id=station_block_id,
                name=name.strip(),
                lines=normalized_lines,
                directions=direction_specs,
            )
        )
    return normalized


def _expand_station_directions(stations: Sequence[StationBlock]) -> List[StationDirection]:
    expanded: List[StationDirection] = []
    for station in stations:
        for direction in station.directions:
            expanded.append(
                StationDirection(
                    station_block_id=station.id,
                    station_name=station.name,
                    lines=station.lines,
                    direction_code=direction.code,
                    direction_label=direction.label,
                    direction_destination=direction.destination,
                    stop_id=direction.stop_id,
                )
            )
    return expanded


def fetch_subway_arrivals_with_inbound(
    config: dict,
) -> Tuple[List[Arrival], List[InboundTrain]]:
    stations = _extract_station_blocks(config)
    station_directions = _expand_station_directions(stations)
    inbound_config = _parse_inbound_config(config)
    feed_names = get_required_feeds(stations)
    inbound_feeds = _get_inbound_required_feeds(inbound_config)
    if inbound_feeds:
        feed_names = [feed for feed in FEED_URLS.keys() if feed in set(feed_names) | set(inbound_feeds)]
    api_key = os.environ.get("MTA_API_KEY")

    if not api_key:
        logger.info("MTA_API_KEY is not set; fetching feeds without authentication.")

    now_timestamp = int(time.time())
    fetched_timestamp = now_timestamp
    candidates_by_station: Dict[int, List[ArrivalCandidate]] = {
        idx: [] for idx in range(len(station_directions))
    }
    feeds: Dict[str, NYCTFeed] = {}

    try:
        for feed_name in feed_names:
            feed = _fetch_feed(feed_name, api_key, FEED_TIMEOUT_SECONDS)
            feeds[feed_name] = feed
            feed_timestamp = int(feed.last_generated.timestamp())
            if now_timestamp - feed_timestamp > STALE_THRESHOLD_SECONDS:
                raise FeedStaleError(
                    f"Feed {feed_name} is stale: generated at {feed.last_generated}."
                )

            feed_candidates = _collect_candidates(feed, station_directions, now_timestamp)
            for idx, candidates in feed_candidates.items():
                candidates_by_station[idx].extend(candidates)
    except requests.RequestException as exc:
        logger.error("Network error while fetching MTA feed: %s", exc)
        return (
            list(_CACHE.arrivals) if _CACHE.arrivals else [],
            list(_INBOUND_CACHE.trains) if _INBOUND_CACHE.trains else [],
        )
    except FeedStaleError as exc:
        logger.warning("%s Returning cached data if available.", exc)
        return (
            list(_CACHE.arrivals) if _CACHE.arrivals else [],
            list(_INBOUND_CACHE.trains) if _INBOUND_CACHE.trains else [],
        )
    except Exception as exc:  # Explicit catch to keep fetcher resilient
        logger.error("Unexpected error while fetching MTA feed: %s", exc)
        return (
            list(_CACHE.arrivals) if _CACHE.arrivals else [],
            list(_INBOUND_CACHE.trains) if _INBOUND_CACHE.trains else [],
        )

    arrivals = _select_arrivals(candidates_by_station, now_timestamp, fetched_timestamp)
    inbound_trains = (
        _collect_inbound_trains(feeds, inbound_config, now_timestamp)
        if inbound_config is not None
        else []
    )
    _CACHE.timestamp = fetched_timestamp
    _CACHE.arrivals = arrivals
    _INBOUND_CACHE.timestamp = fetched_timestamp
    _INBOUND_CACHE.trains = inbound_trains
    return arrivals, inbound_trains


def fetch_subway_arrivals(config: dict) -> List[Arrival]:
    arrivals, _ = fetch_subway_arrivals_with_inbound(config)
    return arrivals


def _format_station_header(station: StationBlock) -> str:
    lines_display = "/".join(station.lines)
    return f"{station.name.upper()} ({lines_display})"


def _render_output(stations: Sequence[StationBlock], arrivals: Sequence[Arrival]) -> str:
    arrivals_by_station: Dict[str, Dict[str, List[Arrival]]] = {}
    for arrival in arrivals:
        block_id = arrival["station_block_id"]
        direction = arrival["direction"]
        arrivals_by_station.setdefault(block_id, {}).setdefault(direction, []).append(arrival)

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
        station_arrivals = arrivals_by_station.get(station.id, {})
        if not station_arrivals:
            output_lines.append("  (no upcoming trains)")
            output_lines.append("")
            continue
        for direction in station.directions:
            direction_arrivals = station_arrivals.get(direction.code, [])
            output_lines.append(f"  {direction.label}:")
            if not direction_arrivals:
                output_lines.append("    (no upcoming trains)")
                continue
            for arrival in direction_arrivals:
                output_lines.append(
                    f"    {arrival['line']} train → {arrival['minutes_until']} min"
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

    stations = _extract_station_blocks(config)
    arrivals = fetch_subway_arrivals(config)
    output = _render_output(stations, arrivals)
    print(output)


if __name__ == "__main__":
    main()
