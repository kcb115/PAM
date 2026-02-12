from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from models import (
    User, UserCreate, UserUpdate, TasteProfile,
    DiscoverRequest, DiscoverResponse, FavoriteCreate, Favorite, ShareProfile,
)
import spotify_service
import taste_profile as tp
import jambase_service
import matching
import event_discovery

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ─── Health ──────────────────────────────────────────────
@api_router.get("/")
async def root():
    return {"message": "PAM API is running"}


# ─── Users ───────────────────────────────────────────────
@api_router.post("/users")
async def create_user(data: UserCreate):
    user = User(
        name=data.name,
        email=data.email,
        concerts_per_month=data.concerts_per_month,
        ticket_budget=data.ticket_budget,
    )
    doc = user.model_dump()
    await db.users.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@api_router.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@api_router.put("/users/{user_id}")
async def update_user(user_id: str, data: UserUpdate):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    return user


# ─── Spotify OAuth ───────────────────────────────────────
@api_router.get("/spotify/login")
async def spotify_login(user_id: str = Query(...)):
    """Initiate Spotify OAuth flow. Pass user_id as query param."""
    state = f"{user_id}:{uuid.uuid4().hex[:8]}"
    auth_url = spotify_service.get_auth_url(state)
    return {"auth_url": auth_url}


@api_router.get("/spotify/callback")
async def spotify_callback(code: str = Query(...), state: str = Query(""), error: str = Query(None)):
    """Handle Spotify OAuth callback."""
    if error:
        logger.error(f"Spotify auth error: {error}")
        frontend_url = os.environ.get("SPOTIFY_REDIRECT_URI", "").replace("/api/spotify/callback", "")
        return RedirectResponse(url=f"{frontend_url}/?error={error}")

    # Extract user_id from state
    user_id = state.split(":")[0] if ":" in state else ""

    try:
        token_data = await spotify_service.exchange_code(code)
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        frontend_url = os.environ.get("SPOTIFY_REDIRECT_URI", "").replace("/api/spotify/callback", "")
        return RedirectResponse(url=f"{frontend_url}/?error=token_exchange_failed")

    access_token = token_data.get("access_token")
    refresh_tok = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)

    # Store tokens server-side in MongoDB
    session_id = str(uuid.uuid4())
    await db.spotify_sessions.insert_one({
        "session_id": session_id,
        "user_id": user_id,
        "access_token": access_token,
        "refresh_token": refresh_tok,
        "expires_in": expires_in,
    })

    # Get Spotify profile and update user
    try:
        profile = await spotify_service.get_user_profile(access_token)
        display_name = profile.get("display_name", "")
        await db.users.update_one(
            {"id": user_id},
            {"$set": {"spotify_connected": True, "spotify_display_name": display_name}},
        )
    except Exception as e:
        logger.warning(f"Failed to get Spotify profile: {e}")

    # Redirect back to frontend with session info
    frontend_url = os.environ.get("SPOTIFY_REDIRECT_URI", "").replace("/api/spotify/callback", "")
    return RedirectResponse(
        url=f"{frontend_url}/dashboard?session_id={session_id}&user_id={user_id}"
    )


@api_router.get("/spotify/session/{session_id}")
async def get_session(session_id: str):
    """Check if a Spotify session is valid."""
    session = await db.spotify_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"valid": True, "user_id": session.get("user_id")}


