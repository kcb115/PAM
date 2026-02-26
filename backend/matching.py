"""
Concert Matching Engine.
Direct genre string matching + ranking algorithm.

Compares raw Spotify genre tags from concert artists against
the user's genre profile without any simplification.

Caches Spotify artist lookups in MongoDB to avoid rate limits.
"""
import logging
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Optional
from models import TasteProfile, ConcertMatch
import spotify_service

logger = logging.getLogger(__name__)

# How long cached artist lookups remain valid before re-fetching
CACHE_TTL_DAYS = 30

# Patterns that indicate a tribute or cover band, and how to extract the original artist name
TRIBUTE_PATTERNS = [
    re.compile(r"^(.+?)\s+tribute\b", re.IGNORECASE),           # "X Tribute Band"
    re.compile(r"\btribute\s+to\s+(.+)$", re.IGNORECASE),       # "Tribute to X"
    re.compile(r"^a\s+tribute\s+to\s+(.+)$", re.IGNORECASE),    # "A Tribute to X"
    re.compile(r"^(.+?)\s+cover\s+band$", re.IGNORECASE),       # "X Cover Band"
    re.compile(r"^(.+?)\s+experience$", re.IGNORECASE),         # "The X Experience"
    re.compile(r"^(.+?)\s+legacy$", re.IGNORECASE),             # "X Legacy"
    re.compile(r"^(.+?)\s+salute$", re.IGNORECASE),             # "X Salute"
    re.compile(r"^the\s+(.+?)\s+show$", re.IGNORECASE),         # "The X Show"
]


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _extract_tribute_target(artist_name: str) -> Optional[str]:
    for pattern in TRIBUTE_PATTERNS:
        m = pattern.search(artist_name)
        if m:
            return m.group(1).strip()
    return None


async def _get_cached_artist(db, artist_name: str) -> Optional[dict]:
    """Check MongoDB cache for a previously looked-up artist."""
    if db is None:
        return None
    cache_key = artist_name.lower().strip()
    doc = await db.spotify_artist_cache.find_one({"cache_key": cache_key}, {"_id": 0})
    if not doc:
        return None
    # Check TTL
    cached_at = doc.get("cached_at", "")
    if cached_at:
        try:
            cached_dt = datetime.fromisoformat(cached_at)
            if datetime.now(timezone.utc) - cached_dt > timedelta(days=CACHE_TTL_DAYS):
                return None  # Expired
        except (ValueError, TypeError):
            return None
    return doc.get("artist_data")


