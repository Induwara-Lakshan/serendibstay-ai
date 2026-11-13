import { useEffect, useMemo } from "react";
import { APIProvider, Map, Marker, useMap } from "@vis.gl/react-google-maps";

interface Location {
  latitude: number;
  longitude: number;
  name?: string;
}

export interface TransportRouteData {
  pickup: Location;
  destination: Location;
  distance_km: number;
  duration_minutes: number;
  geometry: {
    type: "LineString";
    coordinates: number[][];
  };
}

interface Props {
  route: TransportRouteData;
}

type LatLng = { lat: number; lng: number };

function RouteOverlay({ positions }: { positions: LatLng[] }) {
  const map = useMap();

  useEffect(() => {
    if (!map || positions.length < 2) return;

    const line = new google.maps.Polyline({
      path: positions,
      strokeColor: "#2563eb",
      strokeOpacity: 0.95,
      strokeWeight: 5,
      map,
    });

    const bounds = new google.maps.LatLngBounds();
    positions.forEach((position) => bounds.extend(position));
    map.fitBounds(bounds, 35);

    return () => line.setMap(null);
  }, [map, positions]);

  return null;
}

export default function TransportRouteMap({ route }: Props) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  // GeoJSON/OSRM: [longitude, latitude] -> Google Maps: {lat, lng}
  const positions = useMemo<LatLng[]>(
    () =>
      (route.geometry?.coordinates ?? [])
        .filter(
          (point) =>
            Array.isArray(point) &&
            point.length >= 2 &&
            Number.isFinite(point[0]) &&
            Number.isFinite(point[1]) &&
            point[1] >= -90 &&
            point[1] <= 90 &&
            point[0] >= -180 &&
            point[0] <= 180
        )
        .map(([longitude, latitude]) => ({ lat: latitude, lng: longitude })),
    [route.geometry]
  );

  const pickup: LatLng = {
    lat: route.pickup.latitude,
    lng: route.pickup.longitude,
  };
  const destination: LatLng = {
    lat: route.destination.latitude,
    lng: route.destination.longitude,
  };

  if (!apiKey) return <p>Google Maps API Key is missing.</p>;
  if (positions.length < 2) return <p>Route information is unavailable.</p>;

  return (
    <div style={{ width: "100%", minWidth: 0, boxSizing: "border-box" }}>
      <div style={{ marginBottom: 12 }}>
        <strong>Transport Route</strong>
        <p>
          Distance: {route.distance_km} km | Estimated time: {route.duration_minutes} min
        </p>
      </div>

      <div
        style={{
          height: "clamp(280px, 48dvh, 420px)",
          width: "100%",
          minWidth: 0,
          borderRadius: 14,
          overflow: "hidden",
        }}
      >
        
<APIProvider apiKey={apiKey} libraries={["places"]}>
  <Map
    defaultCenter={pickup}
    defaultZoom={12}
    gestureHandling="cooperative"
    style={{ width: "100%", height: "100%" }}
  >
    <Marker position={pickup} title="Pickup Location" />
    <Marker position={destination} title="Destination" />
    <RouteOverlay positions={positions} />
  </Map>
</APIProvider>

      </div>
    </div>
  );
}
