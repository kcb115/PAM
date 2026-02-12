"""
MusicBrainz API service.
Free alternative for genre/tag data and artist discovery,
used when Spotify's deprecated endpoints are unavailable.
Rate limit: ~1 req/sec. We batch and respect this.
"""
import logging
import asyncio
import httpx
from typing import List, Dict, Optional
from cachetools import TTLCache

logger = logging.getLogger(__name__)

MB_API = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "PAM/1.0 (pam-concert-discovery)"}

# Cache artist lookups for 1 hour
_artist_cache = TTLCache(maxsize=500, ttl=3600)
_genre_artists_cache = TTLCache(maxsize=100, ttl=3600)


async def _mb_get(endpoint: str, params: dict) -> dict:
    params["fmt"] = "json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{MB_API}{endpoint}",
            params=params,
            headers=HEADERS,
            timeout=10.0,
        )
        if resp.status_code == 503:
            await asyncio.sleep(2)
            resp = await client.get(
                f"{MB_API}{endpoint}",
                params=params,
                headers=HEADERS,
                timeout=10.0,
            )
        resp.raise_for_status()
        return resp.json()


async def get_artist_tags(artist_name: str) -> List[str]:
    """Look up an artist on MusicBrainz and return their genre tags."""
    cache_key = artist_name.lower().strip()
    if cache_key in _artist_cache:
        return _artist_cache[cache_key]

    try:
        data = await _mb_get("/artist/", {"query": f'artist:"{artist_name}"', "limit": "1"})
        artists = data.get("artists", [])
        if not artists:
            _artist_cache[cache_key] = []
            return []

        best = artists[0]
        # Only accept high-confidence matches
        if best.get("score", 0) < 80:
            _artist_cache[cache_key] = []
            return []

        tags = [t["name"] for t in best.get("tags", []) if t.get("count", 0) >= 0]
        if not tags:
            tags = [t["name"] for t in best.get("tags", [])][:5]

        _artist_cache[cache_key] = tags
        return tags

    except Exception as e:
        logger.warning(f"MusicBrainz lookup failed for '{artist_name}': {e}")
        _artist_cache[cache_key] = []
        return []


async def get_genres_for_artists(artist_names: List[str], max_concurrent: int = 3) -> Dict[str, List[str]]:
    """
    Look up genres for multiple artists with rate limiting.
    Returns {artist_name: [genre_tags]}.
    """
    results = {}
    # Process in small batches to respect rate limits
    for i in range(0, len(artist_names), max_concurrent):
        batch = artist_names[i:i + max_concurrent]
        tasks = [get_artist_tags(name) for name in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, tags in zip(batch, batch_results):
            if isinstance(tags, Exception):
                results[name] = []
            else:
                results[name] = tags

        # Rate limit: ~1 request per second
        if i + max_concurrent < len(artist_names):
            await asyncio.sleep(1.2)

    return results


async def find_artists_by_tags(tags: List[str], exclude_names: set, limit: int = 30) -> List[dict]:
    """
    Search MusicBrainz for artists matching given genre tags.
    Used as alternative to Spotify recommendations.
    """
    discovered = []
    exclude_lower = {n.lower() for n in exclude_names}

    # Search with top tags
    for tag in tags[:5]:
        cache_key = f"tag:{tag}"
        if cache_key in _genre_artists_cache:
            artists = _genre_artists_cache[cache_key]
        else:
            try:
                data = await _mb_get("/artist/", {
                    "query": f'tag:"{tag}"',
                    "limit": "20",
                })
                artists = data.get("artists", [])
                _genre_artists_cache[cache_key] = artists
            except Exception as e:
                logger.warning(f"MusicBrainz tag search failed for '{tag}': {e}")
                artists = []
            await asyncio.sleep(1.2)

        for artist in artists:
            name = artist.get("name", "")
            if not name or name.lower() in exclude_lower:
                continue
            if name.lower() == "various artists":
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
