"""Custom exceptions for the ConvertIntoMP4 SDK."""

from typing import Any, Optional


class ConvertIntoMP4Error(Exception):
    """Base exception for all ConvertIntoMP4 SDK errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class ApiError(ConvertIntoMP4Error):
    """Raised when the API returns an error response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.details = details
        super().__init__(f"[{status_code}] {code}: {message}")


class AuthenticationError(ApiError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Invalid or missing API key") -> None:
        super().__init__(401, "AUTHENTICATION_ERROR", message)


class RateLimitError(ApiError):
    """Raised when the rate limit is exceeded (429)."""

    def __init__(self, retry_after: Optional[int] = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after:
            msg += f". Retry after {retry_after} seconds"
        super().__init__(429, "RATE_LIMIT_EXCEEDED", msg)


class NotFoundError(ApiError):
    """Raised when a resource is not found (404)."""

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: str = "",
        message: "str | None" = None,
        code: str = "NOT_FOUND",
    ) -> None:
        msg = message or f"{resource} not found"
        if resource_id and not message:
            msg += f": {resource_id}"
        super().__init__(404, code, msg)


class ValidationError(ApiError):
    """Raised when request validation fails (400)."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(400, "VALIDATION_ERROR", message, details)


class TimeoutError(ConvertIntoMP4Error):
    """Raised when an operation times out."""

    def __init__(self, message: str = "Operation timed out") -> None:
        super().__init__(message)
