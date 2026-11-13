
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/transport/routes",
    tags=["Transport Routes"],
)

# Configure a geocoding service that permits your usage.
GEOCODING_URL = os.getenv("GEOCODING_URL", "").strip()
ROUTING_URL = os.getenv(
    "ROUTING_URL",
    "https://router.project-osrm.org",
).rstrip("/")


class RouteRequest(BaseModel):
    pickup_latitude: float = Field(ge=-90, le=90)
    pickup_longitude: float = Field(ge=-180, le=180)
    destination_latitude: float = Field(ge=-90, le=90)
    destination_longitude: float = Field(ge=-180, le=180)


@router.post("/calculate")
async def calculate_transport_route(request: RouteRequest):
    coordinates = (
        f"{request.pickup_longitude},{request.pickup_latitude};"
        f"{request.destination_longitude},{request.destination_latitude}"
    )

    url = f"{ROUTING_URL}/route/v1/driving/{coordinates}"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "false",
                },
            )
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Routing service is currently unavailable",
        )

    if data.get("code") != "Ok" or not data.get("routes"):
        raise HTTPException(
            status_code=404,
            detail="No driving route found",
        )

    route = data["routes"][0]

    return {
        "pickup": {
            "latitude": request.pickup_latitude,
            "longitude": request.pickup_longitude,
        },
        "destination": {
            "latitude": request.destination_latitude,
            "longitude": request.destination_longitude,
        },
        "distance_km": round(route["distance"] / 1000, 2),
        "duration_minutes": round(route["duration"] / 60, 1),
        "geometry": route["geometry"],
    }
