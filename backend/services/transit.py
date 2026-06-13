from math import atan2, ceil, cos, radians, sin, sqrt
from typing import Any, Dict, List, Optional, Sequence, Tuple

import networkx as nx

from services.safety import score_route


STOPS: Dict[str, Dict[str, Any]] = {
    "kashmere_gate": {"name": "Kashmere Gate", "lat": 28.6675, "lon": 77.2280},
    "lal_qila": {"name": "Lal Qila", "lat": 28.6567, "lon": 77.2360},
    "jama_masjid": {"name": "Jama Masjid", "lat": 28.6500, "lon": 77.2370},
    "new_delhi": {"name": "New Delhi", "lat": 28.6431, "lon": 77.2197},
    "rajiv_chowk": {"name": "Rajiv Chowk", "lat": 28.6328, "lon": 77.2197},
    "shivaji_stadium": {"name": "Shivaji Stadium", "lat": 28.6290, "lon": 77.2115},
    "patel_chowk": {"name": "Patel Chowk", "lat": 28.6230, "lon": 77.2144},
    "central_secretariat": {"name": "Central Secretariat", "lat": 28.6147, "lon": 77.2119},
    "india_gate": {"name": "India Gate", "lat": 28.6129, "lon": 77.2295},
    "mandi_house": {"name": "Mandi House", "lat": 28.6259, "lon": 77.2343},
    "ito": {"name": "ITO", "lat": 28.6288, "lon": 77.2410},
    "supreme_court": {"name": "Supreme Court", "lat": 28.6234, "lon": 77.2425},
    "indraprastha": {"name": "Indraprastha", "lat": 28.6206, "lon": 77.2495},
    "yamuna_bank": {"name": "Yamuna Bank", "lat": 28.6233, "lon": 77.2678},
    "akshardham": {"name": "Akshardham", "lat": 28.6180, "lon": 77.2798},
    "udyog_bhawan": {"name": "Udyog Bhawan", "lat": 28.6110, "lon": 77.2120},
    "lok_kalyan": {"name": "Lok Kalyan Marg", "lat": 28.5975, "lon": 77.2091},
    "jor_bagh": {"name": "Jor Bagh", "lat": 28.5860, "lon": 77.2121},
    "ina": {"name": "Dilli Haat INA", "lat": 28.5740, "lon": 77.2093},
    "aiims": {"name": "AIIMS", "lat": 28.5680, "lon": 77.2077},
    "green_park": {"name": "Green Park", "lat": 28.5580, "lon": 77.2067},
    "hauz_khas": {"name": "Hauz Khas", "lat": 28.5433, "lon": 77.2060},
    "malviya_nagar": {"name": "Malviya Nagar", "lat": 28.5286, "lon": 77.2055},
    "saket": {"name": "Saket", "lat": 28.5206, "lon": 77.2014},
    "qutub_minar": {"name": "Qutub Minar", "lat": 28.5130, "lon": 77.1869},
    "dhaula_kuan": {"name": "Dhaula Kuan", "lat": 28.5918, "lon": 77.1616},
    "aerocity": {"name": "Delhi Aerocity", "lat": 28.5488, "lon": 77.1209},
    "airport_t3": {"name": "IGI Airport T3", "lat": 28.5562, "lon": 77.1000},
    "delhi_gate": {"name": "Delhi Gate", "lat": 28.6392, "lon": 77.2407},
    "janpath": {"name": "Janpath", "lat": 28.6251, "lon": 77.2197},
    "khan_market": {"name": "Khan Market", "lat": 28.6000, "lon": 77.2262},
    "jln_stadium": {"name": "JLN Stadium", "lat": 28.5903, "lon": 77.2331},
    "lajpat_nagar": {"name": "Lajpat Nagar", "lat": 28.5708, "lon": 77.2365},
    "kalkaji": {"name": "Kalkaji Mandir", "lat": 28.5496, "lon": 77.2590},
    "lotus_temple": {"name": "Lotus Temple", "lat": 28.5535, "lon": 77.2588},
    "connaught_place": {"name": "Connaught Place", "lat": 28.6315, "lon": 77.2167},
    "red_fort": {"name": "Red Fort", "lat": 28.6562, "lon": 77.2410},
}

