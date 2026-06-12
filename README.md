# Nagomi

## GraphIQ Transit: AI-Powered Multi-Modal Mobility Optimization Platform

Nagomi models urban mobility as a dynamic, multi-layer graph spanning roads,
walking links, public transport, and shared mobility. Instead of returning only
the shortest path, the platform is designed to compare journeys by time, cost,
carbon impact, comfort, and reliability.

> An AI-powered graph intelligence platform that transforms fragmented urban
> transportation into a self-optimizing, sustainable, and predictive mobility
> network.

## Current Prototype

The repository currently contains a working road-routing foundation:

- React and Leaflet map centered on Delhi
- Delhi landmark search, coordinate input, and click-to-pin locations
- FastAPI `POST /routes` multi-objective endpoint
- Local OpenStreetMap road graph loaded through OSMnx
- Fastest, Cheapest, and Eco Saver road-route profiles
- Comparative time, fare, emissions, distance, and ETA estimates
- Selectable route cards with corresponding map polylines
- Responsive planner layout for desktop and mobile
- Experimental Neo4j graph import scripts
- PostgreSQL and Neo4j connectivity probes

The included graph contains 10,192 intersections and 24,441 directed road
edges. It was generated as a `drive` network, so the current prototype does not
yet contain walk paths, metro schedules, bus schedules, or live traffic. Fare,
emissions, and arrival ranges are explicitly labeled estimates.

## Target Experience

A traveler enters a start and destination, then compares complete multimodal
itineraries such as:

- Walk -> Metro -> Walk
- Walk -> Bus -> Rickshaw
- Rickshaw -> Metro -> Walk
- Direct cab or two-wheeler

Nagomi will rank viable itineraries under selectable objectives:

- **Fastest:** minimize traffic-aware arrival time
- **Cheapest:** minimize fares, tolls, and estimated ride-hailing cost
- **Eco Saver:** minimize estimated CO2 and congestion impact
- **Comfort:** reduce walking, transfers, and crowding
- **Safety:** account for lighting, incident data, and time of day

See [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for the audited feature
status, recommended architecture, data requirements, and phased build plan.

## Run the Current Prototype

### Backend

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8010
```

The API is available at `http://127.0.0.1:8010`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, usually `http://localhost:5173`.

### Current Usage

1. Choose Delhi landmarks or enter coordinates as `latitude, longitude`.
2. You can also click the map to pin the active location field.
3. Select Fastest, Cheapest, or Eco Saver.
4. Choose **Find smarter routes**.
5. Compare time, estimated fare, distance, emissions, and ETA range.
6. Select any route card to highlight that path on the map.

## Repository Layout

```text
backend/   FastAPI application and routing service
data/      Local graph and future transit datasets
frontend/  React/Vite map application
graph/     OSM download, debugging, plotting, and Neo4j import scripts
ml/        Reserved for prediction models
docs/      Product, architecture, and implementation documentation
docker/    Reserved for local service orchestration
```
