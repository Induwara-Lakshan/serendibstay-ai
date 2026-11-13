import { useRef, useState } from "react";

import type { FormEvent } from "react";

import ReactMarkdown from "react-markdown";

import remarkGfm from "remark-gfm";

import "./App.css";

import hotelBackground from "./assets/hotel-assistant-bg.png";

import ProviderRegistration from "./components/ProviderRegistration";

import AdminProviderApproval from "./components/AdminProviderApproval";
import AdminHotelManagement from "./components/AdminHotelManagement";

import ProviderLogin from "./components/ProviderLogin";

import ProviderDashboard from "./components/ProviderDashboard";

import AdminLogin from "./components/AdminLogin";



import GoogleHotelMap from "./components/GoogleHotelMap";
import type { HotelRouteRequest } from "./components/GoogleHotelMap";

import TransportRouteMap from "./components/TransportRouteMap";

import type { TransportRouteData } from "./components/TransportRouteMap";

type LocationCandidate = {

  name: string;

  latitude: number;

  longitude: number;

};

type RouteSelection = {

  pickup?: LocationCandidate;

  destination?: LocationCandidate;

  destination_name?: string;

  original_request?: string;

};

type Message = {

  role: "user" | "assistant";

  text: string;

  transport_route?: TransportRouteData | null;

  location_candidates?: LocationCandidate[];

  location_role?: "pickup" | "destination";

  highlightedHotelId?: number;

  hotels?: {
  id: number;
  name: string;
  address?: string | null;
  district?: string | null;
  latitude?: number | null;
  longitude?: number | null;

  // Additional hotel details
  description?: string | null;
  accommodation_type?: string | null;
  price_per_night?: number | null;
  rating?: number | null;
  available?: boolean | null;
  registration_no?: string | null;
  licence_no?: string | null;
}[];

};

// Highlight only a hotel explicitly named in the user's request.
// Avoid guessing when the request is broad or multiple names match.
function findRequestedHotelId(
  request: string,
  hotels: NonNullable<Message["hotels"]>
): number | undefined {
  const normalize = (value: string) =>
    value
      .toLocaleLowerCase("en")
      .replace(/[’‘]/g, "'")
      .replace(/[^a-z0-9]+/g, " ")
      .trim()
      .replace(/\s+/g, " ");

  const normalizedRequest = ` ${normalize(request)} `;

  const matches = hotels.filter((hotel) => {
    const normalizedName = normalize(hotel.name);
    return (
      normalizedName.length > 0 &&
      normalizedRequest.includes(` ${normalizedName} `)
    );
  });

  if (matches.length === 0) return undefined;

  // Prefer the longest matching hotel name.
  // This avoids selecting a shorter name contained in a longer hotel name.
  matches.sort((a, b) => normalize(b.name).length - normalize(a.name).length);

  const best = matches[0];
  const second = matches[1];

  if (
    second &&
    normalize(best.name).length === normalize(second.name).length
  ) {
    return undefined;
  }

  return best.id;
}

// For a specifically requested hotel, show only hotels in its district.
// Keep the requested hotel even when its district is missing.
function hotelsForRequestedDistrict(
  hotels: NonNullable<Message["hotels"]>,
  highlightedHotelId?: number
): NonNullable<Message["hotels"]> {
  if (highlightedHotelId === undefined) return hotels;

  const requested = hotels.find((hotel) => hotel.id === highlightedHotelId);
  if (!requested) return [];

  const district = requested.district?.trim().toLocaleLowerCase("en");
  if (!district) return [requested];

  return hotels.filter(
    (hotel) =>
      hotel.id === requested.id ||
      hotel.district?.trim().toLocaleLowerCase("en") === district
  );
}

function compactLocationName(name: string): string {

  const parts = name.split(",").map((part) => part.trim()).filter(Boolean);

  const street = parts[0] || "Location";

  const areas = parts.slice(1).filter((part) =>

    !/^(Sri Lanka|Western Province|Central Province|Colombo District|Kandy District|\d{4,5})$/i.test(part)

  );

  const useful = areas.filter((part) => !/^(L B Gate|St\\\\. Bastian)$/i.test(part));

  const area = useful.slice(0, 2).join(", ");

  return area ? `${street} — ${area}` : street;

}

