import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  CircleMarker,
  MapContainer,
  Polyline,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import type { LatLngBoundsExpression } from "leaflet";
import "./App.css";

type Preference = "fastest" | "cheapest" | "eco" | "safest";
type ActiveField = "source" | "destination";

type Location = {
  name: string;
  subtitle: string;
  lat: number;
  lon: number;
};

type RoutePoint = {
  lat: number;
  lon: number;
};

type RouteLeg = {
  mode: string;
  label: string;
  line: string | null;
  color: string;
  from: string;
  to: string;
  duration_minutes: number;
  distance_meters: number;
  fare_inr: number;
  co2_grams: number;
  geometry: RoutePoint[];
};

type RouteOption = {
  id: Preference;
  label: string;
  mode: string;
  mode_label: string;
  color: string;
  duration_minutes: number;
  distance_meters: number;
  fare_inr: number;
  co2_grams: number;
  transfers: number;
  walk_meters: number;
  safety: {
    score: number;
    label: string;
    is_night: boolean;
    factors: string[];
    source: string;
  };
  traffic: {
    source: string;
    is_live: boolean;
    level: string;
    delay_multiplier: number;
    current_speed_kph: number;
    free_flow_speed_kph: number;
    confidence: number;
    incidents: string[];
    updated_at: string;
  };
  reliability: {
    likely_min: number;
    likely_max: number;
    high_confidence_max: number;
  };
  summary: string;
  legs: RouteLeg[];
  geometry: RoutePoint[];
  data_quality: string;
};

