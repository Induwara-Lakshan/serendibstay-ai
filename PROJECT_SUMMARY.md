# SerendibStay AI - Complete Project Summary

**Project:** SerendibStay AI / Sri Lanka Hotel API  
**Repository:** `Induwara-Lakshan/serendibstay-ai`  
**Summary date:** 2026-10-24  
**Purpose:** Sri Lankan hotel discovery, hotel booking requests, transport-provider management, transport requests, and AI-assisted travel chat.

> Me document eka project eka understand karanna, setup karanna, demo/presentation ekakata explain karanna, saha future development plan karanna use karanna puluwan. `venv`, `node_modules`, `dist`, database dumps, saha secrets me summary ekata include karala naha.

## 1. Project eka gena short overview

SerendibStay AI is a full-stack travel platform focused on Sri Lanka. The user can:

- Search publicly visible hotels by city, district, or natural-language chat.
- View hotel locations on an interactive Leaflet map.
- Submit a pending hotel booking request.
- Search approved and available transport providers by district and passenger count.
- View and calculate driving routes between named places or verified coordinates.
- Register and log in as a transport provider.
- Manage provider availability and accept/reject transport requests.
- Use an admin portal to approve providers and manage hotel listings.
- Ask the AI assistant questions using hotel and transport data exposed through MCP servers.

The project is split into a React/Vite frontend, a FastAPI backend, a PostgreSQL database, two MCP services, external AI/routing/geocoding services, and Docker Compose deployment configuration.

## 2. High-level architecture

```text
Browser (React + TypeScript + Vite)
        |
        | HTTP/JSON
        v
FastAPI Backend :8001
        |
        +--> PostgreSQL :5433 (hotels, bookings, providers, requests)
        |
        +--> Hotel MCP Server :8002
        |       |
        |       +--> Hotel REST endpoints on backend
        |
        +--> Transport MCP Server :8003
        |       |
        |       +--> Transport REST endpoints on backend
        |       +--> Nominatim geocoding
        |       +--> OSRM driving route service
        |
        +--> OpenRouter / OpenAI-compatible Chat Completions
                (tool calling using the two MCP tool catalogues)
```

### Main ports

| Service | Default port | Role |
|---|---:|---|
| PostgreSQL | 5433 on host / 5432 in container | Application database |
| FastAPI backend | 8001 | REST API and AI chat API |
| Hotel MCP | 8002 | Hotel tools for the AI |
| Transport MCP | 8003 | Transport and route tools for the AI |
| Frontend Vite | 5173-5175 in development, 5174 in Compose | User interface |

## 3. Repository structure

### Backend

- [`backend/main.py`](backend/main.py) - Creates the FastAPI application, configures CORS, and registers routers.
- [`backend/database.py`](backend/database.py) - SQLAlchemy engine, session factory, and database dependency.
- [`backend/models.py`](backend/models.py) - Database models.
- [`backend/schemas.py`](backend/schemas.py) - Pydantic request/response validation schemas.
- [`backend/routers/hotels.py`](backend/routers/hotels.py) - Public hotel search and admin hotel management.
- [`backend/routers/bookings.py`](backend/routers/bookings.py) - Pending hotel booking requests.
- [`backend/routers/transport.py`](backend/routers/transport.py) - Provider auth, provider management, provider search, and transport requests.
- [`backend/routers/transport_routes.py`](backend/routers/transport_routes.py) - Coordinate-based route calculation through OSRM.
- [`backend/routers/chat.py`](backend/routers/chat.py) - AI chat orchestration and MCP tool calling.
- [`backend/hotel_mcp_server/server.py`](backend/hotel_mcp_server/server.py) - Hotel MCP tools.
- [`backend/transport_mcp_server/server.py`](backend/transport_mcp_server/server.py) - Transport, geocoding, and route MCP tools.
- [`backend/seed_hotels.py`](backend/seed_hotels.py) - Hotel data seeding and dataset validation.
- [`backend/email_service.py`](backend/email_service.py) - Email notification helpers.
- [`backend/migrations/add_hotel_management_fields.sql`](backend/migrations/add_hotel_management_fields.sql) - Hotel management field migration.
- [`backend/tests/test_booking_restrictions.py`](backend/tests/test_booking_restrictions.py) - Booking restriction tests.
- [`backend/test_hotel_mcp_client.py`](backend/test_hotel_mcp_client.py) and [`backend/test_transport_mcp.py`](backend/test_transport_mcp.py) - MCP connectivity/manual test scripts.