LINES = [
    {
        "name": "Yellow Line",
        "mode": "metro",
        "color": "#e4b523",
        "stops": [
            "kashmere_gate", "new_delhi", "rajiv_chowk", "patel_chowk",
            "central_secretariat", "udyog_bhawan", "lok_kalyan", "jor_bagh",
            "ina", "aiims", "green_park", "hauz_khas", "malviya_nagar",
            "saket", "qutub_minar",
        ],
    },
    {
        "name": "Blue Line",
        "mode": "metro",
        "color": "#3578d4",
        "stops": [
            "rajiv_chowk", "mandi_house", "supreme_court", "indraprastha",
            "yamuna_bank", "akshardham",
        ],
    },
    {
        "name": "Violet Line",
        "mode": "metro",
        "color": "#7b4bb7",
        "stops": [
            "kashmere_gate", "lal_qila", "jama_masjid", "delhi_gate", "ito",
            "mandi_house", "janpath", "central_secretariat", "khan_market",
            "jln_stadium", "lajpat_nagar", "kalkaji",
        ],
    },
    {
        "name": "Airport Express",
        "mode": "metro",
        "color": "#e66b72",
        "stops": ["new_delhi", "shivaji_stadium", "dhaula_kuan", "aerocity", "airport_t3"],
        "speed_kph": 48,
    },
    {
        "name": "Bus 522",
        "mode": "bus",
        "color": "#e07b39",
        "stops": [
            "new_delhi", "connaught_place", "india_gate", "jor_bagh", "ina",
            "aiims", "green_park", "hauz_khas", "saket",
        ],
    },
    {
        "name": "Bus 729",
        "mode": "bus",
        "color": "#cc5f43",
        "stops": ["new_delhi", "connaught_place", "dhaula_kuan", "aerocity", "airport_t3"],
    },
    {
        "name": "Bus 419",
        "mode": "bus",
        "color": "#d38b2f",
        "stops": [
            "kashmere_gate", "red_fort", "jama_masjid", "delhi_gate", "ito",
            "indraprastha", "akshardham",
        ],
    },
    {
        "name": "Bus 543",
        "mode": "bus",
        "color": "#bc6c35",
        "stops": [
            "connaught_place", "mandi_house", "india_gate", "khan_market",
            "jln_stadium", "lajpat_nagar", "kalkaji", "lotus_temple",
        ],
    },
]

PROFILE_WEIGHTS = {
    "fastest": "duration_weight",
    "cheapest": "cost_weight",
    "eco": "carbon_weight",
    "safest": "safety_weight",
}


def haversine_meters(a: Dict[str, float], b: Dict[str, float]) -> float:
    radius = 6_371_000
    lat1, lat2 = radians(a["lat"]), radians(b["lat"])
    dlat = radians(b["lat"] - a["lat"])
    dlon = radians(b["lon"] - a["lon"])
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return radius * 2 * atan2(sqrt(value), sqrt(1 - value))


def _build_graph() -> nx.MultiGraph:
    graph = nx.MultiGraph()
    for stop_id, stop in STOPS.items():
        graph.add_node(stop_id, **stop)

    for line in LINES:
        speed = line.get("speed_kph", 34 if line["mode"] == "metro" else 19)
        for first, second in zip(line["stops"][:-1], line["stops"][1:]):
            distance = haversine_meters(STOPS[first], STOPS[second])
            minutes = distance / (speed * 1000 / 60)
            if line["mode"] == "metro":
                minutes += 0.65
                safety_weight = distance * 0.58
                carbon_weight = distance * 0.012
                cost_weight = distance * 0.018
            else:
                minutes += 1.2
                safety_weight = distance * 0.82
                carbon_weight = distance * 0.055
                cost_weight = distance * 0.010

            graph.add_edge(
                first,
                second,
                key=line["name"],
                mode=line["mode"],
                line=line["name"],
                color=line["color"],
                distance_meters=distance,
                duration_minutes=minutes,
                duration_weight=minutes,
                cost_weight=cost_weight,
                carbon_weight=carbon_weight,
                safety_weight=safety_weight,
            )
    return graph


