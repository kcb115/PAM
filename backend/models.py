from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid


class UserCreate(BaseModel):
    name: str
    email: str
    concerts_per_month: int = 2
    ticket_budget: float = 50.0


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    concerts_per_month: int = 2
    ticket_budget: float = 50.0
    spotify_connected: bool = False
    spotify_display_name: Optional[str] = None
    city: Optional[str] = None
    radius: int = 25
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    concerts_per_month: Optional[int] = None
    ticket_budget: Optional[float] = None
    city: Optional[str] = None
    radius: Optional[int] = None


class AudioFeatures(BaseModel):
    energy: float = 0.0
    danceability: float = 0.0
    valence: float = 0.0
    acousticness: float = 0.0
    instrumentalness: float = 0.0
    tempo: float = 0.0


class TasteProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    genre_map: Dict[str, float] = {}
    root_genre_map: Dict[str, float] = {}
    audio_features: AudioFeatures = Field(default_factory=AudioFeatures)
    top_artist_ids: List[str] = []
    top_artist_names: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ConcertMatch(BaseModel):
    event_id: str
    artist_name: str
    genre_description: str
    match_score: float
    match_explanation: str
    venue_name: str
    venue_city: str
    date: str
    time: Optional[str] = None
    ticket_url: Optional[str] = None
    event_url: Optional[str] = None
    spotify_popularity: Optional[int] = None
    image_url: Optional[str] = None
    featured_track: Optional[str] = None
    source: str = "discovery"


class DiscoverRequest(BaseModel):
    user_id: str
    city: str
    radius: int = 25
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class DiscoverResponse(BaseModel):
    concerts: List[ConcertMatch] = []
    taste_profile: Optional[TasteProfile] = None
    total_events_scanned: int = 0
    message: str = ""
    source: str = "spotify_discovery"


class FavoriteCreate(BaseModel):
    user_id: str
    concert: ConcertMatch


class Favorite(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    concert: ConcertMatch
    saved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ShareProfile(BaseModel):
    share_id: str
    user_name: str
    top_genres: List[str] = []
    root_genre_map: Dict[str, float] = {}
    audio_features: AudioFeatures = Field(default_factory=AudioFeatures)
    top_artist_count: int = 0
    created_at: str = ""
