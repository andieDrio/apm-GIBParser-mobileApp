from datetime import datetime

from pydantic import BaseModel, Field


class ReportSummary(BaseModel):
    report_id: str
    run_id: str
    status: str
    created_at: datetime
    activity_level: str | None = None
    assessment_confidence: str | None = None
    records_retrieved: int = Field(ge=0)
    new_compromises: int = Field(ge=0)
    pdf_available: bool


class ReportHistoryResponse(BaseModel):
    items: list[ReportSummary]
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class ReportDetailResponse(ReportSummary):
    completed_at: datetime | None = None
