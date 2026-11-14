"""ConvertIntoMP4 - Official Python SDK for the ConvertIntoMP4 file conversion API."""

from .client import Client
from .exceptions import (
    ApiError,
    AuthenticationError,
    ConvertIntoMP4Error,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from .webhooks import verify_job_webhook
from .types import (
    ConversionOptions,
    Format,
    FormatOption,
    Job,
    PdfOperationResult,
    PdfPermissions,
    Task,
    TaskResult,
    TaskResultFile,
    WaitOptions,
    Webhook,
)

__version__ = "1.0.0"

__all__ = [
    "Client",
    "verify_job_webhook",
    "ApiError",
    "AuthenticationError",
    "ConvertIntoMP4Error",
    "NotFoundError",
    "RateLimitError",
    "TimeoutError",
    "ValidationError",
    "ConversionOptions",
    "Format",
    "FormatOption",
    "Job",
    "PdfOperationResult",
    "PdfPermissions",
    "Task",
    "TaskResult",
    "TaskResultFile",
    "WaitOptions",
    "Webhook",
]
