import os
import httpx
from mcp.server import MCPServer

mcp = MCPServer("Sri Lanka Hotel MCP")

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8001"
)


@mcp.tool()
async def search_hotels() -> list:
    """Return all hotels available in the Sri Lanka Hotel API."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/hotels/"
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_hotel(hotel_id: int) -> dict:
    """Get a hotel by its ID."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/hotels/{hotel_id}"
        )

        if response.status_code == 404:
            return {
                "error": "Hotel not found",
                "hotel_id": hotel_id
            }

        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_hotels_by_city(city_name: str) -> list:
    """Return hotels in a given Sri Lankan city."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/hotels/city/{city_name}"
        )

        if response.status_code == 404:
            return []

        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_hotels_by_district(district_name: str) -> list:
    """Return hotels in a given Sri Lankan district."""

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/hotels/district/{district_name}"
        )

        if response.status_code == 404:
            return []

        response.raise_for_status()
        return response.json()


@mcp.tool()
async def create_booking(
    hotel_id: int,
    customer_name: str,
    customer_email: str,
    check_in: str,
    check_out: str,
    status: str = "confirmed"
) -> dict:
    """Create a hotel booking."""

    booking_data = {
        "hotel_id": hotel_id,
        "customer_name": customer_name,
        "customer_email": customer_email,
        "check_in": check_in,
        "check_out": check_out,
        "status": status
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE_URL}/bookings/",
            json=booking_data
        )

        if response.status_code == 404:
            return {
                "error": "Hotel not found",
                "hotel_id": hotel_id
            }

        response.raise_for_status()
        return response.json()



if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8002, 
        stateless_http=True,
        json_response=True
    )