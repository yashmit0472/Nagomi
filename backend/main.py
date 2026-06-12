from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from models import HealthResponse, PlaceSearchResponse, RouteRequest
from services.places import search_places
from services.routing import G, build_route_plan, get_route


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
        "live_traffic": False,
        "scheduled_transit": False,
    }


@app.get("/places", response_model=PlaceSearchResponse)
def places(q: str = Query("", max_length=80)):
    return {"places": search_places(q)}


@app.post("/routes")
def routes(request: RouteRequest):
    return build_route_plan(
        request.source.lat,
        request.source.lon,
        request.destination.lat,
        request.destination.lon,
        request.preference,
    )


@app.post("/route")
def route(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float,
):
    return get_route(source_lat, source_lon, dest_lat, dest_lon)