TRANSIT_GRAPH = _build_graph()


def transit_available() -> bool:
    return TRANSIT_GRAPH.number_of_nodes() > 0


def _edge_for_weight(first: str, second: str, weight: str) -> Dict[str, Any]:
    edge_data = TRANSIT_GRAPH.get_edge_data(first, second) or {}
    return min(edge_data.values(), key=lambda edge: float(edge[weight]))


def _nearest_stops(point: Dict[str, float], count: int = 5) -> List[Tuple[str, float]]:
    ranked = [
        (stop_id, haversine_meters(point, stop))
        for stop_id, stop in STOPS.items()
    ]
    return sorted(ranked, key=lambda item: item[1])[:count]


def _access_mode(profile_id: str, distance: float) -> str:
    thresholds = {"fastest": 450, "cheapest": 1500, "eco": 2000, "safest": 350}
    if distance <= thresholds[profile_id]:
        return "walk"
    return "electric_rickshaw" if profile_id in {"fastest", "eco", "safest"} else "shared_auto"


def _road_leg(
    mode: str,
    start: Dict[str, float],
    end: Dict[str, float],
    start_name: str,
    end_name: str,
) -> Dict[str, Any]:
    distance = haversine_meters(start, end) * 1.18
    speed = {"walk": 4.8, "electric_rickshaw": 22, "shared_auto": 18}[mode]
    duration = distance / (speed * 1000 / 60)
    if mode != "walk":
        duration += 2
    fare = 0
    co2 = 0
    if mode == "electric_rickshaw":
        fare = ceil(18 + distance / 1000 * 8)
        co2 = ceil(distance / 1000 * 18)
    elif mode == "shared_auto":
        fare = ceil(10 + distance / 1000 * 6)
        co2 = ceil(distance / 1000 * 55)
    return {
        "mode": mode,
        "label": "Walk" if mode == "walk" else (
            "E-rickshaw" if mode == "electric_rickshaw" else "Shared auto"
        ),
        "line": None,
        "color": "#697386" if mode == "walk" else "#22a06b",
        "from": start_name,
        "to": end_name,
        "duration_minutes": max(1, ceil(duration)),
        "distance_meters": round(distance, 1),
        "fare_inr": fare,
        "co2_grams": co2,
        "geometry": [
            {"lat": start["lat"], "lon": start["lon"]},
            {"lat": end["lat"], "lon": end["lon"]},
        ],
    }


