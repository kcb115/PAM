"""
Smart Event Discovery Service.
Uses Spotify recommendations to find similar artists the user hasn't heard,
then generates concert-like event listings.

When a real events API (Jambase/Ticketmaster) is available,
this module can be bypassed in favor of real event data.

Now applies the same 2-stage pipeline as the main discovery path:
  Stage 1: rank discovered artists by tag overlap (cheap, no Spotify calls)
  Stage 2: enrich only the top candidates via Spotify, cap at MAX_SHOWS_PER_CITY
"""
import logging
import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import spotify_service
import musicbrainz_service
from matching import MAX_SHOWS_PER_CITY, PREFILTER_CANDIDATES_PER_CITY

logger = logging.getLogger(__name__)

# Venue databases per city (realistic venues)
VENUE_DB = {
    "default": [
        {"name": "The Underground", "capacity": 200},
        {"name": "Red Room", "capacity": 150},
        {"name": "The Parish", "capacity": 300},
        {"name": "Vinyl Lounge", "capacity": 100},
        {"name": "Warehouse Live", "capacity": 500},
        {"name": "The Basement", "capacity": 180},
        {"name": "Songbird Theater", "capacity": 250},
        {"name": "Electric Owl", "capacity": 350},
        {"name": "The Hideout", "capacity": 120},
        {"name": "Main Street Music Hall", "capacity": 400},
    ],
    "austin": [
        {"name": "Mohawk", "capacity": 600},
        {"name": "Hotel Vegas", "capacity": 250},
        {"name": "The Parish", "capacity": 500},
        {"name": "Cheer Up Charlies", "capacity": 200},
        {"name": "Empire Control Room", "capacity": 400},
        {"name": "Hole in the Wall", "capacity": 100},
        {"name": "Stubb's Waller Creek Amphitheater", "capacity": 2100},
        {"name": "Continental Club", "capacity": 200},
    ],
    "new york": [
        {"name": "Bowery Ballroom", "capacity": 575},
        {"name": "Mercury Lounge", "capacity": 250},
        {"name": "Baby's All Right", "capacity": 300},
        {"name": "Brooklyn Steel", "capacity": 1800},
        {"name": "Rough Trade NYC", "capacity": 250},
        {"name": "Le Poisson Rouge", "capacity": 700},
        {"name": "Elsewhere", "capacity": 500},
        {"name": "Music Hall of Williamsburg", "capacity": 550},
    ],
    "los angeles": [
        {"name": "The Echo", "capacity": 350},
        {"name": "The Troubadour", "capacity": 500},
        {"name": "Zebulon", "capacity": 200},
        {"name": "Lodge Room", "capacity": 500},
        {"name": "The Moroccan Lounge", "capacity": 250},
        {"name": "Teragram Ballroom", "capacity": 800},
        {"name": "The Regent Theater", "capacity": 1000},
    ],
    "nashville": [
        {"name": "The Basement East", "capacity": 600},
        {"name": "Exit/In", "capacity": 500},
        {"name": "The 5 Spot", "capacity": 150},
        {"name": "Mercy Lounge", "capacity": 500},
        {"name": "3rd & Lindsley", "capacity": 400},
        {"name": "The Station Inn", "capacity": 200},
    ],
    "chicago": [
        {"name": "Empty Bottle", "capacity": 400},
        {"name": "Lincoln Hall", "capacity": 507},
        {"name": "Schubas Tavern", "capacity": 165},
        {"name": "Metro", "capacity": 1100},
        {"name": "Sleeping Village", "capacity": 250},
        {"name": "Thalia Hall", "capacity": 900},
    ],
    "portland": [
        {"name": "Doug Fir Lounge", "capacity": 300},
        {"name": "Mississippi Studios", "capacity": 250},
        {"name": "Wonder Ballroom", "capacity": 800},
        {"name": "Polaris Hall", "capacity": 500},
        {"name": "The Aladdin Theater", "capacity": 620},
    ],
    "seattle": [
        {"name": "Neumos", "capacity": 650},
        {"name": "The Crocodile", "capacity": 550},
        {"name": "Tractor Tavern", "capacity": 300},
        {"name": "The Showbox", "capacity": 1100},
        {"name": "Barboza", "capacity": 200},
    ],
    "denver": [
        {"name": "Globe Hall", "capacity": 200},
        {"name": "Larimer Lounge", "capacity": 250},
        {"name": "Bluebird Theater", "capacity": 550},
        {"name": "Gothic Theatre", "capacity": 1100},
        {"name": "Lost Lake Lounge", "capacity": 200},
    ],
}


def _get_venues_for_city(city: str) -> list:
    city_lower = city.lower().strip()
    for key in VENUE_DB:
        if key in city_lower or city_lower in key:
            return VENUE_DB[key]
    return VENUE_DB["default"]


def _generate_event_dates(count: int, date_from: str = None, date_to: str = None) -> List[str]:
    """Generate realistic upcoming concert dates."""
    now = datetime.now(timezone.utc)

    if date_from:
        try:
            start = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            start = now + timedelta(days=1)
    else:
        start = now + timedelta(days=1)

    if date_to:
        try:
            end = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            end = start + timedelta(days=90)
    else:
        end = start + timedelta(days=90)

    dates = []
    delta_days = (end - start).days
    if delta_days < 1:
        delta_days = 90

    for i in range(count):
        # Bias toward Thursdays-Saturdays (typical concert nights)
        day_offset = random.randint(1, max(delta_days, 7))
        event_date = start + timedelta(days=day_offset)
        # Adjust to nearby Thu/Fri/Sat
        weekday = event_date.weekday()
        if weekday < 3:
            event_date += timedelta(days=(3 - weekday))
        elif weekday == 6:
            event_date -= timedelta(days=1)

        hour = random.choice([19, 20, 21])
        event_date = event_date.replace(hour=hour, minute=0, second=0)
        dates.append(event_date.isoformat())

    dates.sort()
    return dates


