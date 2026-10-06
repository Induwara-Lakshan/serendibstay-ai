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


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8003,
        stateless_http=True,
        json_response=True
    )