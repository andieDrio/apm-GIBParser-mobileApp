from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Query, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select

from app.db.models import AssessmentModel, ReportModel, ReportRecordModel, RunModel
from app.db.session import SessionLocal
from app.reporting.pdf import REPORT_ROOT
from app.schemas.errors import ErrorBody, ErrorResponse
from app.schemas.reports import ReportDetailResponse, ReportHistoryResponse, ReportSummary

router = APIRouter(prefix="/reports", tags=["reports"])


def _error_response(code: str, message: str, *, report_id: str | None = None, status_code: int) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, report_id=report_id)
    ).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


def _summary(db, report: ReportModel) -> ReportSummary:
    run = db.get(RunModel, report.run_id)
    assessment = db.scalar(select(AssessmentModel).where(AssessmentModel.run_id == report.run_id))
    new_count = db.scalar(
        select(func.count())
        .select_from(ReportRecordModel)
        .where(
            ReportRecordModel.run_id == report.run_id,
            ReportRecordModel.classification == "NEW",
        )
    ) or 0
    pdf_available = bool(report.pdf_path and Path(report.pdf_path).is_file())
    return ReportSummary(
        report_id=report.report_id,
        run_id=report.run_id,
        status=report.status,
        created_at=report.created_at,
        activity_level=assessment.activity_level if assessment else None,
        assessment_confidence=assessment.confidence if assessment else None,
        records_retrieved=run.records_retrieved if run else 0,
        new_compromises=new_count,
        pdf_available=pdf_available,
    )


@router.get("/latest", response_model=ReportDetailResponse, responses={404: {"model": ErrorResponse}})
def get_latest_report() -> ReportDetailResponse | JSONResponse:
    with SessionLocal() as db:
        report = db.scalar(
            select(ReportModel)
            .where(ReportModel.status == "SUCCEEDED")
            .order_by(ReportModel.created_at.desc())
            .limit(1)
        )
        if report is None:
            return _error_response(
                "REPORT_NOT_FOUND",
                "No successful report was found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        summary = _summary(db, report)
        run = db.get(RunModel, report.run_id)
        return ReportDetailResponse(**summary.model_dump(), completed_at=run.completed_at if run else None)


@router.get("/history", response_model=ReportHistoryResponse)
def get_report_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ReportHistoryResponse:
    with SessionLocal() as db:
        reports = list(
            db.scalars(
                select(ReportModel)
                .where(ReportModel.status == "SUCCEEDED")
                .order_by(ReportModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        )
        return ReportHistoryResponse(
            items=[_summary(db, report) for report in reports],
            limit=limit,
            offset=offset,
        )


@router.get("/{report_id}", response_model=ReportDetailResponse, responses={404: {"model": ErrorResponse}})
def get_report(report_id: str) -> ReportDetailResponse | JSONResponse:
    with SessionLocal() as db:
        report = db.get(ReportModel, report_id)
        if report is None or report.status != "SUCCEEDED":
            return _error_response(
                "REPORT_NOT_FOUND",
                "Report was not found.",
                report_id=report_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        summary = _summary(db, report)
        run = db.get(RunModel, report.run_id)
        return ReportDetailResponse(**summary.model_dump(), completed_at=run.completed_at if run else None)


@router.get("/{report_id}/download", response_model=None, responses={404: {"model": ErrorResponse}})
def download_report(report_id: str) -> FileResponse | JSONResponse:
    with SessionLocal() as db:
        report = db.get(ReportModel, report_id)
        if report is None or report.status != "SUCCEEDED":
            return _error_response(
                "REPORT_NOT_FOUND",
                "Report was not found.",
                report_id=report_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        if not report.pdf_path:
            return _error_response(
                "REPORT_ARTIFACT_NOT_FOUND",
                "Report PDF artifact was not found.",
                report_id=report_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        root = REPORT_ROOT.resolve()
        artifact = Path(report.pdf_path).resolve()
        if root not in artifact.parents or not artifact.is_file():
            return _error_response(
                "REPORT_ARTIFACT_NOT_FOUND",
                "Report PDF artifact was not found.",
                report_id=report_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            artifact,
            media_type="application/pdf",
            filename=f"{report.report_id}.pdf",
        )
