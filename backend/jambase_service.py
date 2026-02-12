"""
Jambase Events API v1 service.
Base URL: https://www.jambase.com/jb-api/v1/events
Uses lat/lng geo search with genre filtering.
"""
import os
import logging
import httpx
from cachetools import TTLCache
from datetime import datetime, timezone
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

JAMBASE_API = "https://www.jambase.com/jb-api/v1/events"

# Cache events for 1 hour per location+genre key
_event_cache = TTLCache(maxsize=200, ttl=3600)

# Mapping from root genres to Jambase genre slugs
ROOT_TO_JAMBASE_SLUG = {
    "indie": "indie",
    "folk": "folk",
    "jazz": "jazz",
    "blues": "blues",
    "rock": "rock",
    "pop": "pop",
    "punk": "punk",
    "metal": "metal",
    "electronic": "edm",
    "dance": "edm",
    "house": "edm",
    "techno": "edm",
    "hip hop": "hip-hop-rap",
    "rap": "hip-hop-rap",
    "country": "country-music",
    "bluegrass": "bluegrass",
    "r&b": "rhythm-and-blues-soul",
    "soul": "rhythm-and-blues-soul",
    "reggae": "reggae",
    "latin": "latin",
    "classical": "classical",
    "gospel": "christian",
}


def get_jambase_slugs_for_profile(root_genre_map: Dict[str, float], max_slugs: int = 5) -> List[str]:
    """Map a user's root genre map to Jambase genre slugs, ordered by weight."""
    slug_weights = {}
    for genre, weight in root_genre_map.items():
        slug = ROOT_TO_JAMBASE_SLUG.get(genre.lower())
        if slug:
            slug_weights[slug] = slug_weights.get(slug, 0) + weight

    sorted_slugs = sorted(slug_weights.items(), key=lambda x: x[1], reverse=True)
    return [s[0] for s in sorted_slugs[:max_slugs]]


async def _fetch_page(
    api_key: str,
    lat: float,
    lng: float,
    radius: int,
    genre_slug: Optional[str],
    date_from: str,
    date_to: Optional[str],
    page: int,
    per_page: int,
) -> dict:
    """Fetch a single page of events from Jambase."""
    params = {
        "apikey": api_key,
        "geoLatitude": str(lat),
        "geoLongitude": str(lng),
        "geoRadiusAmount": str(radius),
        "geoRadiusUnits": "mi",
        "eventType": "concerts",
        "eventDateFrom": date_from,
        "page": str(page),
        "perPage": str(per_page),
    }
    if date_to:
        params["eventDateTo"] = date_to
    if genre_slug:
        params["genreSlug"] = genre_slug

    async with httpx.AsyncClient() as client:
        resp = await client.get(JAMBASE_API, params=params, timeout=20.0)

        if resp.status_code == 429:
            logger.warning("Jambase rate limited")
            return {"events": [], "pagination": {}}
        if resp.status_code != 200:
            logger.error(f"Jambase API error {resp.status_code}: {resp.text[:200]}")
            return {"events": [], "pagination": {}}

        return resp.json()


def _parse_event(event: dict) -> dict:
    """Parse a single Jambase Concert object into our normalized format."""
    # Performer info
    performers = event.get("performer", [])
    artist_names = []
    genres = []
    for p in performers:
        name = p.get("name", "")
        if name:
            artist_names.append(name)
        for g in p.get("genre", []):
            if g and g.lower() not in genres:
                genres.append(g.lower())

    if not artist_names:
        artist_names = [event.get("name", "Unknown")]

    # Venue info
    location = event.get("location", {})
    venue_name = location.get("name", "Unknown Venue")
    address = location.get("address", {})
    venue_city = address.get("addressLocality", "")
    region = address.get("addressRegion", {})
    venue_state = region.get("alternateName", "") if isinstance(region, dict) else ""
    if venue_state:
        venue_city = f"{venue_city}, {venue_state}"

    # Date/time
    start_date = event.get("startDate", "")
    door_time = event.get("doorTime", "")

    # URLs
    event_url = event.get("url", "")
    ticket_url = ""
    for offer in event.get("offers", []):
        url = offer.get("url", "")
        if url:
            ticket_url = url
            break
    if not ticket_url:
        ticket_url = event_url

    # Image
    image_url = event.get("image", "")

    # Event ID
    event_id = event.get("identifier", "")

    return {
        "event_id": event_id,
        "artist_names": artist_names,
        "genres": genres,
        "popularity": None,
        "venue_name": venue_name,
        "venue_city": venue_city,
        "date": start_date,
        "time": door_time,
        "ticket_url": ticket_url,
        "event_url": event_url,
        "image_url": image_url,
        "featured_track": "",
        "source": "jambase",
    }


async def search_events(
    lat: float,
    lng: float,
    radius: int = 25,
    genre_slugs: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    max_pages: int = 3,
    per_page: int = 50,
) -> dict:
    """
    Search for upcoming concerts near coordinates.
    Always fetches ALL events first. If genre_slugs provided,
    also makes genre-filtered calls and merges/deduplicates.
    """
    api_key = os.environ.get("JAMBASE_API_KEY", "")
    if not api_key:
        return {"events": [], "error": "no_key", "total": 0}

    if not date_from:
        date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    all_events = {}  # keyed by event_id to deduplicate

    # Always fetch unfiltered events first (broad pool)
    slugs_to_query = [None]
    # Add genre-specific queries for higher relevance
    if genre_slugs:
        slugs_to_query.extend(genre_slugs)

    for slug in slugs_to_query:
        cache_key = f"{lat:.2f}:{lng:.2f}:{radius}:{slug or 'all'}:{date_from}"
        if cache_key in _event_cache:
            cached = _event_cache[cache_key]
            for ev in cached:
                all_events[ev["event_id"]] = ev
            continue

        slug_events = []
        for page in range(1, max_pages + 1):
            try:
                data = await _fetch_page(
                    api_key, lat, lng, radius, slug, date_from, date_to, page, per_page
                )
            except Exception as e:
                logger.error(f"Jambase fetch failed (slug={slug}, page={page}): {e}")
                break

            if not data.get("success"):
                break

            raw_events = data.get("events", [])
            if not raw_events:
                break

            for raw in raw_events:
                parsed = _parse_event(raw)
                slug_events.append(parsed)
                all_events[parsed["event_id"]] = parsed

            # Check if more pages
            pagination = data.get("pagination", {})
            total_pages = pagination.get("totalPages", 1)
            if page >= total_pages:
                break

        _event_cache[cache_key] = slug_events

    events_list = list(all_events.values())
    logger.info(f"Jambase returned {len(events_list)} events for {lat},{lng} r={radius}")
    return {
        "events": events_list,
        "total": len(events_list),
        "source": "jambase",
    }