### Frontend

- [`frontend/src/App.tsx`](frontend/src/App.tsx) - Main UI state, chat interaction, hotel filtering/highlighting, route selection, and portal navigation.
- [`frontend/src/components/HotelMap.tsx`](frontend/src/components/HotelMap.tsx) - Hotel markers and map view.
- [`frontend/src/components/TransportRouteMap.tsx`](frontend/src/components/TransportRouteMap.tsx) - Route geometry and route map.
- [`frontend/src/components/ProviderRegistration.tsx`](frontend/src/components/ProviderRegistration.tsx) - Provider registration form.
- [`frontend/src/components/ProviderLogin.tsx`](frontend/src/components/ProviderLogin.tsx) - Provider login.
- [`frontend/src/components/ProviderDashboard.tsx`](frontend/src/components/ProviderDashboard.tsx) - Provider profile, availability, and request actions.
- [`frontend/src/components/AdminLogin.tsx`](frontend/src/components/AdminLogin.tsx) - Admin login.
- [`frontend/src/components/AdminProviderApproval.tsx`](frontend/src/components/AdminProviderApproval.tsx) - Provider approval screen.
- [`frontend/src/components/AdminHotelManagement.tsx`](frontend/src/components/AdminHotelManagement.tsx) - Admin hotel CRUD, verification, and activation controls.
- [`frontend/package.json`](frontend/package.json) - React, Leaflet, React-Leaflet, Markdown, TypeScript, Vite, and Oxlint dependencies/scripts.

### Deployment and data files

- [`docker-compose.yml`](docker-compose.yml) - PostgreSQL, backend, frontend, and combined MCP deployment.
- [`backend/Dockerfile.mcp`](backend/Dockerfile.mcp) - MCP container image.
- [`backend/requirements.txt`](backend/requirements.txt) - Python dependencies.
- [`frontend/README.md`](frontend/README.md) - Vite frontend notes.
- `hotel_geocoding_cache.json` - Geocoding-related local data.
- `hotels_without_gps_ids.txt` - Hotel records that need coordinates.
- Database dump files exist in the repository workspace; they should be handled as data backups, not application source.

## 4. Backend REST API

The backend application is created in [`backend/main.py`](backend/main.py). It registers the following routers:

### Root

- `GET /` - Returns a simple API-running message.
- FastAPI interactive documentation is normally available at `/docs` and `/redoc`.

### Hotels: `/hotels`

Public results are intentionally restricted to hotels where:

```text
available = true
is_active = true
verification_status IN ("legacy", "verified")
```

Routes:

- `GET /hotels/` - List public hotels.
- `GET /hotels/{hotel_id}` - Get one public hotel.
- `GET /hotels/city/{city_name}` - Search public hotels by city.
- `GET /hotels/district/{district_name}` - Search public hotels by district.
- `GET /hotels/admin/list` - Admin-only list including inactive/unverified records.
- `POST /hotels/admin` - Admin creates a hotel; new hotel starts pending, inactive, and unavailable.
- `PATCH /hotels/admin/{hotel_id}` - Admin edits hotel data.
- `PATCH /hotels/admin/{hotel_id}/verification` - Change pending/verified/rejected status.
- `PATCH /hotels/admin/{hotel_id}/activation` - Activate or deactivate a hotel.

