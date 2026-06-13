import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  provider?: string;
  result_type?: string;
  confidence?: number;
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

type PlaceSearchResponse = {
  places: Location[];
  source: "geoapify" | "local_graph";
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8010";

const DEFAULT_PLACES: Location[] = [
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
  const knownPlace = DEFAULT_PLACES.find(
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
  centerOnUser,
  onCenterOnUserHandled,
}: {
  route?: RouteOption;
  source: Location;
  destination: Location;
  centerOnUser?: [number, number] | null;
  onCenterOnUserHandled?: () => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (centerOnUser) {
      map.flyTo(centerOnUser, 15, { animate: true, duration: 1.5 });
      if (onCenterOnUserHandled) {
        onCenterOnUserHandled();
      }
      return;
    }

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
  }, [destination, map, route, source, centerOnUser, onCenterOnUserHandled]);

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
  const [source, setSource] = useState<Location>(DEFAULT_PLACES[0]);
  const [destination, setDestination] = useState<Location>(DEFAULT_PLACES[1]);
  const [sourceInput, setSourceInput] = useState(source.name);
  const [destinationInput, setDestinationInput] = useState(destination.name);
  const [activeField, setActiveField] = useState<ActiveField>("source");
  const [preference, setPreference] = useState<Preference>("fastest");
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedRouteId, setSelectedRouteId] =
    useState<Preference>("fastest");
  const [notice, setNotice] = useState("");
  const [userLocation, setUserLocation] = useState<Location | null>(null);
  const [userGps, setUserGps] = useState<{ lat: number; lon: number } | null>(null);
  const [locatingField, setLocatingField] = useState<ActiveField | null>(null);
  const [centerOnUser, setCenterOnUser] = useState<[number, number] | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const reverseGeocodedRef = useRef(false);

  useEffect(() => {
    if (!navigator.geolocation) return;

    const onSuccess = (position: GeolocationPosition) => {
      const { latitude, longitude } = position.coords;
      setUserGps({ lat: latitude, lon: longitude });

      // Only reverse geocode once so we don't spam the API on every GPS update
      if (!reverseGeocodedRef.current) {
        reverseGeocodedRef.current = true;
        axios.get<Location>(`${API_URL}/places/reverse`, {
          params: { lat: latitude, lon: longitude },
        }).then((response) => {
          setUserLocation(response.data);
        }).catch(() => {
          setUserLocation({
            name: "Current Location",
            subtitle: `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`,
            lat: latitude,
            lon: longitude,
          });
        });
      }
    };

    const onError = (err: GeolocationPositionError) => {
      console.warn("GPS watch error:", err.message);
    };

    watchIdRef.current = navigator.geolocation.watchPosition(
      onSuccess,
      onError,
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 }
    );

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
    };
  }, []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [suggestions, setSuggestions] = useState<Location[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchSource, setSearchSource] = useState<
    "geoapify" | "local_graph"
  >("local_graph");

  const activeQuery =
    activeField === "source" ? sourceInput : destinationInput;
  const locationsResolved =
    sourceInput.trim() === source.name &&
    destinationInput.trim() === destination.name;

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
      setSuggestions([]);
      setSearchOpen(false);
    },
    [],
  );

  const handleSelectCurrentLocation = useCallback((field: ActiveField) => {
    if (!navigator.geolocation) {
      setError("Geolocation is not supported by your browser.");
      return;
    }
    setLocatingField(field);
    setError("");
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        try {
          const response = await axios.get<Location>(
            `${API_URL}/places/reverse`,
            { params: { lat: latitude, lon: longitude } }
          );
          updateLocation(field, response.data);
        } catch (err) {
          const fallbackLocation: Location = {
            name: "Current Location",
            subtitle: `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`,
            lat: latitude,
            lon: longitude,
          };
          updateLocation(field, fallbackLocation);
        } finally {
          setLocatingField(null);
        }
      },
      (err) => {
        setError("Location access denied or timed out. Please enable GPS.");
        setLocatingField(null);
      },
      { enableHighAccuracy: true, timeout: 7000 }
    );
  }, [updateLocation]);

  const handleLocateUser = useCallback(() => {
    // If watchPosition already has a fix, fly there immediately
    if (userGps) {
      setCenterOnUser([userGps.lat, userGps.lon]);
      return;
    }
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setCenterOnUser([latitude, longitude]);
        setUserGps({ lat: latitude, lon: longitude });
      },
      () => {
        alert("Unable to retrieve your location. Please ensure location access is allowed.");
      },
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
    );

  }, [userGps]);

  const handleCenterOnUserHandled = useCallback(() => {
    setCenterOnUser(null);
  }, []);

  useEffect(() => {
    const query = activeQuery.trim();
    if (!searchOpen || query.length < 2) return;

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await axios.get<PlaceSearchResponse>(
          `${API_URL}/places`,
          {
            params: { q: query },
            signal: controller.signal,
          },
        );
        setSuggestions(response.data.places);
        setSearchSource(response.data.source);
      } catch (requestError) {
        if (!axios.isCancel(requestError)) {
          setSuggestions([]);
          setSearchSource("local_graph");
        }
      }
    }, 250);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [activeQuery, searchOpen]);

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
          ? typeof requestError.response?.data?.message === "string"
            ? requestError.response.data.message
            : "Nagomi could not reach the routing engine. Start the FastAPI server and try again."
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
    if (locatingField !== null) return;
    const currentLoc = field === "source" ? source : destination;
    if (value.trim() === currentLoc.name) return;
    if (value.trim() === "Locating...") return;

    const suggested = suggestions.find(
      (place) => place.name.toLowerCase() === value.trim().toLowerCase(),
    );
    const parsed = suggested ?? suggestions[0] ?? parseLocation(value);
    if (parsed) {
      updateLocation(field, parsed);
    } else {
      if (field === "source") {
        setSourceInput(source.name);
      } else {
        setDestinationInput(destination.name);
      }
    }
  };

  const handleLocationKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>,
    field: ActiveField,
  ) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const selected = suggestions[0] ?? parseLocation(event.currentTarget.value);
      if (selected) updateLocation(field, selected);
    }
    if (event.key === "Escape") {
      setSearchOpen(false);
    }
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
                value={locatingField === "source" ? "Locating..." : sourceInput}
                disabled={locatingField === "source"}
                onFocus={() => {
                  setActiveField("source");
                  setSearchOpen(true);
                }}
                onChange={(event) => {
                  setSourceInput(event.target.value);
                  setSearchOpen(true);
                }}
                onBlur={(event) => applyInput("source", event.target.value)}
                onKeyDown={(event) =>
                  handleLocationKeyDown(event, "source")
                }
                placeholder="Choose starting point"
                autoComplete="off"
              />
              <small>{source.subtitle}</small>
            </label>

            <div className="field-divider" />

            <label className={activeField === "destination" ? "active" : ""}>
              <span>TO</span>
              <input
                value={locatingField === "destination" ? "Locating..." : destinationInput}
                disabled={locatingField === "destination"}
                onFocus={() => {
                  setActiveField("destination");
                  setSearchOpen(true);
                }}
                onChange={(event) => {
                  setDestinationInput(event.target.value);
                  setSearchOpen(true);
                }}
                onBlur={(event) =>
                  applyInput("destination", event.target.value)
                }
                onKeyDown={(event) =>
                  handleLocationKeyDown(event, "destination")
                }
                placeholder="Choose destination"
                autoComplete="off"
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

          {searchOpen && (
            <div className="place-suggestions">
              <button
                type="button"
                className="gps-suggestion-row"
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSelectCurrentLocation(activeField);
                }}
                disabled={locatingField !== null}
              >
                <span className="suggestion-gps-icon">🎯</span>
                <span>
                  <strong>Use current location</strong>
                  <small>Detect location using GPS</small>
                </span>
                {locatingField === activeField && <span className="spinner suggestion-spinner" />}
              </button>

              {activeQuery.trim().length >= 2 ? (
                <>
                  <div className="suggestion-source">
                    <span>
                      {searchSource === "geoapify"
                        ? "Searching across Delhi"
                        : "Offline road and landmark search"}
                    </span>
                    <small>
                      {searchSource === "geoapify" ? "Geoapify" : "Local graph"}
                    </small>
                  </div>
                  {suggestions.length > 0 ? (
                    suggestions.map((place) => (
                      <button
                        key={`${place.name}-${place.lat}-${place.lon}`}
                        type="button"
                        onMouseDown={(event) => {
                          event.preventDefault();
                          updateLocation(activeField, place);
                        }}
                      >
                        <span className="suggestion-pin" />
                        <span>
                          <strong>{place.name}</strong>
                          <small>{place.subtitle}</small>
                        </span>
                        <small className="result-type">
                          {place.result_type?.replaceAll("_", " ") ?? "place"}
                        </small>
                      </button>
                    ))
                  ) : (
                    <p>No matching Delhi location found.</p>
                  )}
                </>
              ) : (
                <>
                  <div className="suggestion-source">
                    <span>Quick Select Delhi Landmarks</span>
                    <small>Curated</small>
                  </div>
                  {DEFAULT_PLACES.slice(0, 6).map((place) => (
                    <button
                      key={`${place.name}-${place.lat}-${place.lon}`}
                      type="button"
                      onMouseDown={(event) => {
                        event.preventDefault();
                        updateLocation(activeField, place);
                      }}
                    >
                      <span className="suggestion-pin" />
                      <span>
                        <strong>{place.name}</strong>
                        <small>{place.subtitle}</small>
                      </span>
                      <small className="result-type">landmark</small>
                    </button>
                  ))}
                </>
              )}
            </div>
          )}
        </section>

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
          disabled={loading || !locationsResolved}
          onClick={() => void findRoutes()}
        >
          {loading ? <span className="spinner" /> : <span className="button-arrow">-&gt;</span>}
          {loading ? "Building route options..." : "Find smarter routes"}
        </button>

        {!locationsResolved && (
          <p className="selection-hint">
            Choose a search suggestion or press Enter to confirm both locations.
          </p>
        )}

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
            centerOnUser={centerOnUser}
            onCenterOnUserHandled={handleCenterOnUserHandled}
          />

          {userGps && (
            <>
              {/* Outer pulsing halo */}
              <CircleMarker
                center={[userGps.lat, userGps.lon]}
                radius={18}
                pathOptions={{
                  color: "#3b82f6",
                  weight: 0,
                  fillColor: "#3b82f6",
                  fillOpacity: 0.18,
                  className: "user-location-pulse",
                }}
              />
              {/* Solid blue dot */}
              <CircleMarker
                center={[userGps.lat, userGps.lon]}
                radius={8}
                pathOptions={{
                  color: "#ffffff",
                  weight: 3,
                  fillColor: "#2563eb",
                  fillOpacity: 1,
                }}
              >
                <Tooltip direction="top" offset={[0, -8]} permanent={false}>
                  <span style={{ fontWeight: 700, fontSize: "11px" }}>📍 You are here</span>
                  {userLocation && (
                    <span style={{ display: "block", fontSize: "10px", opacity: 0.75 }}>
                      {userLocation.name}
                    </span>
                  )}
                </Tooltip>
              </CircleMarker>
            </>
          )}

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

        <button
          className="locate-me-btn"
          style={{ bottom: selectedRoute ? "130px" : "24px" }}
          onClick={handleLocateUser}
          title="Find my location"
          type="button"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 2v4" />
            <path d="M12 18v4" />
            <path d="M4 12H2" />
            <path d="M22 12h-4" />
          </svg>
        </button>

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
