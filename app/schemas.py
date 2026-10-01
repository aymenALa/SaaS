from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Metrics(BaseModel):
    faces_detected: int = 0
    faces_protected: int = 0
    protected_fraction: float = Field(0, ge=0, le=1)
    mean_absolute_change: float = 0
    psnr_db: float | None = None
    backend: str
    device: str
    detector_reports: list[dict] = []
    transform: str = "pixelate"
    elapsed_ms: float | None = None
    cpu_ms: float | None = None
    peak_memory_kb: float | None = None
    baseline: dict | None = None
    manifest: dict | None = None
    verification: dict | None = None
    limitation: str = "Protection is not guaranteed against every detector or recognition system."


class Job(BaseModel):
    id: str
    status: JobStatus
    filename: str
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    metrics: Metrics | None = None
