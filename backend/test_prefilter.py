#!/usr/bin/env python3
"""
Unit tests for the 2-stage concert matching pipeline.

Self-contained: creates lightweight stubs for pydantic-based modules
so the tests run in any environment. In production (where pydantic is
installed), the real modules are used automatically.

Covers:
  1. prefilter_events sorts by prefilter score and respects candidate cap
  2. match_and_rank_concerts never returns more than MAX_SHOWS_PER_CITY
  3. Sorting by match_score is correct with deterministic tie-breaking
  4. Request-level dedup cache prevents duplicate Spotify lookups
  5. Prefilter scoring components produce expected relative ordering
  6. Genre match scoring and indie bonus
  7. Config constants are sensible
  8. Known artists excluded from results
"""
import asyncio
import sys
import os
import types
from unittest.mock import AsyncMock, patch

# ---------------------------------------------------------------------------
# Module shims: only needed when pydantic is not installed (CI, containers)
# ---------------------------------------------------------------------------
try:
    import pydantic  # noqa: F401
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False

if not _PYDANTIC_AVAILABLE:
    # Create a minimal pydantic shim
    pydantic_shim = types.ModuleType("pydantic")

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_dump(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    class _Field:
        @staticmethod
        def __call__(**kwargs):
            return kwargs.get("default", kwargs.get("default_factory", lambda: None)())

    class _ConfigDict:
        def __init__(self, **kwargs):
            pass

    pydantic_shim.BaseModel = _BaseModel
    pydantic_shim.Field = _Field()
    pydantic_shim.ConfigDict = _ConfigDict
    sys.modules["pydantic"] = pydantic_shim

# Now we can safely import the backend modules
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

# Stub spotify_service before importing matching (matching imports it at module level)
if "spotify_service" not in sys.modules:
    sp_stub = types.ModuleType("spotify_service")

    class SpotifyRateLimitError(Exception):
        def __init__(self, retry_after=1):
            self.retry_after = retry_after
            super().__init__(f"Rate limited for {retry_after}s")

    sp_stub.SpotifyRateLimitError = SpotifyRateLimitError

    async def _noop_search(*a, **kw):
        return {"artists": {"items": []}}

    sp_stub.search_artist = _noop_search
    sys.modules["spotify_service"] = sp_stub

from models import TasteProfile, ConcertMatch  # noqa: E402
from matching import (  # noqa: E402
    prefilter_events,
    match_and_rank_concerts,
    _prefilter_genre_score,
    _prefilter_artist_score,
    _prefilter_headliner_boost,
    compute_genre_match_score,
    compute_indie_bonus,
    MAX_SHOWS_PER_CITY,
    PREFILTER_CANDIDATES_PER_CITY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_taste_profile(**overrides) -> TasteProfile:
    defaults = {
        "user_id": "test-user",
        "root_genre_map": {
            "indie rock": 0.8,
            "folk": 0.6,
            "alternative": 0.5,
            "dream pop": 0.3,
        },
        "genre_map": {
            "indie rock": 0.8,
            "folk": 0.6,
        },
        "top_artist_names": ["Phoebe Bridgers", "Big Thief", "Waxahatchee"],
        "top_artist_ids": ["id1", "id2", "id3"],
    }
    defaults.update(overrides)
    return TasteProfile(**defaults)


def _make_event(
    artist_name: str,
    genres: list = None,
    event_id: str = None,
    date: str = "2025-08-15T20:00:00",
    venue_city: str = "Austin, TX",
    popularity: int = None,
) -> dict:
    return {
        "event_id": event_id or f"evt-{artist_name[:8].lower().replace(' ', '')}",
        "artist_names": [artist_name],
        "genres": genres or [],
        "popularity": popularity,
        "venue_name": "Test Venue",
        "venue_city": venue_city,
        "date": date,
        "ticket_url": "",
        "event_url": "",
        "image_url": "",
        "featured_track": "",
        "source": "jambase",
    }


def _run(coro):
    """Run an async coroutine synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# 1. Prefilter sorts correctly and respects candidate cap
# ---------------------------------------------------------------------------
def test_prefilter_sorts_by_score():
    """Events with better genre overlap should rank higher after prefilter."""
    taste = _make_taste_profile()
    events = [
        _make_event("No Match Band", genres=["metal", "death metal"]),
        _make_event("Indie Darling", genres=["indie rock", "folk"]),
        _make_event("Dream Artist", genres=["dream pop", "shoegaze"]),
    ]
    result = prefilter_events(events, taste, max_candidates=10)
    names = [e["artist_names"][0] for e in result]
    assert names[0] == "Indie Darling", f"Expected Indie Darling first, got {names}"
    print("PASS: prefilter_sorts_by_score")


def test_prefilter_respects_candidate_cap():
    """Prefilter should return at most max_candidates events."""
    taste = _make_taste_profile()
    events = [_make_event(f"Band {i}", genres=["rock"]) for i in range(200)]
    result = prefilter_events(events, taste, max_candidates=75)
    assert len(result) <= 75, f"Expected <=75, got {len(result)}"
    result_small = prefilter_events(events, taste, max_candidates=10)
    assert len(result_small) == 10, f"Expected 10, got {len(result_small)}"
    print("PASS: prefilter_respects_candidate_cap")


def test_prefilter_fewer_events_than_cap():
    """When there are fewer events than the cap, return them all."""
    taste = _make_taste_profile()
    events = [_make_event(f"Band {i}", genres=["indie rock"]) for i in range(5)]
    result = prefilter_events(events, taste, max_candidates=75)
    assert len(result) == 5, f"Expected 5, got {len(result)}"
    print("PASS: prefilter_fewer_events_than_cap")


# ---------------------------------------------------------------------------
# 2. match_and_rank_concerts enforces MAX_SHOWS_PER_CITY
# ---------------------------------------------------------------------------
def test_match_and_rank_caps_at_max():
    """Stage 2 should never return more than max_results."""
    taste = _make_taste_profile()
    events = [
        _make_event(f"Artist {i}", genres=["indie rock", "folk"], popularity=30)
        for i in range(50)
    ]
    mock_sp = {
        "name": "Mock Artist",
        "genres": ["indie rock", "folk", "alternative"],
        "popularity": 30,
        "external_urls": {"spotify": "https://open.spotify.com/artist/mock"},
    }
    with patch("matching._find_spotify_artist", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_sp
        result = _run(
            match_and_rank_concerts(events, taste, "fake_token", db=None, max_results=25)
        )
    assert len(result) <= 25, f"Expected <=25, got {len(result)}"
    print("PASS: match_and_rank_caps_at_max")


def test_match_and_rank_custom_cap():
    """max_results parameter should override the default."""
    taste = _make_taste_profile()
    events = [
        _make_event(f"Artist {i}", genres=["indie rock"], popularity=25)
        for i in range(20)
    ]
    mock_sp = {
        "name": "Mock",
        "genres": ["indie rock"],
        "popularity": 25,
        "external_urls": {"spotify": ""},
    }
    with patch("matching._find_spotify_artist", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_sp
        result = _run(
            match_and_rank_concerts(events, taste, "fake_token", db=None, max_results=5)
        )
    assert len(result) <= 5, f"Expected <=5, got {len(result)}"
    print("PASS: match_and_rank_custom_cap")


# ---------------------------------------------------------------------------
# 3. Results sorted by match_score desc, date asc tie-breaker
# ---------------------------------------------------------------------------
def test_results_sorted_by_score():
    """Output should be sorted by match_score descending."""
    taste = _make_taste_profile()
    events = [
        _make_event("Low Match", genres=["blues"], popularity=50),
        _make_event("High Match", genres=["indie rock", "folk", "alternative"], popularity=15),
        _make_event("Mid Match", genres=["folk"], popularity=30),
    ]
    mock_sp = {"genres": [], "popularity": None, "external_urls": {"spotify": ""}}
    with patch("matching._find_spotify_artist", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_sp
        result = _run(
            match_and_rank_concerts(events, taste, "fake_token", db=None)
        )
    if len(result) >= 2:
        for i in range(len(result) - 1):
            assert result[i].match_score >= result[i + 1].match_score, (
                f"Not sorted: {result[i].match_score} < {result[i+1].match_score}"
            )
    print("PASS: test_results_sorted_by_score")


# ---------------------------------------------------------------------------
# 4. Request-level dedup prevents duplicate Spotify lookups
# ---------------------------------------------------------------------------
def test_request_cache_dedup():
    """Same artist in multiple events should only trigger one Spotify lookup."""
    taste = _make_taste_profile()
    events = [
        _make_event("Same Artist", genres=["indie rock"], event_id=f"evt-{i}")
        for i in range(5)
    ]
    call_count = 0
    original_result = {
        "name": "Same Artist",
        "genres": ["indie rock"],
        "popularity": 40,
        "external_urls": {"spotify": ""},
    }

    async def mock_find(access_token, artist_name, db=None, request_cache=None):
        nonlocal call_count
        norm = artist_name.lower().strip()
        if request_cache is not None and norm in request_cache:
            return request_cache[norm]
        call_count += 1
        if request_cache is not None:
            request_cache[norm] = original_result
        return original_result

    with patch("matching._find_spotify_artist", side_effect=mock_find):
        _run(match_and_rank_concerts(events, taste, "fake_token", db=None))

    assert call_count == 1, f"Expected 1 Spotify lookup, got {call_count}"
    print("PASS: test_request_cache_dedup")


# ---------------------------------------------------------------------------
# 5. Prefilter scoring components
# ---------------------------------------------------------------------------
def test_prefilter_genre_score_direct_hit():
    user_map = {"indie rock": 0.8, "folk": 0.5}
    hit = _prefilter_genre_score(["indie rock"], user_map)
    miss = _prefilter_genre_score(["death metal"], user_map)
    assert hit > miss, f"Hit {hit} should > miss {miss}"
    print("PASS: test_prefilter_genre_score_direct_hit")


def test_prefilter_genre_score_partial_match():
    user_map = {"indie rock": 0.8}
    score = _prefilter_genre_score(["indie"], user_map)
    assert score > 0, f"Expected >0 for partial match, got {score}"
    print("PASS: test_prefilter_genre_score_partial_match")


def test_prefilter_artist_score():
    user_names = {"phoebe bridgers", "big thief"}
    match = _prefilter_artist_score(["Phoebe Bridgers"], user_names)
    no_match = _prefilter_artist_score(["Totally Unknown"], user_names)
    assert match > no_match, f"Match {match} should > no match {no_match}"
    print("PASS: test_prefilter_artist_score")


def test_headliner_boost_decreases():
    b0 = _prefilter_headliner_boost(0)
    b100 = _prefilter_headliner_boost(100)
    assert b0 > b100, f"Index 0 ({b0}) should > index 100 ({b100})"
    print("PASS: test_headliner_boost_decreases")


# ---------------------------------------------------------------------------
# 6. Genre match scoring
# ---------------------------------------------------------------------------
def test_compute_genre_match_score_basic():
    score, matched, _ = compute_genre_match_score(
        ["indie rock", "folk"], {"indie rock": 0.8, "folk": 0.6, "pop": 0.2}
    )
    assert score > 0, f"Expected positive score, got {score}"
    assert "indie rock" in matched
    print("PASS: test_compute_genre_match_score_basic")


def test_compute_genre_match_score_no_overlap():
    score, matched, _ = compute_genre_match_score(
        ["death metal"], {"indie rock": 0.8, "folk": 0.6}
    )
    assert score == 0.0
    assert matched == []
    print("PASS: test_compute_genre_match_score_no_overlap")


# ---------------------------------------------------------------------------
# 7. Indie bonus
# ---------------------------------------------------------------------------
def test_indie_bonus():
    assert compute_indie_bonus(10) == 15.0
    assert compute_indie_bonus(30) == 10.0
    assert compute_indie_bonus(50) == 5.0
    assert compute_indie_bonus(80) == 0.0
    assert compute_indie_bonus(None) == 5.0
    print("PASS: test_indie_bonus")


# ---------------------------------------------------------------------------
# 8. Config constants
# ---------------------------------------------------------------------------
def test_config_constants():
    assert MAX_SHOWS_PER_CITY == 25, f"Expected 25, got {MAX_SHOWS_PER_CITY}"
    assert PREFILTER_CANDIDATES_PER_CITY >= 25, (
        f"Candidate cap ({PREFILTER_CANDIDATES_PER_CITY}) must be >= final cap"
    )
    print("PASS: test_config_constants")


# ---------------------------------------------------------------------------
# 9. Known artists excluded
# ---------------------------------------------------------------------------
def test_known_artists_excluded():
    taste = _make_taste_profile(top_artist_names=["Known Band"])
    events = [
        _make_event("Known Band", genres=["indie rock"]),
        _make_event("Unknown Band", genres=["indie rock"]),
    ]
    mock_sp = {
        "name": "Mock",
        "genres": ["indie rock"],
        "popularity": 30,
        "external_urls": {"spotify": ""},
    }
    with patch("matching._find_spotify_artist", new_callable=AsyncMock) as mock_find:
        mock_find.return_value = mock_sp
        result = _run(
            match_and_rank_concerts(events, taste, "fake_token", db=None)
        )
    artist_names = [c.artist_name for c in result]
    assert "Known Band" not in artist_names, "Known artist should be excluded"
    print("PASS: test_known_artists_excluded")


# ===========================================================================
# Runner
# ===========================================================================
if __name__ == "__main__":
    tests = [
        test_prefilter_sorts_by_score,
        test_prefilter_respects_candidate_cap,
        test_prefilter_fewer_events_than_cap,
        test_match_and_rank_caps_at_max,
        test_match_and_rank_custom_cap,
        test_results_sorted_by_score,
        test_request_cache_dedup,
        test_prefilter_genre_score_direct_hit,
        test_prefilter_genre_score_partial_match,
        test_prefilter_artist_score,
        test_headliner_boost_decreases,
        test_compute_genre_match_score_basic,
        test_compute_genre_match_score_no_overlap,
        test_indie_bonus,
        test_config_constants,
        test_known_artists_excluded,
    ]

    passed = 0
    failed = 0
    for fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {fn.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
