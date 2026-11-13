import os
import httpx
from datetime import datetime

from mcp.server.mcpserver import MCPServer


API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8001"
)

mcp = MCPServer("Sri Lanka Transport MCP")


def normalize_pickup_time(pickup_time: str) -> str:
    """
    Convert common user time formats to HH:MM:SS format.

    Examples:
    10:30 AM -> 10:30:00
    2:30 PM  -> 14:30:00
    14:30    -> 14:30:00
    14:30:00 -> 14:30:00
    """

    value = pickup_time.strip()

    supported_formats = [
        "%I:%M %p",
        "%I:%M%p",
        "%H:%M",
        "%H:%M:%S",
    ]

    for time_format in supported_formats:
        try:
            parsed_time = datetime.strptime(
                value,
                time_format
            )

            return parsed_time.strftime("%H:%M:%S")

        except ValueError:
            continue

    raise ValueError(
        "Invalid pickup time. "
        "Use a format such as 10:30 AM or 14:30."
    )


@mcp.tool()
async def search_transport(
    district: str,
    passengers: int = 1
) -> list:
    """
    Search approved and available transport providers
    by service district and passenger capacity.
    """

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/transport/search",
            params={
                "district": district,
                "passengers": passengers
            }
        )

        response.raise_for_status()

        return response.json()


@mcp.tool()
async def get_transport_provider(
    provider_id: int
) -> dict:
    """
    Get details of a specific transport provider
    by provider ID.
    """

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/transport/providers/{provider_id}"
        )

        if response.status_code == 404:
            return {
                "error": "Transport provider not found",
                "provider_id": provider_id
            }

        response.raise_for_status()

        return response.json()


@mcp.tool()
async def create_transport_request(
    provider_id: int,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    pickup_location: str,
    destination: str,
    pickup_date: str,
    pickup_time: str,
    passengers: int
) -> dict:
    """
    Create a transport request for a selected
    transport provider.
    """

    # ------------------------------------------
    # Normalize pickup time
    # ------------------------------------------
    try:
        normalized_time = normalize_pickup_time(
            pickup_time
        )

    except ValueError as error:
        return {
            "error": str(error)
        }

    # ------------------------------------------
    # Build API request
    # ------------------------------------------
    request_data = {
        "provider_id": provider_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "customer_phone": customer_phone,
        "pickup_location": pickup_location,
        "destination": destination,
        "pickup_date": pickup_date,
        "pickup_time": normalized_time,
        "passengers": passengers
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/transport/requests",
            json=request_data
        )

        # --------------------------------------
        # Handle API validation/errors
        # --------------------------------------
        if response.status_code in [
            400,
            404,
            422
        ]:
            try:
                error_data = response.json()

                return {
                    "error": error_data.get(
                        "detail",
                        "Transport request failed"
                    )
                }

            except Exception:
                return {
                    "error": "Transport request failed"
                }

        response.raise_for_status()

        return response.json()



@mcp.tool()
async def get_transport_route(
    pickup_latitude: float,
    pickup_longitude: float,
    destination_latitude: float,
    destination_longitude: float,
) -> dict:
    """
    Calculate a driving route between two known coordinates.
    Returns route geometry, distance and estimated duration.
    Does not create a transport booking.
    """

    request_data = {
        "pickup_latitude": pickup_latitude,
        "pickup_longitude": pickup_longitude,
        "destination_latitude": destination_latitude,
        "destination_longitude": destination_longitude,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/transport/routes/calculate",
                json=request_data,
            )

            if response.status_code != 200:
                return {
                    "error": "Unable to calculate transport route",
                    "status_code": response.status_code,
                }

            return response.json()

    except httpx.HTTPError:
        return {
            "error": "Transport routing service is unavailable"
        }


GEOCODING_URL = os.getenv(
    "GEOCODING_URL",
    "https://nominatim.openstreetmap.org/search"
)

GEOCODING_USER_AGENT = os.getenv(
    "GEOCODING_USER_AGENT",
    "SerendibStayAI-Development/1.0 (contact: configure-your-email)"
)


async def geocode_place(
    client: httpx.AsyncClient,
    place_name: str
) -> dict | None:
    """
    Find coordinates for a named place in Sri Lanka.
    Returns None if no location is found.
    """

    response = await client.get(
        GEOCODING_URL,
        params={
            "q": place_name,
            "format": "jsonv2",
            "limit": 5,
            "countrycodes": "lk"
        },
        headers={
            "User-Agent": GEOCODING_USER_AGENT
        }
    )

    response.raise_for_status()
    results = response.json()


    if not results:
        return None

    # Do not automatically select an ambiguous location.
    if len(results) > 1:
        return {
            "ambiguous": True,
            "query": place_name,
            "candidates": [
                {
                    "name": item.get("display_name", ""),
                    "latitude": float(item["lat"]),
                    "longitude": float(item["lon"]),
                }
                for item in results
            ],
        }

    location = results[0]


    return {
        "name": location.get("display_name", place_name),
        "latitude": float(location["lat"]),
        "longitude": float(location["lon"])
    }


