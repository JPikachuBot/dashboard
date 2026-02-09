from __future__ import annotations

import argparse
import difflib
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, TypedDict

import requests
import yaml


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"

STATION_INFORMATION_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
STATION_STATUS_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"

REQUEST_TIMEOUT_SECONDS = 10
STALE_THRESHOLD_SECONDS = 300
WALKING_SPEED_MPS = 1.4
METERS_PER_MILE = 1609.34
MINUTES_PER_MILE = METERS_PER_MILE / (WALKING_SPEED_MPS * 60)


class StationConfig(TypedDict):
    name: str
    station_id: str


class StationStatusOutput(TypedDict):
    station_id: str
    name: str
    bikes_available: int
    ebikes_available: int
    docks_available: int
    total_capacity: int
    is_renting: bool
    is_returning: bool
    last_reported: int
    percent_full: int
    distance_miles: Optional[float]
    walk_minutes: Optional[int]


@dataclass(frozen=True)
class StationInfo:
    station_id: str
    name: str
    lat: float
    lon: float
    capacity: int


@dataclass(frozen=True)
class StationStatus:
    station_id: str
    bikes_available: int
    ebikes_available: int
    docks_available: int
    is_renting: bool
    is_returning: bool
    last_reported: int


class CitibikeDataError(RuntimeError):
    pass


def load_config(config_path: Path = CONFIG_PATH) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping.")
    return data


