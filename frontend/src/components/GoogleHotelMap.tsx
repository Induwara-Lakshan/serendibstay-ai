import { useCallback, useEffect, useRef, useState } from "react";
import {
  APIProvider,
  Map,
  Marker,
  InfoWindow,
  useMap,
  useMapsLibrary,
} from "@vis.gl/react-google-maps";

function CurrentLocationController({
  location,
}: {
  location: { lat: number; lng: number } | null;
}) {
  const map = useMap();

  useEffect(() => {
    if (!map || !location) return;

    map.panTo(location);
    map.setZoom(15);
  }, [map, location]);

  return null;
}
 
interface HotelLocation {
  id: number;
  name: string;
  address?: string | null;
  district?: string | null;
  latitude?: number | null;
  longitude?: number | null;

  description?: string | null;
  accommodation_type?: string | null;
  price_per_night?: number | null;
  rating?: number | null;
  available?: boolean | null;
  registration_no?: string | null;
  licence_no?: string | null;
}

type Coordinates = { lat: number; lng: number };

type RouteSummary = { distance: string; duration: string };

export type HotelRouteRequest = {
  pickup: Coordinates;
  pickupName?: string;
  destination: Coordinates;
  hotelName: string;
};

function Directions({
  origin,
  destination,
  onResult,
}: {
  origin: Coordinates | null;
  destination: Coordinates | null;
  onResult: (summary: RouteSummary | null, error: string) => void;
}) {
  const map = useMap();
  const routesLibrary = useMapsLibrary("routes");
  const [renderer, setRenderer] = useState<google.maps.DirectionsRenderer | null>(null);

  useEffect(() => {
    if (!map || !routesLibrary) return;
    const instance = new routesLibrary.DirectionsRenderer({
      map,
      suppressMarkers: false,
      polylineOptions: {
        strokeColor: "#087f72",
        strokeOpacity: 0.9,
        strokeWeight: 6,
      },
    });
    setRenderer(instance);
    return () => {
      instance.setMap(null);
    };
  }, [map, routesLibrary]);

  const originLat = origin?.lat;
  const originLng = origin?.lng;
  const destinationLat = destination?.lat;
  const destinationLng = destination?.lng;

  useEffect(() => {
    if (!renderer || !routesLibrary || !map) return;
    if (
      originLat === undefined || originLng === undefined ||
      destinationLat === undefined || destinationLng === undefined
    ) {
      renderer.setMap(null);
      return;
    }

    renderer.setMap(map);
    const service = new routesLibrary.DirectionsService();
    let cancelled = false;

    service.route(
      {
        origin: { lat: originLat, lng: originLng },
        destination: { lat: destinationLat, lng: destinationLng },
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (result, status) => {
        if (cancelled) return;
        if (status === google.maps.DirectionsStatus.OK && result) {
          renderer.setDirections(result);
          const leg = result.routes[0]?.legs[0];
          onResult(
            {
              distance: leg?.distance?.text ?? "Unavailable",
              duration: leg?.duration?.text ?? "Unavailable",
            },
            ""
          );
        } else {
          renderer.setMap(null);
          onResult(null, `Could not calculate route (${status}). Check Google Maps routing access and billing.`);
        }
      }
    );
    return () => {
      cancelled = true;
    };
  }, [renderer, routesLibrary, map, originLat, originLng, destinationLat, destinationLng, onResult]);

  return null;
}

interface GoogleHotelMapProps {
  hotels: HotelLocation[];
  highlightedHotelId?: number;
  onRouteRequest?: (request: HotelRouteRequest) => void;
}

export default function GoogleHotelMap({
  hotels,
  highlightedHotelId,
  onRouteRequest,
}: GoogleHotelMapProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  const [selectedHotelId, setSelectedHotelId] = useState<number | null>(null);
  const [routeHotelId, setRouteHotelId] = useState<number | null>(null);
  const [routeSummary, setRouteSummary] = useState<RouteSummary | null>(null);
  const [routeError, setRouteError] = useState("");
  const handleRouteResult = useCallback((summary: RouteSummary | null, error: string) => {
    setRouteSummary(summary);
    setRouteError(error);
  }, []);

  const [userLocation, setUserLocation] = useState<{
  lat: number;
  lng: number;
} | null>(null);

const [userLocationName, setUserLocationName] = useState("");
const locationLookupId = useRef(0);

const [locationError, setLocationError] = useState("");
const [loadingLocation, setLoadingLocation] = useState(false);

const [isSelectingLocation, setIsSelectingLocation] = useState(false);

const [locationAccuracy, setLocationAccuracy] = useState<number | null>(
  null
);

const getCurrentLocation = () => {
  if (!navigator.geolocation) {
    setLocationError("Your browser does not support location access.");
    return;
  }

  if (!window.isSecureContext) {
    setLocationError("Location access requires HTTPS or localhost.");
    return;
  }

  setLoadingLocation(true);
  setLocationError("");

  navigator.geolocation.getCurrentPosition(
    (position) => {
  const accuracy = position.coords.accuracy;

  setLocationAccuracy(accuracy);
  setLoadingLocation(false);

  // Reject inaccurate browser locations (over 1 km).
  if (accuracy > 1000) {
    setLocationError(
      `Your detected location is inaccurate (±${(
        accuracy / 1000
      ).toFixed(1)} km). Please use "Select Location on Map".`
    );
    return;
  }

  ++locationLookupId.current;
  setUserLocationName("");
  setUserLocation({
    lat: position.coords.latitude,
    lng: position.coords.longitude,
  });

  setLocationError("");
},
    (error) => {
      if (error.code === 1) {
        setLocationError(
          "Location permission denied. Please allow location access."
        );
      } else if (error.code === 2) {
        setLocationError(
          "Your current location is unavailable."
        );
      } else {
        setLocationError(
          "Location request timed out. Please try again."
        );
      }

      setLoadingLocation(false);
    },
    {
      enableHighAccuracy: true,
      timeout: 15000,
      maximumAge: 60000,
    }
  );
};

  const validHotels = hotels.filter(
    (hotel) =>
      typeof hotel.latitude === "number" &&
      typeof hotel.longitude === "number" &&
      Number.isFinite(hotel.latitude) &&
      Number.isFinite(hotel.longitude) &&
      hotel.latitude >= -90 &&
      hotel.latitude <= 90 &&
      hotel.longitude >= -180 &&
      hotel.longitude <= 180
  );

  if (!apiKey) {
    return <p>Google Maps API Key is missing.</p>;
  }

  if (validHotels.length === 0) {
    return <p>No hotel locations available.</p>;
  }

  const center = {
    lat: validHotels[0].latitude!,
    lng: validHotels[0].longitude!,
  };

  const routeHotel = validHotels.find((hotel) => hotel.id === routeHotelId);
  const routeDestination: Coordinates | null = routeHotel
    ? { lat: routeHotel.latitude!, lng: routeHotel.longitude! }
    : null;

  const selectedHotel = validHotels.find(
    (hotel) => hotel.id === selectedHotelId
  );

  return (
    <APIProvider
  apiKey={apiKey}
  libraries={["places"]}
>
      <div
        style={{
          width: "100%",
          minWidth: 0,
          maxWidth: "100%",
          boxSizing: "border-box",
          height: "auto",
          borderRadius: "14px",
          overflow: "hidden",
        }}
      >
       <Map
  style={{ width: "100%", height: "clamp(320px, 65dvh, 600px)" }}
  defaultCenter={center}
  defaultZoom={12}
  gestureHandling="greedy"
  disableDefaultUI={false}
  onClick={(event) => {
    if (!isSelectingLocation || !event.detail.latLng) return;

    const { lat, lng } = event.detail.latLng;
    console.log("MANUAL SELECTED LOCATION:", lat, lng);
    console.log("GOOGLE PLACE ID:", event.detail.placeId);
    console.log("GOOGLE MAP CLICK DETAILS:", event.detail);
    setUserLocation({ lat, lng });

    setUserLocationName("Finding location name...");

    // Prefer the name of the Google Maps place that was actually clicked.
    // If the click has no place ID (or Places lookup fails), use an address fallback.
    const placeId = event.detail.placeId;
    const lookupId = ++locationLookupId.current;

    const resolveLocationName = async () => {
      const coordinatesLabel = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      let resolvedName = "";

      if (placeId) {
        try {
          const { Place } = (await google.maps.importLibrary(
            "places"
          )) as google.maps.PlacesLibrary;
          const place = new Place({ id: placeId });
          await place.fetchFields({ fields: ["displayName"] });
          resolvedName = place.displayName?.trim() ?? "";
          console.log("GOOGLE PLACE NAME:", resolvedName);
        } catch (error) {
          console.warn("Google Places lookup failed; using fallback:", error);
        }
      }

      if (!resolvedName) {
        try {
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`
          );
          if (!response.ok) throw new Error("Location lookup failed");
          const data = await response.json();
          console.log("NOMINATIM LOCATION DATA:", data);
          resolvedName =
            data.name ||
            data.address?.tourism ||
            data.address?.attraction ||
            data.address?.leisure ||
            data.address?.amenity ||
            data.address?.road ||
            data.address?.suburb ||
            data.address?.city ||
            data.display_name ||
            coordinatesLabel;
        } catch (error) {
          console.warn("Nominatim lookup failed:", error);
          resolvedName = coordinatesLabel;
        }
      }

      // Ignore responses from a previously selected location.
      if (lookupId === locationLookupId.current) {
        setUserLocationName(resolvedName);
      }
    };

    void resolveLocationName();

    setLocationAccuracy(null);
    setLocationError("");
    setIsSelectingLocation(false);
  }}
>
           <CurrentLocationController location={userLocation} />

           
           <Directions
             origin={userLocation}
             destination={routeDestination}
             onResult={handleRouteResult}
           />

          {validHotels.map((hotel) => (
            <Marker
              key={hotel.id}
              position={{
                lat: hotel.latitude!,
                lng: hotel.longitude!,
              }}
              title={hotel.name}
              onClick={() => setSelectedHotelId(hotel.id)}
              zIndex={hotel.id === highlightedHotelId ? 100 : 1}
            />
          ))}

          {userLocation && (
  <Marker
    position={userLocation}
    title="My Current Location"
    zIndex={200}
    icon={{
      path: 0,
      scale: 10,
      fillColor: "#2563eb",
      fillOpacity: 1,
      strokeColor: "#ffffff",
      strokeWeight: 3,
    }}
  />
)}

          {selectedHotel && (
            <InfoWindow
  position={{
    lat: selectedHotel.latitude!,
    lng: selectedHotel.longitude!,
  }}
  onCloseClick={() => setSelectedHotelId(null)}
>
            <div
  style={{
    width: "290px",
    maxWidth: "100%",
    maxHeight: "370px",
    overflowY: "auto",
    padding: "10px 8px",
    fontFamily: "'Segoe UI', Arial, sans-serif",
    color: "#173b38",
  }}
>
  {/* Premium Hotel Header */}
  <div
    style={{
      padding: "14px",
      background: "linear-gradient(135deg, #087f72, #14532d)",
      borderRadius: "12px",
      color: "#ffffff",
      marginBottom: "12px",
    }}
  >
    <div
      style={{
        fontSize: "10px",
        letterSpacing: "1px",
        opacity: 0.9,
        marginBottom: "7px",
      }}
    >
      SERENDIBSTAY AI • HOTEL DETAILS
    </div>

    <div
      style={{
        fontSize: "18px",
        fontWeight: 700,
        lineHeight: 1.4,
      }}
    >
      🏨 {selectedHotel.name}
    </div>

    {selectedHotel.accommodation_type && (
      <div style={{ fontSize: "12px", marginTop: "8px" }}>
        🛏️ {selectedHotel.accommodation_type}
      </div>
    )}
  </div>

  {/* Rating and Availability */}
  <div
    style={{
      display: "flex",
      flexWrap: "wrap",
      gap: "8px",
      marginBottom: "12px",
    }}
  >
    {selectedHotel.rating != null &&
      Number.isFinite(selectedHotel.rating) && (
        <span
          style={{
            padding: "7px 10px",
            backgroundColor: "#fff7e6",
            color: "#92400e",
            borderRadius: "8px",
            fontSize: "12px",
            fontWeight: 700,
          }}
        >
          ⭐ {selectedHotel.rating.toFixed(1)} Rating
        </span>
      )}

    {selectedHotel.available != null && (
      <span
        style={{
          padding: "7px 10px",
          backgroundColor: selectedHotel.available
            ? "#dcfce7"
            : "#fee2e2",
          color: selectedHotel.available ? "#166534" : "#991b1b",
          borderRadius: "8px",
          fontSize: "12px",
          fontWeight: 700,
        }}
      >
        {selectedHotel.available ? "🟢 Available" : "🔴 Unavailable"}
      </span>
    )}
  </div>

  {/* Price Per Night */}
  {selectedHotel.price_per_night != null &&
    Number.isFinite(selectedHotel.price_per_night) && (
      <div
        style={{
          padding: "12px",
          backgroundColor: "#f0fdf4",
          border: "1px solid #bbf7d0",
          borderRadius: "10px",
          marginBottom: "12px",
        }}
      >
        <div style={{ fontSize: "11px", color: "#64748b" }}>
          PRICE PER NIGHT
        </div>

        <div
          style={{
            fontSize: "20px",
            fontWeight: 800,
            color: "#087f72",
            marginTop: "4px",
          }}
        >
          {selectedHotel.price_per_night.toLocaleString("en-US")}
        </div>
      </div>
    )}

  {/* Hotel Description */}
  {selectedHotel.description && (
    <div style={{ marginBottom: "12px" }}>
      <div
        style={{
          fontSize: "12px",
          fontWeight: 700,
          color: "#087f72",
          marginBottom: "5px",
        }}
      >
        📝 About This Hotel
      </div>

      <div
        style={{
          fontSize: "12px",
          lineHeight: 1.6,
          color: "#475569",
          overflowWrap: "anywhere",
        }}
      >
        {selectedHotel.description}
      </div>
    </div>
  )}

  {/* Hotel Address */}
  {selectedHotel.address && (
    <div
      style={{
        fontSize: "12px",
        color: "#475569",
        marginBottom: "10px",
        lineHeight: 1.6,
        overflowWrap: "anywhere",
      }}
    >
      📍 {selectedHotel.address}
    </div>
  )}

  {/* District */}
  {selectedHotel.district && (
    <div
      style={{
        display: "inline-block",
        padding: "6px 11px",
        backgroundColor: "#e6f7f3",
        color: "#087f72",
        borderRadius: "20px",
        fontSize: "12px",
        fontWeight: 600,
        marginBottom: "14px",
      }}
    >
      🌍 {selectedHotel.district} District
    </div>
  )}

  {/* Get Directions - draw the route on this map */}
  <button
    type="button"
    onClick={() => {
      if (!userLocation) {
        setLocationError('Choose your starting point with "My Current Location" or "Select Location on Map" first.');
        return;
      }
      setRouteSummary(null);
      setRouteError("");

if (onRouteRequest) {
   onRouteRequest({
  pickup: userLocation,
  pickupName: userLocationName,
  destination: {
    lat: selectedHotel.latitude!,
    lng: selectedHotel.longitude!,
  },
  hotelName: selectedHotel.name,
});
  setSelectedHotelId(null);
  return;
}

      setRouteHotelId(selectedHotel.id);
      setSelectedHotelId(null);
    }}
    style={{
      display: "block",
      width: "100%",
      textAlign: "center",
      padding: "12px 14px",
      background: "linear-gradient(135deg, #087f72, #166534)",
      color: "#ffffff",
      border: "none",
      borderRadius: "10px",
      fontWeight: 700,
      fontSize: "13px",
      cursor: "pointer",
      boxShadow: "0 4px 12px rgba(8,127,114,0.22)",
    }}
  >
    🚗 Get Directions (Show on Map)
  </button>
</div>
            </InfoWindow>
          )}
        </Map>

        {userLocation && (
  <div style={{ padding: "10px", background: "#f0fdfa" }}>
    <label
      htmlFor="starting-location-name"
      style={{ display: "block", fontWeight: 600, marginBottom: "6px" }}
    >
      📍 Starting Location Name
    </label>

    <input
      id="starting-location-name"
      type="text"
      value={userLocationName}
      onChange={(event) => {
        ++locationLookupId.current;
        setUserLocationName(event.target.value);
      }}
      placeholder="Example: Diyatha Uyana, Battaramulla"
      style={{
        width: "100%",
        padding: "10px",
        border: "1px solid #99f6e4",
        borderRadius: "8px",
      }}
    />
  </div>
)}
      </div>

      {routeHotelId !== null && (
        <div role="status" style={{ marginTop: "12px", padding: "12px", borderRadius: "10px", background: "#f0fdf4", color: "#14532d" }}>
          {routeHotel && <strong>🚗 Route to {routeHotel.name}</strong>}
          {routeSummary && <p>📏 {routeSummary.distance} · ⏱️ {routeSummary.duration}</p>}
          {routeError && <p style={{ color: "#b42318" }}>{routeError}</p>}
          {!routeSummary && !routeError && <p>Calculating route...</p>}
          <button type="button" onClick={() => { setRouteHotelId(null); setRouteSummary(null); setRouteError(""); }}>
            Clear Route
          </button>
        </div>
      )}

      <div style={{ marginTop: "12px" }}>
  <button
    type="button"
    onClick={getCurrentLocation}
    disabled={loadingLocation}
    style={{
      padding: "10px 16px",
      backgroundColor: "#16745f",
      color: "white",
      border: "none",
      borderRadius: "8px",
      cursor: loadingLocation ? "wait" : "pointer",
      fontWeight: 600,
    }}
  >
    {loadingLocation ? "📍 Finding Location..." : "📍 My Current Location"}
  </button>

  <button
  type="button"
  onClick={() => {
    setIsSelectingLocation((previous) => !previous);
    setLocationError("");
  }}
  style={{
    marginLeft: "10px",
    padding: "10px 16px",
    backgroundColor: isSelectingLocation ? "#dc2626" : "#2563eb",
    color: "white",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
    fontWeight: 600,
  }}
>
  {isSelectingLocation
    ? "❌ Cancel Selection"
    : "🎯 Select Location on Map"}
</button>

{locationAccuracy !== null && locationAccuracy > 1000 && (
  <p
    role="status"
    style={{
      color: "#b45309",
      backgroundColor: "#fffbeb",
      padding: "10px",
      borderRadius: "8px",
      marginTop: "10px",
      fontSize: "13px",
    }}
  >
    ⚠️ Your detected location may be inaccurate.
    Estimated accuracy: {(locationAccuracy / 1000).toFixed(1)} km.
    Please use "Select Location on Map" to choose your correct location.
  </p>
)}

  {locationError && (
    <p role="alert" style={{ color: "#b42318", fontSize: "13px" }}>
      {locationError}
    </p>
  )}
</div>
    </APIProvider>
  );
}