type RouteSummaryFields = {

  pickup?: { name?: string };

  destination?: { name?: string };

  distance_km?: number;

  duration_minutes?: number;

};

function RouteResultCard({ route }: { route: TransportRouteData }) {

  const info = route as unknown as RouteSummaryFields;

  const distance = typeof info.distance_km === "number" ? `${info.distance_km.toFixed(1)} km` : "—";

  const minutes = typeof info.duration_minutes === "number" ? Math.round(info.duration_minutes) : null;

  const duration = minutes === null ? "—" : minutes >= 60

    ? `${Math.floor(minutes / 60)} hr ${minutes % 60} min`

    : `${minutes} min`;

  return (

    <section className="route-result-card" aria-label="Calculated transport route">

      <div className="route-result-details">

        <div className="route-result-status"><span aria-hidden="true">✓</span> Route ready</div>

        <h3>Your journey at a glance</h3>

        <p className="route-result-subtitle">Driving route successfully calculated</p>

        <div className="route-result-stops">

          <div className="route-result-stop">

            <span className="route-result-dot pickup-dot" aria-hidden="true" />

            <div><small>FROM</small><strong>{info.pickup?.name ? compactLocationName(info.pickup.name) : "Pickup location"}</strong></div>

          </div>

          <div className="route-result-stop">

            <span className="route-result-dot destination-dot" aria-hidden="true" />

            <div><small>TO</small><strong>{info.destination?.name ? compactLocationName(info.destination.name) : "Destination"}</strong></div>

          </div>

        </div>

        <div className="route-result-metrics">

          <div><span>↗ Distance</span><strong>{distance}</strong></div>

          <div><span>◷ Estimated time</span><strong>{duration}</strong></div>

        </div>

        <p className="route-result-note">Travel time is an estimate and may vary with traffic.</p>

      </div>

      <div className="route-result-map"><TransportRouteMap route={route} /></div>

    </section>

  );

}

function App() {
  const [hotelRoute, setHotelRoute] = useState<TransportRouteData | null>(null);
  const [hotelRouteLoading, setHotelRouteLoading] = useState(false);
  const [hotelRouteError, setHotelRouteError] = useState("");

  // Identifies which hotel search owns the calculated route.
const [routeOwnerIndex, setRouteOwnerIndex] = useState<number | null>(null);
const hotelRouteRequestId = useRef(0);

  const handleHotelRouteRequest = async (
  request: HotelRouteRequest,
  ownerIndex: number
) => {
  const requestId = ++hotelRouteRequestId.current;

  setRouteOwnerIndex(ownerIndex);
  console.log("HOTEL ROUTE REQUEST:", request);

  setHotelRoute(null);
  setHotelRouteError("");
  setHotelRouteLoading(true);

  try {
    const response = await fetch(
      "http://127.0.0.1:8011/transport/routes/calculate",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          pickup_latitude: request.pickup.lat,
          pickup_longitude: request.pickup.lng,
          destination_latitude: request.destination.lat,
          destination_longitude: request.destination.lng,
        }),
      }
    );

    if (!response.ok) {
      throw new Error("Could not calculate the driving route.");
    }

    const route: TransportRouteData = await response.json();
    // Ignore results from outdated route requests.
