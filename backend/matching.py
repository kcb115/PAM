"""
Concert Matching Engine.
Fuzzy genre matching + ranking algorithm.

This module is designed to be swappable with a future
embedding-based similarity system (NVIDIA NIM).
"""
import logging
from typing import List, Dict, Optional
from models import TasteProfile, ConcertMatch
import spotify_service

logger = logging.getLogger(__name__)


def _extract_root_terms(genre_string: str) -> set:
    """Extract root genre terms from a genre string for fuzzy matching."""
    ROOT_TERMS = {
        "indie", "folk", "electronic", "punk", "soul", "jazz", "metal",
        "hip hop", "rap", "rock", "pop", "r&b", "country", "blues",
        "classical", "ambient", "dance", "house", "techno", "reggae",
        "funk", "gospel", "latin", "ska", "grunge", "emo", "shoegaze",
        "dream pop", "synth", "disco", "garage", "psychedelic", "lo-fi",
        "lofi", "alternative", "experimental", "post-punk", "new wave",
        "singer-songwriter", "americana", "bluegrass", "hardcore",
        "noise", "industrial", "trap", "drill", "grime", "afrobeat",
        "bossa nova", "world", "prog",
    }
    genre_lower = genre_string.lower()
    found = set()
    for term in ROOT_TERMS:
        if term in genre_lower:
            found.add(term)
    return found


def compute_genre_match_score(
    artist_genres: List[str],
    user_root_genre_map: Dict[str, float]
) -> tuple:
    """
    Compute genre match score between an artist's genres and user's taste.
    Returns (score 0-100, list of matching genres, explanation text).
    """
    if not artist_genres or not user_root_genre_map:
        return 0.0, [], "No genre data available"

    # Extract root terms from artist genres
    artist_roots = set()
    for g in artist_genres:
        artist_roots.update(_extract_root_terms(g))

    if not artist_roots:
        return 0.0, [], "No recognizable genre terms"

    # Calculate weighted match
    total_weight = 0.0
    matched_terms = []
    for root in artist_roots:
        if root in user_root_genre_map:
            total_weight += user_root_genre_map[root]
            matched_terms.append(root)

    if not matched_terms:
        return 0.0, [], "No genre overlap found"

    # Normalize score: ratio of matched weight to possible weight
    max_possible = sum(sorted(user_root_genre_map.values(), reverse=True)[:len(artist_roots)])
    if max_possible == 0:
        return 0.0, matched_terms, "Minimal overlap"

    raw_score = (total_weight / max_possible) * 100
    # Boost for more overlapping terms
    overlap_ratio = len(matched_terms) / len(artist_roots)
    score = min(raw_score * (0.7 + 0.3 * overlap_ratio), 99.0)

    # Build explanation
    top_user_genres = sorted(user_root_genre_map.items(), key=lambda x: x[1], reverse=True)[:5]
    top_user_names = [g[0] for g in top_user_genres]

    explanation = f"Your top genres include {', '.join(top_user_names[:3])}. "
    explanation += f"This artist blends {', '.join(matched_terms[:4])}."

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

        # If no genre data, search Spotify
        if not artist_genres:
            try:
                search_result = await spotify_service.search_artist(access_token, primary_artist)
                artists_found = search_result.get("artists", {}).get("items", [])
            except Exception as e:
                logger.warning(f"Spotify search failed for '{primary_artist}': {e}")
                artists_found = []

            if artists_found:
                best_match = artists_found[0]
                artist_genres = best_match.get("genres", [])
                spotify_popularity = best_match.get("popularity")

        # Compute genre match score
        score, matched_terms, explanation = compute_genre_match_score(
            artist_genres, taste_profile.root_genre_map
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
            spotify_popularity=spotify_popularity,
            image_url=event.get("image_url", ""),
            featured_track=event.get("featured_track", ""),
            source=event.get("source", "discovery"),
        ))

    # Sort by match score descending
    results.sort(key=lambda c: c.match_score, reverse=True)
    return results