Hotel validation includes required name/district/registration number, non-negative prices, valid latitude/longitude ranges, duplicate registration-number checking, and city/district consistency.

### Bookings: `/bookings`

- `POST /bookings/` - Creates a booking request with `pending` status.

Validation and business rules:

- Hotel must exist.
- Hotel must be active, available, and public (`legacy` or `verified`).
- Check-in cannot be in the past.
- Check-out must be after check-in.
- A pending booking request is not a confirmed reservation.
- The current implementation does not perform room inventory/availability locking; confirmation requires a later business workflow.

### Transport providers and requests: `/transport`

The transport router contains:

- `POST /transport/admin/login` - Admin login and access token.
- `POST /transport/providers` - Register a provider.
- `POST /transport/providers/login` - Provider login and access token.
- `GET /transport/providers/me` - Current provider profile.
- `GET /transport/providers/me/requests` - Current provider's requests.
- `PATCH /transport/providers/me/availability` - Toggle provider availability.
- `PATCH /transport/providers/me/requests/{request_id}/accept` - Accept a request.
- `PATCH /transport/providers/me/requests/{request_id}/reject` - Reject a request.
- `GET /transport/search` - Search approved/available providers by district and passenger capacity.
- `PATCH /transport/providers/{provider_id}/approve` - Admin approves/rejects a provider.
- `GET /transport/providers/{provider_id}` - Provider details.
- `POST /transport/requests` - Customer creates a transport request.
- `GET /transport/providers/{provider_id}/requests` - Provider request list.
- `PATCH /transport/requests/{request_id}/accept` - Request acceptance endpoint.
- `PATCH /transport/requests/{request_id}/reject` - Request rejection endpoint.
- `GET /transport/respond` and `POST /transport/respond/confirm` - Response/confirmation flow, including HTML confirmation.
- `GET /transport/providers` - Provider listing.

Provider records include provider name, contact details, vehicle details, passenger capacity, base district, approval state, availability, and service districts. Transport requests include customer/trip information and a status such as `pending`.

### Routes: `/transport/routes`

- `POST /transport/routes/calculate` - Takes validated pickup/destination coordinates, calls OSRM, and returns:
  - pickup and destination coordinates
  - driving distance in kilometres
  - estimated duration in minutes
  - GeoJSON `LineString` geometry

The endpoint returns a gateway error when OSRM is unavailable and a not-found response when no route is returned.

### AI chat: `/chat`

- `POST /chat/` - Main AI assistant endpoint.

Request shape:

```json
{
  "message": "Find hotels in Kandy",
  "history": [
    {"role": "user", "content": "I need a hotel"},
    {"role": "assistant", "content": "Which city?"}
  ],
  "route_selection": null
}
```

Response shape:

```json
{
  "reply": "Human-friendly assistant response",
  "hotels": [],
  "transport_route": null,
  "location_candidates": [],
  "location_role": null
}
```

`route_selection` is used after the frontend shows ambiguous geocoding candidates. It contains verified pickup/destination coordinates or a selected pickup plus destination place name. This avoids repeated geocoding and prevents the LLM from inventing coordinates.

## 5. AI and MCP chat workflow

The main implementation is in [`backend/routers/chat.py`](backend/routers/chat.py).

### Startup/configuration

1. Load environment variables using `python-dotenv`.
2. Create an OpenAI-compatible client configured for OpenRouter.
3. Connect to the Hotel MCP server at `HOTEL_MCP_SERVER_URL`.
4. Connect to the Transport MCP server at `TRANSPORT_MCP_SERVER_URL`.
5. Initialize both MCP sessions.
6. Discover their tools dynamically with `list_tools()`.
7. Convert MCP schemas into OpenAI tool definitions.

### Normal chat request

