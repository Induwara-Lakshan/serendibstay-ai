import json

import os

import traceback

from dotenv import load_dotenv

from fastapi import APIRouter, HTTPException

from mcp import ClientSession

from mcp.client.streamable_http import streamable_http_client

from openai import OpenAI

from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])

client = OpenAI(

    base_url="https://openrouter.ai/api/v1",

    api_key=os.getenv("OPENROUTER_API_KEY"),

)

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

HOTEL_MCP_SERVER_URL = os.getenv(

    "HOTEL_MCP_SERVER_URL", "http://127.0.0.1:8002/mcp"

)

TRANSPORT_MCP_SERVER_URL = os.getenv(

    "TRANSPORT_MCP_SERVER_URL", "http://127.0.0.1:8003/mcp"

)

class ChatMessage(BaseModel):

    role: str

    content: str

class SelectedLocation(BaseModel):

    name: str

    latitude: float

    longitude: float

class RouteSelection(BaseModel):

    pickup: SelectedLocation | None = None

    destination: SelectedLocation | None = None

    destination_name: str | None = None

    original_request: str | None = None

class ChatRequest(BaseModel):

    message: str

    history: list[ChatMessage] = Field(default_factory=list)

    route_selection: RouteSelection | None = None

class HotelData(BaseModel):

    id: int

    name: str

    address: str | None = None

    district: str | None = None

    accommodation_type: str | None = None

    registration_no: str | None = None

    licence_no: str | None = None

    source: str | None = None

    price_per_night: float | None = None

    rating: float | None = None

    available: bool | None = None

    city_id: int | None = None

    latitude: float | None = None

    longitude: float | None = None

class ChatResponse(BaseModel):

    reply: str

    hotels: list[dict] = Field(default_factory=list)

    transport_route: dict | None = None

    location_candidates: list[dict] = Field(default_factory=list)

    location_role: str | None = None

async def get_openai_tools(session: ClientSession):

    """Convert MCP tools into the OpenRouter Chat Completions format."""

    result = await session.list_tools()

    return [

        {

            "type": "function",

            "function": {

                "name": tool.name,

                "description": tool.description or "",

                "parameters": tool.input_schema,

            },

        }

        for tool in result.tools

    ]

def get_mcp_result_text(mcp_result) -> str:

    """Flatten MCP text blocks for the LLM, preserving existing behavior."""

    return "".join(

        content.text

        for content in mcp_result.content

        if hasattr(content, "text")

    )

def parse_mcp_hotel_results(result_text: str) -> list[dict]:
    """Extract hotel records from JSON MCP responses, including wrapped results.

    Hotels without coordinates are retained for frontend location-search links.
    """
    import math

    decoder = json.JSONDecoder()
    parsed_values = []
    position = 0
    while position < len(result_text):
        try:
            data, end = decoder.raw_decode(result_text, position)
            parsed_values.append(data)
            position = end
        except json.JSONDecodeError:
            position += 1

    def candidates(value, depth=0):
        if depth > 5:
            return
        if isinstance(value, list):
            for item in value:
                yield from candidates(item, depth + 1)
        elif isinstance(value, dict):
            if "id" in value and "name" in value:
                yield value
            else:
                for key in ("hotels", "results", "result", "data", "items", "content", "structuredContent"):
                    if key in value:
                        yield from candidates(value[key], depth + 1)
                if value.get("type") == "text" and isinstance(value.get("text"), str):
                    try:
                        yield from candidates(json.loads(value["text"]), depth + 1)
                    except json.JSONDecodeError:
                        pass
        elif isinstance(value, str):
            try:
                yield from candidates(json.loads(value), depth + 1)
            except json.JSONDecodeError:
                pass

    hotels_by_id = {}
    for value in parsed_values:
        for hotel in candidates(value):
            hotel_id = hotel.get("id")
            name = hotel.get("name")
            if (not isinstance(hotel_id, int) or isinstance(hotel_id, bool)
                    or not isinstance(name, str) or not name.strip()):
                continue
            try:
                lat = float(hotel["latitude"]) if hotel.get("latitude") is not None else None
                lon = float(hotel["longitude"]) if hotel.get("longitude") is not None else None
                if (lat is None or lon is None or not math.isfinite(lat)
                        or not math.isfinite(lon)
                        or not (-90 <= lat <= 90 and -180 <= lon <= 180)):
                    lat, lon = None, None
            except (TypeError, ValueError, OverflowError):
                lat, lon = None, None
            hotels_by_id[hotel_id] = {
                "id": hotel_id,
                "name": name,
                "address": hotel.get("address"),
                "district": hotel.get("district"),
                "latitude": lat,
                "longitude": lon,

                # Additional hotel information
                "description": hotel.get("description"),
                "accommodation_type": hotel.get("accommodation_type"),
                "price_per_night": hotel.get("price_per_night"),
                "rating": hotel.get("rating"),
                "available": hotel.get("available"),
                "registration_no": hotel.get("registration_no"),
                "licence_no": hotel.get("licence_no"),
            }
    return list(hotels_by_id.values())

