
import { useEffect, useMemo, useRef, useState } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Circle,
  Popup,
  Polyline,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

const API_BASE_URL = "http://127.0.0.1:8011";

// Avoid frequent route requests when GPS updates.
const ROUTE_REFRESH_MS = 60_000;
const ROUTE_REFRESH_DISTANCE_METERS = 100;
const GPS_STALE_MS = 30_000;
const GPS_MAX_ACCURACY_METERS = 1500;

const locationIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

type Coordinates = {
  lat: number;
  lng: number;
};

type GeocodeCandidate = {
  name: string;
  latitude: number;
  longitude: number;
};

type GeocodeResponse = {
  ambiguous: boolean;
  candidates: GeocodeCandidate[];
};

type RouteResponse = {
  distance_km: number;
  duration_minutes: number;
  route_coordinates: [number, number][];
};

type DriverNavigationMapProps = {
  pickupLocation: string;
  destination: string;
};

type RouteSummary = {
  toPickup: RouteResponse;
  toDestination: RouteResponse;
};

function toCoordinates(
  location: GeocodeCandidate
): Coordinates {
  return {
    lat: location.latitude,
    lng: location.longitude,
  };
}

function toPosition(
  location: Coordinates
): [number, number] {
  return [location.lat, location.lng];
}

function distanceMeters(
  first: Coordinates,
  second: Coordinates
): number {
  return L.latLng(
    first.lat,
    first.lng
  ).distanceTo(
    L.latLng(second.lat, second.lng)
  );
}

async function geocodeLocation(
  placeName: string,
  signal?: AbortSignal
): Promise<GeocodeResponse> {
  const response = await fetch(
    `${API_BASE_URL}/directions/geocode`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        place_name: placeName,
      }),
      signal,
    }
  );

  if (!response.ok) {
    throw new Error(
      `Unable to find location: ${placeName}`
    );
  }

  return response.json();
}

async function fetchRoute(
  start: Coordinates,
  end: Coordinates,
  signal?: AbortSignal
): Promise<RouteResponse> {
  const params = new URLSearchParams({
    start_lat: String(start.lat),
    start_lng: String(start.lng),
    end_lat: String(end.lat),
    end_lng: String(end.lng),
  });

  const response = await fetch(
    `${API_BASE_URL}/directions/route?${params}`,
    { signal }
  );

  if (!response.ok) {
    throw new Error(
      "Unable to calculate driving route."
    );
  }

  const data: RouteResponse =
    await response.json();

  if (
    !Array.isArray(data.route_coordinates) ||
    data.route_coordinates.length < 2
  ) {
    throw new Error(
      "Route coordinates are unavailable."
    );
  }

  return data;
}

type MapSelectionTarget = "driver" | "pickup" | "destination";

function MapClickSelector({
  enabled,
  onSelect,
}: {
  enabled: boolean;
  onSelect: (coordinates: Coordinates) => void;
}) {
  useMapEvents({
    click(event) {
      if (enabled) onSelect({ lat: event.latlng.lat, lng: event.latlng.lng });
    },
  });
  return null;
}

type MapFocus = "all" | "driver" | "pickup" | "destination";

// Focus only when a button is clicked, or when the route first becomes available.
// Do not repeatedly reset zoom while the driver pans or zooms the map.
function NavigationMapCamera({
  positions,
  driver,
  pickup,
  destination,
  focus,
  focusRequest,
}: {
  positions: [number, number][];
  driver: Coordinates;
  pickup: Coordinates | null;
  destination: Coordinates | null;
  focus: MapFocus;
  focusRequest: number;
}) {
  const map = useMap();
  const lastAutoFit = useRef<[number, number][] | null>(null);
  const lastFocusRequest = useRef(0);

  useEffect(() => {
    // Automatically show the complete route once it has been calculated.
    if (positions.length < 2 || lastAutoFit.current !== null) return;
    lastAutoFit.current = positions;
    if (lastFocusRequest.current === 0) {
      map.fitBounds(L.latLngBounds(positions), {
        padding: [45, 45],
        maxZoom: 14,
      });
    }
  }, [map, positions]);

  useEffect(() => {
    if (focusRequest === 0 || focusRequest === lastFocusRequest.current) return;
    lastFocusRequest.current = focusRequest;

    if (focus === "all") {
      const points = positions.length > 1
        ? positions
        : [toPosition(driver), ...(pickup ? [toPosition(pickup)] : []), ...(destination ? [toPosition(destination)] : [])];
      if (points.length > 1) {
        map.fitBounds(L.latLngBounds(points), { padding: [45, 45], maxZoom: 14 });
      } else {
        map.flyTo(toPosition(driver), 16, { duration: 0.7 });
      }
      return;
    }

    const target = focus === "driver" ? driver : focus === "pickup" ? pickup : destination;
    if (target) map.flyTo(toPosition(target), 16, { duration: 0.7 });
  }, [map, focus, focusRequest, positions, driver, pickup, destination]);

  return null;
}