1. Build a conversation from the last 20 user/assistant messages.
2. Add the latest user message if it is not already the final message.
3. Send system instructions, conversation, and both MCP tool catalogues to the OpenRouter model.
4. Let the model choose tools.
5. Execute hotel tools on the Hotel MCP session or transport tools on the Transport MCP session.
6. Append tool results to the model conversation.
7. Repeat for up to six tool-call rounds.
8. Return a clean assistant reply plus structured hotel/route/location data for the frontend.

### Hotel parsing

`parse_mcp_hotel_results()`:

- Handles standalone JSON and nested/wrapped MCP responses.
- Accepts hotel objects that contain an integer `id` and non-empty `name`.
- Validates latitude and longitude ranges and finite numeric values.
- Deduplicates hotels by ID.
- Retains hotels without coordinates so the UI can still show search results.
- Only collects map data from successful hotel read tools, not booking actions.

### Transport route parsing

`parse_mcp_transport_route()` accepts only route data containing:

- pickup object
- destination object
- GeoJSON `LineString`
- at least two coordinates
- numeric distance
- numeric duration

Invalid or incomplete route output is not shown as a successful route.

### Location clarification

The transport MCP geocodes Sri Lankan place names with Nominatim. If multiple candidates are returned, the backend sends candidate names and coordinates to the frontend. The user selects one, and the next request uses the exact returned coordinates.

### Safety/business instructions built into the assistant

The system prompt instructs the model to:

- Use live MCP data for searches and actions.
- Avoid inventing hotels, prices, ratings, providers, bookings, routes, distances, and coordinates.
- Keep pending bookings and pending transport requests clearly distinct from confirmations.
- Avoid exposing raw JSON, internal tool output, database records, or unnecessary IDs.
- Treat legacy listings as not automatically proving official SLTDA verification.
- Use the latest relevant conversation context and avoid mixing unrelated searches.
- Keep normal chat responses short unless the user asks for details.

## 6. MCP services

### Hotel MCP: [`backend/hotel_mcp_server/server.py`](backend/hotel_mcp_server/server.py)

Runs as a streamable HTTP MCP server on port `8002`.

Tools:

- `search_hotels`
- `get_hotel`
- `get_hotels_by_city`
- `get_hotels_by_district`
- `create_booking`

The tools call the backend REST API rather than connecting to the database directly. Booking output explicitly says it is a request and not a confirmed reservation.

### Transport MCP: [`backend/transport_mcp_server/server.py`](backend/transport_mcp_server/server.py)

Runs as a streamable HTTP MCP server on port `8003`.

Tools:

- `search_transport`
- `get_transport_provider`
- `create_transport_request`
- `get_transport_route`
- `get_transport_route_by_places`
- `get_transport_route_from_coordinates_to_place`

The server normalizes common time formats such as `10:30 AM`, `2:30 PM`, `14:30`, and `14:30:00`. Named-place routing uses Nominatim geocoding and coordinate routing uses the backend route endpoint.

## 7. Database design

SQLAlchemy entities are defined in [`backend/models.py`](backend/models.py).

### Tables/entities

| Entity | Main responsibility |
|---|---|
| `City` | Sri Lankan city, district, and province reference data |
| `Hotel` | Hotel listing, contact/location data, price/rating, availability, verification, activation |
| `Booking` | Customer hotel booking request and dates |
| `TransportProvider` | Provider account, vehicle, capacity, approval, and availability |
| `ProviderServiceDistrict` | Additional districts served by a provider |
| `TransportRequest` | Customer transport request, trip details, provider, and status |

Important hotel state fields:

- `verification_status`: `pending`, `verified`, or `rejected`; `legacy` is supported for earlier listings.
- `is_active`: administrative publication control.
- `available`: operational availability control.

The database session is provided through `get_db()` in [`backend/database.py`](backend/database.py). The `DATABASE_URL` environment variable should be configured for the target environment.

## 8. Frontend behavior

The frontend is a React 19 + TypeScript + Vite application.

Main UI areas:

