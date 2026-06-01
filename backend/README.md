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
alembic upgrade head
uvicorn app.main:app --reload
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

## Requirements

- PostgreSQL, Redis, Qdrant running locally
- `GOOGLE_API_KEY` for grading/generation (retrieval still works without it using score threshold)
- `DEV_AUTH_BYPASS=true` for local development (default)
