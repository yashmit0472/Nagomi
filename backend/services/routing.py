from math import atan2, ceil, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
import osmnx as ox

from services.safety import road_safety_weight, score_route
from services.traffic import analyze_traffic
from services.transit import build_transit_itinerary


BASE_DIR = Path(__file__).resolve().parent.parent.parent
GRAPH_PATH = BASE_DIR / "data" / "graphs" / "delhi_graph.graphml"

ROAD_SPEEDS_KPH = {
    "motorway": 70,
    "motorway_link": 45,
    "trunk": 60,
    "trunk_link": 40,
    "primary": 45,
    "primary_link": 35,
    "secondary": 35,
    "secondary_link": 30,
    "tertiary": 30,
    "tertiary_link": 25,
    "residential": 22,
    "living_street": 12,
    "service": 15,
    "unclassified": 20,
}

ECO_FACTORS = {
    "motorway": 1.30,
    "motorway_link": 1.20,
    "trunk": 1.18,
    "trunk_link": 1.14,
    "primary": 1.10,
    "primary_link": 1.08,
    "secondary": 1.02,
    "secondary_link": 1.00,
    "tertiary": 0.96,
    "tertiary_link": 0.95,
    "residential": 0.90,
    "living_street": 0.88,
    "service": 0.92,
    "unclassified": 0.94,
}

PROFILES = {
    "fastest": {
        "label": "Fastest",
        "mode": "cab",
        "mode_label": "Cab",
        "color": "#6d5dfc",
        "weight": "travel_time",
        "co2_per_km": 130,
    },
    "cheapest": {
        "label": "Cheapest",
        "mode": "shared_auto",
        "mode_label": "Shared auto",
        "color": "#f4a340",
        "weight": "length",
        "co2_per_km": 55,
    },
    "eco": {
        "label": "Eco Saver",
        "mode": "electric_rickshaw",
        "mode_label": "E-rickshaw",
        "color": "#22a06b",
        "weight": "eco_weight",
        "co2_per_km": 18,
    },
    "safest": {
        "label": "Safest",
        "mode": "cab",
        "mode_label": "Cab",
        "color": "#1687a7",
        "weight": "safe_weight",
        "co2_per_km": 130,
    },
}


def _road_class(value: Any) -> str:
    if isinstance(value, list):
        value = value[0] if value else "unclassified"
    return str(value or "unclassified")


def _parse_speed(value: Any) -> Optional[float]:
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None

    digits = "".join(char for char in str(value) if char.isdigit() or char == ".")
    try:
        speed = float(digits)
    except ValueError:
        return None
    return speed if speed > 0 else None


def _prepare_graph() -> nx.MultiDiGraph:
    graph = ox.load_graphml(str(GRAPH_PATH))
    for _, _, _, data in graph.edges(keys=True, data=True):
        road_class = _road_class(data.get("highway"))
        length = float(data.get("length", 0.0))
        speed_kph = _parse_speed(data.get("maxspeed"))
        if speed_kph is None:
            speed_kph = ROAD_SPEEDS_KPH.get(road_class, 20)

        data["speed_kph"] = speed_kph
        data["travel_time"] = length / (speed_kph * 1000 / 3600)
        data["eco_weight"] = length * ECO_FACTORS.get(road_class, 1.0)
        data["safe_weight"] = road_safety_weight(road_class, length)
    return graph


G = _prepare_graph()
MAX_LOCAL_SNAP_METERS = 1800


def _haversine_meters(first: Dict[str, float], second: Dict[str, float]) -> float:
    radius = 6_371_000
    lat1, lat2 = radians(first["lat"]), radians(second["lat"])
    dlat = radians(second["lat"] - first["lat"])
    dlon = radians(second["lon"] - first["lon"])
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return radius * 2 * atan2(sqrt(value), sqrt(1 - value))


def _nearest_node_with_distance(point: Dict[str, float]) -> Tuple[int, float]:
    node = ox.distance.nearest_nodes(G, point["lon"], point["lat"])
    node_point = {"lat": float(G.nodes[node]["y"]), "lon": float(G.nodes[node]["x"])}
    return node, _haversine_meters(point, node_point)


