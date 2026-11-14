"""Type definitions for the ConvertIntoMP4 SDK."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union


# ============================================================================
# Enums as Literals
# ============================================================================

JobStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
TaskStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
FormatCategory = Literal["video", "audio", "image", "document"]


# ============================================================================
# Task Result
# ============================================================================


class TaskResultFile(TypedDict, total=False):
    name: str
    size: int
    mime_type: str


class TaskResult(TypedDict, total=False):
    file: TaskResultFile
    url: str
    expires_at: str


# ============================================================================
# Core Models (dataclasses for mutable state)
# ============================================================================


@dataclass
class Task:
    """Represents a single task within a job."""

    id: str
    operation: str
    status: TaskStatus
    progress: float = 0
    input: Optional[str] = None
    result: Optional[TaskResult] = None
    error: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            id=data.get("id", ""),
            operation=data.get("operation", ""),
            status=data.get("status", "pending"),
            progress=data.get("progress", 0),
            input=data.get("input"),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class Job:
    """Represents a conversion job."""

    id: str
    status: JobStatus
    tag: Optional[str] = None
    webhook_url: Optional[str] = None
    tasks: Dict[str, Task] = field(default_factory=dict)
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        tasks = {}
        for name, task_data in data.get("tasks", {}).items():
            tasks[name] = Task.from_dict(task_data)
        return cls(
            id=data.get("id", ""),
            status=data.get("status", "pending"),
            tag=data.get("tag"),
            webhook_url=data.get("webhook_url"),
            tasks=tasks,
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


@dataclass
class Format:
    """Represents a file format supported by the API."""

    id: str
    name: str
    category: FormatCategory
    extension: str
    mime_types: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Format":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=data.get("category", "video"),
            extension=data.get("extension", ""),
            mime_types=data.get("mime_types", []),
        )


@dataclass
class FormatOption:
    """Represents a conversion option for a format pair."""

    name: str
    type: str
    description: str
    enum: Optional[List[str]] = None
    default: Optional[Union[str, int, float, bool]] = None
    min: Optional[float] = None
    max: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FormatOption":
        return cls(
            name=data.get("name", ""),
            type=data.get("type", "string"),
            description=data.get("description", ""),
            enum=data.get("enum"),
            default=data.get("default"),
            min=data.get("min"),
            max=data.get("max"),
        )


@dataclass
class Webhook:
    """Represents a webhook subscription."""

    id: str
    url: str
    events: List[str]
    active: bool = True
    secret: Optional[str] = None
    created_at: str = ""
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Webhook":
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            events=data.get("events", []),
            active=data.get("active", True),
            secret=data.get("secret"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata"),
        )


# ============================================================================
# Request TypedDicts
# ============================================================================


class ConversionOptions(TypedDict, total=False):
    """Options for file conversion."""

    quality: str
    resolution: str
    codec: str
    fps: int
    bitrate: str
    crf: int
    preset: str
    profile: str
    level: str
    pixel_format: str
    audio_codec: str
    audio_bitrate: str
    audio_channels: int
    audio_sample_rate: str
    audio_normalize: bool
    width: int
    height: int
    fit: str
    dpi: int
    strip_metadata: bool
    auto_orient: bool
    progressive: bool
    lossless: bool
    background: str
    pdf_quality: str
    password: str
    pages: str


class WaitOptions(TypedDict, total=False):
    """Options for waiting on a job."""

    interval: float
    timeout: float


class PdfPermissions(TypedDict, total=False):
    """PDF encryption permissions."""

    printing: bool
    copying: bool
    modifying: bool


@dataclass
class PdfOperationResult:
    """Result of a PDF operation."""

    url: str
    file_size: int = 0
    page_count: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PdfOperationResult":
        return cls(
            url=data.get("url", ""),
            file_size=data.get("file_size", 0),
            page_count=data.get("page_count"),
        )