1. **AI chat**
   - Sends messages and recent history to `POST http://127.0.0.1:8001/chat/`.
   - Renders assistant replies with Markdown/GFM.
   - Shows hotel cards and map markers returned in structured response data.
   - Supports clear-chat and quick-action style interactions.

2. **Hotel map**
   - Uses Leaflet/React-Leaflet.
   - Shows only hotel data returned from successful hotel read operations.
   - Highlights an explicitly requested hotel without guessing when names are ambiguous.
   - Can narrow related results to the requested hotel's district.

3. **Transport route map**
   - Displays the returned route geometry.
   - Shows pickup, destination, distance, and estimated duration.
   - Shows a traffic disclaimer because duration is an estimate.

4. **Provider portal**
   - Registration and login.
   - Provider dashboard.
   - Availability toggle.
   - Request list and accept/reject actions.

5. **Admin portal**
   - Admin login.
   - Provider approval.
   - Hotel listing management.
   - Hotel verification and activation.

The frontend currently uses direct backend URLs in several components. For production deployment, these should be moved to a Vite environment variable or reverse-proxy-relative API URL.

## 9. Configuration and environment variables

The application reads environment variables in backend/MCP modules. Configure these in a local `.env` file or deployment secret manager; do not commit real credentials.

Common variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENROUTER_API_KEY` | OpenRouter authentication |
| `OPENROUTER_MODEL` | Model name; defaults to `openrouter/free` |
| `HOTEL_MCP_SERVER_URL` | Hotel MCP endpoint; default local URL uses port 8002 |
| `TRANSPORT_MCP_SERVER_URL` | Transport MCP endpoint; default local URL uses port 8003 |
| `API_BASE_URL` | Backend URL used by MCP servers |
| `GEOCODING_URL` | Geocoding provider URL; transport MCP defaults to Nominatim |
| `GEOCODING_USER_AGENT` | User-Agent for geocoding requests |
| `ROUTING_URL` | Routing provider URL; backend defaults to OSRM |
| JWT/admin/provider secret variables | Check the auth implementation in `backend/routers/transport.py` and set deployment-specific secrets |
| Email service variables | Check `backend/email_service.py` before enabling notifications |

## 10. Local setup

### Backend

From the repository root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `backend/.env` with a valid database URL, OpenRouter key, MCP URLs, and authentication/email settings.

Start the REST API:

```powershell
cd backend
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Start the MCP servers separately when running without Docker:

```powershell
cd backend
python -m hotel_mcp_server.server
python -m transport_mcp_server.server
```

Run database seed/migration scripts only after verifying the target database and backup:

