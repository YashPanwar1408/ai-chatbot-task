"""API v1 route aggregator."""

from fastapi import APIRouter

from app.api.v1 import chat, compare, content, creators, health, ingest, jobs, runs, usage

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(creators.router, prefix="/creators", tags=["creators"])
api_router.include_router(content.router, tags=["content"])
api_router.include_router(ingest.router, tags=["ingest"])
api_router.include_router(compare.router, prefix="/compare", tags=["compare"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(runs.router, prefix="/runs", tags=["runs"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
