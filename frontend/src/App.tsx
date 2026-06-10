import { useState } from "react";
import axios from "axios";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  useMapEvents,
} from "react-leaflet";

function LocationSelector({
  onSelect,
}: {
  onSelect: (lat: number, lon: number) => void;
}) {
  useMapEvents({
    click(e) {
      onSelect(e.latlng.lat, e.latlng.lng);
    },
  });

  return null;
}

function App() {
  const [source, setSource] = useState<any>(null);
  const [destination, setDestination] = useState<any>(null);
  const [route, setRoute] = useState<any[]>([]);
  const [distance, setDistance] = useState<number | null>(null);

  const fetchRoute = async () => {
    if (!source || !destination) return;

    const response = await axios.post(
      "http://127.0.0.1:8000/route",
      null,
      {
        params: {
          source_lat: source.lat,
          source_lon: source.lng,
          dest_lat: destination.lat,
          dest_lon: destination.lng,
        },
      }
    );

    setRoute(
      response.data.route.map((p: any) => [
        p.lat,
        p.lon,
      ])
    );

    setDistance(response.data.distance_meters);
  };

  return (
    <div>
      <h1>Nagomi</h1>

      <button onClick={fetchRoute}>
        Calculate Route
      </button>

      {distance && (
        <h3>
          Distance: {distance.toFixed(2)} m
        </h3>
      )}

      <MapContainer
        center={[28.6315, 77.2167]}
        zoom={13}
        style={{
          height: "80vh",
          width: "100%",
        }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <LocationSelector
          onSelect={(lat, lon) => {
            if (!source) {
              setSource({
                lat,
                lng: lon,
              });
            } else if (!destination) {
              setDestination({
                lat,
                lng: lon,
              });
            } else {
              setSource({
                lat,
                lng: lon,
              });
              setDestination(null);
              setRoute([]);
              setDistance(null);
            }
          }}
        />

        {source && (
          <Marker position={[source.lat, source.lng]} />
        )}

        {destination && (
          <Marker
            position={[
              destination.lat,
              destination.lng,
            ]}
          />
        )}

        {route.length > 0 && (
          <Polyline positions={route} />
        )}
      </MapContainer>
    </div>
  );
}

export default App;