def _cheap_tag_score(
    artist_tags: List[str],
    root_genre_map: Dict[str, float],
) -> float:
    """
    Stage 1 scoring for MusicBrainz-discovered artists.
    Compares artist tags against the user's root_genre_map.
    Returns a score (higher = better match).
    """
    if not artist_tags or not root_genre_map:
        return 0.0

    score = 0.0
    for tag in artist_tags:
        tl = tag.lower().strip()
        if tl in root_genre_map:
            score += root_genre_map[tl] * 10.0
        else:
            for ug, w in root_genre_map.items():
                if tl in ug or ug in tl:
                    score += w * 2.0
                    break
    return score


async def discover_events_via_spotify(
    access_token: str,
    top_artist_ids: List[str],
    top_artist_names: List[str],
    root_genre_map: Dict[str, float],
    city: str,
    radius: int = 25,
    date_from: str = None,
    date_to: str = None,
) -> dict:
    """
    Discover similar artists using MusicBrainz (since Spotify recommendations
    were deprecated in Nov 2024), then generate event listings.

    Now applies a 2-stage pipeline:
      Stage 1: rank discovered artists by tag overlap (no Spotify calls)
      Stage 2: enrich only top candidates via Spotify, cap at MAX_SHOWS_PER_CITY
    """
    logger.info(f"Discovering events via MusicBrainz for {city}")

    if not root_genre_map and not top_artist_names:
        return {"events": [], "total": 0, "source": "musicbrainz_discovery"}

    known_names_lower = {n.lower() for n in top_artist_names}

    # Use top root genres to find similar artists via MusicBrainz
    top_tags = sorted(root_genre_map.items(), key=lambda x: x[1], reverse=True)[:6]
    tag_names = [t[0] for t in top_tags]

    discovered = await musicbrainz_service.find_artists_by_tags(
        tags=tag_names,
        exclude_names=set(top_artist_names),
        limit=30,
    )

    if not discovered:
        return {"events": [], "total": 0, "source": "musicbrainz_discovery"}

    total_discovered = len(discovered)

    # ── Stage 1: Rank by tag overlap, keep top candidates ────
    scored_artists = []
    for idx, artist in enumerate(discovered):
        tags = artist.get("tags", [])
        tag_score = _cheap_tag_score(tags, root_genre_map)
        scored_artists.append((-tag_score, idx, artist))

    scored_artists.sort()
    candidate_cap = min(PREFILTER_CANDIDATES_PER_CITY, len(scored_artists))
    candidates = [item[2] for item in scored_artists[:candidate_cap]]

    logger.info(
        f"MusicBrainz prefilter: {total_discovered} artists -> "
        f"{len(candidates)} candidates"
    )

    # ── Stage 2: Spotify enrichment for candidates only ──────
    venues = _get_venues_for_city(city)
    dates = _generate_event_dates(len(candidates), date_from, date_to)

    events = []
    spotify_calls = 0

    for i, artist in enumerate(candidates):
        name = artist["name"]
        tags = artist.get("tags", [])

        # Try to get Spotify artist info for image/popularity
        image_url = ""
        popularity = None
        spotify_url = ""
        try:
            search_result = await spotify_service.search_artist(access_token, name)
            spotify_calls += 1
            sp_artists = search_result.get("artists", {}).get("items", [])
            if sp_artists:
                sp = sp_artists[0]
                popularity = sp.get("popularity")
                images = sp.get("images", [])
                image_url = images[0]["url"] if images else ""
                spotify_url = sp.get("external_urls", {}).get("spotify", "")
                # Merge Spotify genres if available
                sp_genres = sp.get("genres", [])
                if sp_genres:
                    tags = list(set(tags + sp_genres))
        except Exception:
            pass

        venue = venues[i % len(venues)]
        date_str = dates[i] if i < len(dates) else dates[-1]

        eid = hashlib.md5(f"{name}:{city}:{date_str}".encode()).hexdigest()[:12]

        events.append({
            "event_id": eid,
            "artist_names": [name],
            "genres": tags,
            "popularity": popularity,
            "venue_name": venue["name"],
            "venue_city": city,
            "date": date_str,
            "ticket_url": f"https://www.google.com/search?q={name.replace(' ', '+')}+concert+tickets",
            "event_url": spotify_url,
            "spotify_artist_url": spotify_url,
            "image_url": image_url,
            "featured_track": "",
            "source": "musicbrainz_discovery",
        })

    # ── Cap to MAX_SHOWS_PER_CITY ────────────────────────────
    # Events are already ordered by tag relevance from Stage 1, but if we want
    # to re-sort by a combined score we could. For now, the Stage-1 ordering
    # plus Spotify enrichment gives a good result. Just enforce the cap.
    capped = events[:MAX_SHOWS_PER_CITY]

    logger.info(
        f"MusicBrainz discovery: {total_discovered} found -> "
        f"{len(candidates)} enriched ({spotify_calls} Spotify calls) -> "
        f"{len(capped)} returned (cap={MAX_SHOWS_PER_CITY})"
    )

    return {
        "events": capped,
        "total": len(capped),
        "source": "musicbrainz_discovery",
    }
