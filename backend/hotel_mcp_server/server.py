import os
from urllib.parse import quote

import httpx
from mcp.server import MCPServer

mcp = MCPServer("Sri Lanka Hotel MCP")

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
TIMEOUT = httpx.Timeout(20.0, connect=5.0)


def api_error(response: httpx.Response) -> dict:
    try:
        payload = response.json()
        detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
    except ValueError:
        detail = "Hotel API request failed"
    return {"error": str(detail), "status_code": response.status_code}


@mcp.tool()
async def search_hotels() -> list | dict:
    """Find publicly visible hotels (active, available, legacy or verified)."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{API_BASE_URL}/hotels/")
            if response.is_error:
                return api_error(response)
            return response.json()
    except httpx.RequestError:
        return {"error": "Hotel API is currently unreachable"}


@mcp.tool()
async def get_hotel(hotel_id: int) -> dict:
    """Get a publicly visible hotel by ID."""
    if hotel_id <= 0:
        return {"error": "Invalid hotel ID"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{API_BASE_URL}/hotels/{hotel_id}")
            if response.is_error:
                return api_error(response)
            return response.json()
    except httpx.RequestError:
        return {"error": "Hotel API is currently unreachable"}


@mcp.tool()
async def get_hotels_by_city(city_name: str) -> list | dict:
    """Find publicly visible hotels in a Sri Lankan city."""
    if not city_name.strip():
        return {"error": "City name is required"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{API_BASE_URL}/hotels/city/{quote(city_name.strip(), safe='')}"
            )
            if response.status_code == 404:
                return []
            if response.is_error:
                return api_error(response)
            return response.json()
    except httpx.RequestError:
        return {"error": "Hotel API is currently unreachable"}


@mcp.tool()
async def get_hotels_by_district(district_name: str) -> list | dict:
    """Find publicly visible hotels in a Sri Lankan district."""
    if not district_name.strip():
        return {"error": "District name is required"}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(
                f"{API_BASE_URL}/hotels/district/{quote(district_name.strip(), safe='')}"
            )
            if response.status_code == 404:
                return []
            if response.is_error:
                return api_error(response)
            return response.json()
    except httpx.RequestError:
        return {"error": "Hotel API is currently unreachable"}


@mcp.tool()
async def create_booking(
    hotel_id: int,
    customer_name: str,
    customer_email: str,
    check_in: str,
    check_out: str,
) -> dict:
    """Submit a pending hotel booking request; does not confirm a reservation."""
    if hotel_id <= 0:
        return {"error": "Invalid hotel ID"}
    if not customer_name.strip() or not customer_email.strip():
        return {"error": "Customer name and email are required"}

    booking_data = {
        "hotel_id": hotel_id,
        "customer_name": customer_name.strip(),
        "customer_email": customer_email.strip(),
        "check_in": check_in,
        "check_out": check_out,
        "status": "pending",
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/bookings/", json=booking_data
            )
            if response.is_error:
                return api_error(response)
            result = response.json()
            if isinstance(result, dict):
                result["notice"] = (
                    "Booking request submitted; reservation is not confirmed."
                )
            return result
    except httpx.RequestError:
        return {"error": "Booking API is currently unreachable"}


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8002,
        stateless_http=True,
        json_response=True,
    )