def _geoapify_fallback(
    source: Dict[str, float],
    destination: Dict[str, float],
    preference: str,
) -> Optional[Dict[str, Any]]:
    from services.geo_routing import build_geoapify_route_plan

    return build_geoapify_route_plan(source, destination, preference)


def _edge_for_weight(u: int, v: int, weight: str) -> Dict[str, Any]:
    edge_data = G.get_edge_data(u, v) or {}
    if not edge_data:
        return {}
    return min(
        edge_data.values(),
        key=lambda edge: float(edge.get(weight, edge.get("length", float("inf")))),
    )


def _route_details(
    route: Sequence[int],
    weight: str,
) -> Tuple[float, float, float, List[Dict[str, float]]]:
    distance = 0.0
    travel_time = 0.0
    safety_weight = 0.0
    coordinates: List[Dict[str, float]] = []

    for u, v in zip(route[:-1], route[1:]):
        edge = _edge_for_weight(u, v, weight)
        if not edge:
            continue

        distance += float(edge.get("length", 0.0))
        travel_time += float(edge.get("travel_time", 0.0))
        safety_weight += float(edge.get("safe_weight", edge.get("length", 0.0)))
        geometry = edge.get("geometry")
        if geometry is not None:
            edge_coordinates = list(geometry.coords)
        else:
            edge_coordinates = [
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"]),
            ]

        for lon, lat in edge_coordinates:
            point = {"lat": float(lat), "lon": float(lon)}
            if not coordinates or coordinates[-1] != point:
                coordinates.append(point)

    return distance, travel_time, safety_weight, coordinates


def _fallback_paths(source_node: int, destination_node: int) -> Iterable[List[int]]:
    simple_graph = nx.DiGraph()
    for u, v, data in G.edges(data=True):
        length = float(data.get("length", float("inf")))
        current = simple_graph.get_edge_data(u, v)
        if current is None or length < current["length"]:
            simple_graph.add_edge(u, v, length=length)

    try:
        paths = nx.shortest_simple_paths(
            simple_graph,
            source_node,
            destination_node,
            weight="length",
        )
        for path in paths:
            yield path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return


def _unique_profile_paths(source_node: int, destination_node: int) -> Dict[str, List[int]]:
    paths: Dict[str, List[int]] = {}
    used: set = set()

    for profile_id, profile in PROFILES.items():
        route = ox.shortest_path(
            G,
            source_node,
            destination_node,
            weight=profile["weight"],
        )
        if route:
            route_tuple = tuple(route)
            if route_tuple not in used:
                paths[profile_id] = route
                used.add(route_tuple)

    if len(paths) < len(PROFILES):
        for route in _fallback_paths(source_node, destination_node):
            route_tuple = tuple(route)
            if route_tuple in used:
                continue
            missing_profile = next(
                profile_id for profile_id in PROFILES if profile_id not in paths
            )
            paths[missing_profile] = route
            used.add(route_tuple)
            if len(paths) == len(PROFILES):
                break

    if not paths:
        return {}

    first_route = next(iter(paths.values()))
    for profile_id in PROFILES:
        paths.setdefault(profile_id, first_route)
    return paths


def _fare(profile_id: str, distance_km: float, duration_minutes: int) -> int:
    if profile_id in {"fastest", "safest"}:
        return int(ceil(45 + distance_km * 14 + duration_minutes * 1.2))
    if profile_id == "cheapest":
        return int(ceil(12 + distance_km * 6))
    return int(ceil(20 + distance_km * 8))


def _duration(profile_id: str, road_seconds: float, distance_km: float) -> int:
    road_minutes = road_seconds / 60
    if profile_id in {"fastest", "safest"}:
        return max(1, int(ceil(road_minutes + 3)))
    if profile_id == "cheapest":
        return max(1, int(ceil(max(road_minutes * 1.35, distance_km / 18 * 60) + 5)))
    return max(1, int(ceil(max(road_minutes * 1.15, distance_km / 24 * 60) + 3)))


