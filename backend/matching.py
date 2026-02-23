"""
Concert Matching Engine.
Direct genre string matching + ranking algorithm.

Compares raw Spotify genre tags from concert artists against
the user's genre profile without any simplification.
"""
import logging
import re
from difflib import SequenceMatcher
from typing import List, Dict, Optional
from models import TasteProfile, ConcertMatch
import spotify_service

logger = logging.getLogger(__name__)

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


async def _find_spotify_artist(access_token: str, artist_name: str) -> dict:
    """
    Three-stage Spotify artist lookup:
    1. Quoted artist search with best-match fuzzy scoring
    2. Tribute/cover detection - search for the original artist
    3. Fallback: raw unquoted search, take top result
    Returns a Spotify artist dict or {}.
    """
    # Stage 1: quoted search, pick closest name match
    try:
        result = await spotify_service.search_artist(
            access_token, artist_name, limit=5, query=f'artist:"{artist_name}"'
        )
        candidates = result.get("artists", {}).get("items", [])
        if candidates:
            best = max(candidates, key=lambda a: _name_similarity(a.get("name", ""), artist_name))
            if _name_similarity(best.get("name", ""), artist_name) >= 0.85:
                return best
    except Exception as e:
        logger.warning(f"Spotify stage-1 search failed for '{artist_name}': {e}")

    # Stage 2: tribute/cover detection
    original = _extract_tribute_target(artist_name)
    if original:
        try:
            result = await spotify_service.search_artist(
                access_token, original, limit=5, query=f'artist:"{original}"'
            )
            candidates = result.get("artists", {}).get("items", [])
            if candidates:
                best = max(candidates, key=lambda a: _name_similarity(a.get("name", ""), original))
                if _name_similarity(best.get("name", ""), original) >= 0.80:
                    logger.info(f"Tribute match: '{artist_name}' -> '{best.get('name')}'")
                    return best
        except Exception as e:
            logger.warning(f"Spotify stage-2 tribute search failed for '{original}': {e}")

    # Stage 3: raw fallback
    try:
        result = await spotify_service.search_artist(access_token, artist_name, limit=1)
        candidates = result.get("artists", {}).get("items", [])
        if candidates:
            return candidates[0]
    except Exception as e:
        logger.warning(f"Spotify stage-3 fallback search failed for '{artist_name}': {e}")

    return {}


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
) -> List[ConcertMatch]:
    """
    Match and rank concert events against user's taste profile.
    Handles both external API events and Spotify-discovered events.
    """
    results = []
    known_artist_names_lower = {n.lower() for n in taste_profile.top_artist_names}

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

        # Search Spotify using three-stage logic (exact -> tribute fallback -> raw)
        sp_artist = await _find_spotify_artist(access_token, primary_artist)
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
