"""
Concert Matching Engine.
Direct genre string matching + ranking algorithm.

Two-stage pipeline:
  Stage 1 (prefilter): cheap scoring using JamBase genre tags + artist name
           similarity against the user's taste profile. No Spotify calls.
  Stage 2 (enrich):    Spotify lookups only for the prefiltered candidate set,
           then final scoring and top-N selection.

Caches Spotify artist lookups in MongoDB (long-term) and in an in-memory
dict per request (request-lifetime) to avoid duplicate API calls.
"""
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import List, Dict, Optional, Tuple

from models import TasteProfile, ConcertMatch
import spotify_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (all overridable via env vars)
# ---------------------------------------------------------------------------
MAX_SHOWS_PER_CITY: int = int(os.environ.get("MAX_SHOWS_PER_CITY", "25"))
PREFILTER_CANDIDATES_PER_CITY: int = int(
    os.environ.get("PREFILTER_CANDIDATES_PER_CITY", "75")
)

# How long MongoDB-cached artist lookups remain valid
CACHE_TTL_DAYS = 30

# ---------------------------------------------------------------------------
# Tribute / cover band detection
# ---------------------------------------------------------------------------
TRIBUTE_PATTERNS = [
    re.compile(r"^(.+?)\s+tribute\b", re.IGNORECASE),
    re.compile(r"\btribute\s+to\s+(.+)$", re.IGNORECASE),
    re.compile(r"^a\s+tribute\s+to\s+(.+)$", re.IGNORECASE),
    re.compile(r"^(.+?)\s+cover\s+band$", re.IGNORECASE),
    re.compile(r"^(.+?)\s+experience$", re.IGNORECASE),
    re.compile(r"^(.+?)\s+legacy$", re.IGNORECASE),
    re.compile(r"^(.+?)\s+salute$", re.IGNORECASE),
    re.compile(r"^the\s+(.+?)\s+show$", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _extract_tribute_target(artist_name: str) -> Optional[str]:
    for pattern in TRIBUTE_PATTERNS:
        m = pattern.search(artist_name)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# MongoDB cache (long-term, cross-request)
# ---------------------------------------------------------------------------
async def _get_cached_artist(db, artist_name: str) -> Optional[dict]:
    """Check MongoDB cache for a previously looked-up artist."""
    if db is None:
        return None
    cache_key = artist_name.lower().strip()
    doc = await db.spotify_artist_cache.find_one(
        {"cache_key": cache_key}, {"_id": 0}
    )
    if not doc:
        return None
    cached_at = doc.get("cached_at", "")
    if cached_at:
        try:
            cached_dt = datetime.fromisoformat(cached_at)
            if datetime.now(timezone.utc) - cached_dt > timedelta(days=CACHE_TTL_DAYS):
                return None
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
        {
            "$set": {
                "cache_key": cache_key,
                "artist_data": artist_data,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )


# ---------------------------------------------------------------------------
# Spotify artist lookup (with both cache layers + tribute fallback)
# ---------------------------------------------------------------------------
async def _find_spotify_artist(
    access_token: str,
    artist_name: str,
    db=None,
    request_cache: Optional[dict] = None,
) -> dict:
    """
    Spotify artist lookup with two cache layers and tribute/cover fallback.

    1. Check in-memory request_cache (avoids duplicate lookups within one request).
    2. Check MongoDB cache (avoids duplicate lookups across requests).
    3. Hit Spotify Search API, pick best fuzzy match from top 5 results.
    4. If no good match, try tribute/cover fallback.
    5. Store result in both caches.
    """
    norm_key = artist_name.lower().strip()

    # Layer 1: in-memory request-level cache
    if request_cache is not None and norm_key in request_cache:
        return request_cache[norm_key]

    # Layer 2: MongoDB cache
    cached = await _get_cached_artist(db, artist_name)
    if cached is not None:
        if request_cache is not None:
            request_cache[norm_key] = cached
        return cached

    # Layer 3: Spotify API
    async def _search(name: str) -> dict:
        try:
            result = await spotify_service.search_artist(
                access_token, name, limit=5
            )
            candidates = result.get("artists", {}).get("items", [])
            if not candidates:
                return {}
            best = max(
                candidates,
                key=lambda a: _name_similarity(a.get("name", ""), name),
            )
            return best
        except spotify_service.SpotifyRateLimitError:
            logger.warning(f"Rate limited during search for '{name}'. Skipping.")
            return {}
        except Exception as e:
            logger.warning(f"Spotify search failed for '{name}': {e}")
            return {}

    result = await _search(artist_name)
    if result and _name_similarity(result.get("name", ""), artist_name) >= 0.6:
        await _set_cached_artist(db, artist_name, result)
        if request_cache is not None:
            request_cache[norm_key] = result
        return result

    # Tribute/cover fallback
    original = _extract_tribute_target(artist_name)
    if original:
        tribute_result = await _search(original)
        if tribute_result:
            logger.info(
                f"Tribute fallback: '{artist_name}' -> "
                f"'{tribute_result.get('name')}'"
            )
            await _set_cached_artist(db, artist_name, tribute_result)
            if request_cache is not None:
                request_cache[norm_key] = tribute_result
            return tribute_result

    # Cache whatever we got (even empty) to prevent re-searching
    final = result or {}
    await _set_cached_artist(db, artist_name, final)
    if request_cache is not None:
        request_cache[norm_key] = final
    return final


# ---------------------------------------------------------------------------
# Genre match scoring (unchanged logic)
# ---------------------------------------------------------------------------
def compute_genre_match_score(
    artist_genres: List[str],
    user_genre_map: Dict[str, float],
) -> Tuple[float, List[str], str]:
    """
    Compute genre match score between an artist's genres and user's taste.
    Returns (score 0-100, list of matching genres, explanation text).
    """
    if not artist_genres or not user_genre_map:
        return 0.0, [], "No genre data available"

    artist_genres_lower = [g.lower().strip() for g in artist_genres]
    if not artist_genres_lower:
        return 0.0, [], "No recognizable genre terms"

    total_weight = 0.0
    matched_terms: List[str] = []
    for genre in artist_genres_lower:
        if genre in user_genre_map:
            total_weight += user_genre_map[genre]
            matched_terms.append(genre)

    if not matched_terms:
        return 0.0, [], "No genre overlap found"

    max_possible = sum(
        sorted(user_genre_map.values(), reverse=True)[: len(artist_genres_lower)]
    )
    if max_possible == 0:
        return 0.0, matched_terms, "Minimal overlap"

    raw_score = (total_weight / max_possible) * 100
    overlap_ratio = len(matched_terms) / len(artist_genres_lower)
    score = min(raw_score * (0.7 + 0.3 * overlap_ratio), 99.0)

    top_user_genres = sorted(
        user_genre_map.items(), key=lambda x: x[1], reverse=True
    )[:5]
    top_user_names = [g[0] for g in top_user_genres]

    explanation = f"Your top genres include {', '.join(top_user_names[:3])}. "
    explanation += f"This artist's genres include {', '.join(matched_terms[:4])}."

    return round(score, 1), matched_terms, explanation


def compute_indie_bonus(popularity: Optional[int]) -> float:
    """Bonus for independent/lesser-known artists."""
    if popularity is None:
        return 5.0
    if popularity < 20:
        return 15.0
    elif popularity < 40:
        return 10.0
    elif popularity < 60:
        return 5.0
    return 0.0


# ===================================================================
# STAGE 1: Cheap prefilter (NO Spotify calls)
# ===================================================================
def _prefilter_genre_score(
    event_genres: List[str],
    user_root_genre_map: Dict[str, float],
) -> float:
    """
    Score 0-50 based on how well the event's genre tags overlap with the
    user's root_genre_map. Checks direct match and substring containment.
    """
    if not event_genres or not user_root_genre_map:
        return 0.0

    score = 0.0
    for g in event_genres:
        gl = g.lower().strip()
        # Direct hit
        if gl in user_root_genre_map:
            score += user_root_genre_map[gl] * 30.0
        else:
            # Substring / partial match (e.g., "indie" in "indie rock")
            for ug, w in user_root_genre_map.items():
                if gl in ug or ug in gl:
                    score += w * 5.0
                    break  # only count first partial match per event genre

    return min(score, 50.0)


def _prefilter_artist_score(
    artist_names: List[str],
    user_artist_names_lower: set,
) -> float:
    """
    Score 0-30 based on string similarity between event artist names and the
    user's top artist list. A near-exact match scores highest.
    """
    if not artist_names or not user_artist_names_lower:
        return 0.0

    best = 0.0
    for artist in artist_names:
        al = artist.lower().strip()
        for ua in user_artist_names_lower:
            sim = SequenceMatcher(None, al, ua).ratio()
            if sim > best:
                best = sim

    # Scale: 0.8+ similarity -> full 30 points, linear below
    return min(best * 37.5, 30.0)


def _prefilter_headliner_boost(index: int) -> float:
    """
    Small positional boost for events listed earlier in JamBase results
    (proxy for relevance/popularity). Ranges from 5.0 down to 0.0.
    """
    return max(5.0 - (index * 0.02), 0.0)


def prefilter_events(
    events: List[dict],
    taste_profile: TasteProfile,
    max_candidates: int = None,
) -> List[dict]:
    """
    Stage 1: Score and rank events cheaply using only data already present
    (genre tags from JamBase, artist names vs. user taste profile).
    Returns the top ``max_candidates`` events sorted by prefilter_score desc.
    No Spotify API calls are made here.
    """
    if max_candidates is None:
        max_candidates = PREFILTER_CANDIDATES_PER_CITY

    user_root_genre_map = taste_profile.root_genre_map or {}
    user_artist_names_lower = {n.lower() for n in taste_profile.top_artist_names}

    scored: List[Tuple[float, int, dict]] = []

    for idx, event in enumerate(events):
        artist_names = event.get("artist_names", [])
        event_genres = event.get("genres", [])

        genre_sc = _prefilter_genre_score(event_genres, user_root_genre_map)
        artist_sc = _prefilter_artist_score(artist_names, user_artist_names_lower)
        headliner_sc = _prefilter_headliner_boost(idx)

        total = genre_sc + artist_sc + headliner_sc

        # Attach score to event dict for debugging (not part of response schema)
        event["_prefilter_score"] = round(total, 2)

        # Negative score for descending sort; index for stable tie-break
        scored.append((-total, idx, event))

    scored.sort()
    candidates = [item[2] for item in scored[:max_candidates]]

    logger.info(
        f"Prefilter: {len(events)} events -> {len(candidates)} candidates "
        f"(cap={max_candidates})"
    )
    return candidates


# ===================================================================
# STAGE 2: Full Spotify-enriched matching + final ranking
# ===================================================================
async def match_and_rank_concerts(
    events: List[dict],
    taste_profile: TasteProfile,
    access_token: str,
    db=None,
    max_results: int = None,
) -> List[ConcertMatch]:
    """
    Match and rank concert events against user's taste profile.
    Uses MongoDB cache + in-memory request cache to minimize Spotify calls.

    Parameters
    ----------
    events : list
        Pre-filtered candidate events (output of prefilter_events).
    taste_profile : TasteProfile
    access_token : str
    db : Motor database instance (for MongoDB caching).
    max_results : int or None
        Hard cap on returned results. Defaults to MAX_SHOWS_PER_CITY.
    """
    if max_results is None:
        max_results = MAX_SHOWS_PER_CITY

    results: List[ConcertMatch] = []
    known_artist_names_lower = {n.lower() for n in taste_profile.top_artist_names}
    user_genre_map = taste_profile.root_genre_map
    rate_limited = False

    # In-memory request-level cache keyed by normalized artist name.
    # Prevents searching the same artist twice within this single request.
    request_cache: Dict[str, dict] = {}
    spotify_api_calls = 0

    for event in events:
        artist_names = event.get("artist_names", [])
        if not artist_names:
            continue

        primary_artist = artist_names[0]

        # Exclude artists the user already knows
        if primary_artist.lower() in known_artist_names_lower:
            continue

        # Data that may already exist on the event dict
        artist_genres = event.get("genres", [])
        spotify_popularity = event.get("popularity")
        spotify_artist_url = event.get("spotify_artist_url", "")

        # Track whether this lookup was already in request cache
        norm_key = primary_artist.lower().strip()
        was_cached = norm_key in request_cache

        # Spotify lookup (cache-first, skip if rate limited)
        if not rate_limited:
            sp_artist = await _find_spotify_artist(
                access_token,
                primary_artist,
                db=db,
                request_cache=request_cache,
            )
            if not was_cached:
                spotify_api_calls += 1
        else:
            sp_artist = await _get_cached_artist(db, primary_artist) or {}

        if sp_artist:
            if not artist_genres:
                artist_genres = sp_artist.get("genres", [])
            if not spotify_popularity:
                spotify_popularity = sp_artist.get("popularity")
            spotify_artist_url = (
                sp_artist.get("external_urls", {}).get("spotify", "")
            )

        # Compute genre match score
        score, matched_terms, explanation = compute_genre_match_score(
            artist_genres, user_genre_map
        )

        # Add indie bonus
        indie_bonus = compute_indie_bonus(spotify_popularity)
        final_score = min(score + indie_bonus, 99.0)

        if final_score < 5.0:
            continue

        genre_desc = (
            ", ".join(artist_genres[:3]) if artist_genres else "Genre unknown"
        )

        results.append(
            ConcertMatch(
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
            )
        )

    # Sort by match_score desc, then by date asc as deterministic tie-breaker
    results.sort(key=lambda c: (-c.match_score, c.date))

    # Enforce hard cap
    capped = results[:max_results]

    logger.info(
        f"Stage 2: {len(events)} candidates -> {len(results)} scored -> "
        f"{len(capped)} returned (cap={max_results}). "
        f"Spotify lookups (approx): {spotify_api_calls}, "
        f"Request cache size: {len(request_cache)}"
    )
    return capped