export default function DriverNavigationMap({
  pickupLocation,
  destination,
}: DriverNavigationMapProps) {
  const [driverLocation, setDriverLocation] =
    useState<Coordinates | null>(null);

    const [locationMode, setLocationMode] =
  useState<"gps" | "manual">("gps");

const [gpsLocation, setGpsLocation] =
  useState<Coordinates | null>(null);
const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
const [gpsTimestamp, setGpsTimestamp] = useState<number | null>(null);
const [gpsNow, setGpsNow] = useState(Date.now());
const [routeAnchor, setRouteAnchor] = useState<Coordinates | null>(null);
const lastRouteAnchorRef = useRef<{ position: Coordinates; time: number } | null>(null);

const [manualLocationInput, setManualLocationInput] =
  useState("");

const [manualLocationCandidates, setManualLocationCandidates] =
  useState<GeocodeCandidate[]>([]);

const [manualLocationError, setManualLocationError] =
  useState("");

const [searchingManualLocation, setSearchingManualLocation] =
  useState(false);

  const [locationError, setLocationError] =
    useState("");




  const [pickupCandidates, setPickupCandidates] =
    useState<GeocodeCandidate[]>([]);

  const [
    destinationCandidates,
    setDestinationCandidates,
  ] = useState<GeocodeCandidate[]>([]);

  const [selectedPickup, setSelectedPickup] =
    useState<GeocodeCandidate | null>(null);

  const [
    selectedDestination,
    setSelectedDestination,
  ] = useState<GeocodeCandidate | null>(null);

  const [pickupSearchInput, setPickupSearchInput] = useState(pickupLocation);
  const [destinationSearchInput, setDestinationSearchInput] = useState(destination);
  const [searchingTarget, setSearchingTarget] = useState<"pickup" | "destination" | null>(null);
  const [mapSelectionTarget, setMapSelectionTarget] = useState<MapSelectionTarget | null>(null);
  const [locationNotice, setLocationNotice] = useState("");

  const [routeData, setRouteData] =
    useState<RouteSummary | null>(null);

  const [routeError, setRouteError] =
    useState("");

  const [pickupError, setPickupError] =
    useState("");

  const [destinationError, setDestinationError] =
    useState("");

  const [loadingLocations, setLoadingLocations] =
    useState(false);

  const [loadingRoute, setLoadingRoute] =
    useState(false);

  const [refreshRequested, setRefreshRequested] =
    useState(0);
  const [refreshStatus, setRefreshStatus] = useState("");
  // Clear Route pauses automatic recalculation until Refresh Route is pressed.
  const [routeCleared, setRouteCleared] = useState(false);
  const manualRefreshPending = useRef(false);

  const [mapFocus, setMapFocus] = useState<MapFocus>("all");
  const [mapFocusRequest, setMapFocusRequest] = useState(0);
  const focusMap = (target: MapFocus) => {
    setMapFocus(target);
    setMapFocusRequest((value) => value + 1);
  };

  const lastRouteRequest = useRef<{
    time: number;
    driver: Coordinates;
    key: string;
  } | null>(null);

  const locationModeRef = useRef<"gps" | "manual">("gps");

  const changeLocationMode = (mode: "gps" | "manual") => {
    locationModeRef.current = mode;
    setLocationMode(mode);
    const freshGps = gpsLocation && gpsTimestamp && Date.now() - gpsTimestamp < GPS_STALE_MS
      ? gpsLocation : null;
    const nextLocation = mode === "gps" ? freshGps : null;
    setDriverLocation(nextLocation);
    setRouteAnchor(nextLocation);
    lastRouteAnchorRef.current = nextLocation ? { position: nextLocation, time: Date.now() } : null;
    setRouteData(null);
    setRouteError("");
    lastRouteRequest.current = null;
  };

  const searchManualLocation = async () => {
    const searchText = manualLocationInput.trim();

    if (searchText.length < 2) {
      setManualLocationError(
        "Enter a location name (at least 2 characters)."
      );
      return;
    }

    setSearchingManualLocation(true);
    setManualLocationError("");
    setManualLocationCandidates([]);

    try {
      const result = await geocodeLocation(searchText);

      if (result.candidates.length === 0) {
        setManualLocationError("Location not found.");
        return;
      }

      setManualLocationCandidates(result.candidates);
    } catch (error) {
      setManualLocationError(
        error instanceof Error
          ? error.message
          : "Unable to search location."
      );
    } finally {
      setSearchingManualLocation(false);
    }
  };

  const applyCandidate = (target: "pickup" | "destination", candidate: GeocodeCandidate) => {
    if (target === "pickup") {
      setSelectedPickup(candidate);
      setPickupCandidates([]);
      setPickupError("");
    } else {
      setSelectedDestination(candidate);
      setDestinationCandidates([]);
      setDestinationError("");
    }
    setRouteData(null);
    setRouteError("");
    lastRouteRequest.current = null;
  };

  const searchTripLocation = async (target: "pickup" | "destination") => {
    const query = (target === "pickup" ? pickupSearchInput : destinationSearchInput).trim();
    const setError = target === "pickup" ? setPickupError : setDestinationError;
    const setCandidates = target === "pickup" ? setPickupCandidates : setDestinationCandidates;
    if (query.length < 2) {
      setError("Enter at least 2 characters.");
      return;
    }
    setSearchingTarget(target);
    setError("");
    setCandidates([]);
    try {
      const result = await geocodeLocation(query);
      if (!result.candidates.length) {
        setError("No matching places found. Try selecting a point on the map.");
      } else {
        setCandidates(result.candidates);
        if (result.candidates.length === 1) applyCandidate(target, result.candidates[0]);
      }
    } catch {
      setError("Location search failed. Try a different spelling or choose a point on the map.");
    } finally {
      setSearchingTarget(null);
    }
  };

  const selectMapPoint = (coordinates: Coordinates) => {
    if (!mapSelectionTarget) return;
    const name = `Map pin (${coordinates.lat.toFixed(5)}, ${coordinates.lng.toFixed(5)})`;
    if (mapSelectionTarget === "driver") {
      locationModeRef.current = "manual";
      setLocationMode("manual");
      setDriverLocation(coordinates);
      setRouteAnchor(coordinates);
      lastRouteAnchorRef.current = { position: coordinates, time: Date.now() };
      setManualLocationInput(name);
      setManualLocationCandidates([]);
      setManualLocationError("");
      setLocationNotice("Driver location selected from the map.");
    } else {
      applyCandidate(mapSelectionTarget, {
        name,
        latitude: coordinates.lat,
        longitude: coordinates.lng,
      });
      setLocationNotice(`${mapSelectionTarget === "pickup" ? "Pickup" : "Destination"} selected from the map.`);
    }
    setRouteData(null);
    setRouteError("");
    lastRouteRequest.current = null;
    setMapSelectionTarget(null);
  };

  // Watch GPS only in GPS mode. Browser permission does not guarantee a fix.
  useEffect(() => {
    if (locationMode !== "gps") return;
    if (!navigator.geolocation) {
      setLocationError("GPS is not supported by this browser. Use manual location.");
      return;
    }
    let active = true;
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        if (!active) return;
        const accuracy = position.coords.accuracy;
        if (!Number.isFinite(accuracy) || accuracy > GPS_MAX_ACCURACY_METERS) {
          setLocationError("GPS location is too imprecise. Move outdoors or use manual location.");
          return;
        }
        const currentPosition: Coordinates = {
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        };
        const timestamp = Date.now();
        setGpsLocation(currentPosition);
        setGpsAccuracy(accuracy);
        setGpsTimestamp(timestamp);
        setGpsNow(timestamp);
        setDriverLocation(currentPosition);
        setLocationError("");
        const previous = lastRouteAnchorRef.current;
        if (!previous ||
          distanceMeters(previous.position, currentPosition) >= ROUTE_REFRESH_DISTANCE_METERS ||
          timestamp - previous.time >= ROUTE_REFRESH_MS) {
          lastRouteAnchorRef.current = { position: currentPosition, time: timestamp };
          setRouteAnchor(currentPosition);
        }
      },
      (error) => {
        if (!active) return;
        setLocationError(`GPS: ${error.message}. Try manual location or a phone with GPS.`);
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );
    return () => {
      active = false;
      navigator.geolocation.clearWatch(watchId);
    };
  }, [locationMode]);

  // Remove stale GPS from navigation; never present an old fix as live.
  useEffect(() => {
    if (locationMode !== "gps") return;
    const timer = window.setInterval(() => {
      const now = Date.now();
      setGpsNow(now);
      if (gpsTimestamp && now - gpsTimestamp >= GPS_STALE_MS) {
        setDriverLocation(null);
        setRouteAnchor(null);
        lastRouteAnchorRef.current = null;
        setRouteData(null);
        setLocationError("GPS fix expired. Waiting for a fresh location; manual mode is available.");
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [locationMode, gpsTimestamp]);

  // Search pickup and destination sequentially.
  // This prevents simultaneous geocoding requests.
  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    setPickupSearchInput(pickupLocation);
    setDestinationSearchInput(destination);
    setPickupCandidates([]);
    setDestinationCandidates([]);
    setSelectedPickup(null);
    setSelectedDestination(null);
    setRouteData(null);
    setPickupError("");
    setDestinationError("");
    setRouteError("");
    lastRouteRequest.current = null;

    if (
      !pickupLocation.trim() ||
      !destination.trim()
    ) {
      setLoadingLocations(false);
      return;
    }

    const timer = window.setTimeout(async () => {
      setLoadingLocations(true);

      try {
        const pickupResult =
          await geocodeLocation(
            pickupLocation.trim(),
            controller.signal
          );

        if (cancelled) return;

        setPickupCandidates(
          pickupResult.candidates
        );

        if (
          pickupResult.candidates.length === 1
        ) {
          setSelectedPickup(
            pickupResult.candidates[0]
          );
        }

        // Keep requests spaced apart for Nominatim.
        await new Promise<void>((resolve) => {
          window.setTimeout(resolve, 1200);
        });

        if (cancelled) return;

        const destinationResult =
          await geocodeLocation(
            destination.trim(),
            controller.signal
          );

        if (cancelled) return;

        setDestinationCandidates(
          destinationResult.candidates
        );

        if (
          destinationResult.candidates.length === 1
        ) {
          setSelectedDestination(
            destinationResult.candidates[0]
          );
        }
      } catch (error) {
        if (cancelled) return;

        if (
          error instanceof Error &&
          error.name === "AbortError"
        ) {
          return;
        }

        setRouteError(
          "Unable to search locations. Please try again."
        );
      } finally {
        if (!cancelled) {
          setLoadingLocations(false);
        }
      }
    }, 500);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [pickupLocation, destination]);

  const pickup = selectedPickup
    ? toCoordinates(selectedPickup)
    : null;

  const dropoff = selectedDestination
    ? toCoordinates(selectedDestination)
    : null;

  const routeKey =
    selectedPickup && selectedDestination
      ? [
          selectedPickup.latitude,
          selectedPickup.longitude,
          selectedDestination.latitude,
          selectedDestination.longitude,
        ].join(",")
      : "";

  // Request two driving routes:
  // Driver -> Pickup and Pickup -> Destination.
  useEffect(() => {
    if (
      routeCleared ||
      !routeAnchor ||
      !pickup ||
      !dropoff ||
      !routeKey
    ) {
      setRouteData(null);
      return;
    }

    const now = Date.now();
    const previous = lastRouteRequest.current;

    if (
      previous &&
      previous.key === routeKey &&
      now - previous.time < ROUTE_REFRESH_MS &&
      distanceMeters(previous.driver, routeAnchor) < ROUTE_REFRESH_DISTANCE_METERS
    ) {
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    const timer = window.setTimeout(async () => {
      setLoadingRoute(true);
      // Always remove the previous route while recalculating.
      setRouteData(null);
      setRouteError("");

      lastRouteRequest.current = {
        time: Date.now(),
        driver: routeAnchor,
        key: routeKey,
      };

      try {
        const firstRoute = await fetchRoute(
          routeAnchor,
          pickup,
          controller.signal
        );

        if (cancelled) return;

        const secondRoute = await fetchRoute(
          pickup,
          dropoff,
          controller.signal
        );

        if (cancelled) return;

        setRouteData({
          toPickup: firstRoute,
          toDestination: secondRoute,
        });
        if (manualRefreshPending.current) setRefreshStatus("Route updated successfully.");
      } catch (error) {
        if (cancelled) return;

        if (
          error instanceof Error &&
          error.name === "AbortError"
        ) {
          return;
        }

        if (manualRefreshPending.current) setRefreshStatus("Route refresh failed. Please try again.");
        setRouteError(
          error instanceof Error
            ? error.message
            : "Unable to calculate route."
        );
      } finally {
        if (!cancelled) {
          setLoadingRoute(false);
          manualRefreshPending.current = false;
        }
      }
    }, 800);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [
    routeAnchor?.lat,
    routeAnchor?.lng,
    routeKey,
    refreshRequested,
    routeCleared,
  ]);

  const gpsFresh = locationMode === "gps" && gpsTimestamp !== null &&
    gpsNow - gpsTimestamp < GPS_STALE_MS;
  const visibleDriver = locationMode === "gps" && !gpsFresh ? null : driverLocation;
  const mapCenter = visibleDriver ?? pickup ?? dropoff ?? { lat: 7.8731, lng: 80.7718 };

  const selectTargetButton = (target: MapSelectionTarget) => {
    setMapSelectionTarget((current) => current === target ? null : target);
    setLocationNotice("");
  };

  const locationFieldStyle = { width: "100%", padding: "9px 11px", border: "1px solid #cbd5e1", borderRadius: 8, background: "#ffffff", color: "#0f172a" };
  const actionStyle = { padding: "9px 13px", borderRadius: 8, border: "1px solid #0f766e", background: "#0f766e", color: "white", cursor: "pointer" };

  const navigationButtonGridStyle = {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: 9,
    width: "100%",
    marginBottom: 12,
  };
  const routeButtonStyle = {
    width: "100%",
    minWidth: 0,
    minHeight: 44,
    padding: "10px 8px",
    borderRadius: 9,
    border: "1px solid #cbd5e1",
    fontWeight: 600,
    fontSize: 13,
    cursor: "pointer",
    whiteSpace: "normal" as const,
    overflowWrap: "anywhere" as const,
  };

  const firstPositions = useMemo(
    () =>
      routeData?.toPickup.route_coordinates ?? [],
    [routeData]
  );

  const secondPositions = useMemo(
    () =>
      routeData?.toDestination.route_coordinates ?? [],
    [routeData]
  );

  const allPositions = useMemo(
    () => [
      ...firstPositions,
      ...secondPositions,
    ],
    [firstPositions, secondPositions]
  );

  const totalDistance = routeData
    ? (
        routeData.toPickup.distance_km +
        routeData.toDestination.distance_km
      ).toFixed(2)
    : null;

  const totalDuration = routeData
    ? (
        routeData.toPickup.duration_minutes +
        routeData.toDestination.duration_minutes
      ).toFixed(1)
    : null;

  return (
    <div style={{ width: "100%" }}>
      <h3>🚗 Driver Navigation</h3>


<div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
  <button
    type="button"
    onClick={() => changeLocationMode("gps")}
    disabled={locationMode === "gps"}
  >
    📍 Use Live GPS
  </button>

  <button
    type="button"
    onClick={() => changeLocationMode("manual")}
    disabled={locationMode === "manual"}
  >
    🗺️ Set Manual Location
  </button>
</div>

<p style={{ fontSize: 13, marginBottom: 12 }}>
  Location mode:{" "}
  <strong>
    {locationMode === "gps"
      ? "Live browser GPS (accuracy-dependent)"
      : "Manual Location"}
  </strong>
</p>



{locationMode === "manual" && (
  <div style={{ marginBottom: 16 }}>
    <label htmlFor="manual-driver-location">
      Driver's current location:
    </label>

    <div
      style={{
        display: "flex",
        gap: 8,
        marginTop: 6,
      }}
    >
      <input
        id="manual-driver-location"
        type="text"
        value={manualLocationInput}
        onChange={(event) => {
          setManualLocationInput(event.target.value);
          setManualLocationCandidates([]);
          setManualLocationError("");
        }}
        placeholder="e.g. Kalutara, Sri Lanka"
        style={{ flex: 1, padding: 8 }}
      />

      <button
        type="button"
        onClick={searchManualLocation}
        disabled={searchingManualLocation}
      >
        {searchingManualLocation ? "Searching..." : "Search"}
      </button>
    </div>

    {manualLocationError && (
      <p role="alert" style={{ color: "red" }}>
        {manualLocationError}
      </p>
    )}

    {manualLocationCandidates.length > 0 && (
      <div style={{ marginTop: 10 }}>
        <label htmlFor="manual-location-results">
          Select your location:
        </label>

        <select
          id="manual-location-results"
          defaultValue=""
          onChange={(event) => {
            const index = Number(event.target.value);
            const selected = manualLocationCandidates[index];

            if (!selected) return;

            const nextLocation = toCoordinates(selected);
            setDriverLocation(nextLocation);
            setRouteAnchor(nextLocation);
            lastRouteAnchorRef.current = { position: nextLocation, time: Date.now() };
            setRouteData(null);
            setRouteError("");
            lastRouteRequest.current = null;
          }}
          style={{
            display: "block",
            width: "100%",
            padding: 8,
            marginTop: 6,
          }}
        >
          <option value="" disabled>
            Choose a location
          </option>

          {manualLocationCandidates.map((candidate, index) => (
            <option
              key={`${candidate.name}-${index}`}
              value={index}
            >
              {candidate.name}
            </option>
          ))}
        </select>
      </div>
    )}

    <p style={{ fontSize: 12, marginTop: 8 }}>
      Manual location is selected by the driver.
      It is not live GPS tracking.
    </p>
  </div>
)}


      {locationMode === "gps" && gpsFresh && gpsAccuracy !== null && (
        <p style={{ fontSize: 12, color: "#0f766e" }}>
          GPS fix received · accuracy approximately ±{Math.round(gpsAccuracy)} m · updated {Math.max(0, Math.floor((gpsNow - (gpsTimestamp ?? gpsNow)) / 1000))}s ago.
          Accuracy is an estimate, not an exact road position.
        </p>
      )}
      {locationMode === "gps" && !gpsFresh && (
        <p style={{ fontSize: 12, color: "#92400e" }}>Waiting for a fresh GPS fix. On laptops this may time out; use Manual Location as a backup.</p>
      )}
      {locationMode === "gps" && locationError && (
        <p role="alert" style={{ color: "red" }}>
          GPS: {locationError}
        </p>
      )}

      {loadingLocations && (
        <p>Searching pickup and destination...</p>
      )}

      {pickupError && (
        <p role="alert">{pickupError}</p>
      )}

      {destinationError && (
        <p role="alert">{destinationError}</p>
      )}

      {routeError && (
        <p role="alert" style={{ color: "red" }}>
          {routeError}
        </p>
      )}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 14, margin: "16px 0" }}>
        {(["pickup", "destination"] as const).map((target) => {
          const input = target === "pickup" ? pickupSearchInput : destinationSearchInput;
          const setInput = target === "pickup" ? setPickupSearchInput : setDestinationSearchInput;
          const candidates = target === "pickup" ? pickupCandidates : destinationCandidates;
          const selected = target === "pickup" ? selectedPickup : selectedDestination;
          const error = target === "pickup" ? pickupError : destinationError;
          return (
            <div key={target} style={{ padding: 14, border: "1px solid #dbe4ea", borderRadius: 12, background: "#f8fafc" }}>
              <label htmlFor={`${target}-search`} style={{ display: "block", fontWeight: 700, marginBottom: 7 }}>
                {target === "pickup" ? "📍 Pickup location" : "🏁 Destination location"}
              </label>
              <form onSubmit={(event) => { event.preventDefault(); void searchTripLocation(target); }} style={{ display: "flex", gap: 7 }}>
                <input id={`${target}-search`} value={input} onChange={(event) => setInput(event.target.value)} placeholder="Search town, city or address" style={{ ...locationFieldStyle, flex: 1, minWidth: 0 }} />
                <button type="submit" disabled={searchingTarget !== null} style={actionStyle}>
                  {searchingTarget === target ? "Searching..." : "Search"}
                </button>
              </form>
              {candidates.length > 0 && (
                <select aria-label={`Choose ${target} search result`} value="" onChange={(event) => {
                  const candidate = candidates[Number(event.target.value)];
                  if (candidate) applyCandidate(target, candidate);
                }} style={{ ...locationFieldStyle, marginTop: 8 }}>
                  <option value="" disabled>Select an exact place (not a whole district)</option>
                  {candidates.map((candidate, index) => (
                    <option key={`${candidate.name}-${index}`} value={index}>{candidate.name}</option>
                  ))}
                </select>
              )}
              {selected && <p style={{ fontSize: 12, color: "#0f766e", margin: "8px 0 0", overflowWrap: "anywhere" }}>Selected: {selected.name}</p>}
              {error && <p role="alert" style={{ color: "#b91c1c", fontSize: 12 }}>{error}</p>}
              <button type="button" onClick={() => selectTargetButton(target)} style={{ marginTop: 9, padding: "7px 10px", borderRadius: 7, border: "1px solid #94a3b8", background: mapSelectionTarget === target ? "#ccfbf1" : "white", cursor: "pointer" }}>
                {mapSelectionTarget === target ? "Cancel map selection" : "📌 Choose on map"}
              </button>
            </div>
          );
        })}
      </section>

      <div style={{ marginBottom: 12, display: "flex", alignItems: "center", flexWrap: "wrap", gap: 9 }}>
        <button type="button" onClick={() => selectTargetButton("driver")} style={{ padding: "8px 12px", border: "1px solid #94a3b8", borderRadius: 8, background: mapSelectionTarget === "driver" ? "#ccfbf1" : "white", cursor: "pointer" }}>
          {mapSelectionTarget === "driver" ? "Cancel driver map selection" : "🚗 Set driver location on map"}
        </button>
        {mapSelectionTarget && <strong style={{ color: "#0f766e", fontSize: 13 }}>Click the exact {mapSelectionTarget} point on the map below. Zoom in first for accuracy.</strong>}
        {locationNotice && <span style={{ color: "#0f766e", fontSize: 13 }}>{locationNotice}</span>}
      </div>

      {loadingRoute && (
        <p>{manualRefreshPending.current ? "Refreshing route..." : "Calculating driving route..."}</p>
      )}
      {refreshStatus && !loadingRoute && (
        <p role="status" style={{ color: refreshStatus.includes("successfully") || refreshStatus.includes("cleared") ? "#047857" : "#b91c1c", fontWeight: 600 }}>{refreshStatus}</p>
      )}

      {routeData && (
        <div style={{ marginBottom: 12 }}>
          <strong>Navigation Summary</strong>

          <p>
            Driver to pickup:{" "}
            {routeData.toPickup.distance_km} km
          </p>

          <p>
            Pickup to destination:{" "}
            {routeData.toDestination.distance_km} km
          </p>

          <p>
            Total distance: {totalDistance} km
            {" | "}
            Estimated time: {totalDuration} min
          </p>
        </div>
      )}

      {!visibleDriver && <p style={{ color: "#475569" }}>Choose a driver location using search or by clicking the map to calculate a route.</p>}
      {(
        <div style={{ width: "100%" }}>
          <div style={navigationButtonGridStyle}>
            {([
              ["all", "🗺️ Full Route"],
              ["driver", "🚗 Follow Driver"],
              ["pickup", "📍 Pickup"],
              ["destination", "🏁 Destination"],
            ] as const).map(([target, label]) => (
              <button
                key={target}
                type="button"
                onClick={() => focusMap(target)}
                disabled={(target === "driver" && !visibleDriver) || (target === "pickup" && !pickup) || (target === "destination" && !dropoff)}
                style={{
                  ...routeButtonStyle,
                  background: mapFocus === target ? "#0f766e" : "#ffffff",
                  color: mapFocus === target ? "#ffffff" : "#0f172a",
                  borderColor: mapFocus === target ? "#0f766e" : "#cbd5e1",
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <div style={navigationButtonGridStyle}>
            {visibleDriver &&
        selectedPickup &&
        selectedDestination && (
          <button
            type="button"
            onClick={() => {
              manualRefreshPending.current = true;
              setRouteCleared(false);
              // Clear old polylines and summary immediately on click.
              setRouteData(null);
              setLoadingRoute(true);
              setRefreshStatus("");
              setRouteError("");
              lastRouteRequest.current = null;
              setRouteAnchor(visibleDriver);
              lastRouteAnchorRef.current = { position: visibleDriver, time: Date.now() };
              setRefreshRequested(
                (value) => value + 1
              );
            }}
            style={{ ...routeButtonStyle, background: "#0f766e", color: "#ffffff", borderColor: "#0f766e" }}
            disabled={loadingRoute}
          >
            Refresh Route
          </button>
        )}
      {(routeData || loadingRoute || routeCleared) && (
        <button
          type="button"
          onClick={() => {
            // Changing routeCleared aborts any in-flight routing effect.
            setRouteCleared(true);
            setRouteData(null);
            setLoadingRoute(false);
            setRouteError("");
            setRefreshStatus("Route cleared. Press Refresh Route to calculate a new route.");
            manualRefreshPending.current = false;
            lastRouteRequest.current = null;
          }}
          disabled={routeCleared && !loadingRoute && !routeData}
          style={{ ...routeButtonStyle, background: "#ffffff", color: "#b91c1c", borderColor: "#fecaca" }}
        >
          Clear Route
        </button>
      )}
          </div>
          <div style={{ fontSize: 13, marginBottom: 9, display: "flex", gap: 18, flexWrap: "wrap" }}>
            <span><strong style={{ color: "#2563eb" }}>━━</strong> Driver → Pickup</span>
            <span><strong style={{ color: "#16a34a" }}>━━</strong> Pickup → Destination</span>
            <span style={{ color: "#475569" }}>Use + / − or the mouse wheel to zoom into roads.</span>
          </div>
          <div
            style={{
              height: 540,
              width: "100%",
              borderRadius: 14,
              overflow: "hidden",
              border: "1px solid #cbd5e1",
            }}
          >
            <MapContainer
              center={toPosition(mapCenter)}
              zoom={13}
              scrollWheelZoom={true}
              zoomControl={true}
              style={{ height: "100%", width: "100%" }}
            >
              <TileLayer
                attribution="&copy; OpenStreetMap contributors"
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                maxZoom={19}
              />

              <MapClickSelector enabled={mapSelectionTarget !== null} onSelect={selectMapPoint} />
              {visibleDriver && (
                <>
                  <Marker position={toPosition(visibleDriver)} icon={locationIcon}>
                    <Popup>🚗 {locationMode === "gps" ? "GPS Driver Location (estimated)" : "Manually selected Driver Location"}</Popup>
                  </Marker>
                  {locationMode === "gps" && gpsFresh && gpsAccuracy !== null && (
                    <Circle center={toPosition(visibleDriver)} radius={gpsAccuracy}
                      pathOptions={{ color: "#2563eb", fillColor: "#60a5fa", fillOpacity: 0.12, weight: 1 }} />
                  )}
                </>
              )}
              {pickup && (
                <Marker position={toPosition(pickup)} icon={locationIcon}>
                  <Popup>📍 Pickup: {selectedPickup?.name}</Popup>
                </Marker>
              )}
              {dropoff && (
                <Marker position={toPosition(dropoff)} icon={locationIcon}>
                  <Popup>🏁 Destination: {selectedDestination?.name}</Popup>
                </Marker>
              )}

              {firstPositions.length > 1 && (
                <>
                  <Polyline positions={firstPositions} pathOptions={{ color: "#ffffff", weight: 11, opacity: 0.95, lineCap: "round", lineJoin: "round" }} />
                  <Polyline positions={firstPositions} pathOptions={{ color: "#2563eb", weight: 7, opacity: 1, lineCap: "round", lineJoin: "round" }} />
                </>
              )}
              {secondPositions.length > 1 && (
                <>
                  <Polyline positions={secondPositions} pathOptions={{ color: "#ffffff", weight: 11, opacity: 0.95, lineCap: "round", lineJoin: "round" }} />
                  <Polyline positions={secondPositions} pathOptions={{ color: "#16a34a", weight: 7, opacity: 1, lineCap: "round", lineJoin: "round" }} />
                </>
              )}
              <NavigationMapCamera
                positions={allPositions}
                driver={mapCenter}
                pickup={pickup}
                destination={dropoff}
                focus={mapFocus}
                focusRequest={mapFocusRequest}
              />
            </MapContainer>
          </div>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>
            Full Route shows the whole journey; Follow Driver zooms to the driver's selected position.
            Manual mode does not continuously track a moving vehicle.
          </p>
        </div>
      )}


    </div>
  );
}
