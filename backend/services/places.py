import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List

import httpx
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY", "").strip()
GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/autocomplete"

# Covers the National Capital Territory of Delhi.
DELHI_RECT = "rect:76.8388,28.4041,77.3470,28.8830"
DELHI_CENTER = "proximity:77.2090,28.6139"

PLACES: List[Dict[str, object]] = [
    {
        "id": "connaught-place",
        "name": "Connaught Place",
        "subtitle": "New Delhi",
        "lat": 28.6315,
        "lon": 77.2167,
        "provider": "curated",
    },
    {
        "id": "india-gate",
        "name": "India Gate",
        "subtitle": "Kartavya Path",
        "lat": 28.6129,
        "lon": 77.2295,
        "provider": "curated",
    },
    {
        "id": "new-delhi-station",
        "name": "New Delhi Railway Station",
        "subtitle": "Ajmeri Gate",
        "lat": 28.6431,
        "lon": 77.2197,
        "provider": "curated",
    },
    {
        "id": "red-fort",
        "name": "Red Fort",
        "subtitle": "Old Delhi",
        "lat": 28.6562,
        "lon": 77.2410,
        "provider": "curated",
    },
    {
        "id": "airport-t3",
        "name": "Delhi Airport Terminal 3",
        "subtitle": "IGI Airport",
        "lat": 28.5562,
        "lon": 77.1000,
        "provider": "curated",
    },
    {
        "id": "aiims",
        "name": "AIIMS Delhi",
        "subtitle": "Ansari Nagar",
        "lat": 28.5672,
        "lon": 77.2100,
        "provider": "curated",
    },
    {
        "id": "hauz-khas",
        "name": "Hauz Khas",
        "subtitle": "South Delhi",
        "lat": 28.5494,
        "lon": 77.2001,
        "provider": "curated",
    },
    {
        "id": "rajiv-chowk",
        "name": "Rajiv Chowk Metro",
        "subtitle": "Blue and Yellow lines",
        "lat": 28.6328,
        "lon": 77.2197,
        "provider": "curated",
    },
    {
        "id": "kashmere-gate",
        "name": "Kashmere Gate Metro",
        "subtitle": "Red, Yellow and Violet lines",
        "lat": 28.6675,
        "lon": 77.2280,
        "provider": "curated",
    },
    {
        "id": "saket",
        "name": "Saket Metro",
        "subtitle": "Yellow line",
        "lat": 28.5206,
        "lon": 77.2014,
        "provider": "curated",
    },
    {
        "id": "lotus-temple",
        "name": "Lotus Temple",
        "subtitle": "Kalkaji",
        "lat": 28.5535,
        "lon": 77.2588,
        "provider": "curated",
    },
    {
        "id": "akshardham",
        "name": "Akshardham",
        "subtitle": "East Delhi",
        "lat": 28.6127,
        "lon": 77.2773,
        "provider": "curated",
    },
]


def geocoding_source() -> str:
    return "geoapify" if GEOAPIFY_API_KEY else "local_graph"


def _names(value: Any) -> Iterable[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)] if value else []


@lru_cache(maxsize=1)
def _local_graph_places() -> List[Dict[str, object]]:
    # Imported lazily to avoid loading the road graph twice during application startup.
    from services.routing import G

    grouped: Dict[str, Dict[str, Any]] = {}
    for u, v, data in G.edges(data=True):
        for name in _names(data.get("name")):
            key = name.strip().casefold()
            if len(key) < 3:
                continue
            entry = grouped.setdefault(
                key,
                {
                    "name": name.strip(),
                    "lat_total": 0.0,
                    "lon_total": 0.0,
                    "count": 0,
                },
            )
            entry["lat_total"] += (float(G.nodes[u]["y"]) + float(G.nodes[v]["y"])) / 2
            entry["lon_total"] += (float(G.nodes[u]["x"]) + float(G.nodes[v]["x"])) / 2
            entry["count"] += 1

    return [
        {
            "id": "road-{}".format(index),
            "name": entry["name"],
            "subtitle": "Road, Delhi",
            "lat": entry["lat_total"] / entry["count"],
            "lon": entry["lon_total"] / entry["count"],
            "provider": "local_graph",
        }
        for index, entry in enumerate(
            sorted(grouped.values(), key=lambda item: item["name"].casefold())
        )
    ]


def _local_search(query: str, limit: int = 8) -> List[Dict[str, object]]:
    normalized = query.strip().casefold()
    candidates = [*PLACES, *_local_graph_places()]
    if not normalized:
        return PLACES[:limit]

    prefix_matches = []
    contains_matches = []
    for place in candidates:
        searchable = "{} {}".format(place["name"], place["subtitle"]).casefold()
        if str(place["name"]).casefold().startswith(normalized):
            prefix_matches.append(place)
        elif normalized in searchable:
            contains_matches.append(place)
    return [*prefix_matches, *contains_matches][:limit]


def _geoapify_place(feature: Dict[str, Any], index: int) -> Dict[str, object]:
    properties = feature.get("properties", feature)
    name = (
        properties.get("address_line1")
        or properties.get("name")
        or properties.get("street")
        or properties.get("formatted")
        or "Delhi location"
    )
    subtitle = properties.get("address_line2")
    if not subtitle:
        formatted = str(properties.get("formatted", "Delhi"))
        subtitle = formatted.replace(str(name), "", 1).strip(" ,") or "Delhi"

    return {
        "id": "geoapify-{}-{}".format(properties.get("place_id", "result"), index),
        "name": str(name),
        "subtitle": str(subtitle),
        "lat": float(properties["lat"]),
        "lon": float(properties["lon"]),
        "provider": "geoapify",
        "result_type": str(properties.get("result_type", "place")),
        "confidence": float(properties.get("rank", {}).get("confidence", 0)),
    }


@lru_cache(maxsize=512)
def _geoapify_search(query: str) -> List[Dict[str, object]]:
    if not GEOAPIFY_API_KEY or len(query.strip()) < 2:
        return []

    response = httpx.get(
        GEOAPIFY_URL,
        params={
            "text": query.strip(),
            "format": "geojson",
            "filter": DELHI_RECT,
            "bias": DELHI_CENTER,
            "lang": "en",
            "limit": 8,
            "apiKey": GEOAPIFY_API_KEY,
        },
        timeout=4.0,
    )
    response.raise_for_status()
    features = response.json().get("features", [])
    places = [_geoapify_place(feature, index) for index, feature in enumerate(features)]
    return [
        place
        for index, place in enumerate(places)
        if index == 0 or float(place["confidence"]) >= 0.35
    ]


def _dedupe(places: Iterable[Dict[str, object]], limit: int = 8) -> List[Dict[str, object]]:
    unique = []
    seen = set()
    for place in places:
        key = (
            str(place["name"]).strip().casefold(),
            round(float(place["lat"]), 4),
            round(float(place["lon"]), 4),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(place)
        if len(unique) == limit:
            break
    return unique


def search_places(query: str = "") -> List[Dict[str, object]]:
    normalized = query.strip()
    local_results = _local_search(normalized)
    if not GEOAPIFY_API_KEY or len(normalized) < 2:
        return local_results

    try:
        online_results = _geoapify_search(normalized)
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        online_results = []
    return _dedupe([*online_results, *local_results])
