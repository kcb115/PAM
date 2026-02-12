"""
MusicBrainz API service.
Free alternative for genre/tag data and artist discovery,
used when Spotify's deprecated endpoints are unavailable.
Rate limit: ~1 req/sec. We batch and respect this.
"""
import logging
import asyncio
import httpx
from typing import List, Dict
from cachetools import TTLCache

logger = logging.getLogger(__name__)

MB_API = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "PAM/1.0 (pam-concert-discovery)"}

# Cache artist lookups for 1 hour
_artist_cache = TTLCache(maxsize=500, ttl=3600)
_genre_artists_cache = TTLCache(maxsize=100, ttl=3600)

# Shared client for connection reuse
_client = None


async def _get_client():
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(15.0, connect=10.0),
        )
    return _client


async def _mb_get(endpoint: str, params: dict, retries: int = 2) -> dict:
    params["fmt"] = "json"
    client = await _get_client()

    for attempt in range(retries + 1):
        try:
            resp = await client.get(f"{MB_API}{endpoint}", params=params)
            if resp.status_code == 503:
                await asyncio.sleep(2 + attempt)
                continue
            resp.raise_for_status()
            return resp.json()
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            if attempt < retries:
                await asyncio.sleep(1.5 + attempt)
                continue
            raise
    return {}


async def get_artist_tags(artist_name: str) -> List[str]:
    """Look up an artist on MusicBrainz and return their genre tags."""
    cache_key = artist_name.lower().strip()
    if cache_key in _artist_cache:
        return _artist_cache[cache_key]

    try:
        data = await _mb_get("/artist/", {
            "query": f'artist:"{artist_name}"',
            "limit": "1",
        })
        artists = data.get("artists", [])
        if not artists:
            _artist_cache[cache_key] = []
            return []

        best = artists[0]
        if best.get("score", 0) < 75:
            _artist_cache[cache_key] = []
            return []

        raw_tags = best.get("tags", [])
        # Filter to tags with positive count, or take first 8
        tags = [t["name"] for t in raw_tags if t.get("count", 0) >= 0]
        if not tags:
            tags = [t["name"] for t in raw_tags][:8]

        _artist_cache[cache_key] = tags
        return tags

    except Exception as e:
        logger.warning(f"MusicBrainz lookup failed for '{artist_name}': {e}")
        _artist_cache[cache_key] = []
        return []


async def get_genres_for_artists(artist_names: List[str]) -> Dict[str, List[str]]:
    """
    Look up genres for multiple artists with rate limiting.
    Returns {artist_name: [genre_tags]}.
    """
    results = {}

    for i, name in enumerate(artist_names):
        tags = await get_artist_tags(name)
        results[name] = tags

        # Rate limit: wait between requests (MusicBrainz allows ~1/sec)
        if i < len(artist_names) - 1:
            await asyncio.sleep(1.1)

    return results


async def find_artists_by_tags(tags: List[str], exclude_names: set, limit: int = 30) -> List[dict]:
    """
    Search MusicBrainz for artists matching given genre tags.
    Used as alternative to Spotify recommendations.
    """
    discovered = []
    exclude_lower = {n.lower() for n in exclude_names}

    for tag in tags[:6]:
        cache_key = f"tag:{tag}"
        if cache_key in _genre_artists_cache:
            artists = _genre_artists_cache[cache_key]
        else:
            try:
                data = await _mb_get("/artist/", {
                    "query": f'tag:"{tag}"',
                    "limit": "25",
                })
                artists = data.get("artists", [])
                _genre_artists_cache[cache_key] = artists
            except Exception as e:
                logger.warning(f"MusicBrainz tag search failed for '{tag}': {e}")
                artists = []
            await asyncio.sleep(1.1)

        for artist in artists:
            name = artist.get("name", "")
            if not name or name.lower() in exclude_lower:
                continue
            if name.lower() in ("various artists", "[unknown]", "unknown"):
                continue

            artist_tags = [t["name"] for t in artist.get("tags", []) if t.get("count", 0) >= 0]
            if not artist_tags:
                artist_tags = [t["name"] for t in artist.get("tags", [])][:5]

            discovered.append({
                "name": name,
                "mb_id": artist.get("id", ""),
                "tags": artist_tags,
                "score": artist.get("score", 0),
                "type": artist.get("type", ""),
            })

        if len(discovered) >= limit:
            break

    # Deduplicate by name
    seen = set()
    unique = []
    for a in discovered:
        key = a["name"].lower()
        if key not in seen and key not in exclude_lower:
            seen.add(key)
            unique.append(a)

    return unique[:limit]