# ─── Taste Profile ───────────────────────────────────────
@api_router.post("/taste-profile/build")
async def build_taste_profile(session_id: str = Query(...), user_id: str = Query(...)):
    """Build taste profile from Spotify data."""
    session = await db.spotify_sessions.find_one({"session_id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    access_token = session["access_token"]

    # Try refreshing if needed
    try:
        profile = await tp.build_taste_profile(user_id, access_token)
    except Exception as e:
        # Try refreshing token
        logger.warning(f"Taste profile build failed, trying token refresh: {e}")
        try:
            new_tokens = await spotify_service.refresh_token(session["refresh_token"])
            access_token = new_tokens["access_token"]
            await db.spotify_sessions.update_one(
                {"session_id": session_id},
                {"$set": {"access_token": access_token}},
            )
            profile = await tp.build_taste_profile(user_id, access_token)
        except Exception as e2:
            logger.error(f"Taste profile build failed after refresh: {e2}")
            raise HTTPException(status_code=500, detail=f"Failed to build taste profile: {str(e2)}")

    # Store in DB
    doc = profile.model_dump()
    await db.taste_profiles.delete_many({"user_id": user_id})
    await db.taste_profiles.insert_one(doc)

    return {k: v for k, v in doc.items() if k != "_id"}


@api_router.get("/taste-profile/{user_id}")
async def get_taste_profile(user_id: str):
    """Get the stored taste profile for a user."""
    profile = await db.taste_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=404, detail="Taste profile not found. Build one first.")
    return profile


# ─── Concert Discovery ───────────────────────────────────
@api_router.post("/concerts/discover")
async def discover_concerts(data: DiscoverRequest):
    """Discover matching concerts near the user's location."""
    profile_doc = await db.taste_profiles.find_one({"user_id": data.user_id}, {"_id": 0})
    if not profile_doc:
        raise HTTPException(status_code=400, detail="Build your taste profile first")

    taste = TasteProfile(**profile_doc)

    session = await db.spotify_sessions.find_one({"user_id": data.user_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=401, detail="Spotify session expired. Reconnect.")

    access_token = session["access_token"]

    # Update user location
    await db.users.update_one(
        {"id": data.user_id},
        {"$set": {"city": data.city, "radius": data.radius}},
    )

    # Try Jambase first, fall back to Spotify-based discovery
    events_data = await jambase_service.search_events(data.city, data.radius)
    events = events_data.get("events", [])
    source = "jambase"

    if not events or events_data.get("error"):
        # Use Spotify-based smart discovery
        logger.info("Falling back to Spotify-based event discovery")
        events_data = await event_discovery.discover_events_via_spotify(
            access_token=access_token,
            top_artist_ids=taste.top_artist_ids,
            top_artist_names=taste.top_artist_names,
            root_genre_map=taste.root_genre_map,
            city=data.city,
            radius=data.radius,
            date_from=data.date_from,
            date_to=data.date_to,
        )
        events = events_data.get("events", [])
        source = "spotify_discovery"

    if not events:
        return DiscoverResponse(
            concerts=[],
            taste_profile=taste,
            total_events_scanned=0,
            message="No upcoming events found. Try a different city or expand your search.",
            source=source,
        )

    # Match and rank
    try:
        concerts = await matching.match_and_rank_concerts(events, taste, access_token)
    except Exception as e:
        logger.error(f"Matching failed: {e}")
        raise HTTPException(status_code=500, detail=f"Matching error: {str(e)}")

    message = ""
    if not concerts:
        message = "No matching concerts found. Try expanding your radius or a different city."

    return DiscoverResponse(
        concerts=concerts,
        taste_profile=taste,
        total_events_scanned=len(events),
        message=message,
        source=source,
    )


# ─── Favorites ───────────────────────────────────────────
@api_router.post("/favorites")
async def add_favorite(data: FavoriteCreate):
    """Save a concert to favorites."""
    # Check for duplicate
    existing = await db.favorites.find_one({
        "user_id": data.user_id,
        "concert.event_id": data.concert.event_id,
    }, {"_id": 0})
    if existing:
        return {k: v for k, v in existing.items() if k != "_id"}

    fav = Favorite(user_id=data.user_id, concert=data.concert)
    doc = fav.model_dump()
    await db.favorites.insert_one(doc)
    return {k: v for k, v in doc.items() if k != "_id"}


@api_router.get("/favorites/{user_id}")
async def get_favorites(user_id: str):
    """Get all saved favorites for a user."""
    favs = await db.favorites.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    return favs


@api_router.delete("/favorites/{favorite_id}")
async def remove_favorite(favorite_id: str):
    """Remove a concert from favorites."""
    result = await db.favorites.delete_one({"id": favorite_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"deleted": True}


# ─── Share Taste Profile ─────────────────────────────────
@api_router.post("/share/create")
async def create_share(user_id: str = Query(...)):
    """Generate a shareable taste profile link."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = await db.taste_profiles.find_one({"user_id": user_id}, {"_id": 0})
    if not profile:
        raise HTTPException(status_code=400, detail="No taste profile to share")

    # Create or update share
    share_id = uuid.uuid4().hex[:10]

    top_genres = sorted(
        profile.get("genre_map", {}).items(),
        key=lambda x: x[1],
        reverse=True,
    )[:8]

    share_doc = {
        "share_id": share_id,
        "user_id": user_id,
        "user_name": user.get("name", "Anonymous"),
        "top_genres": [g[0] for g in top_genres],
        "root_genre_map": profile.get("root_genre_map", {}),
        "audio_features": profile.get("audio_features", {}),
        "top_artist_count": len(profile.get("top_artist_ids", [])),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Upsert
    await db.shares.update_one(
        {"user_id": user_id},
        {"$set": share_doc},
        upsert=True,
    )

    return share_doc


@api_router.get("/share/{share_id}")
async def get_share(share_id: str):
    """Get a shared taste profile by share_id."""
    share = await db.shares.find_one({"share_id": share_id}, {"_id": 0})
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    return share


# ─── Include router ─────────────────────────────────────
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
