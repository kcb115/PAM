# PAM - Concert Discovery App PRD

## Original Problem Statement
Build "PAM" - a web app that helps users discover local concerts by independent artists based on their Spotify listening taste profile. NOT about finding concerts by artists they already listen to — it's about building a taste profile and recommending concerts by similar, lesser-known artists they haven't heard yet.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI + Framer Motion + Recharts
- **Backend**: FastAPI (Python) + MongoDB
- **External APIs**: Spotify Web API (OAuth + recommendations + artist data)
- **Design**: Dark theme "Underground Curator" — amber + teal accents, Syne + Plus Jakarta Sans fonts

## User Personas
1. **Music Explorer** (Primary): 20-40, active Spotify user, attends 1-4 live shows/month, wants to discover new indie artists
2. **Casual Concertgoer**: Occasional show attendee, wants curated recommendations without effort

## Core Requirements (Static)
- Spotify OAuth Authorization Code Flow (server-side tokens)
- Taste profile: weighted genre map + audio features (energy, danceability, valence, acousticness, instrumentalness, tempo)
- Smart event discovery via Spotify recommendations (fallback for Jambase)
- Fuzzy genre matching algorithm (keyword-based root term extraction)
- Exclude known artists, prioritize low-popularity indie artists
- "Why this match?" explanations
- User registration (name, email, concert prefs)
- Favorites/bookmarking system
- Shareable taste profile cards
- Date range filtering for concerts

## What's Been Implemented

### Phase 1 (Feb 12, 2026)
- Landing page with hero, feature cards, animated entrance
- Onboarding flow: 2-step (user info → concert preferences → Spotify OAuth)
- Backend: User CRUD, Spotify OAuth flow, taste profile builder, Jambase event search, matching engine
- Dashboard: Taste fingerprint display (radar chart + genre bars + genre cloud), location search, concert results list
- Concert cards with match scores, "Why this match?" expandable sections, ticket links
- Loading states with equalizer animation
- All backend modules are modular (matching.py is swappable for future vector embeddings)

### Phase 2 (Feb 12, 2026)
- **Concert Date Filtering**: Calendar date pickers (From/To) in location search using Shadcn Calendar + Popover
- **Favorites/Bookmarking**: Heart button on concert cards, Saved tab in dashboard, full CRUD (add/remove/list)
- **Share My Taste**: Shareable taste profile page at /share/:shareId with radar chart, genre DNA bars, genre tags, and CTA
- **Smart Event Discovery**: Spotify recommendations-based fallback (since Jambase API is enterprise-only). Uses /recommendations endpoint with seed artists and genres, generates venue/date data per city
- **Tabbed Dashboard**: Discover + Saved tabs using Shadcn Tabs
- **Copy to Clipboard**: Share URL copy functionality

## Prioritized Backlog
### P0 (Done)
- [x] User registration + Spotify OAuth
- [x] Taste profile generation
- [x] Event discovery (Spotify-based)
- [x] Matching algorithm
- [x] Dashboard UI
- [x] Concert date filtering
- [x] Favorites/bookmarking
- [x] Share My Taste

### P1 (Next)
- [ ] Connect real events API (Ticketmaster/Songkick) when available
- [ ] Token refresh handling on frontend (auto-reconnect)
- [ ] Pagination for concert results
- [ ] Artist preview audio clips (Spotify 30s previews)

### P2 (Future)
- [ ] Embedding-based matching (NVIDIA NIM / NeMo Retriever)
- [ ] Social features (follow friends' taste profiles)
- [ ] Push notifications for new matching events
- [ ] Multi-city saved searches
- [ ] OG image generation for share cards

## API Note
Jambase API (api.jambase.com) has migrated to enterprise-only access. The app gracefully falls back to Spotify-based discovery. When a real events API key is connected, the system seamlessly switches to real event data.
