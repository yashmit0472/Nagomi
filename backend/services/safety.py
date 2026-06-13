from datetime import datetime, timezone
from typing import Any, Dict, Iterable


ROAD_SAFETY_FACTORS = {
    "motorway": 0.92,
    "motorway_link": 0.96,
    "trunk": 0.78,
    "trunk_link": 0.82,
    "primary": 0.72,
    "primary_link": 0.76,
    "secondary": 0.82,
    "secondary_link": 0.86,
    "tertiary": 0.94,
    "tertiary_link": 0.98,
    "residential": 1.14,
    "living_street": 1.24,
    "service": 1.32,
    "unclassified": 1.12,
}

MODE_SAFETY = {
    "metro": 91,
    "cab": 86,
    "bus": 82,
    "electric_rickshaw": 78,
    "shared_auto": 74,
    "walk": 72,
    "transfer": 70,
}


def is_night(now: datetime = None) -> bool:
    timestamp = now or datetime.now(timezone.utc)
    hour = (timestamp.hour + 5 + (1 if timestamp.minute >= 30 else 0)) % 24
    return hour >= 21 or hour < 6


def road_safety_weight(road_class: str, length: float) -> float:
    return length * ROAD_SAFETY_FACTORS.get(road_class, 1.12)


def score_route(
    modes: Iterable[str],
    transfers: int,
    walk_meters: float,
    infrastructure_score: float = 80,
    now: datetime = None,
) -> Dict[str, Any]:
    mode_list = list(modes) or ["walk"]
    average_mode_score = sum(MODE_SAFETY.get(mode, 72) for mode in mode_list) / len(mode_list)
    nighttime = is_night(now)
    walking_penalty = min(walk_meters / 250, 12) * (1.45 if nighttime else 0.65)
    transfer_penalty = transfers * (4.5 if nighttime else 2.5)
    score = (
        average_mode_score * 0.55
        + infrastructure_score * 0.45
        - walking_penalty
        - transfer_penalty
    )
    score = max(30, min(98, round(score)))

    if score >= 86:
        label = "Very high"
    elif score >= 76:
        label = "High"
    elif score >= 64:
        label = "Moderate"
    else:
        label = "Use caution"

    factors = []
    if "metro" in mode_list:
        factors.append("staffed metro segment")
    if walk_meters < 700:
        factors.append("limited walking exposure")
    if transfers == 0:
        factors.append("no transfers")
    elif transfers == 1:
        factors.append("one controlled transfer")
    if nighttime:
        factors.append("night-time penalty applied")

    return {
        "score": score,
        "label": label,
        "is_night": nighttime,
        "factors": factors,
        "source": "infrastructure_proxy",
    }
