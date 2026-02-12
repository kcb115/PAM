"""
Ticketmaster Discovery API service.
Free API - register at https://developer.ticketmaster.com
Returns REAL upcoming concert events by city/location.
"""
import os
import logging
import httpx
from cachetools import TTLCache
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TM_API = "https://app.ticketmaster.com/discovery/v2"

# Cache events for 30 min per location
_event_cache = TTLCache(maxsize=100, ttl=1800)


def _cache_key(city: str, radius: int, date_from: str = None) -> str:
    return f"{city.lower().strip()}:{radius}:{date_from or 'any'}"


async def search_events(
    city: str,
    radius: int = 50,
    date_from: str = None,
    date_to: str = None,
    size: int = 50,
) -> dict:
    """Search for upcoming music events near a city."""
    api_key = os.environ.get("TICKETMASTER_API_KEY", "")
    if not api_key:
        return {
            "events": [],
            "error": "no_key",
            "message": "Ticketmaster API key not configured. Get a free key at developer.ticketmaster.com",
        }

    cache_key = _cache_key(city, radius, date_from)
    if cache_key in _event_cache:
        logger.info(f"Cache hit for events in {city}")
        return _event_cache[cache_key]

    # Parse city for state code
    state_code = ""
    city_name = city.strip()
    parts = [p.strip() for p in city.split(",")]
    if len(parts) >= 2:
        city_name = parts[0]
        state_part = parts[-1].strip().upper()
        # Handle "VA", "Virginia", etc.
        STATE_ABBREVS = {
            "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
            "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
            "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
            "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
            "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
            "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
            "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
            "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
            "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
            "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
            "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
            "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
            "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
        }
        if len(state_part) == 2:
            state_code = state_part
        elif state_part in STATE_ABBREVS:
            state_code = STATE_ABBREVS[state_part]

    params = {
        "apikey": api_key,
        "classificationName": "music",
        "city": city_name,
        "radius": str(radius),
        "unit": "miles",
        "size": str(min(size, 100)),
        "sort": "date,asc",
    }

    if state_code:
        params["stateCode"] = state_code

    # Date filtering
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            params["startDateTime"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass
    else:
        params["startDateTime"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if date_to:
        try:
            dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            params["endDateTime"] = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            pass

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{TM_API}/events.json", params=params, timeout=15.0)

            if resp.status_code == 401:
                return {"events": [], "error": "invalid_key", "message": "Invalid Ticketmaster API key"}
            if resp.status_code == 429:
                return {"events": [], "error": "rate_limit", "message": "Rate limited. Try again shortly."}
            if resp.status_code != 200:
                logger.error(f"Ticketmaster API error: {resp.status_code}")
                return {"events": [], "error": f"api_error_{resp.status_code}"}

            data = resp.json()
            result = _parse_events(data)

            _event_cache[cache_key] = result
            return result

    except httpx.TimeoutException:
        return {"events": [], "error": "timeout", "message": "Search timed out. Try again."}
    except Exception as e:
        logger.error(f"Ticketmaster error: {e}")
        return {"events": [], "error": str(e)}


def _parse_events(data: dict) -> dict:
    """Parse Ticketmaster Discovery API response."""
    embedded = data.get("_embedded", {})
    raw_events = embedded.get("events", [])
    page_info = data.get("page", {})

    events = []
    for event in raw_events:
        # Get artist/attraction info
        attractions = event.get("_embedded", {}).get("attractions", [])
        artist_names = [a.get("name", "") for a in attractions if a.get("name")]
        if not artist_names:
            artist_names = [event.get("name", "Unknown")]

        # Get genres from classifications
        genres = []
        for cls in event.get("classifications", []):
            genre = cls.get("genre", {}).get("name", "")
            subgenre = cls.get("subGenre", {}).get("name", "")
            segment = cls.get("segment", {}).get("name", "")
            if genre and genre != "Undefined":
                genres.append(genre.lower())
            if subgenre and subgenre != "Undefined":
                genres.append(subgenre.lower())

        # Get venue info
        venues = event.get("_embedded", {}).get("venues", [{}])
        venue = venues[0] if venues else {}
        venue_name = venue.get("name", "Unknown Venue")
        venue_city = venue.get("city", {}).get("name", "")

        # Get date/time
        dates = event.get("dates", {})
        start = dates.get("start", {})
        date_str = start.get("dateTime", start.get("localDate", ""))
        time_str = start.get("localTime", "")

        # Get URLs
        event_url = event.get("url", "")
        # Look for images
        images = event.get("images", [])
        image_url = ""
        for img in images:
            if img.get("ratio") == "16_9" and img.get("width", 0) >= 300:
                image_url = img.get("url", "")
                break
        if not image_url and images:
            image_url = images[0].get("url", "")

        # Get popularity/other info from attractions
        popularity = None
        for attraction in attractions:
            up = attraction.get("upcomingEvents", {})
            if up:
                total = up.get("_total", 0)
                # Use upcoming event count as a proxy (fewer = more indie)
                if total < 20:
                    popularity = 15
                elif total < 50:
                    popularity = 30
                elif total < 100:
                    popularity = 50
                else:
                    popularity = 70

        event_id = event.get("id", "")

        events.append({
            "event_id": event_id,
            "artist_names": artist_names,
            "genres": genres,
            "popularity": popularity,
            "venue_name": venue_name,
            "venue_city": venue_city,
            "date": date_str,
            "time": time_str,
            "ticket_url": event_url,
            "event_url": event_url,
            "image_url": image_url,
            "featured_track": "",
            "source": "ticketmaster",
        })

    return {
        "events": events,
        "total": page_info.get("totalElements", len(events)),
        "source": "ticketmaster",
    }
