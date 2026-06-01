"""Domain and HTTP-layer exceptions."""


class DomainError(Exception):
    """Base domain exception."""

    def __init__(self, message: str, code: str = "domain_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(f"{resource} not found: {identifier}", code="not_found")


class ConflictError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="conflict")


class ValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class QuotaExceededError(DomainError):
    def __init__(self, message: str = "Daily quota exceeded") -> None:
        super().__init__(message, code="quota_exceeded")


class IntegrationError(DomainError):
    def __init__(self, service: str, message: str) -> None:
        super().__init__(f"{service}: {message}", code="integration_error")


class NotImplementedFeatureError(DomainError):
    def __init__(self, feature: str) -> None:
        super().__init__(f"Feature not implemented: {feature}", code="not_implemented")