def parse_mcp_transport_route(result_text: str) -> dict | None:

    """Extract a valid transport route from MCP tool output."""

    decoder = json.JSONDecoder()

    position = 0

    while position < len(result_text):

        try:

            data, end = decoder.raw_decode(result_text, position)

            position = end

        except json.JSONDecodeError:

            position += 1

            continue

        if not isinstance(data, dict):

            continue

        geometry = data.get("geometry")

        pickup = data.get("pickup")

        destination = data.get("destination")

        if not all(

            isinstance(item, dict)

            for item in (geometry, pickup, destination)

        ):

            continue

        if (

            geometry.get("type") == "LineString"

            and isinstance(geometry.get("coordinates"), list)

            and len(geometry["coordinates"]) >= 2

            and isinstance(data.get("distance_km"), (int, float))

            and isinstance(data.get("duration_minutes"), (int, float))

        ):

            return data

    return None

def build_conversation_input(request: ChatRequest):

    conversation = []

    for message in request.history[-20:]:

        if message.role in ("user", "assistant"):

            conversation.append({"role": message.role, "content": message.content})

    if (

        not conversation

        or conversation[-1]["role"] != "user"

        or conversation[-1]["content"] != request.message

    ):

        conversation.append({"role": "user", "content": request.message})

    return conversation

def parse_location_candidates(result_text: str) -> list[dict]:

    """

    Extract location candidates from an ambiguous

    Transport MCP tool response.

    """

    try:

        data = json.loads(result_text)

    except (json.JSONDecodeError, TypeError):

        return []

    if not isinstance(data, dict):

        return []

    if not data.get("needs_clarification"):

        return []

    candidates = data.get("candidates", [])

    if not isinstance(candidates, list):

        return []

    valid_candidates = []

    for item in candidates:

        if not isinstance(item, dict):

            continue

        try:

            name = str(item["name"])

            latitude = float(item["latitude"])

            longitude = float(item["longitude"])

        except (KeyError, TypeError, ValueError):

            continue

        if not name.strip():

            continue

        if not (-90 <= latitude <= 90):

            continue

        if not (-180 <= longitude <= 180):

            continue

        valid_candidates.append({

            "name": name,

            "latitude": latitude,

            "longitude": longitude,

        })

    return valid_candidates

