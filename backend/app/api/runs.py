from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, status
from fastapi.responses import JSONResponse

from app.db.repository import create_or_get_run, get_run
from app.db.session import SessionLocal
from app.orchestration.run_service import RunOrchestrator, progress_for_status
from app.schemas.errors import ErrorBody, ErrorResponse
from app.schemas.runs import RunCreateResponse, RunStatusResponse

router = APIRouter(prefix="/runs", tags=["runs"])
orchestrator = RunOrchestrator()


def _status_response(run) -> RunStatusResponse:
    report_id = run.report.report_id if run.report is not None else None
    return RunStatusResponse(
        run_id=run.run_id,
        status=run.status,
        progress=progress_for_status(run.status),
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        records_retrieved=run.records_retrieved,
        records_normalized=run.records_normalized,
        records_classified=run.records_classified,
        normalization_errors=run.normalization_errors,
        previous_baseline_available=run.previous_baseline_available,
        report_id=report_id,
        error_code=run.error_code,
    )


def _error_response(code: str, message: str, *, run_id: str | None = None, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, run_id=run_id)).model_dump(mode="json")
    return JSONResponse(status_code=status_code, content=body)


@router.post("", response_model=RunCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> RunCreateResponse | JSONResponse:
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= 255:
        return _error_response(
            "INVALID_IDEMPOTENCY_KEY",
            "Idempotency-Key must be 1 to 255 characters.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    with SessionLocal() as db:
        run, _created = create_or_get_run(db, idempotency_key)
    orchestrator.schedule(run.run_id)
    return RunCreateResponse(run_id=run.run_id, status=run.status, created_at=run.created_at)


@router.get("/{run_id}", response_model=RunStatusResponse, responses={404: {"model": ErrorResponse}})
def get_run_status(run_id: str) -> RunStatusResponse | JSONResponse:
    with SessionLocal() as db:
        run = get_run(db, run_id)
        if run is None:
            return _error_response(
                "RUN_NOT_FOUND",
                "Run was not found.",
                run_id=run_id,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return _status_response(run)