type RouteResponse = {
  success: boolean;
  recommended_route_id: Preference;
  routes: RouteOption[];
  notice: string;
  message?: string;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8010";

const PLACES: Location[] = [
  { name: "Connaught Place", subtitle: "New Delhi", lat: 28.6315, lon: 77.2167 },
  { name: "India Gate", subtitle: "Kartavya Path", lat: 28.6129, lon: 77.2295 },
  {
    name: "New Delhi Railway Station",
    subtitle: "Ajmeri Gate",
    lat: 28.6431,
    lon: 77.2197,
  },
  { name: "Red Fort", subtitle: "Old Delhi", lat: 28.6562, lon: 77.241 },
  {
    name: "Delhi Airport Terminal 3",
    subtitle: "IGI Airport",
    lat: 28.5562,
    lon: 77.1,
  },
  { name: "AIIMS Delhi", subtitle: "Ansari Nagar", lat: 28.5672, lon: 77.21 },
  { name: "Hauz Khas", subtitle: "South Delhi", lat: 28.5494, lon: 77.2001 },
  {
    name: "Rajiv Chowk Metro",
    subtitle: "Blue and Yellow lines",
    lat: 28.6328,
    lon: 77.2197,
  },
  {
    name: "Kashmere Gate Metro",
    subtitle: "Red, Yellow and Violet lines",
    lat: 28.6675,
    lon: 77.228,
  },
  {
    name: "Saket Metro",
    subtitle: "Yellow line",
    lat: 28.5206,
    lon: 77.2014,
  },
  { name: "Lotus Temple", subtitle: "Kalkaji", lat: 28.5535, lon: 77.2588 },
  { name: "Akshardham", subtitle: "East Delhi", lat: 28.6127, lon: 77.2773 },
];

const PREFERENCES: Array<{
  id: Preference;
  title: string;
  caption: string;
}> = [
  { id: "fastest", title: "Fastest", caption: "Save time" },
  { id: "cheapest", title: "Cheapest", caption: "Spend less" },
  { id: "eco", title: "Eco Saver", caption: "Lower carbon" },
  { id: "safest", title: "Safest", caption: "Reduce exposure" },
];

function formatDistance(meters: number) {
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}

function parseLocation(value: string): Location | null {
  const knownPlace = PLACES.find(
    (place) => place.name.toLowerCase() === value.trim().toLowerCase(),
  );
  if (knownPlace) return knownPlace;

  const parts = value.split(",").map((part) => Number(part.trim()));
  if (
    parts.length === 2 &&
    Number.isFinite(parts[0]) &&
    Number.isFinite(parts[1])
  ) {
    return {
      name: "Custom coordinates",
      subtitle: `${parts[0].toFixed(5)}, ${parts[1].toFixed(5)}`,
      lat: parts[0],
      lon: parts[1],
    };
  }
  return null;
}

function MapClickHandler({
  activeField,
  onSelect,
}: {
  activeField: ActiveField;
  onSelect: (field: ActiveField, location: Location) => void;
}) {
  useMapEvents({
    click(event) {
      const location = {
        name: "Pinned location",
        subtitle: `${event.latlng.lat.toFixed(5)}, ${event.latlng.lng.toFixed(5)}`,
        lat: event.latlng.lat,
        lon: event.latlng.lng,
      };
      onSelect(activeField, location);
    },
  });
  return null;
}

function MapViewport({
  route,
  source,
  destination,
}: {
  route?: RouteOption;
  source: Location;
  destination: Location;
}) {
  const map = useMap();

  useEffect(() => {
    const points = route?.geometry.length
      ? route.geometry.map(
          (point) => [point.lat, point.lon] as [number, number],
        )
      : [
          [source.lat, source.lon] as [number, number],
          [destination.lat, destination.lon] as [number, number],
        ];

    map.fitBounds(points as LatLngBoundsExpression, {
      padding: [48, 48],
      maxZoom: 15,
    });
  }, [destination, map, route, source]);

  return null;
}

function RouteModeIcon({ route }: { route: RouteOption }) {
  const letters: Record<string, string> = {
    cab: "C",
    shared_auto: "A",
    electric_rickshaw: "E",
    multimodal: "M",
    metro: "M",
    bus: "B",
    walk: "W",
  };

  return (
    <span
      className="route-mode-icon"
      style={{ backgroundColor: route.color }}
      aria-hidden="true"
    >
      {letters[route.mode] ?? "R"}
    </span>
  );
}

function App() {
  const [source, setSource] = useState<Location>(PLACES[0]);
  const [destination, setDestination] = useState<Location>(PLACES[1]);
  const [sourceInput, setSourceInput] = useState(source.name);
  const [destinationInput, setDestinationInput] = useState(destination.name);
  const [activeField, setActiveField] = useState<ActiveField>("source");
  const [preference, setPreference] = useState<Preference>("fastest");
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedRouteId, setSelectedRouteId] =
    useState<Preference>("fastest");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedRoute = useMemo(
    () => routes.find((route) => route.id === selectedRouteId) ?? routes[0],
    [routes, selectedRouteId],
  );

  const updateLocation = useCallback(
    (field: ActiveField, location: Location) => {
      if (field === "source") {
        setSource(location);
        setSourceInput(location.name);
        setActiveField("destination");
      } else {
        setDestination(location);
        setDestinationInput(location.name);
      }
      setRoutes([]);
      setError("");
    },
    [],
  );

  const findRoutes = useCallback(
    async (nextPreference: Preference = preference) => {
      setLoading(true);
      setError("");
      try {
        const response = await axios.post<RouteResponse>(`${API_URL}/routes`, {
          source: { lat: source.lat, lon: source.lon },
          destination: { lat: destination.lat, lon: destination.lon },
          preference: nextPreference,
        });

        if (!response.data.success) {
          throw new Error(response.data.message ?? "No route found.");
        }

        setRoutes(response.data.routes);
        setSelectedRouteId(response.data.recommended_route_id);
        setNotice(response.data.notice);
      } catch (requestError) {
        const message = axios.isAxiosError(requestError)
          ? "Nagomi could not reach the routing engine. Start the FastAPI server and try again."
          : requestError instanceof Error
            ? requestError.message
            : "Something went wrong while planning this trip.";
        setError(message);
      } finally {
        setLoading(false);
      }
    },
    [destination, preference, source],
  );

  const applyInput = (field: ActiveField, value: string) => {
    const parsed = parseLocation(value);
    if (parsed) updateLocation(field, parsed);
  };

  const choosePreference = (nextPreference: Preference) => {
    setPreference(nextPreference);
    if (routes.length) {
      setSelectedRouteId(nextPreference);
    }
  };

  const swapLocations = () => {
    setSource(destination);
    setDestination(source);
    setSourceInput(destination.name);
    setDestinationInput(source.name);
    setRoutes([]);
  };

  return (
    <main className="app-shell">
      <aside className="planner-panel">
        <header className="brand">
          <div className="brand-mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div>
            <strong>Nagomi</strong>
            <small>GraphIQ Transit</small>
          </div>
          <span className="prototype-badge">Delhi beta</span>
        </header>

        <section className="planner-intro">
          <span className="eyebrow">Smarter urban mobility</span>
          <h1>Move better through the city.</h1>
          <p>Compare live traffic, transit, price, carbon, and safety.</p>
        </section>

        <section className="search-card">
          <div className="location-rail" aria-hidden="true">
            <span className="origin-dot" />
            <span className="rail-line" />
            <span className="destination-dot" />
          </div>

          <div className="location-fields">
            <label className={activeField === "source" ? "active" : ""}>
              <span>FROM</span>
              <input
                list="nagomi-places"
                value={sourceInput}
                onFocus={() => setActiveField("source")}
                onChange={(event) => setSourceInput(event.target.value)}
                onBlur={(event) => applyInput("source", event.target.value)}
                placeholder="Choose starting point"
              />
              <small>{source.subtitle}</small>
            </label>

            <div className="field-divider" />

            <label className={activeField === "destination" ? "active" : ""}>
              <span>TO</span>
              <input
                list="nagomi-places"
                value={destinationInput}
                onFocus={() => setActiveField("destination")}
                onChange={(event) => setDestinationInput(event.target.value)}
                onBlur={(event) =>
                  applyInput("destination", event.target.value)
                }
                placeholder="Choose destination"
              />
              <small>{destination.subtitle}</small>
            </label>
          </div>

          <button
            className="swap-button"
            type="button"
            onClick={swapLocations}
            aria-label="Swap source and destination"
          >
            <span>up</span>
            <span>down</span>
          </button>
        </section>

        <datalist id="nagomi-places">
          {PLACES.map((place) => (
            <option key={place.name} value={place.name}>
              {place.subtitle}
            </option>
          ))}
        </datalist>

        <section className="preference-section">
          <div className="section-heading">
            <h2>Optimize for</h2>
            <span>Choose what matters most</span>
          </div>
          <div className="preference-grid">
            {PREFERENCES.map((item) => (
              <button
                key={item.id}
                type="button"
                className={preference === item.id ? "selected" : ""}
                onClick={() => choosePreference(item.id)}
              >
                <span className={`preference-icon ${item.id}`}>
                  {item.id === "fastest"
                    ? "01"
                    : item.id === "cheapest"
                      ? "02"
                      : item.id === "eco"
                        ? "03"
                        : "04"}
                </span>
                <strong>{item.title}</strong>
                <small>{item.caption}</small>
              </button>
            ))}
          </div>
        </section>

        <button
          className="find-button"
          type="button"
          disabled={loading}
          onClick={() => void findRoutes()}
        >
          {loading ? <span className="spinner" /> : <span className="button-arrow">-&gt;</span>}
          {loading ? "Building route options..." : "Find smarter routes"}
        </button>

        {error && <div className="error-message">{error}</div>}

        {routes.length > 0 && (
          <section className="results-section">
            <div className="section-heading results-heading">
              <h2>Recommended routes</h2>
              <span>{routes.length} options compared</span>
            </div>

            <div className="route-list">
              {routes.map((route) => {
                const selected = route.id === selectedRouteId;
                return (
                  <button
                    key={route.id}
                    type="button"
                    className={`route-card ${selected ? "selected" : ""}`}
                    onClick={() => setSelectedRouteId(route.id)}
                  >
                    <div className="route-card-top">
                      <RouteModeIcon route={route} />
                      <div className="route-title">
                        <span>
                          {route.label}
                          {route.id === preference && (
                            <small className="best-tag">BEST MATCH</small>
                          )}
                        </span>
                        <strong>{route.duration_minutes} min</strong>
                      </div>
                    </div>
                    <div className="route-metrics">
                      <span>{route.mode_label}</span>
                      <span>INR {route.fare_inr}</span>
                      <span>{formatDistance(route.distance_meters)}</span>
                      <span>{route.co2_grams} g CO2</span>
                      <span>Safety {route.safety.score}/100</span>
                    </div>
                    {selected && (
                      <>
                        <div className="route-detail">
                          <div>
                            <span>Likely arrival</span>
                            <strong>
                              {route.reliability.likely_min}-
                              {route.reliability.likely_max} min
                            </strong>
                          </div>
                          <div>
                            <span>Transfers</span>
                            <strong>
                              {route.transfers === 0
                                ? "Direct"
                                : route.transfers}
                            </strong>
                          </div>
                          <div>
                            <span>Traffic</span>
                            <strong>
                              {route.traffic.is_live ? "Live " : "Modeled "}
                              {route.traffic.level}
                            </strong>
                          </div>
                          <div>
                            <span>Safety</span>
                            <strong>{route.safety.label}</strong>
                          </div>
                        </div>
                        <div className="journey-legs">
                          {route.legs.map((leg, index) => (
                            <div
                              className="journey-leg"
                              key={`${leg.label}-${leg.from}-${index}`}
                            >
                              <span
                                className="leg-dot"
                                style={{ backgroundColor: leg.color }}
                              />
                              <div>
                                <strong>{leg.label}</strong>
                                <small>
                                  {leg.from} to {leg.to}
                                </small>
                              </div>
                              <span>{leg.duration_minutes} min</span>
                            </div>
                          ))}
                        </div>
                        <div className="analysis-grid">
                          <div>
                            <span>TRAFFIC ANALYSIS</span>
                            <strong>
                              {route.traffic.current_speed_kph} km/h now
                            </strong>
                            <small>
                              {route.traffic.free_flow_speed_kph} km/h free flow
                              {" · "}
                              {route.traffic.delay_multiplier}x delay
                            </small>
                          </div>
                          <div>
                            <span>SAFETY ANALYSIS</span>
                            <strong>{route.safety.score}/100</strong>
                            <small>
                              {route.safety.factors.length
                                ? route.safety.factors.join(" · ")
                                : "Mode and road exposure scored"}
                            </small>
                          </div>
                        </div>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          </section>
        )}

        <footer className="panel-footer">
          <span className="status-dot" />
          <span>Local graph online</span>
          <span className="footer-separator" />
          <span>Bus + metro graph online</span>
        </footer>
      </aside>

      <section className="map-panel">
        <MapContainer
          center={[28.6315, 77.2167]}
          zoom={13}
          zoomControl={false}
          className="map"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          <MapClickHandler
            activeField={activeField}
            onSelect={updateLocation}
          />
          <MapViewport
            route={selectedRoute}
            source={source}
            destination={destination}
          />

          {routes
            .filter((route) => route.id !== selectedRouteId)
            .map((route) => (
              <Polyline
                key={route.id}
                positions={route.geometry.map((point) => [
                  point.lat,
                  point.lon,
                ])}
                pathOptions={{
                  color: route.color,
                  weight: 5,
                  opacity: 0.35,
                  dashArray: "7 10",
                }}
                eventHandlers={{
                  click: () => setSelectedRouteId(route.id),
                }}
              />
            ))}

          {selectedRoute && (
            <>
              {selectedRoute.legs.map((leg, index) => (
                <Polyline
                  key={`${leg.label}-${index}`}
                  positions={leg.geometry.map((point) => [
                    point.lat,
                    point.lon,
                  ])}
                  pathOptions={{
                    color: leg.color || selectedRoute.color,
                    weight: leg.mode === "walk" ? 5 : 7,
                    opacity: 0.95,
                    dashArray: leg.mode === "walk" ? "4 8" : undefined,
                  }}
                />
              ))}
            </>
          )}

          <CircleMarker
            center={[source.lat, source.lon]}
            radius={9}
            pathOptions={{
              color: "#ffffff",
              weight: 4,
              fillColor: "#28223e",
              fillOpacity: 1,
            }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              {source.name}
            </Tooltip>
          </CircleMarker>

          <CircleMarker
            center={[destination.lat, destination.lon]}
            radius={9}
            pathOptions={{
              color: "#ffffff",
              weight: 4,
              fillColor: selectedRoute?.color ?? "#6d5dfc",
              fillOpacity: 1,
            }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              {destination.name}
            </Tooltip>
          </CircleMarker>
        </MapContainer>

        <div className="map-topbar">
          <div className="map-instruction">
            <span className="pin-icon" />
            Click the map to set the {activeField}
          </div>
          <div className="data-pill">
            <span
              className={selectedRoute?.traffic.is_live ? "live" : "modeled"}
            />
            {selectedRoute
              ? `${selectedRoute.traffic.is_live ? "Live" : "Modeled"} traffic: ${selectedRoute.traffic.level}`
              : "Road + transit graph online"}
          </div>
        </div>

        {selectedRoute && (
          <div className="map-route-summary">
            <div
              className="summary-accent"
              style={{ backgroundColor: selectedRoute.color }}
            />
            <RouteModeIcon route={selectedRoute} />
            <div className="summary-copy">
              <span>{selectedRoute.label} route</span>
              <strong>
                {source.name} to {destination.name}
              </strong>
            </div>
            <div className="summary-stat">
              <span>TIME</span>
              <strong>{selectedRoute.duration_minutes} min</strong>
            </div>
            <div className="summary-stat">
              <span>FARE</span>
              <strong>INR {selectedRoute.fare_inr}</strong>
            </div>
            <div className="summary-stat green">
              <span>CO2</span>
              <strong>{selectedRoute.co2_grams} g</strong>
            </div>
            <div className="summary-stat safe">
              <span>SAFETY</span>
              <strong>{selectedRoute.safety.score}/100</strong>
            </div>
          </div>
        )}

        {notice && <div className="estimate-notice">{notice}</div>}
      </section>
    </main>
  );
}

export default App;
