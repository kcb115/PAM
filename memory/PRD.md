# PAM - Concert Discovery App PRD

## Original Problem Statement
Build "PAM" - a web app that helps users discover local concerts by independent artists based on their Spotify listening taste profile. NOT about finding concerts by artists they already listen to — it's about building a taste profile and recommending concerts by similar, lesser-known artists they haven't heard yet.

## Architecture
- **Frontend**: React + Tailwind CSS + Shadcn/UI + Framer Motion
- **Backend**: FastAPI (Python) + MongoDB
- **External APIs**: Spotify Web API (OAuth + data), Jambase API (events)
- **Design**: Dark theme "Underground Curator" — amber + teal accents, Syne + Plus Jakarta Sans fonts

## User Personas
1. **Music Explorer** (Primary): 20-40, active Spotify user, attends 1-4 live shows/month, wants to discover new indie artists
2. **Casual Concertgoer**: Occasional show attendee, wants curated recommendations without effort

## Core Requirements (Static)
- Spotify OAuth Authorization Code Flow (server-side tokens)
- Taste profile: weighted genre map + audio features (energy, danceability, valence, acousticness, instrumentalness, tempo)
- Jambase event search with location/radius
- Fuzzy genre matching algorithm (keyword-based root term extraction)
- Exclude known artists, prioritize low-popularity indie artists
- "Why this match?" explanations
- User registration (name, email, concert prefs)

## What's Been Implemented (Feb 12, 2026)
- Landing page with hero, feature cards, animated entrance
- Onboarding flow: 2-step (user info → concert preferences → Spotify OAuth)
- Backend: User CRUD, Spotify OAuth flow, taste profile builder, Jambase event search, matching engine
- Dashboard: Taste fingerprint display (radar chart + genre bars + genre cloud), location search, concert results list
- Concert cards with match scores, "Why this match?" expandable sections, ticket links
- Loading states with equalizer animation
- All backend modules are modular (matching.py is swappable for future vector embeddings)

## Prioritized Backlog
### P0 (Done)
- [x] User registration + Spotify OAuth
- [x] Taste profile generation
- [x] Jambase event search
- [x] Matching algorithm
- [x] Dashboard UI

### P1 (Next)
- [ ] Token refresh handling on frontend (auto-reconnect)
- [ ] Pagination for concert results
- [ ] Save/bookmark favorite concerts
- [ ] Concert date filtering (calendar)

### P2 (Future)
- [ ] Embedding-based matching (NVIDIA NIM / NeMo Retriever)
- [ ] Social features (share discoveries)
- [ ] Push notifications for new matching events
- [ ] Multi-city support
- [ ] Artist preview audio clips

## Next Tasks
1. User tests the Spotify OAuth flow end-to-end with real Spotify account
2. Verify Jambase API responses are parsing correctly for the user's city
3. Add concert date filtering
4. Add favorites/bookmarking
