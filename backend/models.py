from typing import Dict, List

from pydantic import BaseModel, Field


class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class RouteRequest(BaseModel):
    source: Coordinate
    destination: Coordinate
    preference: str = "fastest"


class Place(BaseModel):
    id: str
    name: str
    subtitle: str
    lat: float
    lon: float
    provider: str = "local"
    result_type: str = "place"
    confidence: float = 1


class PlaceSearchResponse(BaseModel):
    places: List[Place]
    source: str


class HealthResponse(BaseModel):
    status: str
    graph: Dict[str, int]
    live_traffic: bool
    scheduled_transit: bool
    traffic_source: str
    geocoding_source: str