def _road_candidate(
    profile_id: str,
    route: Sequence[int],
    source: Dict[str, float],
    destination: Dict[str, float],
) -> Dict[str, Any]:
    profile = PROFILES[profile_id]
    distance, road_seconds, safety_weight, coordinates = _route_details(
        route, profile["weight"]
    )
    distance_km = distance / 1000
    free_flow_minutes = _duration(profile_id, road_seconds, distance_km)
    traffic = analyze_traffic(coordinates)
    duration_minutes = max(
        1,
        int(ceil(free_flow_minutes * float(traffic["delay_multiplier"]))),
    )
    fare = _fare(profile_id, distance_km, duration_minutes)
    co2_grams = int(ceil(distance_km * profile["co2_per_km"]))
    risk_ratio = safety_weight / max(distance, 1)
    infrastructure_score = max(48, min(94, 94 - (risk_ratio - 0.72) * 30))
    safety = score_route(
        [profile["mode"]],
        transfers=0,
        walk_meters=0,
        infrastructure_score=infrastructure_score,
    )

    if coordinates:
        coordinates.insert(0, {"lat": source["lat"], "lon": source["lon"]})
        coordinates.append(
            {"lat": destination["lat"], "lon": destination["lon"]}
        )

    return {
        "kind": "road",
        "duration_minutes": duration_minutes,
        "distance_meters": round(distance, 1),
        "fare_inr": fare,
        "co2_grams": co2_grams,
        "transfers": 0,
        "walk_meters": 0,
        "safety": safety,
        "modes": [profile["mode"]],
        "legs": [
            {
                "mode": profile["mode"],
                "label": profile["mode_label"],
                "line": None,
                "color": profile["color"],
                "from": "Starting point",
                "to": "Destination",
                "duration_minutes": duration_minutes,
                "distance_meters": round(distance, 1),
                "fare_inr": fare,
                "co2_grams": co2_grams,
                "geometry": coordinates,
            }
        ],
        "geometry": coordinates,
        "traffic": traffic,
    }


def _apply_traffic_to_transit(itinerary: Dict[str, Any]) -> Dict[str, Any]:
    for leg in itinerary["legs"]:
        if leg["mode"] not in {"bus", "shared_auto", "electric_rickshaw"}:
            continue
        start = leg["geometry"][0]
        end = leg["geometry"][-1]
        try:
            start_node = ox.distance.nearest_nodes(G, start["lon"], start["lat"])
            end_node = ox.distance.nearest_nodes(G, end["lon"], end["lat"])
            route = ox.shortest_path(G, start_node, end_node, weight="travel_time")
        except (nx.NetworkXNoPath, nx.NodeNotFound, ValueError):
            route = None
        if route:
            _, _, _, coordinates = _route_details(route, "travel_time")
            if coordinates:
                leg["geometry"] = [start, *coordinates, end]

    itinerary["geometry"] = []
    for leg in itinerary["legs"]:
        for point in leg["geometry"]:
            if not itinerary["geometry"] or itinerary["geometry"][-1] != point:
                itinerary["geometry"].append(point)

    traffic = analyze_traffic(itinerary["geometry"])
    added_minutes = 0
    multiplier = float(traffic["delay_multiplier"])
    for leg in itinerary["legs"]:
        if leg["mode"] in {"bus", "shared_auto", "electric_rickshaw"}:
            original = leg["duration_minutes"]
            leg["duration_minutes"] = max(1, int(ceil(original * multiplier)))
            added_minutes += leg["duration_minutes"] - original
    itinerary["duration_minutes"] += added_minutes
    itinerary["traffic"] = traffic
    return itinerary


def _candidate_score(profile_id: str, candidate: Dict[str, Any]) -> float:
    if profile_id == "fastest":
        return candidate["duration_minutes"]
    if profile_id == "cheapest":
        return candidate["fare_inr"] + candidate["duration_minutes"] * 0.08
    if profile_id == "eco":
        return candidate["co2_grams"] + candidate["duration_minutes"] * 0.12
    return -candidate["safety"]["score"] + candidate["duration_minutes"] * 0.035