async def _set_cached_artist(db, artist_name: str, artist_data: dict):
    """Store a Spotify artist lookup result in MongoDB cache."""
    if db is None:
        return
    cache_key = artist_name.lower().strip()
    await db.spotify_artist_cache.update_one(
        {"cache_key": cache_key},
        {"$set": {
            "cache_key": cache_key,
            "artist_data": artist_data,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def _find_spotify_artist(access_token: str, artist_name: str, db=None) -> dict:
    """
    Spotify artist lookup with cache and tribute/cover fallback.
    1. Check MongoDB cache first.
    2. Search by artist name, pick best fuzzy match from top 5 results.
    3. If no good match, check for tribute/cover keywords and search for the original artist.
    4. Cache the result.
    Always returns the best available result, or {} if Spotify is unreachable.
    """
    # Check cache first
    cached = await _get_cached_artist(db, artist_name)
    if cached is not None:
        return cached

    search_name = artist_name

    async def _search(name: str) -> dict:
        try:
            result = await spotify_service.search_artist(access_token, name, limit=5)
            candidates = result.get("artists", {}).get("items", [])
            if not candidates:
                return {}
            # Pick the candidate whose name is closest to what we searched for
            best = max(candidates, key=lambda a: _name_similarity(a.get("name", ""), name))
            return best
        except spotify_service.SpotifyRateLimitError:
            logger.warning(f"Rate limited during search for '{name}'. Skipping.")
            return {}
        except Exception as e:
            logger.warning(f"Spotify search failed for '{name}': {e}")
            return {}

    # Primary search
    result = await _search(search_name)
    if result and _name_similarity(result.get("name", ""), search_name) >= 0.6:
        await _set_cached_artist(db, artist_name, result)
        return result

    # Tribute/cover fallback - search for the original artist instead
    original = _extract_tribute_target(artist_name)
    if original:
        tribute_result = await _search(original)
        if tribute_result:
            logger.info(f"Tribute fallback: '{artist_name}' -> '{tribute_result.get('name')}'")
            await _set_cached_artist(db, artist_name, tribute_result)
            return tribute_result

    # Cache whatever we got (even empty) to avoid re-searching
    final = result or {}
    await _set_cached_artist(db, artist_name, final)
    return final


def compute_genre_match_score(
    artist_genres: List[str],
    user_genre_map: Dict[str, float]
) -> tuple:
    """
    Compute genre match score between an artist's genres and user's taste.
    Compares raw Spotify genre strings directly.
    Returns (score 0-100, list of matching genres, explanation text).
    """
    if not artist_genres or not user_genre_map:
        return 0.0, [], "No genre data available"

    # Normalize artist genres to lowercase
    artist_genres_lower = [g.lower().strip() for g in artist_genres]

    if not artist_genres_lower:
        return 0.0, [], "No recognizable genre terms"

    # Direct match: check which artist genres appear in user's profile
    total_weight = 0.0
    matched_terms = []
    for genre in artist_genres_lower:
        if genre in user_genre_map:
            total_weight += user_genre_map[genre]
            matched_terms.append(genre)

    if not matched_terms:
        return 0.0, [], "No genre overlap found"

    # Normalize score: ratio of matched weight to best possible weight
    max_possible = sum(sorted(user_genre_map.values(), reverse=True)[:len(artist_genres_lower)])
    if max_possible == 0:
        return 0.0, matched_terms, "Minimal overlap"

    raw_score = (total_weight / max_possible) * 100
    # Boost for more overlapping genres
    overlap_ratio = len(matched_terms) / len(artist_genres_lower)
    score = min(raw_score * (0.7 + 0.3 * overlap_ratio), 99.0)

    # Build explanation
    top_user_genres = sorted(user_genre_map.items(), key=lambda x: x[1], reverse=True)[:5]
    top_user_names = [g[0] for g in top_user_genres]

    explanation = f"Your top genres include {', '.join(top_user_names[:3])}. "
    explanation += f"This artist's genres include {', '.join(matched_terms[:4])}."

    return round(score, 1), matched_terms, explanation


def compute_indie_bonus(popularity: Optional[int]) -> float:
    """
    Bonus for independent/lesser-known artists.
    Lower popularity = higher bonus.
    """
    if popularity is None:
        return 5.0
    if popularity < 20:
        return 15.0
    elif popularity < 40:
        return 10.0
    elif popularity < 60:
        return 5.0
    return 0.0


async def match_and_rank_concerts(
    events: List[dict],
    taste_profile: TasteProfile,
    access_token: str,
    db=None,
) -> List[ConcertMatch]:
    """
    Match and rank concert events against user's taste profile.
    Handles both external API events and Spotify-discovered events.
    Uses MongoDB cache to minimize Spotify API calls.
    """
    results = []
    known_artist_names_lower = {n.lower() for n in taste_profile.top_artist_names}
    rate_limited = False

    # Use root_genre_map (which now contains the raw Spotify genres)
    user_genre_map = taste_profile.root_genre_map

    for event in events:
        artist_names = event.get("artist_names", [])
        if not artist_names:
            continue

        primary_artist = artist_names[0]

        # Exclude artists the user already knows
        if primary_artist.lower() in known_artist_names_lower:
            continue

        # Check if event already has genre/popularity data (from Spotify discovery)
        artist_genres = event.get("genres", [])
        spotify_popularity = event.get("popularity")
        spotify_artist_url = event.get("spotify_artist_url", "")

        # Search Spotify (cache-first, skips API if rate limited)
        if not rate_limited:
            sp_artist = await _find_spotify_artist(access_token, primary_artist, db=db)
        else:
            # Still check cache even when rate limited
            sp_artist = await _get_cached_artist(db, primary_artist) or {}

        if sp_artist:
            if not artist_genres:
                artist_genres = sp_artist.get("genres", [])
            if not spotify_popularity:
                spotify_popularity = sp_artist.get("popularity")
            spotify_artist_url = sp_artist.get("external_urls", {}).get("spotify", "")

        # Compute genre match score
        score, matched_terms, explanation = compute_genre_match_score(
            artist_genres, user_genre_map
        )

        # Add indie bonus
        indie_bonus = compute_indie_bonus(spotify_popularity)
        final_score = min(score + indie_bonus, 99.0)

        if final_score < 5.0:
            continue

        genre_desc = ", ".join(artist_genres[:3]) if artist_genres else "Genre unknown"

        results.append(ConcertMatch(
            event_id=event.get("event_id", ""),
            artist_name=primary_artist,
            genre_description=genre_desc,
            match_score=round(final_score, 1),
            match_explanation=explanation,
            venue_name=event.get("venue_name", "Unknown"),
            venue_city=event.get("venue_city", ""),
            date=event.get("date", ""),
            ticket_url=event.get("ticket_url", ""),
            event_url=event.get("event_url", ""),
            spotify_artist_url=spotify_artist_url,
            spotify_popularity=spotify_popularity,
            image_url=event.get("image_url", ""),
            featured_track=event.get("featured_track", ""),
            source=event.get("source", "discovery"),
        ))

    # Sort by match score descending
    results.sort(key=lambda c: c.match_score, reverse=True)
    return results
