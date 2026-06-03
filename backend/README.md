# Shorts vs Reels RAG — Backend API

FastAPI backend scaffolding for the YouTube Shorts / Instagram Reels comparison platform.

## Quick start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Start Postgres, Redis, Qdrant locally, then:
.venv\Scripts\alembic.exe upgrade head   # Windows — use venv, not conda
```

### Start the API (Windows)

**Do not run `uvicorn` from conda `(base)`** — you will get `ModuleNotFoundError: qdrant_client` / `asyncpg`.

Use one of:

```powershell
.\start.ps1
# or
.\start.bat
# or
.\scripts\dev.ps1
```

All of these use `backend\.venv\Scripts\uvicorn.exe`.

### Qdrant / Redis without Docker

If Qdrant or Redis are not running, the API **auto-falls back** to in-memory stores (compare + chat still work for local dev). Optional force:

```env
QDRANT_USE_MEMORY=true
REDIS_USE_MEMORY=true
```

Or start Docker services: Qdrant on port `6333`, Redis on `6379`.

Frontend SSE (optional, avoids Next.js proxy buffering):

```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Structure

See architecture doc: `app/` contains API, domain services, DB models, integrations, LangGraph, and workers.

## Primary flow (two URLs)

```http
POST /v1/compare/urls
Content-Type: application/json

{
  "youtube_url": "https://www.youtube.com/shorts/VIDEO_ID",
  "instagram_url": "https://www.instagram.com/reel/SHORTCODE/",
  "query": "Which hook is stronger and why?"
}
```

This will:

1. Extract transcript, creator, views, likes, comments, upload date, hashtags
2. Compute engagement rate
3. Chunk transcript + metadata/hook/hashtags
4. Generate BGE embeddings and store vectors in Qdrant
5. Optionally run compare RAG (if `query` is provided)

## Chat with memory + streaming

```http
POST /v1/chat/sessions
{ "creator_id": "<creator_id from /compare/urls>" }

POST /v1/chat/sessions/{session_id}/messages
{ "message": "Compare hooks with citations" }

GET /v1/runs/{run_id}/stream
```

SSE events: `status`, `token`, `citation`, `done`, `error`.

## Instagram view counts

Instagram **does not expose public Reel view counts** to unauthenticated scrapers (including yt-dlp).
Likes and comments are usually available; views often show as `—`.

Optional env vars (neither is required for the app to run):

| Variable | Purpose |
|----------|---------|
| `INSTAGRAM_COOKIES_FILE` | Path to a Netscape `cookies.txt` exported while logged into [instagram.com](https://www.instagram.com) in your browser. May allow yt-dlp to read `play_count`. |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram **User** access token from [Meta for Developers](https://developers.facebook.com/). Only returns views for Reels **owned by the account connected to that token**, not arbitrary public URLs. |

To create a token (for your own Business/Creator account media only):

1. Go to [developers.facebook.com](https://developers.facebook.com/) → **My Apps** → Create app → type **Business**.
2. Add product **Instagram** → **Instagram API setup** → connect an Instagram Business/Creator account.
3. Generate a **User access token** with `instagram_basic` and `instagram_manage_insights` (or `pages_read_engagement` depending on setup).
4. Paste the token into `INSTAGRAM_ACCESS_TOKEN` in `.env`.

## Requirements

- PostgreSQL, Redis, Qdrant running locally
- `GOOGLE_API_KEY` for grading/generation (retrieval still works without it using score threshold)
- `DEV_AUTH_BYPASS=true` for local development (default)
