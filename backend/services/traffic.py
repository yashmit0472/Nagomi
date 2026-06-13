import os
import time
from datetime import datetime, timezone
from functools import lru_cache
from math import sqrt
from pathlib import Path
from typing import Any, Dict, List, Sequence

import httpx
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "").strip()
IST = timezone.utc

CONGESTION_ZONES = [
    (28.6315, 77.2167, 0.20, "Connaught Place"),
    (28.6288, 77.2410, 0.18, "ITO"),
    (28.6431, 77.2197, 0.16, "New Delhi Railway Station"),
    (28.6675, 77.2280, 0.14, "Kashmere Gate"),
    (28.5672, 77.2100, 0.13, "AIIMS"),
    (28.5918, 77.1616, 0.12, "Dhaula Kuan"),
]


def live_traffic_available() -> bool:
    return bool(TOMTOM_API_KEY)


def _sample_points(points: Sequence[Dict[str, float]], count: int = 3) -> List[Dict[str, float]]:
    if len(points) <= count:
        return list(points)
    indices = [int(round(index * (len(points) - 1) / (count - 1))) for index in range(count)]
    return [points[index] for index in indices]


def _level(multiplier: float) -> str:
    if multiplier >= 1.65:
        return "severe"
    if multiplier >= 1.35:
        return "heavy"
    if multiplier >= 1.15:
        return "moderate"
    return "light"


@lru_cache(maxsize=256)
def _tomtom_sample(lat: float, lon: float, minute_bucket: int) -> Dict[str, Any]:
    del minute_bucket
    response = httpx.get(
        "https://api.tomtom.com/traffic/services/4/"
        "flowSegmentData/absolute/12/json",
        params={
            "key": TOMTOM_API_KEY,
            "point": "{},{}".format(lat, lon),
            "unit": "kmph",
        },
        timeout=3.0,
    )
    response.raise_for_status()
    data = response.json()["flowSegmentData"]
    free_flow = max(float(data.get("freeFlowSpeed", 1)), 1)
    current = max(float(data.get("currentSpeed", 1)), 1)
    return {
        "current_speed_kph": current,
        "free_flow_speed_kph": free_flow,
        "multiplier": free_flow / current,
        "confidence": float(data.get("confidence", 0)),
        "road_closed": bool(data.get("roadClosure", False)),
    }


def _tomtom_snapshot(points: Sequence[Dict[str, float]]) -> Dict[str, Any]:
    minute_bucket = int(time.time() // 60)
    samples = [
        _tomtom_sample(
            round(point["lat"], 4),
            round(point["lon"], 4),
            minute_bucket,
        )
        for point in _sample_points(points)
    ]

    multiplier = sum(sample["multiplier"] for sample in samples) / len(samples)
    return {
        "source": "tomtom_live",
        "is_live": True,
        "level": "closed" if any(sample["road_closed"] for sample in samples) else _level(multiplier),
        "delay_multiplier": round(min(multiplier, 3.0), 2),
        "current_speed_kph": round(
            sum(sample["current_speed_kph"] for sample in samples) / len(samples), 1
        ),
        "free_flow_speed_kph": round(
            sum(sample["free_flow_speed_kph"] for sample in samples) / len(samples), 1
        ),
        "confidence": round(
            sum(sample["confidence"] for sample in samples) / len(samples), 2
        ),
        "incidents": ["Road closure reported"] if any(sample["road_closed"] for sample in samples) else [],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _modeled_snapshot(points: Sequence[Dict[str, float]], now: datetime) -> Dict[str, Any]:
    hour = (now.hour + 5 + (1 if now.minute >= 30 else 0)) % 24
    weekday = now.weekday() < 5

    if weekday and (8 <= hour < 11 or 17 <= hour < 21):
        multiplier = 1.48
    elif 11 <= hour < 17:
        multiplier = 1.22
    elif 21 <= hour or hour < 6:
        multiplier = 1.05
    else:
        multiplier = 1.12

    midpoint = points[len(points) // 2] if points else {"lat": 28.6315, "lon": 77.2167}
    nearby = []
    for lat, lon, penalty, name in CONGESTION_ZONES:
        distance = sqrt((midpoint["lat"] - lat) ** 2 + (midpoint["lon"] - lon) ** 2)
        if distance < 0.025:
            multiplier += penalty
            nearby.append("{} congestion zone".format(name))

    multiplier = min(multiplier, 2.2)
    free_flow_speed = 38.0
    return {
        "source": "delhi_time_model",
        "is_live": False,
        "level": _level(multiplier),
        "delay_multiplier": round(multiplier, 2),
        "current_speed_kph": round(free_flow_speed / multiplier, 1),
        "free_flow_speed_kph": free_flow_speed,
        "confidence": 0.55,
        "incidents": nearby,
        "updated_at": now.isoformat(),
    }


def analyze_traffic(
    points: Sequence[Dict[str, float]],
    now: datetime = None,
) -> Dict[str, Any]:
    timestamp = now or datetime.now(timezone.utc)
    if TOMTOM_API_KEY and points:
        try:
            return _tomtom_snapshot(points)
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            pass
    return _modeled_snapshot(points, timestamp)
