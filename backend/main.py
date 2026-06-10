from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.routing import get_route

app = FastAPI(
    title="Nagomi API",
    description="AI-Powered Multi-Modal Mobility Optimization Platform",
    version="1.0.0"
)

# ----------------------------------
# CORS Configuration
# ----------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------
# Routes
# ----------------------------------

@app.get("/")
def home():
    return {
        "message": "Nagomi Running"
    }


@app.post("/route")
def route(
    source_lat: float,
    source_lon: float,
    dest_lat: float,
    dest_lon: float
):
    return get_route(
        source_lat,
        source_lon,
        dest_lat,
        dest_lon
    )