if (requestId !== hotelRouteRequestId.current) {
  return;
}
   setHotelRoute({
  ...route,
  pickup: {
    ...route.pickup,
    name: request.pickupName || "Selected starting location",
  },
  destination: {
    ...route.destination,
    name: request.hotelName,
  },
} as TransportRouteData);
 } catch (error) {
  // Ignore errors from outdated route requests.
  if (requestId !== hotelRouteRequestId.current) {
    return;
  }

  setHotelRouteError(
    error instanceof Error
      ? error.message
      : "Routing service is unavailable."
  );
} finally {
  // Only the latest request can update the loading state.
  if (requestId === hotelRouteRequestId.current) {
    setHotelRouteLoading(false);
  }
}
}

  const [currentView, setCurrentView] = useState<

    | "chat"

    | "provider"

    | "providerLogin"

    | "providerDashboard"

    | "adminLogin"

    | "admin"

  >("chat");

  // Controls the right-side Access Portal drawer

  const [portalOpen, setPortalOpen] = useState(false);
  const [adminTab, setAdminTab] = useState<"hotels" | "providers">("hotels");

  const [message, setMessage] = useState("");

  const [messages, setMessages] = useState<Message[]>([

    {

      role: "assistant",

      text: "Hello! I'm your SerendibStay AI Assistant. I can help you search hotels, make bookings, find transport, and request transport services.",

    },

  ]);

  const [loading, setLoading] = useState(false);

  const sendingRef = useRef(false);

  const routeSelectionRef = useRef<RouteSelection>({});

  const routeOriginalRef = useRef("");

  // =========================================================

  // CLEAR CHAT

  // =========================================================

  const clearChat = () => {

    // Invalidate any pending hotel route request.
++hotelRouteRequestId.current;

// Clear the route and its associated hotel search.
setHotelRoute(null);
setHotelRouteError("");
setHotelRouteLoading(false);
setRouteOwnerIndex(null);

    routeSelectionRef.current = {};

    routeOriginalRef.current = "";

    setMessages([

      {

        role: "assistant",

        text: "Hello! I'm your SerendibStay AI Assistant. I can help you search hotels, make bookings, find transport, and request transport services.",

      },

    ]);

  };

  // =========================================================

  // QUICK ACTION

  // =========================================================

  const handleQuickAction = (text: string) => {

    setMessage(text);

  };

  // =========================================================

  // SEND CHAT MESSAGE

  // =========================================================

  // Both typed messages and candidate buttons use the same request flow.

  const submitChatMessage = async (text: string, selection?: RouteSelection, displayText?: string) => {

    const userMessage = text.trim();

if (!userMessage || sendingRef.current) return;

sendingRef.current = true;

// Invalidate any previous route request.
++hotelRouteRequestId.current;
setRouteOwnerIndex(null);



// Clear the previous route before starting a new chat request.
setHotelRoute(null);
setHotelRouteError("");
setHotelRouteLoading(false);

    // Snapshot history before adding the new user message.

    const history = messages.map((item) => ({

      role: item.role,

      content: item.text,

    }));

    setMessages((previous) => [...previous, { role: "user", text: displayText ?? userMessage }]);

    setMessage("");

    setLoading(true);

    try {

      const response = await fetch("http\://127.0.0.1:8011/chat/", {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ message: userMessage, history, ...(selection ? { route_selection: selection } : {}) }),

      });

      if (!response.ok) throw new Error(`Chat request failed (${response.status})`);

      const data: {

        reply: string;

        hotels?: Message["hotels"];

        transport_route?: TransportRouteData | null;

        location_candidates?: LocationCandidate[];

        location_role?: "pickup" | "destination";

      } = await response.json();

      const validHotels = (data.hotels ?? []).filter(

        (hotel) => typeof hotel.id === "number" && typeof hotel.name === "string" && hotel.name.trim().length > 0

      );

      // Clear the previous driving route when new hotel results arrive.
