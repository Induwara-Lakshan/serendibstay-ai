import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const API_BASE_URL = "http://127.0.0.1:8011";

const hotelMarkerIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const highlightedHotelIcon = L.divIcon({
  className: "highlighted-hotel-marker",
  html: `<div style="width:22px;height:22px;background:#16a34a;border:3px solid white;border-radius:50%;box-shadow:0 0 0 3px #16a34a,0 3px 8px #0004;"></div>`,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
  popupAnchor: [0, -16],
});

const userMarkerIcon = L.divIcon({
  className: "user-location-marker",
  html: `<div style="width:16px;height:16px;background:#2563eb;border:3px solid white;border-radius:50%;box-shadow:0 0 0 3px #2563eb,0 2px 7px #0005;"></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

export interface HotelMapLocation {
  id: number;
  name: string;
  address?: string | null;
  district?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

interface HotelMapProps {
  hotels: HotelMapLocation[];
  height?: number;
  highlightedHotelId?: number;
}

type ValidHotelLocation = HotelMapLocation & { latitude: number; longitude: number };
type RouteResponse = {
  distance_km: number;
  duration_minutes: number;
  route_coordinates: [number, number][];
};

function hasValidCoordinates(hotel: HotelMapLocation): hotel is ValidHotelLocation {
  return (
    typeof hotel.latitude === "number" &&
    typeof hotel.longitude === "number" &&
    Number.isFinite(hotel.latitude) &&
    Number.isFinite(hotel.longitude) &&
    hotel.latitude >= -90 && hotel.latitude <= 90 &&
    hotel.longitude >= -180 && hotel.longitude <= 180
  );
}

function getHotelLocationUrl(hotel: HotelMapLocation): string {
  if (hasValidCoordinates(hotel)) {
    return `https://www.openstreetmap.org/?mlat=${hotel.latitude}&mlon=${hotel.longitude}#map=16/${hotel.latitude}/${hotel.longitude}`;
  }
  const searchText = [hotel.name, hotel.address, hotel.district, "Sri Lanka"]
    .filter(Boolean).join(", ");
  return `https://www.openstreetmap.org/search?query=${encodeURIComponent(searchText)}`;
}

function googleMapsDirectionsUrl(hotel: ValidHotelLocation, userLocation?: L.LatLngTuple): string {
  const params = new URLSearchParams({
    api: "1",
    destination: `${hotel.latitude},${hotel.longitude}`,
    travelmode: "driving",
  });
  // When location is unavailable, Google Maps may use its own starting location.
  if (userLocation) params.set("origin", `${userLocation[0]},${userLocation[1]}`);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

function FitHotelMarkers({
  hotels,
  routeCoordinates,
  userLocation,
}: {
  hotels: ValidHotelLocation[];
  routeCoordinates: L.LatLngTuple[];
  userLocation: L.LatLngTuple | null;
}) {
  const map = useMap();
  useEffect(() => {
    if (routeCoordinates.length > 1) {
      const bounds = L.latLngBounds(routeCoordinates);
      if (userLocation) bounds.extend(userLocation);
      map.fitBounds(bounds, { padding: [35, 35], maxZoom: 15 });
    } else if (hotels.length === 1) {
      map.setView([hotels[0].latitude, hotels[0].longitude], 14);
    } else if (hotels.length > 1) {
      map.fitBounds(L.latLngBounds(hotels.map((hotel): L.LatLngTuple => [hotel.latitude, hotel.longitude])), {
        padding: [35, 35], maxZoom: 15,
      });
    }
  }, [hotels, routeCoordinates, userLocation, map]);
  return null;
}

function FixMapSize() {
  const map = useMap();
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => map.invalidateSize());
    return () => window.cancelAnimationFrame(frame);
  }, [map]);
  return null;
}

