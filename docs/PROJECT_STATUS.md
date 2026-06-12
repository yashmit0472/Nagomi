# Nagomi Project Status

## Product Positioning

**GraphIQ Transit: AI-Powered Multi-Modal Mobility Optimization Platform**

Nagomi should be presented as a mobility optimization and network-intelligence
platform, not merely a transit planner. The traveler-facing route planner is
the first product surface. Delay prediction, network analysis, digital-twin
simulation, and authority dashboards build on the same city graph later.

## Audit Summary

Status as of June 13, 2026:

| Capability | Status | Evidence / limitation |
| --- | --- | --- |
| Interactive Delhi map | Working | React Leaflet map in `frontend/src/App.tsx` |
| Select coordinates | Working | Two map clicks set source and destination |
| Local route API | Working in code | FastAPI `POST /route` |
| Road shortest path | Working in code | OSMnx path weighted by edge length |
| Route geometry | Working in code | Edge geometries returned to the frontend |
| Distance display | Working | Frontend renders meters |
| Address/place search | MVP built | Local Delhi landmarks, coordinates, and map pinning |
| Multiple route alternatives | MVP built | Three objective-specific local road paths |
| Fastest routing | Estimated MVP | Road-class travel-time weights; no live traffic yet |
| Cheapest routing | Estimated MVP | Shared-auto fare model over distance |
| Eco Saver routing | Estimated MVP | E-rickshaw emissions model and eco road weights |
| Walking routing | Not built | Saved OSM graph is drive-only |
| Metro and bus routing | Not built | No GTFS schedule/stop graph |
| Rickshaw/ride-share legs | Not built | No provider or first/last-mile model |
| Live transit updates | Not built | No GTFS-Realtime feed |
| Live road traffic | Not built | No traffic provider integration |
| ETA confidence ranges | Estimated MVP | Transparent ranges; historical model remains future work |
| Crowding prediction | Not built | No passenger-count or occupancy data |
| Personalization | Not built | No users, preferences, or feedback loop |
| Network intelligence | Prototype only | Neo4j node/edge import scripts exist |
| Digital twin | Not built | No simulation engine or scenario model |
| Automated tests | Working | Health, search, routing profiles, geometry, and CORS |

The local GraphML file contains 10,192 nodes and 24,441 directed edges. Its
available edge attributes include road class, length, geometry, lanes, and
occasionally `maxspeed`. It has no dynamic travel time, fare, emissions, or
transit schedule data.

## Important Technical Decision

Do not implement metro + walk or bus + rickshaw by assigning labels to paths in
the current road graph. Those results would look multimodal but would be
fictional.

Build a real layered graph:

```text
Street layer:       walk, bicycle, road
Transit layer:      stops, stations, trips, schedules
Mobility layer:     rickshaw, taxi, bike/scooter availability
Transfer layer:     walk-to-stop, station transfer, pickup/drop-off
Realtime overlay:   traffic, delays, closures, occupancy
Cost overlay:       fares, tolls, surge estimates
Impact overlay:     emissions and energy factors
```

For an open-source core, OpenTripPlanner is the strongest starting point. It
combines OpenStreetMap streets with GTFS transit schedules, supports multimodal
itineraries, and can consume real-time updates. Nagomi's FastAPI service can
then act as an optimization and normalization layer in front of it.

## Recommended Architecture

```text
React + Leaflet/MapLibre
        |
FastAPI API gateway
        |
        +-- Geocoder adapter
        +-- OpenTripPlanner adapter (OSM + GTFS + GTFS-Realtime)
        +-- Road traffic adapter (Google, TomTom, or Mapbox)
        +-- Fare and emissions scoring service
        +-- Route ranking / Pareto optimizer
        |
PostgreSQL + PostGIS     Redis cache     Object storage
        |
Analytics graph / warehouse for centrality, prediction, and simulation
```

Neo4j can be useful for offline network intelligence and demonstrations, but it
should not be required for the first traveler-facing routing MVP. OpenTripPlanner
already solves the difficult time-dependent transit-routing problem.

## Route Response Contract

The frontend should receive several complete itineraries, each made of legs:

```json
{
  "routes": [
    {
      "id": "route-1",
      "label": "Fastest",
      "duration_minutes": 38,
      "arrival_time": "10:42",
      "distance_meters": 14200,
      "fare_inr": 64,
      "co2_grams": 310,
      "transfers": 1,
      "walk_meters": 720,
      "reliability": {
        "p70": [36, 41],
        "p90": [34, 47]
      },
      "legs": [
        {"mode": "walk", "from": "Origin", "to": "Metro station"},
        {"mode": "metro", "route": "Yellow Line"},
        {"mode": "walk", "from": "Metro station", "to": "Destination"}
      ],
      "geometry": {}
    }
  ]
}
```

