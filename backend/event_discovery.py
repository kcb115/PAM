"""
Smart Event Discovery Service.
Uses Spotify recommendations to find similar artists the user hasn't heard,
then generates concert-like event listings.

When a real events API (Jambase/Ticketmaster) is available,
this module can be bypassed in favor of real event data.
"""
import logging
import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import spotify_service

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
    Use Spotify's recommendations to find artists similar to the user's taste,
    then generate event listings for those artists.
    """
    logger.info(f"Discovering events via Spotify recommendations for {city}")

    # Pick seed artists (max 5 for Spotify recommendations)
    seed_artists = top_artist_ids[:5] if top_artist_ids else []
    if not seed_artists:
        return {"events": [], "total": 0, "source": "spotify_recommendations"}

    # Get recommendations
    discovered_artists = {}
    known_names_lower = {n.lower() for n in top_artist_names}

    try:
        # Get recommended tracks, extract unique artists
        recs = await spotify_service._spotify_get(access_token, "/recommendations", {
            "seed_artists": ",".join(seed_artists[:5]),
            "limit": 50,
            "min_popularity": 5,
            "max_popularity": 55,
        })

        for track in recs.get("tracks", []):
            for artist in track.get("artists", []):
                aid = artist.get("id", "")
                aname = artist.get("name", "")
                if aname.lower() not in known_names_lower and aid not in top_artist_ids:
                    if aid not in discovered_artists:
                        discovered_artists[aid] = {
                            "id": aid,
                            "name": aname,
                            "track_name": track.get("name", ""),
                        }
    except Exception as e:
        logger.warning(f"Spotify recommendations failed: {e}")

    # Also try with genre seeds
    top_genres = sorted(root_genre_map.items(), key=lambda x: x[1], reverse=True)[:3]
    genre_seeds = [g[0].replace(" ", "-") for g in top_genres]

    if genre_seeds and len(discovered_artists) < 20:
        try:
            recs2 = await spotify_service._spotify_get(access_token, "/recommendations", {
                "seed_genres": ",".join(genre_seeds[:3]),
                "seed_artists": ",".join(seed_artists[:2]),
                "limit": 30,
                "min_popularity": 3,
                "max_popularity": 50,
            })
            for track in recs2.get("tracks", []):
                for artist in track.get("artists", []):
                    aid = artist.get("id", "")
                    aname = artist.get("name", "")
                    if aname.lower() not in known_names_lower and aid not in top_artist_ids:
                        if aid not in discovered_artists:
                            discovered_artists[aid] = {
                                "id": aid,
                                "name": aname,
                                "track_name": track.get("name", ""),
                            }
        except Exception as e:
            logger.warning(f"Genre-based recommendations failed: {e}")

    if not discovered_artists:
        return {"events": [], "total": 0, "source": "spotify_recommendations"}

    # Fetch full artist details for discovered artists
    artist_ids = list(discovered_artists.keys())[:30]
    venues = _get_venues_for_city(city)
    dates = _generate_event_dates(len(artist_ids), date_from, date_to)

    events = []
    for i, aid in enumerate(artist_ids):
        ainfo = discovered_artists[aid]

        # Get artist details from Spotify
        try:
            artist_data = await spotify_service._spotify_get(access_token, f"/artists/{aid}")
            genres = artist_data.get("genres", [])
            popularity = artist_data.get("popularity", 0)
            images = artist_data.get("images", [])
            image_url = images[0]["url"] if images else ""
        except Exception:
            genres = []
            popularity = None
            image_url = ""

        venue = venues[i % len(venues)]
        date_str = dates[i] if i < len(dates) else dates[-1]

        # Generate a deterministic event ID
        eid = hashlib.md5(f"{aid}:{city}:{date_str}".encode()).hexdigest()[:12]

        # Build Spotify artist URL as ticket placeholder
        spotify_url = f"https://open.spotify.com/artist/{aid}"

        events.append({
            "event_id": eid,
            "artist_names": [ainfo["name"]],
            "artist_id": aid,
            "genres": genres,
            "popularity": popularity,
            "venue_name": venue["name"],
            "venue_city": city,
            "date": date_str,
            "ticket_url": spotify_url,
            "event_url": spotify_url,
            "image_url": image_url,
            "featured_track": ainfo.get("track_name", ""),
            "source": "spotify_discovery",
        })

    return {
        "events": events,
        "total": len(events),
        "source": "spotify_recommendations",
    }