```powershell
cd backend
python seed_hotels.py
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Build and lint:

```powershell
cd frontend
npm run build
npm run lint
```

### Docker Compose

From the repository root:

```powershell
docker compose up --build
```

The Compose setup starts PostgreSQL, backend, frontend, and the combined MCP container. Verify that the database URL and mounted backend `.env` file are correct for the local machine before starting.

## 11. Testing and verification

Current verification assets include:

- [`backend/tests/test_booking_restrictions.py`](backend/tests/test_booking_restrictions.py) for booking rules.
- [`backend/test_hotel_mcp_client.py`](backend/test_hotel_mcp_client.py) for Hotel MCP connectivity.
- [`backend/test_transport_mcp.py`](backend/test_transport_mcp.py) for Transport MCP connectivity.
- `npm run build` for TypeScript compilation and Vite production build.
- `npm run lint` for frontend lint checks.

Recommended smoke-test order:

1. Confirm PostgreSQL is reachable.
2. Confirm `GET /` on port 8001.
3. Confirm Hotel MCP and Transport MCP health/connectivity.
4. Test public hotel listing and a public hotel detail.
5. Test the chat search flow.
6. Test an ambiguous route and candidate selection.
7. Test coordinate route calculation and map rendering.
8. Test provider registration/login/approval.
9. Test booking and transport request pending-state behavior.

## 12. Current strengths

- Clear service separation between REST API and AI-facing MCP tools.
- Strong instructions against fabricated hotel/transport/route data.
- Public hotel visibility rules are enforced at the backend, not only in the UI.
- Hotel booking rules reject inactive/unavailable/unverified hotels.
- Route coordinates are validated and selected geocoding results are reused exactly.
- Hotel and route data are returned separately from natural-language chat text.
- Admin workflow distinguishes legacy listings from official verification claims.
- Pydantic validation covers dates, coordinate ranges, required fields, and several domain constraints.
- React UI provides maps and role-specific provider/admin screens.

## 13. Important limitations and risks to address

These are implementation observations for future hardening, not claims that the application is unusable:

1. **Secrets and credentials**
   - Keep database passwords, OpenRouter keys, JWT secrets, and email credentials outside Git.
   - Rotate any credential that may have been exposed in local files, backups, logs, or deployment configuration.

2. **Authentication hardening**
   - Review JWT secret management, token expiry, role checks, password policy, rate limiting, and CORS before production.
   - Replace development/default secrets and avoid relying on local hardcoded admin credentials.

3. **Frontend API configuration**
   - Replace hardcoded `127.0.0.1:8001` URLs with an environment-driven API base URL.
   - Production frontend and backend may run on different hosts.

4. **Booking availability**
   - A pending booking is stored, but the current model does not show room inventory, overlap checks, payment, cancellation, or confirmation workflow.

5. **Database migrations**
   - The project contains SQL migration material, but a complete versioned migration system should be used for repeatable deployments.

6. **External service reliability**
   - Nominatim and OSRM are external services with rate limits and availability constraints. Use an approved provider, identifying User-Agent, caching, retries, and production SLA where required.

7. **Observability**
   - Replace ad-hoc `print()` diagnostics with structured logging, request IDs, and monitored error reporting.

8. **Input and abuse controls**
   - Add request rate limits, payload size limits, stricter email/phone validation, audit logs, and authorization tests for every admin/provider action.

9. **Transport state consistency**
   - Review duplicate accept/reject routes and concurrent status changes so a request cannot be accepted and rejected simultaneously.

10. **Automated test coverage**
    - Add API integration tests for hotel visibility, admin authorization, provider workflows, chat tool loops, MCP failures, and route ambiguity.

## 14. Suggested next development priorities

### Priority 1 - Production safety

- Move all secrets to deployment secret storage.
- Add strong JWT/admin/provider configuration.
- Restrict production CORS origins.
- Add rate limiting and structured logging.
- Add authorization and negative-path integration tests.

### Priority 2 - Booking correctness

- Add room inventory and date-overlap checks.
- Add explicit booking confirmation/rejection/cancellation states.
- Add customer notifications and provider/admin notifications.
- Add idempotency keys for booking and transport request creation.

### Priority 3 - Deployment reliability

- Add proper database migrations and startup checks.
- Add health/readiness endpoints for backend and MCP services.
- Add Docker health checks and service retry policy.
- Use configurable frontend API URLs.

### Priority 4 - Product improvements

- Add search filters for price, rating, accommodation type, and amenities.
- Add pagination and sorting.
- Add hotel detail pages and image support.
- Improve route candidate ranking and caching.
- Add provider ratings and completed-trip history.

## 15. One-paragraph presentation summary

SerendibStay AI is a full-stack Sri Lankan travel platform that combines a React/TypeScript interface with a FastAPI/PostgreSQL backend. It supports hotel discovery, controlled hotel publishing, pending booking requests, transport-provider registration and management, transport requests, and interactive route maps. Its AI assistant uses OpenRouter function calling with separate Hotel and Transport MCP servers so natural-language requests can use live system data while preserving strict rules against invented hotels, prices, confirmations, coordinates, and route details. The application is Docker-ready, but production deployment still requires stronger secret management, authentication hardening, booking inventory/confirmation logic, migration discipline, external-service controls, and broader automated integration testing.