def write_config(config: dict, config_path: Path = CONFIG_PATH) -> None:
    with config_path.open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def fetch_station_information() -> List[StationInfo]:
    try:
        response = requests.get(STATION_INFORMATION_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise CitibikeDataError(f"Failed to fetch station information: {exc}") from exc
    except ValueError as exc:
        raise CitibikeDataError("Station information response was not valid JSON.") from exc

    stations = payload.get("data", {}).get("stations")
    if not isinstance(stations, list):
        raise CitibikeDataError("Station information response missing data.stations list.")

    results: List[StationInfo] = []
    for station in stations:
        try:
            station_id = str(station["station_id"])
            name = str(station["name"])
            lat = float(station["lat"])
            lon = float(station["lon"])
            capacity = int(station.get("capacity", 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise CitibikeDataError("Malformed station information entry.") from exc
        results.append(
            StationInfo(
                station_id=station_id,
                name=name,
                lat=lat,
                lon=lon,
                capacity=capacity,
            )
        )

    return results


def fetch_station_status() -> List[StationStatus]:
    try:
        response = requests.get(STATION_STATUS_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise CitibikeDataError(f"Failed to fetch station status: {exc}") from exc
    except ValueError as exc:
        raise CitibikeDataError("Station status response was not valid JSON.") from exc

    stations = payload.get("data", {}).get("stations")
    if not isinstance(stations, list):
        raise CitibikeDataError("Station status response missing data.stations list.")

    results: List[StationStatus] = []
    for station in stations:
        try:
            station_id = str(station["station_id"])
            bikes_available = int(station.get("num_bikes_available", 0))
            ebikes_available = int(station.get("num_ebikes_available", 0))
            docks_available = int(station.get("num_docks_available", 0))
            is_renting = bool(station.get("is_renting", False))
            is_returning = bool(station.get("is_returning", False))
            last_reported = int(station.get("last_reported", 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise CitibikeDataError("Malformed station status entry.") from exc
        results.append(
            StationStatus(
                station_id=station_id,
                bikes_available=bikes_available,
                ebikes_available=ebikes_available,
                docks_available=docks_available,
                is_renting=is_renting,
                is_returning=is_returning,
                last_reported=last_reported,
            )
        )

    return results


def _normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def _distance_from_location(
    station: StationInfo,
    location: Optional[Mapping[str, float]],
) -> float:
    if not location:
        return float("inf")
    try:
        lat = float(location["lat"])
        lng = float(location["lng"])
    except (KeyError, TypeError, ValueError):
        return float("inf")
    return _haversine_miles(lat, lng, station.lat, station.lon)


def _walk_minutes(distance_miles: float) -> Optional[int]:
    if not math.isfinite(distance_miles):
        return None
    if distance_miles <= 0:
        return 0
    return max(1, int(round(distance_miles * MINUTES_PER_MILE)))


def _select_best_match(
    query: str,
    stations: Sequence[StationInfo],
    location: Optional[Mapping[str, float]],
) -> Optional[StationInfo]:
    normalized_query = _normalize_name(query)
    exact_matches = [
        station
        for station in stations
        if _normalize_name(station.name) == normalized_query
    ]
    if exact_matches:
        exact_matches.sort(key=lambda station: _distance_from_location(station, location))
        return exact_matches[0]

    name_map: Dict[str, List[StationInfo]] = {}
    for station in stations:
        name_map.setdefault(_normalize_name(station.name), []).append(station)

    normalized_names = list(name_map.keys())
    close_matches = difflib.get_close_matches(normalized_query, normalized_names, n=5, cutoff=0.6)
    if not close_matches:
        return None

    candidates: List[Tuple[float, StationInfo]] = []
    for match in close_matches:
        similarity = difflib.SequenceMatcher(None, normalized_query, match).ratio()
        for station in name_map.get(match, []):
            candidates.append((similarity, station))

    if not candidates:
        return None

    max_similarity = max(score for score, _ in candidates)
    top_candidates = [
        station for score, station in candidates if math.isclose(score, max_similarity)
    ]
    top_candidates.sort(key=lambda station: _distance_from_location(station, location))
    return top_candidates[0] if top_candidates else None


def _nearby_stations(
    stations: Sequence[StationInfo],
    location: Optional[Mapping[str, float]],
    limit: int = 3,
) -> List[Tuple[StationInfo, float]]:
    if not location:
        return []
    results = [
        (station, _distance_from_location(station, location))
        for station in stations
    ]
    results.sort(key=lambda pair: pair[1])
    return results[:limit]


def resolve_station_ids(config: dict, interactive: bool = True) -> bool:
    citibike_config = config.get("citibike", {})
    stations_config = citibike_config.get("stations", [])
    if not isinstance(stations_config, list):
        raise ValueError("citibike.stations must be a list in config.yaml")

    unresolved = [
        station
        for station in stations_config
        if not str(station.get("station_id", "")).strip()
        or str(station.get("station_id", "")).strip().upper() == "TBD"
    ]
    if not unresolved:
        return False

    print("Fetching Citibike station information...")
    station_info = fetch_station_information()
    print(f"Found {len(station_info)} stations in NYC\n")

    location = config.get("location") if isinstance(config.get("location"), dict) else None
    updated = False

    for station in unresolved:
        name = str(station.get("name", "")).strip()
        if not name:
            print("Skipping unnamed station entry in config.")
            continue

        print(f"Searching for: \"{name}\"")
        match = _select_best_match(name, station_info, location)
        if match:
            station["station_id"] = match.station_id
            updated = True
            print(f"  [OK] Match found: \"{match.name}\" (ID: {match.station_id})")
            print(f"    Location: {match.lat:.4f}, {match.lon:.4f}")
            print(f"    Capacity: {match.capacity} docks\n")
            continue

        nearby = _nearby_stations(station_info, location)
        if not nearby:
            print("  [WARN] No match found and no location set for nearby suggestions.\n")
            continue

        print("  [WARN] No match found. Nearby stations:")
        for idx, (near_station, distance) in enumerate(nearby, start=1):
            print(
                f"    {idx}. \"{near_station.name}\" ({distance:.2f} mi away, {near_station.capacity} docks)"
            )

        if not interactive:
            print("\n  [WARN] Non-interactive mode; leaving station_id unresolved.\n")
            continue

        selection = input("\nWhich station would you like to use? Enter station name or number [1-3]: ")
        selection = selection.strip()
        chosen: Optional[StationInfo] = None
        if selection.isdigit():
            idx = int(selection)
            if 1 <= idx <= len(nearby):
                chosen = nearby[idx - 1][0]
        else:
            chosen = _select_best_match(selection, station_info, location)

        if chosen:
            station["station_id"] = chosen.station_id
            updated = True
            print(f"\n  [OK] Selected: \"{chosen.name}\" (ID: {chosen.station_id})\n")
        else:
            print("\n  [WARN] Selection not recognized; leaving station_id unresolved.\n")

    if updated:
        write_config(config)
        print("Updated config.yaml with resolved station_ids.\n")
    else:
        print("No station_ids updated.\n")

    return updated


def calculate_percent_full(bikes_available: int, capacity: int) -> int:
    if capacity <= 0:
        return 0
    percent = int(round((bikes_available / capacity) * 100))
    return max(0, min(100, percent))


def fetch_citibike_status(config: dict) -> List[StationStatusOutput]:
    citibike_config = config.get("citibike", {})
    stations_config = citibike_config.get("stations", [])
    if not isinstance(stations_config, list):
        raise ValueError("citibike.stations must be a list in config.yaml")

    station_info = fetch_station_information()
    station_status = fetch_station_status()
    location = config.get("location") if isinstance(config.get("location"), dict) else None

    info_by_id = {station.station_id: station for station in station_info}
    status_by_id = {station.station_id: station for station in station_status}

    results: List[StationStatusOutput] = []

    for station_cfg in stations_config:
        station_id = str(station_cfg.get("station_id", "")).strip()
        if not station_id or station_id.upper() == "TBD":
            print(f"[WARN] Station_id missing for {station_cfg.get('name', 'Unnamed')}; skipping.")
            continue

        info = info_by_id.get(station_id)
        status = status_by_id.get(station_id)
        if status is None:
            print(f"[WARN] Station_id {station_id} not found in live status feed.")
            status = StationStatus(
                station_id=station_id,
                bikes_available=0,
                ebikes_available=0,
                docks_available=0,
                is_renting=False,
                is_returning=False,
                last_reported=0,
            )

        total_bikes = status.bikes_available + status.ebikes_available
        capacity = info.capacity if info else total_bikes + status.docks_available
        name = info.name if info else str(station_cfg.get("name", ""))
        percent_full = calculate_percent_full(total_bikes, capacity)
        distance_miles = (
            _distance_from_location(info, location)
            if info and location
            else float("inf")
        )
        walk_minutes = _walk_minutes(distance_miles)

        results.append(
            {
                "station_id": station_id,
                "name": name,
                "bikes_available": status.bikes_available,
                "ebikes_available": status.ebikes_available,
                "docks_available": status.docks_available,
                "total_capacity": capacity,
                "is_renting": status.is_renting,
                "is_returning": status.is_returning,
                "last_reported": status.last_reported,
                "percent_full": percent_full,
                "distance_miles": None if not math.isfinite(distance_miles) else distance_miles,
                "walk_minutes": walk_minutes,
            }
        )

    def _sort_key(item: StationStatusOutput) -> Tuple[int, float, str]:
        distance = item.get("distance_miles")
        if isinstance(distance, (float, int)) and math.isfinite(distance):
            return (0, float(distance), item["name"].lower())
        return (1, float("inf"), item["name"].lower())

    results.sort(key=_sort_key)
    return results


def _render_bar(percent_full: int, width: int = 14) -> str:
    filled = int(round((percent_full / 100) * width))
    return "#" * filled + "-" * (width - filled)


def _format_age(last_reported: int, now: int) -> str:
    if last_reported <= 0:
        return "unknown"
    delta = max(0, now - last_reported)
    return f"{delta}s ago"


def _print_status(statuses: Sequence[StationStatusOutput]) -> None:
    now = int(time.time())
    print("Fetching Citibike dock status...")
    print(f"Loaded {len(statuses)} stations from config.yaml\n")
    print("=" * 54)

    for station in statuses:
        total_bikes = station["bikes_available"] + station["ebikes_available"]
        percent_full = station["percent_full"]
        bar = _render_bar(percent_full)
        status_flags: List[str] = []
        if not station["is_renting"] and not station["is_returning"]:
            status_flags.append("OUT OF SERVICE")
        else:
            status_flags.append("Renting" if station["is_renting"] else "No rentals")
            status_flags.append("Returning" if station["is_returning"] else "No returns")

        if station["docks_available"] == 0:
            status_flags.append("FULL")
        if total_bikes == 0:
            status_flags.append("EMPTY")

        age = _format_age(station["last_reported"], now)
        stale = (
            station["last_reported"] > 0
            and now - station["last_reported"] > STALE_THRESHOLD_SECONDS
        )

        print(station["name"].upper())
        print(f"  [{bar}]  {percent_full}% full")
        print(f"  Regular bikes:  {station['bikes_available']}")
        print(f"  E-bikes:        {station['ebikes_available']}")
        print(f"  Empty docks:    {station['docks_available']}")
        print(f"  Status: {' | '.join(status_flags)}")
        print(f"  Updated: {age}")
        if stale:
            print("  [WARN] Data is stale (>5 minutes old).")
        print()

    print("=" * 54)


def _needs_resolution(config: dict) -> bool:
    citibike_config = config.get("citibike", {})
    stations_config = citibike_config.get("stations", [])
    if not isinstance(stations_config, list):
        return False
    for station in stations_config:
        station_id = str(station.get("station_id", "")).strip()
        if not station_id or station_id.upper() == "TBD":
            return True
    return False


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Citi Bike dock status.")
    parser.add_argument(
        "--resolve",
        action="store_true",
        help="Resolve station_ids by name and update config.yaml.",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config()
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    try:
        if args.resolve:
            resolve_station_ids(config, interactive=True)
            return 0

        if _needs_resolution(config):
            print("One or more station_ids are missing; running resolution first...\n")
            resolve_station_ids(config, interactive=True)
            config = load_config()

        statuses = fetch_citibike_status(config)
        _print_status(statuses)
    except CitibikeDataError as exc:
        print(f"[ERROR] {exc}")
        return 1
    except KeyboardInterrupt:
        print("\n[ERROR] Interrupted by user.")
        return 1
    except Exception as exc:
        print(f"[ERROR] Unexpected error: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
