from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    QUEUED = "QUEUED"
    COLLECTING = "COLLECTING"
    NORMALIZING = "NORMALIZING"
    CLASSIFYING = "CLASSIFYING"
    ASSESSING = "ASSESSING"
    GENERATING_REPORT = "GENERATING_REPORT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class RunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus
    created_at: datetime


class RunStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    progress: int = Field(ge=0, le=100)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    records_retrieved: int = Field(ge=0)
    records_normalized: int = Field(ge=0)
    records_classified: int = Field(ge=0)
    normalization_errors: int = Field(ge=0)
    previous_baseline_available: bool
    report_id: str | None = None
    error_code: str | None = None
