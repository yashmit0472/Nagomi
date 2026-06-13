import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from math import ceil
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx

from services.places import GEOAPIFY_API_KEY
from services.safety import score_route


GEOAPIFY_ROUTING_URL = "https://api.geoapify.com/v1/routing"

PROFILE_META = {
    "fastest": {"label": "Fastest", "color": "#6d5dfc"},
    "cheapest": {"label": "Cheapest", "color": "#f4a340"},
    "eco": {"label": "Eco Saver", "color": "#22a06b"},
    "safest": {"label": "Safest", "color": "#1687a7"},
}

MODE_COLORS = {
    "walk": "#697386",
    "metro": "#3578d4",
    "bus": "#e07b39",
    "cab": "#6d5dfc",
}


def routing_available() -> bool:
    return bool(GEOAPIFY_API_KEY)


def _flatten_coordinates(value: Any) -> List[List[float]]:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and all(isinstance(item, (int, float)) for item in value[:2])
    ):
        return [value]
    flattened = []
    if isinstance(value, list):
        for item in value:
            flattened.extend(_flatten_coordinates(item))
    return flattened


def _route_mode(instruction: str) -> str:
    lower = instruction.lower()
    if lower.startswith("take the "):
        if "line" in lower or "aex" in lower or "metro" in lower:
            return "metro"
        return "bus"
    return "walk"