def _transit_legs(path: Sequence[str], profile_id: str) -> List[Dict[str, Any]]:
    weight = PROFILE_WEIGHTS[profile_id]
    raw = []
    for first, second in zip(path[:-1], path[1:]):
        edge = _edge_for_weight(first, second, weight)
        raw.append((first, second, edge))

    grouped: List[Dict[str, Any]] = []
    for first, second, edge in raw:
        if grouped and grouped[-1]["line"] == edge["line"] and grouped[-1]["mode"] == edge["mode"]:
            leg = grouped[-1]
            leg["to"] = STOPS[second]["name"]
            leg["duration_minutes"] += edge["duration_minutes"]
            leg["distance_meters"] += edge["distance_meters"]
            leg["geometry"].append({"lat": STOPS[second]["lat"], "lon": STOPS[second]["lon"]})
        else:
            grouped.append(
                {
                    "mode": edge["mode"],
                    "label": edge["line"],
                    "line": edge["line"],
                    "color": edge["color"],
                    "from": STOPS[first]["name"],
                    "to": STOPS[second]["name"],
                    "duration_minutes": edge["duration_minutes"],
                    "distance_meters": edge["distance_meters"],
                    "fare_inr": 0,
                    "co2_grams": 0,
                    "geometry": [
                        {"lat": STOPS[first]["lat"], "lon": STOPS[first]["lon"]},
                        {"lat": STOPS[second]["lat"], "lon": STOPS[second]["lon"]},
                    ],
                }
            )

    for leg in grouped:
        leg["duration_minutes"] = max(1, ceil(leg["duration_minutes"]))
        distance_km = leg["distance_meters"] / 1000
        if leg["mode"] == "metro":
            leg["fare_inr"] = max(10, ceil(10 + distance_km * 2.4))
            leg["co2_grams"] = ceil(distance_km * 12)
        else:
            leg["fare_inr"] = 15 if distance_km < 8 else 25
            leg["co2_grams"] = ceil(distance_km * 55)
    return grouped


def _path_score(
    source_distance: float,
    destination_distance: float,
    path: Sequence[str],
    profile_id: str,
) -> float:
    weight = PROFILE_WEIGHTS[profile_id]
    network_score = 0.0
    for first, second in zip(path[:-1], path[1:]):
        network_score += float(_edge_for_weight(first, second, weight)[weight])

    access = source_distance + destination_distance
    if profile_id == "fastest":
        return network_score + access / 250
    if profile_id == "cheapest":
        return network_score + access * 0.012
    if profile_id == "eco":
        return network_score + access * 0.01
    return network_score + access * 1.15


def build_transit_itinerary(
    source: Dict[str, float],
    destination: Dict[str, float],
    profile_id: str,
) -> Optional[Dict[str, Any]]:
    weight = PROFILE_WEIGHTS[profile_id]
    best = None
    for start_id, start_distance in _nearest_stops(source):
        for end_id, end_distance in _nearest_stops(destination):
            if start_id == end_id:
                continue
            try:
                path = nx.shortest_path(TRANSIT_GRAPH, start_id, end_id, weight=weight)
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            score = _path_score(start_distance, end_distance, path, profile_id)
            if best is None or score < best["score"]:
                best = {
                    "score": score,
                    "path": path,
                    "start_distance": start_distance,
                    "end_distance": end_distance,
                }

    if best is None:
        return None

    start_stop = STOPS[best["path"][0]]
    end_stop = STOPS[best["path"][-1]]
    access_mode = _access_mode(profile_id, best["start_distance"])
    egress_mode = _access_mode(profile_id, best["end_distance"])
    legs = [
        _road_leg(access_mode, source, start_stop, "Starting point", start_stop["name"]),
        *_transit_legs(best["path"], profile_id),
        _road_leg(egress_mode, end_stop, destination, end_stop["name"], "Destination"),
    ]

    modes = [leg["mode"] for leg in legs]
    transfers = max(0, len([leg for leg in legs if leg["mode"] in {"metro", "bus"}]) - 1)
    walk_meters = sum(leg["distance_meters"] for leg in legs if leg["mode"] == "walk")
    safety = score_route(modes, transfers, walk_meters)
    geometry = []
    for leg in legs:
        for point in leg["geometry"]:
            if not geometry or geometry[-1] != point:
                geometry.append(point)

    return {
        "kind": "multimodal",
        "duration_minutes": sum(leg["duration_minutes"] for leg in legs) + transfers * 3,
        "distance_meters": round(sum(leg["distance_meters"] for leg in legs), 1),
        "fare_inr": sum(leg["fare_inr"] for leg in legs),
        "co2_grams": sum(leg["co2_grams"] for leg in legs),
        "transfers": transfers,
        "walk_meters": round(walk_meters, 1),
        "safety": safety,
        "modes": list(dict.fromkeys(modes)),
        "legs": legs,
        "geometry": geometry,
    }