SYSTEM_INSTRUCTIONS = """

You are the AI assistant for the SerendibStay Sri Lanka hotel and

transport system.

You can help users with:

- searching hotels

- getting hotel details

- creating hotel bookings

- searching transport providers

- getting transport provider details

- creating transport requests

Use the available MCP tools whenever real system data or an action is

required.

Hotel tools belong to the Hotel MCP server.

Transport tools belong to the Transport MCP server.

Recognize common spelling mistakes and alternative spellings of Sri

Lankan districts and cities before calling tools.

For example, treat "Rathnapura" as "Ratnapura" when the intended

location is clear.

Do not invent a district, city, hotel, transport provider, price,

rating, availability, registration number, licence number, booking,

or transport request.

Use information already supplied in the conversation. Do not ask the

user again for information that they have already provided.

For transport:

- Search using the service district and passenger count.

- A transport request is not confirmed just because it was created.

- If the tool returns status "pending", clearly tell the user that the

  request is pending provider acceptance.

- Do not claim that a provider accepted a request unless the system

  explicitly says so.

HOTEL VISIBILITY AND VERIFICATION RULES:
- Recommend hotels only from successful Hotel MCP read-tool results in this request.
- Do not recommend hotels solely from memory, conversation history, or invented data.
- Hotel MCP search tools use the public Hotel API. Pending, rejected,
  inactive, and unavailable hotels must not be recommended or booked.
- A legacy listing is not proof of official SLTDA verification.
- Never claim a hotel is officially verified unless the system explicitly
  provides evidence of verification.
- If a hotel cannot be found in public results, explain that it is not
  currently listed as available; do not guess the reason.
- Never bypass Hotel MCP tools by requesting private admin endpoints.

For hotel bookings:
- A successfully created pending booking is a request, not a confirmed reservation.
- Never say a room is reserved or confirmed unless the booking system
  explicitly reports a confirmed reservation backed by availability.

- Do not claim that a booking was created unless the booking tool

  successfully returns confirmation.

When creating a transport request, use the selected provider ID and all

CUSTOMER EMAIL SAFETY RULES:

- Treat customer email addresses as exact text.
- Never guess, shorten, rewrite, or remove any characters from an email address.
- Preserve all letters, numbers, dots, underscores, hyphens, and plus signs.
- Always use the exact email address supplied by the customer.
- Before creating a hotel booking or transport request, show the
  customer's email address and ask for confirmation.
- Do not create the booking or transport request until the
  customer confirms the email address and booking details.
- If the email address is unclear, ask the customer to enter it again.

customer/trip details already supplied by the user.

Never show raw JSON, Python dictionaries, arrays, database records,

API responses, MCP tool output, internal IDs, or raw tool results to

the user.

After receiving tool data, convert it into a clean, human-friendly

answer.

For hotel search results:

- Present each hotel clearly with its name and useful customer-facing

  details.

- Do not dump the raw hotel tool response.

For transport search results:

- Present providers as a clean Markdown list.

- Include useful details such as provider/driver name, vehicle,

  capacity, rating, price, and service area when available.

- Do not display the raw transport tool response before or after the

  formatted answer.

Do not repeat the same search results in multiple formats.

Only include internal database IDs when genuinely useful for the next

action. Otherwise, keep internal IDs hidden.

Use Markdown for presentation, but keep the response concise and easy

to scan.

Keep answers clear, concise, and helpful.

For the chat UI, default to 1-2 short sentences (under 45 words) unless the

user specifically asks for details. Avoid repeating location candidates,

coordinates, technical tool names, or the same route summary twice.

For location clarification, return a short prompt; the frontend renders

location choices as buttons.



TRANSPORT ROUTE INSTRUCTIONS:

MIXED COORDINATES AND PLACE NAME ROUTING:

When the user selects a location candidate and its

verified latitude and longitude are available:

- Do not geocode the selected location again.

- If the selected location is the pickup and the

  destination is a place name, use

  get_transport_route_from_coordinates_to_place.

- Pass the selected pickup latitude and longitude

  exactly as returned by the location lookup tool.

- Pass the destination place name supplied by

  the user.

- If the destination is already known from the

  previous conversation, reuse that destination.

- Do not ask the user for destination coordinates

  when a destination place name is already available.

- If the destination lookup returns multiple

  candidates, ask the user to select the correct one.

- Never invent coordinates, distances, or travel times.

ROUTE LOCATION LOOKUP RULES:

When a user requests a driving route between named places:

1. Always call get_transport_route_by_places first,

   even if a location name might be ambiguous.

2. Do not decide that a location is ambiguous

   based only on general knowledge.

3. Use the geocoding results returned by the MCP

   tool to determine whether clarification is needed.

4. If the tool returns needs_clarification=true,

   show only the location candidates returned by

   the tool and ask the user to select one.

5. Do not invent location candidates.

6. If the tool returns a valid route, show the

   distance and estimated travel time.

7. Never invent route distances or coordinates.

When a user asks for driving distance, travel duration, or a route

between two named places in Sri Lanka, use the

get_transport_route_by_places tool.

Examples:

- "How far is Bandaranaike International Airport from Jetwing Blue Hotel?"

- "Show the route from Colombo Fort to Galle Face Hotel."

- "How long does it take to travel from Kandy to Nuwara Eliya?"

When the user provides latitude and longitude coordinates for both

locations, use get_transport_route instead.

Never invent coordinates, driving distances, or travel times.

If a location is ambiguous, ask the user to clarify it.

LOCATION CLARIFICATION AND SELECTION:

When a route tool returns multiple location candidates:

- Show the candidate names clearly.

- Ask the user to select the correct location.

- Do not invent additional candidates.

When the user selects one of the returned candidates:

- Find the selected candidate in the previous tool results.

- Reuse its exact latitude and longitude.

- Do not geocode the selected location again.

- Never guess or generate coordinates.

If both pickup and destination have verified coordinates,

use get_transport_route to calculate the driving route.

If only one location has verified coordinates, resolve the

other location using the appropriate MCP tool.

If the selected candidate's coordinates are not available

in the conversation context, do not invent them.

Ask for a more precise location instead.

Only report driving distance and duration returned by

the routing tool.

When the route tool succeeds, provide a short summary of the pickup,

destination, distance, and estimated driving time.

The SerendibStay AI frontend supports an interactive transport route map.

Do not tell the user that maps cannot be displayed.

Do not include the full route geometry in the chat message.

CONVERSATION CONTEXT RULES:

- Always prioritize the user's latest message.
- If the user explicitly mentions a new hotel, city, or district,
  treat it as the current topic.
- Do not mix hotel names, locations, or recommendations from
  previous unrelated searches into the current answer.
- Use conversation history only when it is relevant to the
  user's latest request.
- For follow-up questions such as "What is its price?" or
  "Show its location", use the most recent relevant hotel
  from the conversation.
- Never add follow-up suggestions about a previous city or
  hotel when the user has explicitly switched to another one.
- Retrieve current hotel information using Hotel MCP tools
  rather than relying on previous conversation results.

"""



