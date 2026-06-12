from typing import Dict, List


PLACES: List[Dict[str, object]] = [
    {
        "id": "connaught-place",
        "name": "Connaught Place",
        "subtitle": "New Delhi",
        "lat": 28.6315,
        "lon": 77.2167,
    },
    {
        "id": "india-gate",
        "name": "India Gate",
        "subtitle": "Kartavya Path",
        "lat": 28.6129,
        "lon": 77.2295,
    },
    {
        "id": "new-delhi-station",
        "name": "New Delhi Railway Station",
        "subtitle": "Ajmeri Gate",
        "lat": 28.6431,
        "lon": 77.2197,
    },
    {
        "id": "red-fort",
        "name": "Red Fort",
        "subtitle": "Old Delhi",
        "lat": 28.6562,
        "lon": 77.2410,
    },
    {
        "id": "airport-t3",
        "name": "Delhi Airport Terminal 3",
        "subtitle": "IGI Airport",
        "lat": 28.5562,
        "lon": 77.1000,
    },
    {
        "id": "aiims",
        "name": "AIIMS Delhi",
        "subtitle": "Ansari Nagar",
        "lat": 28.5672,
        "lon": 77.2100,
    },
    {
        "id": "hauz-khas",
        "name": "Hauz Khas",
        "subtitle": "South Delhi",
        "lat": 28.5494,
        "lon": 77.2001,
    },
    {
        "id": "rajiv-chowk",
        "name": "Rajiv Chowk Metro",
        "subtitle": "Blue and Yellow lines",
        "lat": 28.6328,
        "lon": 77.2197,
    },
    {
        "id": "kashmere-gate",
        "name": "Kashmere Gate Metro",
        "subtitle": "Red, Yellow and Violet lines",
        "lat": 28.6675,
        "lon": 77.2280,
    },
    {
        "id": "saket",
        "name": "Saket Metro",
        "subtitle": "Yellow line",
        "lat": 28.5206,
        "lon": 77.2014,
    },
    {
        "id": "lotus-temple",
        "name": "Lotus Temple",
        "subtitle": "Kalkaji",
        "lat": 28.5535,
        "lon": 77.2588,
    },
    {
        "id": "akshardham",
        "name": "Akshardham",
        "subtitle": "East Delhi",
        "lat": 28.6127,
        "lon": 77.2773,
    },
]


def search_places(query: str = "") -> List[Dict[str, object]]:
    normalized = query.strip().lower()
    if not normalized:
        return PLACES[:8]

    return [
        place
        for place in PLACES
        if normalized in str(place["name"]).lower()
        or normalized in str(place["subtitle"]).lower()
    ][:8]
