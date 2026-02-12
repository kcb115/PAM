"""
Jambase API service.
Handles event search with caching.
"""
import os
import logging
import httpx
from cachetools import TTLCache
from typing import Optional

logger = logging.getLogger(__name__)

JAMBASE_API_BASE = "https://apiv3.jambase.com"

# Cache events for 30 minutes per location key
_event_cache = TTLCache(maxsize=100, ttl=1800)


def _cache_key(city: str, radius: int) -> str:
    return f"{city.lower().strip()}:{radius}"


async def search_events(city: str, radius: int = 25, page: int = 0) -> dict:
    """Search for upcoming events near a city using Jambase API."""
    cache_key = _cache_key(city, radius)
    if cache_key in _event_cache and page == 0:
        logger.info(f"Cache hit for events in {city}")
        return _event_cache[cache_key]

    api_key = os.environ.get("JAMBASE_API_KEY", "")
    if not api_key:
        logger.error("JAMBASE_API_KEY not configured")
        return {"events": [], "error": "Jambase API key not configured"}

    params = {
        "apikey": api_key,
        "geoCity": city,
        "geoRadius": str(radius),
        "eventDateFrom": "today",
        "page": str(page),
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{JAMBASE_API_BASE}/events",
                params=params,
                timeout=20.0,
            )

            if resp.status_code == 429:
                logger.warning("Jambase rate limited")
                return {"events": [], "error": "Rate limited. Try again shortly."}

            if resp.status_code != 200:
                logger.error(f"Jambase API error: {resp.status_code} - {resp.text[:200]}")
                return {"events": [], "error": f"Jambase API error: {resp.status_code}"}

            data = resp.json()
            result = _parse_events(data)

            if page == 0:
                _event_cache[cache_key] = result

            return result

    except httpx.TimeoutException:
        logger.error("Jambase API timeout")
        return {"events": [], "error": "Jambase API timeout"}
    except Exception as e:
        logger.error(f"Jambase API error: {e}")
        return {"events": [], "error": str(e)}


def _parse_events(data: dict) -> dict:
    """Parse Jambase API response into normalized event list."""
    events = []
    raw_events = data.get("Events", data.get("events", []))

    for event in raw_events:
        # Handle different response formats
        venue = event.get("Venue", event.get("venue", {}))
        location = event.get("Location", event.get("location", {}))

        # Extract performer/artist info
        performers = event.get("Performers", event.get("performers",
                     event.get("performer", [])))
        if isinstance(performers, dict):
            performers = [performers]

        artist_names = []
        for p in performers:
            name = p.get("Name", p.get("name", ""))
            if name:
                artist_names.append(name)

        if not artist_names:
            event_name = event.get("Name", event.get("name", ""))
            if event_name:
                artist_names = [event_name]

        venue_name = venue.get("Name", venue.get("name", "Unknown Venue"))
        venue_city = ""
        if isinstance(location, dict):
            venue_city = location.get("City", location.get("city", ""))
        elif isinstance(venue, dict) and "Location" in venue:
            venue_city = venue["Location"].get("City", "")

        # Extract date
        date_str = event.get("Date", event.get("date",
                   event.get("startDate", event.get("DateStart", ""))))

        # Extract ticket/event URLs
        ticket_url = event.get("TicketUrl", event.get("ticketUrl",
                     event.get("Url", event.get("url", ""))))
        event_url = event.get("Url", event.get("url", ""))

        # Get image
        image = event.get("Image", event.get("image", ""))
        if isinstance(image, dict):
            image = image.get("Url", image.get("url", ""))

        event_id = str(event.get("Id", event.get("id", event.get("@id", ""))))

        events.append({
            "event_id": event_id,
            "artist_names": artist_names,
            "venue_name": venue_name,
            "venue_city": venue_city,
            "date": date_str,
            "ticket_url": ticket_url,
            "event_url": event_url,
            "image_url": image if isinstance(image, str) else "",
        })

    return {
        "events": events,
        "total": len(events),
        "pagination": data.get("Pagination", data.get("pagination", {})),
    }
