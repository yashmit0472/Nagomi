from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from models import HealthResponse, PlaceSearchResponse, RouteRequest
from services.places import geocoding_source, search_places
from services.routing import G, build_route_plan, get_route
from services.traffic import analyze_traffic, live_traffic_available
from services.transit import TRANSIT_GRAPH, transit_available


app = FastAPI(
    title="Nagomi GraphIQ Transit API",
    description="Multi-objective mobility routing for Delhi",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "name": "Nagomi GraphIQ Transit",
        "message": "Mobility intelligence API is running.",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
def health():
    return {
        "status": "ok",
        "graph": {"nodes": len(G.nodes), "edges": len(G.edges)},
        "live_traffic": live_traffic_available(),
        "scheduled_transit": transit_available(),
        "traffic_source": "tomtom_live" if live_traffic_available() else "delhi_time_model",
        "geocoding_source": geocoding_source(),
    }


@app.get("/places", response_model=PlaceSearchResponse)
def places(q: str = Query("", max_length=80)):
    return {"places": search_places(q), "source": geocoding_source()}


@app.post("/routes")
def routes(request: RouteRequest):
    return build_route_plan(
        request.source.lat,
        request.source.lon,
        request.destination.lat,
        request.destination.lon,
        request.preference,
    )


@app.post("/traffic")
def traffic(request: RouteRequest):
    return analyze_traffic(
        [
            {"lat": request.source.lat, "lon": request.source.lon},
            {"lat": request.destination.lat, "lon": request.destination.lon},
        ]
    )


@app.post("/route")
def route(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float,
):
    return get_route(source_lat, source_lon, dest_lat, dest_lon)
