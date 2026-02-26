"""
Taste Profile Builder.
Aggregates genre tags from Spotify data to create a user's genre summary.
Uses raw Spotify genre strings without simplification.
Generates an AI-powered narrative description of the listener's taste.
"""
import logging
import os
from collections import defaultdict
from models import TasteProfile, AudioFeatures
import spotify_service
import musicbrainz_service

logger = logging.getLogger(__name__)


def build_genre_map(artists_data: list, time_range_weight: float = 1.0) -> dict:
    """Build weighted genre map from artist data using raw Spotify tags."""
    genre_counts = defaultdict(float)

    for i, artist in enumerate(artists_data):
        position_weight = max(1.0 - (i * 0.015), 0.2)
        weight = position_weight * time_range_weight

        for genre in artist.get("genres", []):
            genre_counts[genre.lower().strip()] += weight

    return dict(genre_counts)


async def generate_narrative(
    genre_map: dict,
    top_artist_names: list,
    audio_features: AudioFeatures,
) -> str:
    """Generate a 3-4 sentence narrative describing the listener's taste using Claude Haiku."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set. Skipping narrative generation.")
        return ""

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)

        # Prepare the data payload: top 10 genres and top 10 artists
        top_genres = list(genre_map.items())[:10]
        genre_summary = ", ".join(
            f"{genre} ({round(weight * 100)}%)" for genre, weight in top_genres
        )
        artist_summary = ", ".join(top_artist_names[:10])

        features_summary = (
            f"energy: {audio_features.energy:.2f}, "
            f"danceability: {audio_features.danceability:.2f}, "
            f"valence (mood): {audio_features.valence:.2f}, "
            f"acousticness: {audio_features.acousticness:.2f}, "
            f"instrumentalness: {audio_features.instrumentalness:.2f}, "
            f"tempo: {audio_features.tempo:.0f} BPM"
        )

        prompt = (
            "You are PAM, a concert discovery app that knows music deeply. "
            "Based on this listener's Spotify data, write exactly 3-4 sentences "
            "describing who they are as a listener. Speak directly to them in "
            "second person (\"you\"). Be warm, specific, and insightful. Reference "
            "specific genres and artists from the data naturally, not as a list. "
            "Do NOT use generic filler. Every sentence should reveal something "
            "meaningful about their taste. Do NOT use emojis or bullet points.\n\n"
            f"Top genres (weighted): {genre_summary}\n"
            f"Top artists: {artist_summary}\n"
            f"Audio features: {features_summary}"
        )

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        narrative = message.content[0].text.strip()
        logger.info(f"Generated taste narrative ({len(narrative)} chars)")
        return narrative

    except Exception as e:
        logger.error(f"Narrative generation failed: {e}")
        return ""


async def build_taste_profile(user_id: str, access_token: str) -> TasteProfile:
    """Build a genre taste profile from the user's Spotify data."""
    logger.info(f"Building taste profile for user {user_id}")

    # Fetch top artists for both time ranges
    short_artists = await spotify_service.get_top_artists(access_token, "short_term", 50)
    medium_artists = await spotify_service.get_top_artists(access_token, "medium_term", 50)

    short_items = short_artists.get("items", [])
    medium_items = medium_artists.get("items", [])

    # Check if Spotify returned genres (they often don't since late 2024)
    has_spotify_genres = any(
        a.get("genres") for a in short_items + medium_items
    )

    if not has_spotify_genres:
        logger.info("Spotify returned empty genres. Enriching via MusicBrainz...")
        all_names = list({a["name"] for a in short_items + medium_items})
        mb_genres = await musicbrainz_service.get_genres_for_artists(all_names[:30])

        for item_list in [short_items, medium_items]:
            for artist in item_list:
                name = artist.get("name", "")
                if not artist.get("genres") and name in mb_genres:
                    artist["genres"] = mb_genres[name]

    # Build genre maps (short_term weighted more heavily - recent taste)
    short_genres = build_genre_map(short_items, time_range_weight=1.5)
    medium_genres = build_genre_map(medium_items, time_range_weight=1.0)

    # Merge
    combined = defaultdict(float)
    for g, w in short_genres.items():
        combined[g] += w
    for g, w in medium_genres.items():
        combined[g] += w

    # Normalize
    max_val = max(combined.values()) if combined else 1
    normalized = {k: round(v / max_val, 3) for k, v in combined.items()}

    # Sort by weight descending
    sorted_genres = dict(sorted(normalized.items(), key=lambda x: x[1], reverse=True))

    # Collect all unique top artist IDs and names
    all_artists = {a["id"]: a["name"] for a in short_items + medium_items}
    top_artist_ids = list(all_artists.keys())
    top_artist_names = list(all_artists.values())

    # Generate AI narrative
    audio = AudioFeatures()
    narrative = await generate_narrative(sorted_genres, top_artist_names, audio)

    profile = TasteProfile(
        user_id=user_id,
        genre_map=sorted_genres,
        root_genre_map=sorted_genres,
        audio_features=audio,
        top_artist_ids=top_artist_ids,
        top_artist_names=top_artist_names,
        taste_narrative=narrative,
    )

    logger.info(f"Taste profile built: {len(sorted_genres)} genres, {len(top_artist_ids)} artists")
    return profile
