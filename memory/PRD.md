# PAM - Concert Discovery App PRD

## Original Problem Statement
Build "PAM" - a web app that helps users discover local concerts by independent artists based on their Spotify listening taste profile.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI + Framer Motion + Recharts
- **Backend**: FastAPI (Python) + MongoDB
- **External APIs**: 
  - Spotify Web API (OAuth + top artists/tracks)
  - MusicBrainz (genre enrichment - free, no key)
  - Jambase Events API v1 (real concert events - key: f360dd73-...)
  - Nominatim (geocoding fallback)
- **Design**: Dark theme — #DED5EB (lavender) + #380E75 (deep purple), Syne + Plus Jakarta Sans fonts

## What's Been Implemented

### Phase 1 - MVP
- Landing page, onboarding (name/email/concert prefs), Spotify OAuth
- Taste profile builder, matching engine, concert cards

### Phase 2 - Features
- Concert date filtering (calendar), favorites/bookmarking, Share My Taste, tabbed dashboard

### Phase 3 - API Fixes
- MusicBrainz integration for genre enrichment (Spotify deprecated genres on artist objects)
- Audio features estimation from genres (Spotify deprecated /v1/audio-features)
- Spotify iframe OAuth fix (window.top.location.href)

### Phase 4 - Jambase Integration (Current)
- Correct Jambase API v1 (https://www.jambase.com/jb-api/v1/events) with lat/lng geo search
- Embedded US city geocoding database (200+ cities) + Nominatim fallback
- Genre-slug-mapped multi-query (user's top genres → Jambase genre slugs)
- 3-page pagination (up to 150 events per search)
- Event caching (1 hour per location+genre)
- Ticketmaster Discovery API as optional fallback

## Prioritized Backlog
### P1 (Next)
- [ ] Pagination for concert results
- [ ] Artist preview audio clips
- [ ] Auto-detect location via browser geolocation

### P2 (Future)
- [ ] Embedding-based matching (NVIDIA NIM)
- [ ] Social features (follow friends' taste profiles)
- [ ] Push notifications for new matching events
