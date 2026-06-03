"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import (
    domain_error_handler,
    pydantic_validation_handler,
    request_validation_handler,
    unhandled_exception_handler,
)
from app.api.v1.router import api_router
from app.config.logging import configure_logging
from app.config.settings import get_settings
from app.domain.exceptions import DomainError
from app.integrations.qdrant.client import get_qdrant_client
from app.integrations.redis.client import get_redis_client


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    redis = get_redis_client()
    await redis.connect()
    qdrant = get_qdrant_client()
    await qdrant.ensure_collection()
    yield
    await redis.close()
    await qdrant.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