export default function HotelMap({ hotels, height = 320, highlightedHotelId }: HotelMapProps) {
  const validHotels = useMemo(() => (hotels ?? []).filter(hasValidCoordinates), [hotels]);
  const [selectedHotelId, setSelectedHotelId] = useState<number | null>(null);
  const [userLocation, setUserLocation] = useState<L.LatLngTuple | null>(null);
  const [route, setRoute] = useState<RouteResponse | null>(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [routeError, setRouteError] = useState("");
  const requestRef = useRef(0);
  const controllerRef = useRef<AbortController | null>(null);

  const highlightedHotel = validHotels.find((hotel) => hotel.id === highlightedHotelId);
  const selectedHotel = validHotels.find((hotel) => hotel.id === selectedHotelId)
    ?? highlightedHotel ?? (validHotels.length === 1 ? validHotels[0] : null);
  const selectedId = selectedHotel?.id ?? null;
  const destinationKey = selectedHotel ? `${selectedHotel.id}:${selectedHotel.latitude}:${selectedHotel.longitude}` : "none";

  useEffect(() => {
    requestRef.current += 1;
    controllerRef.current?.abort();
    controllerRef.current = null;
    setRoute(null);
    setUserLocation(null);
    setRouteError("");
    setLoadingRoute(false);
  }, [destinationKey]);

  useEffect(() => () => {
    requestRef.current += 1;
    controllerRef.current?.abort();
  }, []);

  const routeCoordinates = useMemo<L.LatLngTuple[]>(() => {
    if (!route) return [];
    return route.route_coordinates.map(([lat, lng]) => [lat, lng]);
  }, [route]);

  const showRoute = () => {
    if (!selectedHotel || loadingRoute) return;
    if (!navigator.geolocation) {
      setRouteError("Your browser does not support location access.");
      return;
    }
    if (!window.isSecureContext) {
      setRouteError("Location access requires HTTPS or localhost. Open the app on localhost for testing.");
      return;
    }

    const requestId = ++requestRef.current;
    controllerRef.current?.abort();
    setLoadingRoute(true);
    setRoute(null);
    setRouteError("");
    setUserLocation(null);

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        if (requestId !== requestRef.current) return;
        const start: L.LatLngTuple = [position.coords.latitude, position.coords.longitude];
        setUserLocation(start);
        const controller = new AbortController();
        controllerRef.current = controller;
        const params = new URLSearchParams({
          start_lat: String(start[0]),
          start_lng: String(start[1]),
          end_lat: String(selectedHotel.latitude),
          end_lng: String(selectedHotel.longitude),
        });
        try {
          const response = await fetch(`${API_BASE_URL}/directions/route?${params}`, {
            signal: controller.signal,
          });
          if (!response.ok) throw new Error("Unable to calculate the driving route. Please try again.");
          const result: RouteResponse = await response.json();
          if (!Array.isArray(result.route_coordinates) || result.route_coordinates.length < 2 ||
              !Number.isFinite(result.distance_km) || !Number.isFinite(result.duration_minutes) ||
              !result.route_coordinates.every((point) => Array.isArray(point) && point.length === 2 &&
                Number.isFinite(point[0]) && Number.isFinite(point[1]))) {
            throw new Error("The routing service returned an invalid route.");
          }
          if (requestId === requestRef.current) setRoute(result);
        } catch (error) {
          if (requestId === requestRef.current && !controller.signal.aborted) {
            setRouteError(error instanceof Error ? error.message : "Route request failed.");
          }
        } finally {
          if (requestId === requestRef.current) setLoadingRoute(false);
        }
      },
      (error) => {
        if (requestId !== requestRef.current) return;
        const message = error.code === 1
          ? "Location permission was denied. Allow location access in your browser and try again."
          : error.code === 2
            ? "Your current location is unavailable. Check your device location settings."
            : "Getting your location timed out. Please try again.";
        setRouteError(message);
        setLoadingRoute(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 }
    );
  };

  if (!hotels || hotels.length === 0) return null;

  const mapCenter: L.LatLngTuple = validHotels.length
    ? [validHotels[0].latitude, validHotels[0].longitude]
    : [7.8731, 80.7718];

  return (
    <div className="hotel-map-results" style={{ width: "100%", marginTop: 12 }}>
      {validHotels.length > 0 ? (
        <>
          <div className="hotel-map-wrapper" style={{ height: `${height}px`, width: "100%", borderRadius: 14, overflow: "hidden", border: "1px solid #dce5df" }}>
            <MapContainer center={mapCenter} zoom={12} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {validHotels.map((hotel) => (
                <Marker
                  key={hotel.id}
                  position={[hotel.latitude, hotel.longitude]}
                  icon={hotel.id === selectedId ? highlightedHotelIcon : hotelMarkerIcon}
                >
                  <Popup>
                    <div style={{ minWidth: 170 }}>
                      <strong>{hotel.name}</strong>
                      {hotel.address && <p style={{ margin: "6px 0" }}>{hotel.address}</p>}
                      <button type="button" onClick={() => setSelectedHotelId(hotel.id)} style={{ cursor: "pointer", marginBottom: 7 }}>
                        Select for route
                      </button>
                      <br />
                      <a href={getHotelLocationUrl(hotel)} target="_blank" rel="noopener noreferrer">View Hotel Location ↗</a>
                    </div>
                  </Popup>
                </Marker>
              ))}
              {userLocation && <Marker position={userLocation} icon={userMarkerIcon}><Popup>My current location</Popup></Marker>}
              {routeCoordinates.length > 1 && (
                <Polyline positions={routeCoordinates} pathOptions={{ color: "#2563eb", weight: 5, opacity: 0.9 }} />
              )}
              <FitHotelMarkers hotels={validHotels} routeCoordinates={routeCoordinates} userLocation={userLocation} />
              <FixMapSize />
            </MapContainer>
          </div>

          <div style={{ marginTop: 12, padding: 12, border: "1px solid #dce5df", borderRadius: 10, background: "#f5faf7" }}>
            <strong style={{ display: "block", color: "#145c45", marginBottom: 8 }}>🚗 Route to Hotel</strong>
            {validHotels.length > 1 && (
              <label style={{ display: "block", marginBottom: 10, fontSize: 13 }}>
                Destination hotel
                <select
                  value={selectedId ?? ""}
                  onChange={(event) => setSelectedHotelId(Number(event.target.value))}
                  style={{ display: "block", width: "100%", marginTop: 5, padding: 8, borderRadius: 7, border: "1px solid #bdd3c8" }}
                >
                  {!selectedHotel && <option value="" disabled>Select a hotel</option>}
                  {validHotels.map((hotel) => <option key={hotel.id} value={hotel.id}>{hotel.name}</option>)}
                </select>
              </label>
            )}
            {selectedHotel ? (
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <button type="button" onClick={showRoute} disabled={loadingRoute}
                  style={{ padding: "9px 12px", background: "#16745f", color: "white", border: 0, borderRadius: 8, cursor: loadingRoute ? "wait" : "pointer", fontWeight: 600 }}>
                  {loadingRoute ? "Finding route…" : "📍 Show Route from My Location"}
                </button>
                <a href={googleMapsDirectionsUrl(selectedHotel, userLocation ?? undefined)} target="_blank" rel="noopener noreferrer"
                  style={{ display: "inline-block", padding: "9px 12px", background: "white", color: "#145c45", border: "1px solid #16745f", borderRadius: 8, fontWeight: 600, textDecoration: "none" }}>
                  🧭 Open in Google Maps ↗
                </a>
              </div>
            ) : <p style={{ margin: 0, fontSize: 13 }}>Select a hotel to calculate a route.</p>}
            {routeError && <p role="alert" style={{ color: "#b42318", fontSize: 13, marginBottom: 0 }}>{routeError}</p>}
            {route && <p style={{ marginBottom: 0, fontSize: 13 }}>
              <strong>Distance:</strong> {route.distance_km.toFixed(2)} km &nbsp;·&nbsp;
              <strong>Estimated driving time:</strong> {route.duration_minutes.toFixed(1)} min
            </p>}
            <p style={{ fontSize: 11, color: "#647067", marginBottom: 0 }}>
              Location is requested only when you select Show Route. Driving times are estimates, not live traffic predictions.
            </p>
          </div>
        </>
      ) : (
        <div className="hotel-map-empty" style={{ padding: 12, borderRadius: 10, background: "#f5f7f5", color: "#555", fontSize: 13 }}>
          Exact map coordinates are not available for these hotels. You can search their locations using the links below.
        </div>
      )}

      <div className="hotel-location-list" style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 10 }}>
        {hotels.map((hotel) => (
          <div key={hotel.id} className="hotel-location-item" style={{ padding: 12, border: "1px solid #e0e8e2", borderRadius: 10, background: "#ffffff" }}>
            <strong style={{ display: "block", color: "#145c45", marginBottom: 5 }}>{hotel.name}</strong>
            {hotel.address && <div style={{ fontSize: 13, color: "#555", marginBottom: 7 }}>📍 {hotel.address}</div>}
            {hotel.district && <div style={{ fontSize: 12, color: "#777", marginBottom: 7 }}>District: {hotel.district}</div>}
            <a href={getHotelLocationUrl(hotel)} target="_blank" rel="noopener noreferrer"
              style={{ color: "#16745f", fontSize: 13, fontWeight: 600, textDecoration: "none" }}>
              {hasValidCoordinates(hotel) ? "View Exact Location on OpenStreetMap ↗" : "Search Location on OpenStreetMap ↗"}
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