if (validHotels.length > 0) {
  setHotelRoute(null);
  setHotelRouteError("");
  setHotelRouteLoading(false);
}


      const validCandidates = (data.location_candidates ?? []).filter(

        (candidate) =>

          typeof candidate.name === "string" &&

          Number.isFinite(candidate.latitude) &&

          Number.isFinite(candidate.longitude)

      );



      // The route service may return coordinates without human-readable names.

      // Reuse the user's verified selections for display only; never change geometry.

      const routeWithNames = data.transport_route

        ? (() => {

            const route = data.transport_route as TransportRouteData & {

              pickup?: { name?: string };

              destination?: { name?: string };

            };

            const selected = selection ?? routeSelectionRef.current;

            return {

              ...route,

              pickup: {

                ...route.pickup,

                name: selected.pickup?.name || route.pickup?.name,

              },

              destination: {

                ...route.destination,

                name: selected.destination?.name || route.destination?.name,

              },

            } as TransportRouteData;

          })()

        : null;

      setMessages((previous) => [

        ...previous,

        {

          role: "assistant",

          text: data.reply || "The assistant returned an empty response.",

          hotels: validHotels,
          highlightedHotelId: findRequestedHotelId(userMessage, validHotels),

          transport_route: routeWithNames,

          location_candidates: validCandidates,

          location_role: data.location_role,

        },

      ]);

    } catch (error) {

      console.error("Chat request error:", error);

      setMessages((previous) => [

        ...previous,

        { role: "assistant", text: "Sorry, I could not connect to the hotel assistant." },

      ]);

    } finally {

      sendingRef.current = false;

      setLoading(false);

    }

  };

  const sendMessage = (event: FormEvent<HTMLFormElement>) => {

    event.preventDefault();

    routeOriginalRef.current = message.trim();

    routeSelectionRef.current = {};

    void submitChatMessage(message);

  };

  // Verified location choices are sent as structured route data.

  // Never echo technical prompts or re-geocode selected coordinates.

  const selectLocation = (candidate: LocationCandidate, messageIndex: number) => {

    if (sendingRef.current || messageIndex !== messages.length - 1) return;

    const selectedMessage = messages[messageIndex];

    const role = selectedMessage.location_role === "destination" ? "destination" : "pickup";

    const original = routeOriginalRef.current || [...messages]

      .find((item) => item.role === "user")?.text || "";

    const destinationName = original.match(/\bto\s+(.+?)(?:[.!?]|$)/i)?.[1]?.trim();

    const current = routeSelectionRef.current;

    const next: RouteSelection = {

      ...current,

      original_request: original,

      ...(role === "pickup" ? { pickup: candidate } : { destination: candidate }),

      destination_name: current.destination_name || destinationName,

    };

    routeSelectionRef.current = next;

    // Do not send duplicate long messages to the assistant.

    const shortLabel = compactLocationName(candidate.name);

    void submitChatMessage(`Selected ${role}: ${shortLabel}`, next, `📍 ${shortLabel}`);

  };

  // =========================================================

  // PROVIDER LOGIN VIEW

  // =========================================================

  if (currentView === "providerLogin") {

    return (

      <div

        className="app"

        style={{

          backgroundImage: `linear-gradient(

            rgba(4, 47, 46, 0.25),

            rgba(4, 47, 46, 0.25)

          ), url(${hotelBackground})`,

        }}

      >

        <div className="chat-container">

          <ProviderLogin

            onBack={() => setCurrentView("chat")}

            onLoginSuccess={() => {

              setCurrentView("providerDashboard");

            }}

          />

        </div>

      </div>

    );

  }

  // =========================================================

  // PROVIDER DASHBOARD VIEW

  // =========================================================

  if (currentView === "providerDashboard") {

    return (

      <div

        className="app"

        style={{

          backgroundImage: `linear-gradient(

            rgba(4, 47, 46, 0.25),

            rgba(4, 47, 46, 0.25)

          ), url(${hotelBackground})`,

        }}

      >

        <div className="chat-container">

          <ProviderDashboard

            onLogout={() => {

              setCurrentView("providerLogin");

            }}

          />

        </div>

      </div>

    );

  }

  // =========================================================

  // PROVIDER REGISTRATION VIEW

  // =========================================================

  if (currentView === "provider") {

    return (

      <div

        className="app"

        style={{

          backgroundImage: `linear-gradient(

            rgba(4, 47, 46, 0.25),

            rgba(4, 47, 46, 0.25)

          ), url(${hotelBackground})`,

        }}

      >

        <div className="chat-container">

          <button

            type="button"

            className="clear-button"

            onClick={() => setCurrentView("chat")}

          >

            ← Back to Assistant

          </button>

          <ProviderRegistration />

        </div>

      </div>

    );

  }

  // =========================================================

  // ADMIN LOGIN VIEW

  // =========================================================

  if (currentView === "adminLogin") {

    return (

      <div

        className="app"

        style={{

          backgroundImage: `linear-gradient(

            rgba(4, 47, 46, 0.25),

            rgba(4, 47, 46, 0.25)

          ), url(${hotelBackground})`,

        }}

      >

        <div className="chat-container">

          <AdminLogin

            onBack={() => setCurrentView("chat")}

            onLoginSuccess={() => {

              setCurrentView("admin");

            }}

          />

        </div>

      </div>

    );

  }

  // =========================================================

  // ADMIN PROVIDER MANAGEMENT VIEW

  // =========================================================

  if (currentView === "admin") {

    return (

      <div

        className="app"

        style={{

          backgroundImage: `linear-gradient(

            rgba(4, 47, 46, 0.25),

            rgba(4, 47, 46, 0.25)

          ), url(${hotelBackground})`,

        }}

      >

        <div className="chat-container">

          <button

            type="button"

            className="clear-button"

            onClick={() => {

              sessionStorage.removeItem(

                "admin_access_token"

              );

              setCurrentView("adminLogin");

            }}

          >

            Logout Admin

          </button>

          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", margin: "18px 0" }}>
            <button
              type="button"
              onClick={() => setAdminTab("hotels")}
              aria-pressed={adminTab === "hotels"}
              style={{
                padding: "11px 18px", borderRadius: 9,
                border: "1px solid #16745f",
                background: adminTab === "hotels" ? "#16745f" : "#ffffff",
                color: adminTab === "hotels" ? "#ffffff" : "#16745f",
                fontWeight: 600, cursor: "pointer"
              }}
            >
              Hotel Management
            </button>
            <button
              type="button"
              onClick={() => setAdminTab("providers")}
              aria-pressed={adminTab === "providers"}
              style={{
                padding: "11px 18px", borderRadius: 9,
                border: "1px solid #16745f",
                background: adminTab === "providers" ? "#16745f" : "#ffffff",
                color: adminTab === "providers" ? "#ffffff" : "#16745f",
                fontWeight: 600, cursor: "pointer"
              }}
            >
              Transport Providers
            </button>
          </div>
          {adminTab === "hotels" ? (
            <div className="admin-hotel-scope">
              <AdminHotelManagement />
            </div>
          ) : <AdminProviderApproval />}

        </div>

      </div>

    );

  }

  // =========================================================

  // MAIN CHAT VIEW

  // =========================================================

  return (

    <div

      className="app"

      style={{

        backgroundImage: `linear-gradient(

          rgba(4, 47, 46, 0.25),

          rgba(4, 47, 46, 0.25)

        ), url(${hotelBackground})`,

      }}

    >

      <div className="chat-container">

        {/* =====================================================

            HEADER

        ===================================================== */}

        <header className="chat-header">

          <div className="brand">

            <div className="logo">

              SL

            </div>

            <div>

              <h1>SerendibStay AI</h1>

              <p>

                AI powered hotel & transport assistant

                for Sri Lanka

              </p>

            </div>

          </div>

          <div className="header-actions">

            <button

              className="portal-button"

              type="button"

              onClick={() => setPortalOpen(true)}

            >

              Portal

            </button>

            <button

              className="clear-button"

              type="button"

              onClick={clearChat}

            >

              Clear Chat

            </button>

          </div>

        </header>

        {/* =====================================================

            CUSTOMER QUICK ACTIONS

        ===================================================== */}

        <div className="quick-actions">

          <button

            type="button"

            onClick={() =>

              handleQuickAction(

                "Help me search for hotels in Sri Lanka."

              )

            }

          >

            Search Hotels

          </button>

          <button

            type="button"

            onClick={() =>

              handleQuickAction(

                "I want to make a hotel booking. What information do you need?"

              )

            }

          >

            Make a Booking

          </button>

          <button

            type="button"

            onClick={() =>

              handleQuickAction(

                "Help me find a transport provider in Sri Lanka."

              )

            }

          >

            Find Transport

          </button>

          <button

            type="button"

            onClick={() =>

              handleQuickAction(

                "I want to request transport. What information do you need?"

              )

            }

          >

            Request Transport

          </button>

        </div>

        {/* =====================================================

            CHAT MESSAGES

        ===================================================== */}

        <main className="messages">

          {messages.map((item, index) => (

            item.role === "assistant" && item.transport_route ? (

              <div key={index} className="message-row assistant-row route-result-row">



              </div>

            ) : (

            <div

              key={index}

              className={`message-row ${

                item.role === "user"

                  ? "user-row"

                  : "assistant-row"

              } ${

                item.role === "assistant" && item.hotels?.length

                  ? "hotel-results-row"

                  : ""

              }`}

            >

              <div className={`message ${item.role}`} style={item.location_candidates?.length ? {maxWidth: "min(480px, 100%)", width: "100%", boxSizing: "border-box"} : undefined}>

                {item.role === "assistant" ? (

                  <>

                    <div className="ai-response-content">

                      <ReactMarkdown remarkPlugins={[remarkGfm]}>

                        {item.location_candidates?.length

                          ? (item.location_role === "destination" ? "📍 **Choose your destination**" : "📍 **Choose your pickup**")

                          : item.text}

                      </ReactMarkdown>

                    </div>

                    {item.location_candidates && item.location_candidates.length > 0 && (

                      <div style={{display: "grid", gap: "7px", marginTop: "10px"}}>

                        {index === messages.length - 1 ? (

                          item.location_candidates.map((candidate, candidateIndex) => (

                            <button

                              key={`${index}-${candidateIndex}-${candidate.latitude}-${candidate.longitude}`}

                              type="button"

                              disabled={loading}

                              onClick={() => selectLocation(candidate, index)}

                              title={candidate.name}

                              style={{textAlign: "left", padding: "9px 12px", border: "1px solid #9ac7c0", borderRadius: "9px", background: "#f3faf8", color: "#153e3b", cursor: loading ? "wait" : "pointer", fontSize: "0.88rem", lineHeight: 1.35}}

                            >

                              <span style={{marginRight: "8px"}}>📍</span>{compactLocationName(candidate.name)}

                            </button>

                          ))

                        ) : (

                          <span style={{fontSize: "0.82rem", opacity: 0.7}}>Selection completed</span>

                        )}

                      </div>

                    )}

                  </>

                ) : item.text}

              </div>

              {item.role === "assistant" &&
                item.hotels &&
                item.hotels.length > 0 &&
                (() => {
                  const mapHotels = hotelsForRequestedDistrict(
                    item.hotels,
                    item.highlightedHotelId
                  );




                  if (mapHotels.length === 0) return null;

                  return (
                    <div
                      style={{
                        width: "100%",
                        maxWidth: "850px",
                        marginTop: "12px",
                      }}
                    >
                      {/* Temporary Google Maps test */}
                     <GoogleHotelMap
  hotels={mapHotels}
  highlightedHotelId={item.highlightedHotelId}
  onRouteRequest={(request) => handleHotelRouteRequest(request, index)}
/>

{routeOwnerIndex === index && hotelRouteLoading && (
  <p role="status">🚗 Calculating driving route...</p>
)}

{routeOwnerIndex === index && hotelRouteError && (
  <p role="alert" style={{ color: "red" }}>
    ⚠️ {hotelRouteError}
  </p>
)}

{routeOwnerIndex === index &&
  hotelRoute &&
  mapHotels.some(
    (hotel) =>
      hotel.name.trim().toLowerCase() ===
      (
        hotelRoute as TransportRouteData & {
          destination?: { name?: string };
        }
      ).destination?.name?.trim().toLowerCase()
  ) && (
    <RouteResultCard route={hotelRoute} />
  )}


                    </div>
                  );
                })()}
            </div>
            )

          ))}

          {/* Typing animation */}

          {loading && (

            <div className="message-row assistant-row">

              <div className="message assistant typing-indicator">

                <span></span>

                <span></span>

                <span></span>

              </div>

            </div>

          )}

        </main>

        {/* =====================================================

            CHAT INPUT

        ===================================================== */}

        <form

          className="chat-form"

          onSubmit={sendMessage}

        >

          <input

            type="text"

            value={message}

            onChange={(event) =>

              setMessage(event.target.value)

            }

            placeholder="Ask about hotels or transport in Sri Lanka..."

            disabled={loading}

          />

          <button

            type="submit"

            disabled={

              loading || !message.trim()

            }

          >

            Send

          </button>

        </form>

        {/* =====================================================

            ACCESS PORTAL OVERLAY + RIGHT SIDE DRAWER

        ===================================================== */}

        {portalOpen && (

          <>

            {/* Dark background overlay */}

            <div

              className="portal-overlay"

              onClick={() => setPortalOpen(false)}

            />

            {/* Portal Drawer */}

            <aside className="portal-drawer">

              {/* Drawer Header */}

              <div className="portal-drawer-header">

                <div>

                  <span className="portal-label">

                    SERENDIBSTAY AI

                  </span>

                  <h2>

                    Access Portal

                  </h2>

                  <p>

                    Select the portal you want to access.

                  </p>

                </div>

                <button

                  type="button"

                  className="portal-close-button"

                  onClick={() =>

                    setPortalOpen(false)

                  }

                  aria-label="Close portal"

                >

                  ×

                </button>

              </div>

              {/* =================================================

                  TRANSPORT PROVIDER SECTION

              ================================================= */}

              <div className="portal-section">

                <div className="portal-section-icon">

                  🚐

                </div>

                <div className="portal-section-content">

                  <span className="portal-section-label">

                    PROVIDER PORTAL

                  </span>

                  <h3>

                    Transport Provider

                  </h3>

                  <p>

                    Register your transport service or

                    securely access your provider dashboard

                    to manage customer transport requests.

                  </p>

                  <div className="portal-section-actions">

                    <button

                      type="button"

                      className="portal-primary-action"

                      onClick={() => {

                        setPortalOpen(false);

                        setCurrentView("provider");

                      }}

                    >

                      Register as Provider

                    </button>

                    <button

                      type="button"

                      className="portal-secondary-action"

                      onClick={() => {

                        setPortalOpen(false);

                        setCurrentView(

                          "providerLogin"

                        );

                      }}

                    >

                      Provider Login

                    </button>

                  </div>

                </div>

              </div>

              <div className="portal-divider" />

              {/* =================================================

                  ADMINISTRATION SECTION

              ================================================= */}

              <div className="portal-section">

                <div className="portal-section-icon">

                  🛡️

                </div>

                <div className="portal-section-content">

                  <span className="portal-section-label">

                    ADMINISTRATION

                  </span>

                  <h3>

                    Admin Portal

                  </h3>

                  <p>

                    Secure administrative access for

                    managing transport provider registrations

                    and approvals.

                  </p>

                  <div className="portal-section-actions">

                    <button

                      type="button"

                      className="portal-admin-action"

                      onClick={() => {

                        setPortalOpen(false);

                        setCurrentView(

                          "adminLogin"

                        );

                      }}

                    >

                      Admin Login

                    </button>

                  </div>

                </div>

              </div>

              {/* =================================================

                  PORTAL FOOTER

              ================================================= */}

              <div className="portal-drawer-footer">

                <span>

                  Secure Access Portal

                </span>

                <p>

                  SerendibStay AI • Sri Lanka

                </p>

              </div>

            </aside>

          </>

        )}

      </div>

    </div>

  );

}

export default App;
