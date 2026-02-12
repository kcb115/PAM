"""
Taste Profile Builder.
Aggregates genre tags and audio features from Spotify data
to create a user's musical taste fingerprint.
"""
import logging
from collections import defaultdict
from models import TasteProfile, AudioFeatures
import spotify_service

logger = logging.getLogger(__name__)

# Root genre terms for fuzzy matching
ROOT_GENRES = [
    "indie", "folk", "electronic", "punk", "soul", "jazz", "metal",
    "hip hop", "rap", "rock", "pop", "r&b", "country", "blues",
    "classical", "ambient", "dance", "house", "techno", "reggae",
    "funk", "gospel", "latin", "ska", "grunge", "emo", "shoegaze",
    "dream pop", "synth", "disco", "garage", "psychedelic", "lo-fi",
    "lofi", "alternative", "experimental", "post-punk", "new wave",
    "math rock", "prog", "singer-songwriter", "americana", "bluegrass",
    "hardcore", "noise", "industrial", "trap", "drill", "grime",
    "afrobeat", "bossa nova", "world",
]


def extract_root_genres(genre_string: str) -> list:
    """Extract root genre terms from a detailed Spotify genre string."""
    genre_lower = genre_string.lower()
    found = []
    for root in ROOT_GENRES:
        if root in genre_lower:
            found.append(root)
    if not found:
        found.append(genre_lower.strip())
    return found


def build_genre_map(artists_data: list, time_range_weight: float = 1.0) -> dict:
    """Build weighted genre maps from artist data."""
    genre_counts = defaultdict(float)
    root_genre_counts = defaultdict(float)

    for i, artist in enumerate(artists_data):
        # Weight by position (top artists weigh more)
        position_weight = max(1.0 - (i * 0.015), 0.2)
        weight = position_weight * time_range_weight

        for genre in artist.get("genres", []):
            genre_counts[genre] += weight
            for root in extract_root_genres(genre):
                root_genre_counts[root] += weight

    return dict(genre_counts), dict(root_genre_counts)


def compute_audio_features(features_list: list) -> AudioFeatures:
    """Compute average audio features from a list of track features."""
    if not features_list:
        return AudioFeatures()

    valid = [f for f in features_list if f is not None]
    if not valid:
        return AudioFeatures()

    n = len(valid)
    return AudioFeatures(
        energy=round(sum(f.get("energy", 0) for f in valid) / n, 3),
        danceability=round(sum(f.get("danceability", 0) for f in valid) / n, 3),
        valence=round(sum(f.get("valence", 0) for f in valid) / n, 3),
        acousticness=round(sum(f.get("acousticness", 0) for f in valid) / n, 3),
        instrumentalness=round(sum(f.get("instrumentalness", 0) for f in valid) / n, 3),
        tempo=round(sum(f.get("tempo", 0) for f in valid) / n, 1),
    )


async def build_taste_profile(user_id: str, access_token: str) -> TasteProfile:
    """Build a complete taste profile from the user's Spotify data."""
    logger.info(f"Building taste profile for user {user_id}")

    # Fetch top artists for both time ranges
    short_artists = await spotify_service.get_top_artists(access_token, "short_term", 50)
    medium_artists = await spotify_service.get_top_artists(access_token, "medium_term", 50)

    short_items = short_artists.get("items", [])
    medium_items = medium_artists.get("items", [])

    # Build genre maps (short_term weighted more heavily - recent taste)
    short_genre, short_root = build_genre_map(short_items, time_range_weight=1.5)
    medium_genre, medium_root = build_genre_map(medium_items, time_range_weight=1.0)

    # Merge genre maps
    combined_genre = defaultdict(float)
    combined_root = defaultdict(float)
    for g, w in short_genre.items():
        combined_genre[g] += w
    for g, w in medium_genre.items():
        combined_genre[g] += w
    for g, w in short_root.items():
        combined_root[g] += w
    for g, w in medium_root.items():
        combined_root[g] += w

    # Normalize genre maps
    max_genre_val = max(combined_genre.values()) if combined_genre else 1
    max_root_val = max(combined_root.values()) if combined_root else 1
    normalized_genre = {k: round(v / max_genre_val, 3) for k, v in combined_genre.items()}
    normalized_root = {k: round(v / max_root_val, 3) for k, v in combined_root.items()}

    # Sort by weight descending
    sorted_genre = dict(sorted(normalized_genre.items(), key=lambda x: x[1], reverse=True))
    sorted_root = dict(sorted(normalized_root.items(), key=lambda x: x[1], reverse=True))

    # Collect all unique top artist IDs and names
    all_artists = {a["id"]: a["name"] for a in short_items + medium_items}
    top_artist_ids = list(all_artists.keys())
    top_artist_names = list(all_artists.values())

    # Fetch top tracks and audio features
    short_tracks = await spotify_service.get_top_tracks(access_token, "short_term", 50)
    medium_tracks = await spotify_service.get_top_tracks(access_token, "medium_term", 50)

    all_tracks = short_tracks.get("items", []) + medium_tracks.get("items", [])
    track_ids = list({t["id"] for t in all_tracks})

    # Audio features endpoint may be restricted (Spotify deprecated it for newer apps)
    try:
        features_data = await spotify_service.get_audio_features(access_token, track_ids)
        audio_features = compute_audio_features(features_data.get("audio_features", []))
    except Exception as e:
        logger.warning(f"Audio features unavailable (Spotify API restriction): {e}")
        # Estimate audio features from track popularity distribution
        audio_features = _estimate_audio_features_from_artists(short_items + medium_items)

    profile = TasteProfile(
        user_id=user_id,
        genre_map=sorted_genre,
        root_genre_map=sorted_root,
        audio_features=audio_features,
        top_artist_ids=top_artist_ids,
        top_artist_names=top_artist_names,
    )

    logger.info(f"Taste profile built: {len(sorted_genre)} genres, {len(sorted_root)} root genres, {len(top_artist_ids)} artists")
    return profile
