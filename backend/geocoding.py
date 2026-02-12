"""
Geocoding service.
Converts city/state names to lat/lng coordinates.
Uses the free Nominatim (OpenStreetMap) geocoder.
"""
import logging
import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Cache geocoding results for 24 hours
_geo_cache = TTLCache(maxsize=200, ttl=86400)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


async def geocode(city: str) -> dict:
    """
    Convert a city name to lat/lng coordinates.
    Returns {"lat": float, "lng": float, "display_name": str} or None.
    """
    cache_key = city.lower().strip()
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": city,
                    "format": "json",
                    "limit": "1",
                    "countrycodes": "us",
                },
                headers={"User-Agent": "PAM/1.0 (concert-discovery-app)"},
                timeout=10.0,
            )
            resp.raise_for_status()
            results = resp.json()

            if not results:
                logger.warning(f"No geocoding results for '{city}'")
                return None

            result = results[0]
            geo = {
                "lat": float(result["lat"]),
                "lng": float(result["lon"]),
                "display_name": result.get("display_name", city),
            }
            _geo_cache[cache_key] = geo
            return geo

    except Exception as e:
        logger.error(f"Geocoding failed for '{city}': {e}")
        return None