@mcp.tool()
async def get_transport_route_by_places(
    pickup_location: str,
    destination: str
) -> dict:
    """
    Calculate a driving route between two named places
    in Sri Lanka.

    Use this tool when the user provides place names,
    addresses, airports or hotel names instead of
    latitude and longitude coordinates.

    Returns distance, duration and route geometry.
    Does not create a booking.
    """

    if not pickup_location.strip() or not destination.strip():
        return {
            "error": "Pickup and destination are required"
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:

            pickup = await geocode_place(
                client,
                pickup_location
            )

            if pickup is None:
                return {
                    "error": "Pickup location not found",
                    "location": pickup_location
                }

            
            if pickup.get("ambiguous"):
                return {
                    "error": "Pickup location is ambiguous",
                    "needs_clarification": True,
                    "location": pickup_location,
                    "candidates": pickup["candidates"],
                    "message": (
                        "Please ask the user to select one "
                        "of the returned pickup locations."
                    )
                }


            # Keep requests sequential to respect
            # public geocoding service usage limits.
            import asyncio
            await asyncio.sleep(1.1)

            dropoff = await geocode_place(
                client,
                destination
            )

            if dropoff is None:
                return {
                    "error": "Destination not found",
                    "location": destination
                }

            
            if dropoff.get("ambiguous"):
                return {
                    "error": "Destination is ambiguous",
                    "needs_clarification": True,
                    "location": destination,
                    "candidates": dropoff["candidates"],
                    "message": (
                        "Please ask the user to select one "
                        "of the returned destination locations."
                    )
                }

            
            route_response = await client.post(
                f"{API_BASE_URL}/transport/routes/calculate",
                json={
                    "pickup_latitude": pickup["latitude"],
                    "pickup_longitude": pickup["longitude"],
                    "destination_latitude": dropoff["latitude"],
                    "destination_longitude": dropoff["longitude"]
                }
            )

            if route_response.status_code != 200:
                return {
                    "error": "Unable to calculate driving route",
                    "status_code": route_response.status_code
                }

            route_data = route_response.json()

            route_data["pickup_name"] = pickup["name"]
            route_data["destination_name"] = dropoff["name"]

            return route_data

    except httpx.HTTPError:
        return {
            "error": "Location lookup or routing service unavailable"
        }



@mcp.tool()
async def get_transport_route_from_coordinates_to_place(
    pickup_latitude: float,
    pickup_longitude: float,
    destination: str,
    pickup_name: str = "Selected pickup location",
) -> dict:
    """
    Calculate a driving route from verified pickup
    coordinates to a named destination in Sri Lanka.

    Use when the user has selected a pickup candidate
    with known coordinates, but the destination is
    provided as a place name.

    Does not create a transport booking.
    """

    if not (-90 <= pickup_latitude <= 90):
        return {"error": "Invalid pickup latitude"}

    if not (-180 <= pickup_longitude <= 180):
        return {"error": "Invalid pickup longitude"}

    if not destination.strip():
        return {"error": "Destination is required"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:

            dropoff = await geocode_place(
                client,
                destination
            )

            if dropoff is None:
                return {
                    "error": "Destination not found",
                    "location": destination,
                }

            if dropoff.get("ambiguous"):
                return {
                    "error": "Destination is ambiguous",
                    "needs_clarification": True,
                    "location": destination,
                    "candidates": dropoff["candidates"],
                    "message": (
                        "Please ask the user to select "
                        "the correct destination."
                    ),
                }

            route_response = await client.post(
                f"{API_BASE_URL}/transport/routes/calculate",
                json={
                    "pickup_latitude": pickup_latitude,
                    "pickup_longitude": pickup_longitude,
                    "destination_latitude": dropoff["latitude"],
                    "destination_longitude": dropoff["longitude"],
                },
            )

            if route_response.status_code != 200:
                return {
                    "error": "Unable to calculate driving route",
                    "status_code": route_response.status_code,
                }

            route_data = route_response.json()

            route_data["pickup_name"] = pickup_name
            route_data["destination_name"] = dropoff["name"]

            return route_data

    except httpx.HTTPError:
        return {
            "error": "Location lookup or routing service unavailable"
        }



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8003,
        stateless_http=True,
        json_response=True
    )