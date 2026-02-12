"""
Taste Profile Builder.
Aggregates genre tags and audio features from Spotify data
to create a user's musical taste fingerprint.
"""
import logging
from collections import defaultdict
from models import TasteProfile, AudioFeatures
import spotify_service
import musicbrainz_service

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


# Genre-based audio feature profiles for estimation when API is restricted
GENRE_AUDIO_PROFILES = {
    "rock": {"energy": 0.72, "danceability": 0.50, "valence": 0.55, "acousticness": 0.15, "instrumentalness": 0.05, "tempo": 128},
    "indie": {"energy": 0.55, "danceability": 0.52, "valence": 0.48, "acousticness": 0.30, "instrumentalness": 0.08, "tempo": 120},
    "pop": {"energy": 0.68, "danceability": 0.70, "valence": 0.65, "acousticness": 0.15, "instrumentalness": 0.02, "tempo": 120},
    "electronic": {"energy": 0.78, "danceability": 0.75, "valence": 0.45, "acousticness": 0.05, "instrumentalness": 0.25, "tempo": 128},
    "hip hop": {"energy": 0.65, "danceability": 0.78, "valence": 0.50, "acousticness": 0.10, "instrumentalness": 0.02, "tempo": 130},
    "rap": {"energy": 0.68, "danceability": 0.76, "valence": 0.48, "acousticness": 0.08, "instrumentalness": 0.01, "tempo": 132},
    "folk": {"energy": 0.35, "danceability": 0.45, "valence": 0.50, "acousticness": 0.70, "instrumentalness": 0.05, "tempo": 110},
    "jazz": {"energy": 0.40, "danceability": 0.55, "valence": 0.55, "acousticness": 0.45, "instrumentalness": 0.20, "tempo": 115},
    "metal": {"energy": 0.90, "danceability": 0.35, "valence": 0.30, "acousticness": 0.05, "instrumentalness": 0.10, "tempo": 140},
    "punk": {"energy": 0.85, "danceability": 0.45, "valence": 0.50, "acousticness": 0.08, "instrumentalness": 0.02, "tempo": 155},
    "soul": {"energy": 0.50, "danceability": 0.65, "valence": 0.60, "acousticness": 0.30, "instrumentalness": 0.03, "tempo": 110},
    "r&b": {"energy": 0.52, "danceability": 0.68, "valence": 0.55, "acousticness": 0.25, "instrumentalness": 0.02, "tempo": 105},
    "country": {"energy": 0.55, "danceability": 0.55, "valence": 0.65, "acousticness": 0.40, "instrumentalness": 0.02, "tempo": 120},
    "classical": {"energy": 0.25, "danceability": 0.25, "valence": 0.35, "acousticness": 0.85, "instrumentalness": 0.80, "tempo": 100},
    "ambient": {"energy": 0.20, "danceability": 0.30, "valence": 0.35, "acousticness": 0.60, "instrumentalness": 0.65, "tempo": 90},
    "dance": {"energy": 0.82, "danceability": 0.82, "valence": 0.60, "acousticness": 0.05, "instrumentalness": 0.10, "tempo": 125},
    "alternative": {"energy": 0.60, "danceability": 0.50, "valence": 0.45, "acousticness": 0.25, "instrumentalness": 0.08, "tempo": 122},
    "blues": {"energy": 0.45, "danceability": 0.50, "valence": 0.45, "acousticness": 0.45, "instrumentalness": 0.05, "tempo": 100},
}


def _estimate_audio_features_from_artists(artists: list) -> AudioFeatures:
    """Estimate audio features from artist genres when the audio-features API is restricted."""
    totals = {"energy": 0, "danceability": 0, "valence": 0, "acousticness": 0, "instrumentalness": 0, "tempo": 0}
    matches = 0

    for artist in artists:
        for genre in artist.get("genres", []):
            for root in extract_root_genres(genre):
                if root in GENRE_AUDIO_PROFILES:
                    profile = GENRE_AUDIO_PROFILES[root]
                    for key in totals:
                        totals[key] += profile[key]
                    matches += 1

    if matches == 0:
        # Fallback to balanced defaults
        return AudioFeatures(
            energy=0.55, danceability=0.55, valence=0.50,
            acousticness=0.25, instrumentalness=0.05, tempo=120.0,
        )

    return AudioFeatures(
        energy=round(totals["energy"] / matches, 3),
        danceability=round(totals["danceability"] / matches, 3),
        valence=round(totals["valence"] / matches, 3),
        acousticness=round(totals["acousticness"] / matches, 3),
        instrumentalness=round(totals["instrumentalness"] / matches, 3),
        tempo=round(totals["tempo"] / matches, 1),
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