The optimization layer should rank the same candidate set differently for each
preference. Start with a transparent weighted score, then move to Pareto-front
ranking and personalization only after real usage data exists.

## Objective Model

Use normalized features so unlike units can be compared:

```text
score =
  w_time       * normalized_duration +
  w_cost       * normalized_fare +
  w_carbon     * normalized_emissions +
  w_walk       * normalized_walk_distance +
  w_transfers  * normalized_transfer_count +
  w_crowding   * normalized_crowding +
  w_risk       * normalized_safety_risk
```

Initial presets:

| Preset | Dominant weights |
| --- | --- |
| Fastest | duration, delay risk |
| Cheapest | fare, toll, surge |
| Eco Saver | emissions, congestion, private-vehicle distance |
| Comfort | transfers, walking, crowding |
| Safety | incident risk, lighting, late-night transfer exposure |

Keep the component metrics visible. Users should be able to understand why one
route was recommended.

## Live Traffic

OpenStreetMap tiles do not provide live traffic. A provider is required.

Practical choices:

1. **Google Routes API:** strongest direct route/traffic experience and supports
   traffic-aware route calculation, alternatives, transit, and eco-friendly
   road routes. It requires billing and carries platform usage restrictions.
2. **TomTom Routing API:** traffic-aware routing with alternative routes and a
   cleaner path for provider-independent map rendering.
3. **Mapbox Directions:** useful for driving, driving-traffic, walking, and
   cycling. Public-transit journey planning still needs a separate engine/feed.

Recommended split for the hackathon:

- Use OpenTripPlanner for multimodal public-transit itineraries.
- Add one road-traffic provider for live cab/rickshaw/road-leg ETAs.
- Keep provider access behind FastAPI adapters so it can be changed later.
- Cache responses and clearly label live, scheduled, predicted, and estimated
  values in the UI.

Traffic data cannot be reconstructed reliably from the existing OSM graph.

## Data Required

Minimum useful data:

- Delhi pedestrian and road OpenStreetMap extract
- Delhi Metro and bus GTFS Schedule feeds
- GTFS-Realtime feeds when the authority exposes them
- Fare rules for metro, bus, and first/last-mile estimates
- Vehicle emission factors by mode and fuel type
- One geocoding/search provider
- One road traffic/routing provider

Later data:

- Weather observations and forecasts
- Events, holidays, closures, and service alerts
- Station occupancy or ticketing aggregates
- Safety incidents and lighting data
- Historical actual-versus-planned arrival observations

## Build Plan

### Phase 1: Credible Route Planner

- Add typed request/response models and API error handling.
- Add source/destination place autocomplete and retain map-click selection.
- Import walk-capable OSM data and Delhi GTFS into OpenTripPlanner.
- Return and draw multiple itineraries with colored per-mode legs.
- Add Fastest, Cheapest, and Eco Saver ranking presets.
- Show duration, fare, CO2 estimate, transfers, walking, and data freshness.
- Add backend and frontend tests for the complete route flow.

**Demo goal:** Search two Delhi locations and compare at least three genuine
itineraries, including one metro/bus combination and one road option.

### Phase 2: Realtime and Prediction

- Integrate traffic-aware road durations.
- Consume transit delays, alerts, and vehicle positions where available.
- Replan when a selected itinerary becomes invalid.
- Store predictions and actual outcomes.
- Add probabilistic ETA ranges after enough observations exist.

### Phase 3: Graph Intelligence

- Compute centrality, communities, and bottleneck rankings offline.
- Build authority-facing maps and scenario controls.
- Add event, closure, crowding, and disruption simulations.
- Evaluate temporal GNNs only after creating a reliable time-series dataset.

### Phase 4: Personalization and Digital Twin

- Add profiles, accessibility needs, saved preferences, and feedback.
- Learn ranking weights from accepted/rejected route suggestions.
- Add capacity-aware simulation and policy comparison.
- Add disaster-mode constraints and emergency corridors with authority data.

## Immediate Backlog

1. Obtain or create validated Delhi Metro and bus GTFS feeds.
2. Add OpenTripPlanner to `docker/` and build a Delhi routing graph.
3. Define the production route contract using itinerary legs.
4. Replace click-only input with geocoded source/destination search.
5. Implement transparent fare and emissions calculators.
6. Render three selectable route cards and mode-colored map polylines.
7. Choose and integrate one traffic provider behind a backend adapter.
8. Add repeatable tests and one-command local startup.

Avoid starting LSTM, reinforcement learning, or GNN work before these eight
items. Those models need clean historical data and measurable baselines; the
route-planning foundation produces both.