@router.post("/", response_model=ChatResponse)

async def chat(request: ChatRequest):

    try:

        async with streamable_http_client(HOTEL_MCP_SERVER_URL) as (

            hotel_read, hotel_write

        ):

            async with ClientSession(hotel_read, hotel_write) as hotel_session:

                await hotel_session.initialize()

                hotel_tools = await get_openai_tools(hotel_session)

                hotel_tool_names = {

                    tool["function"]["name"] for tool in hotel_tools

                }

                async with streamable_http_client(TRANSPORT_MCP_SERVER_URL) as (

                    transport_read, transport_write

                ):

                    async with ClientSession(

                        transport_read, transport_write

                    ) as transport_session:

                        await transport_session.initialize()

                        transport_tools = await get_openai_tools(transport_session)

                        transport_tool_names = {

                            tool["function"]["name"] for tool in transport_tools

                        }

                        # A verified UI selection is structured input, not an LLM prompt.

                        # This prevents repeat geocoding and clarification loops.

                        if request.route_selection is not None:

                            selection = request.route_selection

                            pickup = selection.pickup

                            destination = selection.destination

                            if pickup and destination:

                                tool_name = "get_transport_route"

                                arguments = {

                                    "pickup_latitude": pickup.latitude,

                                    "pickup_longitude": pickup.longitude,

                                    "destination_latitude": destination.latitude,

                                    "destination_longitude": destination.longitude,

                                    "pickup_name": pickup.name,

                                    "destination_name": destination.name,

                                }

                            elif pickup and selection.destination_name:

                                tool_name = "get_transport_route_from_coordinates_to_place"

                                arguments = {

                                    "pickup_latitude": pickup.latitude,

                                    "pickup_longitude": pickup.longitude,

                                    "pickup_name": pickup.name,

                                    "destination": selection.destination_name,

                                }

                            else:

                                return ChatResponse(reply="Please choose a pickup and destination.")

                            if tool_name not in transport_tool_names:

                                return ChatResponse(reply="The required route tool is unavailable.")

                            tool_result = await transport_session.call_tool(tool_name, arguments)

                            result_text = get_mcp_result_text(tool_result)

                            route = parse_mcp_transport_route(result_text)

                            if route is not None:

                                return ChatResponse(

                                    reply=(f"Route ready! **{route['distance_km']:.1f} km** · "

                                           f"**{route['duration_minutes']:.0f} min**"),

                                    transport_route=route,

                                )

                            candidates = parse_location_candidates(result_text)

                            if candidates:

                                return ChatResponse(

                                    reply="Choose your destination:",

                                    location_candidates=candidates,

                                    location_role="destination",

                                )

                            return ChatResponse(reply="I couldn't calculate that route. Please try a more specific location.")

                        tools = hotel_tools + transport_tools

                        messages = [

                            {"role": "system", "content": SYSTEM_INSTRUCTIONS}

                        ]

                        messages.extend(build_conversation_input(request))

                        # Only hotel read-tools supply map markers. Do not attach

                        # map data from booking actions or transport results.

                        map_hotels_by_id: dict[int, dict] = {}

                        transport_route_data: dict | None = None

                        parsed_route: dict | None = None

                        location_candidates: list[dict] = []

                        hotel_read_tools = {

                            "search_hotels",

                            "get_hotel",

                            "get_hotels_by_city",

                            "get_hotels_by_district",

                        }

                        for _ in range(6):

                            response = client.chat.completions.create(

                                model=OPENROUTER_MODEL,

                                messages=messages,

                                tools=tools,

                                tool_choice="auto",

                            )

                            if not response.choices:

                                return ChatResponse(

                                    reply="I could not generate a response.",

                                    hotels=list(map_hotels_by_id.values()),

                                    transport_route=transport_route_data,

                                    location_candidates=location_candidates,

                                )

                            assistant_message = response.choices[0].message

                            print("AI RESPONSE:", assistant_message.model_dump_json(), flush=True)

                            tool_calls = assistant_message.tool_calls or []

                            if not tool_calls:

                                return ChatResponse(

                                    reply=(

                                        assistant_message.content

                                        or "I could not generate a response."

                                    ),

                                    hotels=list(map_hotels_by_id.values()),

                                    transport_route=transport_route_data,

                                    location_candidates=location_candidates,

                                )

                            assistant_tool_calls = [

                                {

                                    "id": tool_call.id,

                                    "type": "function",

                                    "function": {

                                        "name": tool_call.function.name,

                                        "arguments": tool_call.function.arguments,

                                    },

                                }

                                for tool_call in tool_calls

                            ]

                            messages.append(

                                {

                                    "role": "assistant",

                                    "content": assistant_message.content,

                                    "tool_calls": assistant_tool_calls,

                                }

                            )

                            for tool_call in tool_calls:

                                tool_name = tool_call.function.name

                                try:

                                    arguments = json.loads(

                                        tool_call.function.arguments or "{}"

                                    )

                                except json.JSONDecodeError:

                                    arguments = {}

                                if tool_name in hotel_tool_names:

                                    mcp_result = await hotel_session.call_tool(

                                        tool_name, arguments

                                    )

                                    result_text = get_mcp_result_text(mcp_result)

                                    if tool_name in hotel_read_tools and not mcp_result.is_error:

                                        parsed_hotels = parse_mcp_hotel_results(result_text)
                                        print(
                                            f"Hotel MCP {tool_name}: parsed {len(parsed_hotels)} hotels",
                                            flush=True,
                                        )
                                        for hotel in parsed_hotels:
                                            map_hotels_by_id[hotel["id"]] = hotel

                                elif tool_name in transport_tool_names:

                                    mcp_result = await transport_session.call_tool(

                                        tool_name, arguments

                                    )

                                    result_text = get_mcp_result_text(

                                        mcp_result

                                    )

                                    # Extract location candidates

                                    # when clarification is required.

                                    if tool_name in {

                                        "get_transport_route_by_places",

                                        "get_transport_route_from_coordinates_to_place",

                                    }:

                                        candidates = parse_location_candidates(

                                            result_text

                                        )

                                        if candidates:

                                            location_candidates = candidates

                                    # Extract route data for the map.

                                    if tool_name in {

                                        "get_transport_route",

                                        "get_transport_route_by_places",

                                        "get_transport_route_from_coordinates_to_place",

                                    }:

                                        print(

                                            "ROUTE TOOL:",

                                            tool_name,

                                            flush=True

                                        )

                                        parsed_route = parse_mcp_transport_route(

                                            result_text

                                        )

                                        if parsed_route is not None:

                                            transport_route_data = parsed_route

                                            print(

                                                "ROUTE PARSED SUCCESSFULLY",

                                                flush=True

                                            )

                                        else:

                                            print(

                                                "NO VALID ROUTE DATA",

                                                flush=True

                                            )

                                if not result_text:

                                    result_text = json.dumps(

                                        {"error": "Tool returned no data"}

                                    )

                                messages.append(

                                    {

                                        "role": "tool",

                                        "tool_call_id": tool_call.id,

                                        "content": result_text,

                                    }

                                )

                                if location_candidates:

                                    return ChatResponse(

                                        reply="Choose your pickup:",

                                        location_candidates=location_candidates,

                                        location_role="pickup",

                                    )

                        return ChatResponse(

                            reply=(

                                "I could not complete the request "

                                "after several system operations."

                            ),

                            hotels=list(map_hotels_by_id.values()),

                            transport_route=transport_route_data,

                            location_candidates=location_candidates,

                        )

    except Exception as e:

        traceback.print_exc()

        raise HTTPException(

            status_code=500,

            detail="AI/MCP service error. Check backend logs.",

        )
