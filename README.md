Here is the link to our project ppt:
https://canva.link/zi9ppju92bkadt1

# Nagomi

Nagomi is a Delhi mobility planner that combines a FastAPI backend with a React/Vite frontend to help compare route options. It is designed to show different travel choices based on speed, cost, emissions, and safety rather than only giving one shortest path.

This project is a prototype for exploring multi-modal routing and transportation intelligence in the Delhi area.

## Current Prototype

The repository currently contains a working road-routing foundation:

- React and Leaflet map centered on Delhi
- Delhi landmark search, coordinate input, and click-to-pin locations
- FastAPI `POST /routes` multi-objective endpoint
- Local OpenStreetMap road graph loaded through OSMnx
- Fastest, Cheapest, Eco Saver, and Safest objective profiles
- Safest routing using time-of-day and infrastructure exposure scoring
- Multi-leg journeys combining walking, e-rickshaw, bus, and metro
- Local Delhi metro lines and major bus corridors with transfers
- Traffic analysis on every road and bus itinerary
- Comparative time, fare, emissions, distance, and ETA estimates
- Selectable route cards with corresponding map polylines
- Responsive planner layout for desktop and mobile
- Experimental Neo4j graph import scripts
- PostgreSQL and Neo4j connectivity probes

The included graph contains 10,192 intersections and 24,441 directed road
edges. It was generated as a `drive` network, so the current prototype does not
yet contain walk paths, metro schedules, bus schedules, or live traffic. Fare,
emissions, and arrival ranges are explicitly labeled estimates.

Traffic automatically uses TomTom live flow when `TOMTOM_API_KEY` is present.
Without a key, Nagomi uses a clearly labeled Delhi time-of-day congestion model.
Copy `backend/.env.example` to `backend/.env` and set the key in your shell or
process environment to activate live traffic.

Location search indexes all named roads in the included OSM graph without a
key. Set `GEOAPIFY_API_KEY` to enable autocomplete for addresses, neighborhoods,
businesses, metro stations, and POIs across the whole Delhi NCT. The key stays
in the backend and is never sent to the browser. Trips outside the bundled
central/south Delhi graph automatically use Geoapify whole-Delhi road and
approximated-transit geometry instead of snapping to the local graph boundary.

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

## How to Run the Program

### 1. Start the backend API

From the project root:

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8010
```

This starts the FastAPI service. Once it is running, open:

- http://127.0.0.1:8010
- or the Swagger docs at http://127.0.0.1:8010/docs

### 2. Start the frontend app

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite address shown in the terminal, usually:

- http://localhost:5173

### 3. Use the app

1. Pick a start and destination point on the Delhi map.
2. Choose a route preference such as Fastest, Cheapest, or Eco Saver.
3. Click the route button to view the suggested options.

### Optional: enable extra features

If you want live traffic or address autocomplete, add the relevant keys to the backend environment before starting the API. The app can still run without these extras using the local Delhi graph data.

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