def _line_label(instruction: str, mode: str) -> str:
    if mode == "walk":
        return "Walk"
    match = re.match(r"Take the (.+?) toward", instruction, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Metro" if mode == "metro" else "Bus"


def _station_name(instruction: str, action: str) -> Optional[str]:
    match = re.search(
        r"\b{} (?:the )?(.+?)(?: Station)?\.?$".format(action),
        instruction.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    name = re.sub(r"\s+Station$", "", match.group(1).strip(), flags=re.IGNORECASE)
    return "{} Station".format(name)


def _points_between(
    points: Sequence[Dict[str, float]],
    first: int,
    last: int,
) -> List[Dict[str, float]]:
    if not points:
        return []
    start = max(0, min(first, len(points) - 1))
    end = max(start, min(last, len(points) - 1))
    return list(points[start : end + 1])


def _build_legs(
    steps: Iterable[Dict[str, Any]],
    points: Sequence[Dict[str, float]],
) -> List[Dict[str, Any]]:
    legs: List[Dict[str, Any]] = []
    walking_steps: List[Dict[str, Any]] = []
    current_place = "Starting point"
    pending_transit_index: Optional[int] = None
    pending_enter_station: Optional[str] = None

    def step_values(step: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "distance": float(step.get("distance", 0)),
            "duration": float(step.get("time", 0)) / 60,
            "geometry": _points_between(
                points,
                int(step.get("from_index", 0)),
                int(step.get("to_index", 0)),
            ),
        }

    def append_geometry(
        target: List[Dict[str, float]],
        additions: Iterable[Dict[str, float]],
    ) -> None:
        for point in additions:
            if not target or target[-1] != point:
                target.append(point)

    def flush_walking(destination_name: str) -> None:
        nonlocal current_place
        if not walking_steps:
            current_place = destination_name
            return

        geometry: List[Dict[str, float]] = []
        distance = 0.0
        duration = 0.0
        for walking_step in walking_steps:
            values = step_values(walking_step)
            distance += values["distance"]
            duration += values["duration"]
            append_geometry(geometry, values["geometry"])

        legs.append(
            {
                "mode": "walk",
                "label": "Walk",
                "line": None,
                "color": MODE_COLORS["walk"],
                "from": current_place,
                "to": destination_name,
                "duration_minutes": duration,
                "distance_meters": distance,
                "fare_inr": 0,
                "co2_grams": 0,
                "geometry": geometry,
            }
        )
        walking_steps.clear()
        current_place = destination_name

    for step in steps:
        instruction = str(step.get("instruction", {}).get("text", "Continue"))
        if "arrived at your destination" in instruction.lower():
            continue

        enter_station = _station_name(instruction, "Enter")
        exit_station = _station_name(instruction, "Exit")
        mode = _route_mode(instruction)

        if enter_station:
            walking_steps.append(step)
            pending_enter_station = enter_station
            continue

        if mode in {"metro", "bus"}:
            label = _line_label(instruction, mode)
            if pending_enter_station:
                flush_walking(
                    "{} - {} platform".format(pending_enter_station, label)
                )
                pending_enter_station = None
            elif walking_steps:
                flush_walking("{} boarding point".format(_line_label(instruction, mode)))
            values = step_values(step)
            legs.append(
                {
                    "mode": mode,
                    "label": label,
                    "line": label,
                    "color": MODE_COLORS[mode],
                    "from": current_place,
                    "to": "Destination",
                    "duration_minutes": values["duration"],
                    "distance_meters": values["distance"],
                    "fare_inr": 0,
                    "co2_grams": 0,
                    "geometry": values["geometry"],
                }
            )
            pending_transit_index = len(legs) - 1
            continue

        if exit_station and pending_transit_index is not None:
            values = step_values(step)
            transit_leg = legs[pending_transit_index]
            transit_leg["to"] = exit_station
            transit_leg["duration_minutes"] += values["duration"]
            transit_leg["distance_meters"] += values["distance"]
            append_geometry(transit_leg["geometry"], values["geometry"])
            current_place = exit_station
            pending_transit_index = None
            continue

        walking_steps.append(step)

    if pending_transit_index is not None:
        legs[pending_transit_index]["to"] = "Destination"
        current_place = "Destination"
    elif pending_enter_station is not None:
        flush_walking(pending_enter_station)
        flush_walking("Destination")
    else:
        flush_walking("Destination")

    for leg in legs:
        leg["duration_minutes"] = max(1, int(ceil(leg["duration_minutes"])))
        leg["distance_meters"] = round(leg["distance_meters"], 1)
        if leg["mode"] == "metro":
            leg["fare_inr"] = max(10, int(ceil(10 + leg["distance_meters"] / 1000 * 2.4)))
            leg["co2_grams"] = int(ceil(leg["distance_meters"] / 1000 * 12))
        elif leg["mode"] == "bus":
            leg["fare_inr"] = 15 if leg["distance_meters"] < 8000 else 25
            leg["co2_grams"] = int(ceil(leg["distance_meters"] / 1000 * 55))
    return legs


@lru_cache(maxsize=128)
def _request_route(
    source_lat: float,
    source_lon: float,
    destination_lat: float,
    destination_lon: float,
    mode: str,
    route_type: str,
) -> Dict[str, Any]:
    response = httpx.get(
        GEOAPIFY_ROUTING_URL,
        params={
            "waypoints": "{},{}|{},{}".format(
                source_lat,
                source_lon,
                destination_lat,
                destination_lon,
            ),
            "mode": mode,
            "type": route_type,
            "traffic": "approximated",
            "format": "geojson",
            "lang": "en",
            "apiKey": GEOAPIFY_API_KEY,
        },
        timeout=15.0,
    )
    response.raise_for_status()
    features = response.json().get("features", [])
    if not features:
        raise ValueError("Geoapify did not return a route.")
    return features[0]


def _route_candidate(
    source: Dict[str, float],
    destination: Dict[str, float],
    mode: str,
    route_type: str = "balanced",
) -> Dict[str, Any]:
    feature = _request_route(
        round(source["lat"], 6),
        round(source["lon"], 6),
        round(destination["lat"], 6),
        round(destination["lon"], 6),
        mode,
        route_type,
    )
    properties = feature["properties"]
    raw_coordinates = _flatten_coordinates(feature["geometry"]["coordinates"])
    geometry = [
        {"lat": float(coordinate[1]), "lon": float(coordinate[0])}
        for coordinate in raw_coordinates
    ]
    steps = [
        step
        for leg in properties.get("legs", [])
        for step in leg.get("steps", [])
    ]

    if mode == "drive":
        distance = float(properties.get("distance", 0))
        duration = max(1, int(ceil(float(properties.get("time", 0)) / 60)))
        legs = [
            {
                "mode": "cab",
                "label": "Cab",
                "line": None,
                "color": MODE_COLORS["cab"],
                "from": "Starting point",
                "to": "Destination",
                "duration_minutes": duration,
                "distance_meters": round(distance, 1),
                "fare_inr": int(ceil(45 + distance / 1000 * 14 + duration * 1.2)),
                "co2_grams": int(ceil(distance / 1000 * 130)),
                "geometry": geometry,
            }
        ]
        modes = ["cab"]
    else:
        legs = _build_legs(steps, geometry)
        modes = list(dict.fromkeys(leg["mode"] for leg in legs))

    transit_legs = [leg for leg in legs if leg["mode"] in {"metro", "bus"}]
    transfers = max(0, len(transit_legs) - 1)
    walk_meters = sum(leg["distance_meters"] for leg in legs if leg["mode"] == "walk")
    distance = float(properties.get("distance", sum(leg["distance_meters"] for leg in legs)))
    duration = max(1, int(ceil(float(properties.get("time", 0)) / 60)))
    safety = score_route(
        modes,
        transfers,
        walk_meters,
        infrastructure_score=86 if mode == "drive" else 82,
    )
    return {
        "duration_minutes": duration,
        "distance_meters": round(distance, 1),
        "fare_inr": sum(leg["fare_inr"] for leg in legs),
        "co2_grams": sum(leg["co2_grams"] for leg in legs),
        "transfers": transfers,
        "walk_meters": round(walk_meters, 1),
        "safety": safety,
        "modes": modes,
        "legs": legs,
        "geometry": geometry,
        "traffic": {
            "source": "geoapify_approximated",
            "is_live": False,
            "level": "traffic-aware",
            "delay_multiplier": 1.0,
            "current_speed_kph": round(distance / 1000 / (duration / 60), 1),
            "free_flow_speed_kph": 0,
            "confidence": 0.72,
            "incidents": [],
            "updated_at": "",
        },
    }


def _format_option(profile_id: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    meta = PROFILE_META[profile_id]
    duration = candidate["duration_minutes"]
    spread = max(4, int(ceil(duration * 0.16)))
    labels = {
        "walk": "Walk",
        "metro": "Metro",
        "bus": "Bus",
        "cab": "Cab",
    }
    mode_label = " + ".join(labels.get(mode, mode.title()) for mode in candidate["modes"])
    return {
        "id": profile_id,
        "label": meta["label"],
        "mode": "multimodal" if len(candidate["modes"]) > 1 else candidate["modes"][0],
        "mode_label": mode_label,
        "color": meta["color"],
        **candidate,
        "reliability": {
            "likely_min": max(1, duration - spread),
            "likely_max": duration + spread,
            "high_confidence_max": duration + spread * 2,
        },
        "summary": "Whole-Delhi route via {}".format(mode_label),
        "data_quality": "geoapify_approximated",
    }


def build_geoapify_route_plan(
    source: Dict[str, float],
    destination: Dict[str, float],
    preference: str,
) -> Optional[Dict[str, Any]]:
    if not routing_available():
        return None
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            drive_future = executor.submit(
                _route_candidate,
                source,
                destination,
                "drive",
            )
            safe_future = executor.submit(
                _route_candidate,
                source,
                destination,
                "drive",
                "less_maneuvers",
            )
            transit_future = executor.submit(
                _route_candidate,
                source,
                destination,
                "approximated_transit",
            )
            drive = drive_future.result()
            safe_drive = safe_future.result()
            transit = transit_future.result()
    except (httpx.HTTPError, KeyError, TypeError, ValueError, IndexError):
        return None

    fastest = min([drive, transit], key=lambda candidate: candidate["duration_minutes"])
    cheapest = min([drive, transit], key=lambda candidate: candidate["fare_inr"])
    eco = min([drive, transit], key=lambda candidate: candidate["co2_grams"])
    safest = max(
        [safe_drive, transit],
        key=lambda candidate: (
            candidate["safety"]["score"],
            -candidate["duration_minutes"],
        ),
    )
    routes = [
        _format_option("fastest", fastest),
        _format_option("cheapest", cheapest),
        _format_option("eco", eco),
        _format_option("safest", safest),
    ]
    recommended = preference if preference in PROFILE_META else "fastest"
    routes.sort(key=lambda route: route["id"] != recommended)
    return {
        "success": True,
        "source": source,
        "destination": destination,
        "recommended_route_id": recommended,
        "routes": routes,
        "routing_mode": "geoapify_whole_delhi",
        "notice": (
            "This trip is outside the bundled local road graph, so Nagomi used "
            "Geoapify for whole-Delhi road geometry and approximated transit."
        ),
    }
