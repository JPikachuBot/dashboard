from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml


@dataclass(frozen=True)
class StationSpec:
    name: str
    lines: Tuple[str, ...]
    direction: str
    parent_station: str
    direction_override: Optional[str] = None


@dataclass(frozen=True)
class StopRow:
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float
    location_type: str
    parent_station: str


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config.yaml"
STOPS_PATH = ROOT_DIR / "data" / "mta-static" / "stops.txt"


TARGET_SPECS: List[StationSpec] = [
    StationSpec(name="Wall St", lines=("4", "5"), direction="N", parent_station="419"),
    StationSpec(name="Wall St", lines=("2", "3"), direction="N", parent_station="230"),
    StationSpec(
        name="Broad St",
        lines=("J",),
        direction="W",
        parent_station="M23",
        direction_override="S",
    ),
    StationSpec(name="Rector St", lines=("1",), direction="N", parent_station="139"),
    StationSpec(name="Rector St", lines=("R", "W"), direction="N", parent_station="R26"),
    StationSpec(name="Fulton St", lines=("A", "C"), direction="N", parent_station="A38"),
]


def load_stops(path: Path) -> Dict[str, StopRow]:
    if not path.exists():
        raise FileNotFoundError(f"Stops file not found: {path}")

    stops: Dict[str, StopRow] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            stop_id = row.get("stop_id", "").strip()
            if not stop_id:
                continue
            stop = StopRow(
                stop_id=stop_id,
                stop_name=row.get("stop_name", "").strip(),
                stop_lat=float(row.get("stop_lat", "0") or 0.0),
                stop_lon=float(row.get("stop_lon", "0") or 0.0),
                location_type=row.get("location_type", "").strip(),
                parent_station=row.get("parent_station", "").strip(),
            )
            stops[stop_id] = stop
    return stops


def normalize_lines(lines: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(line.strip() for line in lines))


def resolve_stop_id(spec: StationSpec, stops: Dict[str, StopRow]) -> StopRow:
    suffix = spec.direction_override or spec.direction
    if suffix not in {"N", "S"}:
        raise ValueError(
            f"Unsupported direction suffix for {spec.name} {spec.lines}: {suffix}"
        )

    stop_id = f"{spec.parent_station}{suffix}"
    stop = stops.get(stop_id)
    if stop is None:
        raise KeyError(
            f"Stop ID {stop_id} not found for {spec.name} {spec.lines}."
        )
    if stop.stop_name != spec.name:
        raise ValueError(
            f"Stop ID {stop_id} expected name {spec.name}, got {stop.stop_name}."
        )
    return stop


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping.")
    return data


def update_config(config: dict, resolved: Dict[Tuple[str, Tuple[str, ...]], str]) -> None:
    subway = config.get("subway")
    if not isinstance(subway, dict):
        raise ValueError("Config missing subway section.")
    stations = subway.get("stations")
    if not isinstance(stations, list):
        raise ValueError("Config subway.stations must be a list.")

    for station in stations:
        if not isinstance(station, dict):
            raise ValueError("Each station entry must be a mapping.")
        name = station.get("name")
        lines = station.get("lines")
        if not isinstance(name, str) or not isinstance(lines, list):
            raise ValueError("Station entry missing name or lines.")
        key = (name, normalize_lines(lines))
        if key in resolved:
            station["stop_id"] = resolved[key]


def write_config(path: Path, config: dict) -> None:
    with path.open("w") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)


def format_lines(lines: Iterable[str]) -> str:
    return "/".join(lines)


def main() -> None:
    print("Resolving MTA Stop IDs...\n")

    stops = load_stops(STOPS_PATH)
    config = load_config(CONFIG_PATH)

    resolved: Dict[Tuple[str, Tuple[str, ...]], str] = {}
    summaries: List[str] = []

    for spec in TARGET_SPECS:
        stop = resolve_stop_id(spec, stops)
        key = (spec.name, normalize_lines(spec.lines))
        resolved[key] = stop.stop_id
        lines_display = format_lines(spec.lines)
        summaries.append(
            f"✓ {spec.name} ({lines_display}) → Stop ID: {stop.stop_id} "
            f"({stop.stop_lat:.6f}, {stop.stop_lon:.6f})"
        )

    update_config(config, resolved)
    write_config(CONFIG_PATH, config)

    for line in summaries:
        print(line)

    print("\nConfig file updated: config.yaml")
    print("All stop IDs resolved successfully!")


if __name__ == "__main__":
    main()