def _format_option(profile_id: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    profile = PROFILES[profile_id]
    duration_minutes = candidate["duration_minutes"]
    traffic = candidate["traffic"]
    uncertainty = 0.10 if traffic["is_live"] else 0.18
    spread = max(3, int(ceil(duration_minutes * uncertainty)))
    modes = candidate["modes"]
    mode_labels = {
        "walk": "Walk",
        "metro": "Metro",
        "bus": "Bus",
        "cab": "Cab",
        "shared_auto": "Shared auto",
        "electric_rickshaw": "E-rickshaw",
    }
    mode_label = " + ".join(mode_labels.get(mode, mode.title()) for mode in modes)

    return {
        "id": profile_id,
        "label": profile["label"],
        "mode": "multimodal" if len(modes) > 1 else modes[0],
        "mode_label": mode_label,
        "color": profile["color"],
        "duration_minutes": duration_minutes,
        "distance_meters": candidate["distance_meters"],
        "fare_inr": candidate["fare_inr"],
        "co2_grams": candidate["co2_grams"],
        "transfers": candidate["transfers"],
        "walk_meters": candidate["walk_meters"],
        "safety": candidate["safety"],
        "traffic": traffic,
        "reliability": {
            "likely_min": max(1, duration_minutes - spread),
            "likely_max": duration_minutes + spread,
            "high_confidence_max": duration_minutes + spread * 2,
        },
        "summary": "{} via {}".format(
            "Multimodal trip" if len(modes) > 1 else "Direct trip",
            mode_label,
        ),
        "legs": candidate["legs"],
        "geometry": candidate["geometry"],
        "data_quality": "live" if traffic["is_live"] else "modeled_and_scheduled",
    }


def build_route_plan(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float,
    preference: str = "fastest",
) -> Dict[str, Any]:
    source = {"lat": source_lat, "lon": source_lon}
    destination = {"lat": dest_lat, "lon": dest_lon}
    source_node, source_snap = _nearest_node_with_distance(source)
    destination_node, destination_snap = _nearest_node_with_distance(destination)

    if max(source_snap, destination_snap) > MAX_LOCAL_SNAP_METERS:
        external_plan = _geoapify_fallback(source, destination, preference)
        if external_plan is not None:
            return external_plan
        return {
            "success": False,
            "message": (
                "This location is outside Nagomi's bundled road graph. "
                "Configure GEOAPIFY_API_KEY or choose a point closer to central Delhi."
            ),
            "routes": [],
            "coverage": {
                "source_snap_meters": round(source_snap),
                "destination_snap_meters": round(destination_snap),
            },
        }

    paths = _unique_profile_paths(source_node, destination_node)

    if not paths:
        external_plan = _geoapify_fallback(source, destination, preference)
        if external_plan is not None:
            return external_plan
        return {
            "success": False,
            "message": (
                "No connected local road route was found. Try a nearby search result "
                "or configure Geoapify whole-Delhi routing."
            ),
            "routes": [],
        }

    routes = []
    for profile_id in PROFILES:
        road_candidate = _road_candidate(
            profile_id,
            paths[profile_id],
            source,
            destination,
        )
        transit_candidate = build_transit_itinerary(
            source,
            destination,
            profile_id,
        )
        candidates = [road_candidate]
        if transit_candidate is not None:
            candidates.append(_apply_traffic_to_transit(transit_candidate))
        selected = min(
            candidates,
            key=lambda candidate: _candidate_score(profile_id, candidate),
        )
        routes.append(_format_option(profile_id, selected))

    preference_order = {
        "fastest": "fastest",
        "cheapest": "cheapest",
        "eco": "eco",
        "safest": "safest",
    }
    recommended = preference_order.get(preference, "fastest")
    routes.sort(key=lambda route: route["id"] != recommended)

    return {
        "success": True,
        "source": source,
        "destination": destination,
        "recommended_route_id": recommended,
        "routes": routes,
        "routing_mode": "multimodal_graph",
        "coverage": {
            "source_snap_meters": round(source_snap),
            "destination_snap_meters": round(destination_snap),
        },
        "notice": (
            "Metro and bus times use the local scheduled transit graph. Traffic uses "
            "TomTom live flow when TOMTOM_API_KEY is configured, otherwise a clearly "
            "labeled time-aware Delhi model. Safety is an infrastructure proxy, not a "
            "crime guarantee."
        ),
    }


def get_route(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float,
) -> Dict[str, Any]:
    """Keep the original single-route contract available for older clients."""
    plan = build_route_plan(source_lat, source_lon, dest_lat, dest_lon)
    if not plan["success"]:
        return plan

    route = next(option for option in plan["routes"] if option["id"] == "fastest")
    return {
        "success": True,
        "distance_meters": route["distance_meters"],
        "route": route["geometry"],
        "route_nodes": len(route["geometry"]),
    }
