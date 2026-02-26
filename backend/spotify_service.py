"""
Spotify OAuth and API service.
Handles Authorization Code Flow, token management, and data fetching.
"""
import os
import logging
import httpx
from urllib.parse import urlencode
import base64

logger = logging.getLogger(__name__)

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SCOPES = "user-top-read user-read-recently-played user-read-private"

# Maximum seconds we are willing to wait on a Spotify rate-limit retry.
# Anything beyond this and we fail gracefully instead of blocking the request.
MAX_RETRY_SECONDS = 5


def get_auth_url(state: str) -> str:
    params = {
        "client_id": os.environ["SPOTIFY_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": os.environ["SPOTIFY_REDIRECT_URI"],
        "scope": SCOPES,
        "state": state,
        "show_dialog": "true",
    }
    return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": os.environ["SPOTIFY_REDIRECT_URI"],
            },
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_token(refresh_token_val: str) -> dict:
    client_id = os.environ["SPOTIFY_CLIENT_ID"]
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"]
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_val,
            },
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def _spotify_get(access_token: str, endpoint: str, params: dict = None) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SPOTIFY_API_BASE}{endpoint}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params or {},
            timeout=15.0,
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 1))
            if retry_after <= MAX_RETRY_SECONDS:
                logger.warning(f"Spotify rate limited. Retrying after {retry_after}s")
                import asyncio
                await asyncio.sleep(retry_after)
                return await _spotify_get(access_token, endpoint, params)
            else:
                logger.warning(
                    f"Spotify rate limited for {retry_after}s (>{MAX_RETRY_SECONDS}s cap). "
                    "Skipping request."
                )
                raise SpotifyRateLimitError(retry_after)
        resp.raise_for_status()
        return resp.json()


class SpotifyRateLimitError(Exception):
    """Raised when Spotify rate limit exceeds our max retry threshold."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Spotify rate limited for {retry_after}s")


async def get_user_profile(access_token: str) -> dict:
    return await _spotify_get(access_token, "/me")


async def get_top_artists(access_token: str, time_range: str = "medium_term", limit: int = 50) -> dict:
    return await _spotify_get(access_token, "/me/top/artists", {
        "time_range": time_range,
        "limit": limit,
    })


async def get_top_tracks(access_token: str, time_range: str = "medium_term", limit: int = 50) -> dict:
    return await _spotify_get(access_token, "/me/top/tracks", {
        "time_range": time_range,
        "limit": limit,
    })


async def get_audio_features(access_token: str, track_ids: list) -> dict:
    if not track_ids:
        return {"audio_features": []}
    # Spotify allows max 100 IDs per request
    batches = [track_ids[i:i+100] for i in range(0, len(track_ids), 100)]
    all_features = []
    for batch in batches:
        ids_str = ",".join(batch)
        try:
            result = await _spotify_get(access_token, "/audio-features", {"ids": ids_str})
            all_features.extend(result.get("audio_features", []))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning("Audio features API restricted (403). Spotify deprecated this for newer apps.")
                raise
            raise
    return {"audio_features": all_features}


async def search_artist(access_token: str, artist_name: str, limit: int = 1, query: str = None) -> dict:
    return await _spotify_get(access_token, "/search", {
        "q": query or artist_name,
        "type": "artist",
        "limit": limit,
    })
