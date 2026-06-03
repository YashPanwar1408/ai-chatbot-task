"""Map domain and framework exceptions to HTTP responses."""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError as PydanticValidationError

from app.domain.exceptions import (
    ConflictError,
    DomainError,
    IntegrationError,
    NotFoundError,
    NotImplementedFeatureError,
    QuotaExceededError,
    ValidationError,
)

logger = logging.getLogger(__name__)


async def domain_error_handler(_request: Request, exc: DomainError) -> JSONResponse:
    status_code = 400
    if isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, ConflictError):
        status_code = 409
    elif isinstance(exc, QuotaExceededError):
        status_code = 429
    elif isinstance(exc, NotImplementedFeatureError):
        status_code = 501
    elif isinstance(exc, ValidationError):
        status_code = 422
    elif isinstance(exc, IntegrationError):
        status_code = 503

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )


async def pydantic_validation_handler(
    _request: Request, exc: PydanticValidationError
) -> JSONResponse:
    logger.exception("Response validation failed")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal response validation error",
            "code": "response_validation_error",
        },
    )


async def request_validation_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "code": "request_validation_error"},
    )


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, StarletteHTTPException):
        raise exc
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "internal_error"},
    )
