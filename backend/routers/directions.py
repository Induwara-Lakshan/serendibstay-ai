
import os
import re
import asyncio
import time
from collections import OrderedDict

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

load_dotenv("/app/.env")

router = APIRouter(prefix="/directions", tags=["Directions"])

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"

GEOCODE_CACHE_TTL = 24 * 60 * 60
GEOCODE_CACHE_MAX_SIZE = 500
GEOCODE_MIN_INTERVAL = 1.1

geocode_cache = OrderedDict()
geocode_lock = asyncio.Lock()
last_geocode_request_time = 0.0


# Existing aliases and a few common spelling corrections.
LOCATION_ALIASES = {
    "hambanthota": "Hambantota, Sri Lanka",
    "mathara": "Matara, Sri Lanka",
    "rathnapura": "Ratnapura, Sri Lanka",
}

WORD_CORRECTIONS = {
    "hambanthota": "Hambantota",
    "mathara": "Matara",
    "rathnapura": "Ratnapura",
    "nwaloka": "Nawaloka",
    "discrict": "District",
    "trincomale": "Trincomalee",
}


def normalize_location_name(place_name: str) -> str:
    cleaned = " ".join(place_name.strip().split())

    alias = LOCATION_ALIASES.get(cleaned.casefold())
    if alias:
        return alias

    def replace_word(match):
        word = match.group(0)
        return WORD_CORRECTIONS.get(word.casefold(), word)

    return re.sub(r"[A-Za-z]+", replace_word, cleaned)


def build_search_queries(place_name: str) -> list[str]:
    normalized = normalize_location_name(place_name)

    queries = [normalized]

    # Alternative: search without the country suffix.
    without_country = re.sub(
        r",?\s*Sri Lanka\s*$",
        "",
        normalized,
        flags=re.IGNORECASE,
    ).strip(" ,")

    if without_country and without_country.casefold() != normalized.casefold():
        queries.append(without_country)

    # Alternative: for a comma-separated place, try the
    # place name with the nearest city or town.
    parts = [
        part.strip()
        for part in without_country.split(",")
        if part.strip()
    ]

    if len(parts) >= 2:
        alternative = f"{parts[0]}, {parts[-1]}, Sri Lanka"
        if alternative.casefold() not in {
            query.casefold() for query in queries
        }:
            queries.append(alternative)

    # Maximum three attempts, including the original.
    return queries[:3]


class GeocodeRequest(BaseModel):
    place_name: str = Field(min_length=2, max_length=200)


@router.get("/route")
async def get_driving_route(
    start_lat: float = Query(..., ge=-90, le=90),
    start_lng: float = Query(..., ge=-180, le=180),
    end_lat: float = Query(..., ge=-90, le=90),
    end_lng: float = Query(..., ge=-180, le=180),
):
    api_key = os.getenv("ORS_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Routing service is not configured",
        )

    payload = {
        "coordinates": [
            [start_lng, start_lat],
            [end_lng, end_lat],
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(
                ORS_URL,
                headers={
                    "Authorization": api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
            )

        if response.status_code != 200:
            print("ORS STATUS:", response.status_code)
            print("ORS ERROR:", response.text[:1000])

            raise HTTPException(
                status_code=502,
                detail="Unable to calculate driving route",
            )

        data = response.json()
        features = data.get("features", [])

        if not features:
            raise HTTPException(
                status_code=404,
                detail="No driving route found",
            )

        feature = features[0]
        summary = feature["properties"]["summary"]
        coordinates = feature["geometry"]["coordinates"]

        return {
            "distance_km": round(
                summary["distance"] / 1000, 2
            ),
            "duration_minutes": round(
                summary["duration"] / 60, 1
            ),
            "route_coordinates": [
                [latitude, longitude]
                for longitude, latitude in coordinates
            ],
        }

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Routing service is temporarily unavailable",
        )


async def request_nominatim(
    client: httpx.AsyncClient,
    geocoding_url: str,
    user_agent: str,
    query: str,
):
    global last_geocode_request_time

    elapsed = time.monotonic() - last_geocode_request_time

    wait_seconds = max(
        0.0,
        GEOCODE_MIN_INTERVAL - elapsed,
    )

    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)

    last_geocode_request_time = time.monotonic()

    response = await client.get(
        geocoding_url,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 8,
            "countrycodes": "lk",
            "addressdetails": 1,
        },
        headers={
            "User-Agent": user_agent,
        },
    )

    response.raise_for_status()
    return response.json()


@router.post("/geocode")
async def geocode_location(request: GeocodeRequest):
    place_name = normalize_location_name(
        request.place_name
    )

    if not place_name:
        raise HTTPException(
            status_code=400,
            detail="Location name is required",
        )

    cache_key = place_name.casefold()

    async with geocode_lock:
        current_time = time.monotonic()
        cached = geocode_cache.get(cache_key)

        if cached:
            cached_at, cached_result = cached

            if current_time - cached_at < GEOCODE_CACHE_TTL:
                geocode_cache.move_to_end(cache_key)
                return cached_result

            del geocode_cache[cache_key]

        geocoding_url = os.getenv(
            "GEOCODING_URL",
            "https://nominatim.openstreetmap.org/search",
        )

        user_agent = os.getenv(
            "GEOCODING_USER_AGENT", ""
        ).strip()

        if not user_agent:
            raise HTTPException(
                status_code=503,
                detail="Geocoding User-Agent is not configured",
            )

        queries = build_search_queries(place_name)
        results = []

        try:
            async with httpx.AsyncClient(
                timeout=20.0
            ) as client:
                for query in queries:
                    results = await request_nominatim(
                        client,
                        geocoding_url,
                        user_agent,
                        query,
                    )

                    if results:
                        break

        except httpx.HTTPError:
            raise HTTPException(
                status_code=502,
                detail="Geocoding service unavailable",
            )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="Location not found",
            )

        candidates = []

        for item in results:
            candidates.append({
                "name": item["display_name"],
                "latitude": float(item["lat"]),
                "longitude": float(item["lon"]),
            })

        result = {
            "ambiguous": len(candidates) > 1,
            "candidates": candidates,
        }

        geocode_cache[cache_key] = (
            time.monotonic(),
            result,
        )

        geocode_cache.move_to_end(cache_key)

        while len(geocode_cache) > GEOCODE_CACHE_MAX_SIZE:
            geocode_cache.popitem(last=False)

        return result
