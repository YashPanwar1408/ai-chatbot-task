"""Map domain exceptions to HTTP responses."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
    NotImplementedFeatureError,
    QuotaExceededError,
    ValidationError,
)


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

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message, "code": exc.code},
    )
