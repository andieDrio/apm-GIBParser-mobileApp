from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ReportModel, ReportRecordModel, RunModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_or_get_run(db: Session, idempotency_key: str | None) -> tuple[RunModel, bool]:
    if idempotency_key:
        existing = db.scalar(select(RunModel).where(RunModel.idempotency_key == idempotency_key))
        if existing:
            return existing, False
    run = RunModel(run_id=str(uuid4()), idempotency_key=idempotency_key, status="QUEUED", created_at=utcnow())
    db.add(run)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key:
            existing = db.scalar(select(RunModel).where(RunModel.idempotency_key == idempotency_key))
            if existing:
                return existing, False
        raise
    db.refresh(run)
    return run, True


def create_run(db: Session, idempotency_key: str | None) -> RunModel:
    return create_or_get_run(db, idempotency_key)[0]


def get_run(db: Session, run_id: str) -> RunModel | None:
    return db.get(RunModel, run_id)


def transition_run(db: Session, run: RunModel, status: str, **fields: object) -> RunModel:
    run.status = status
    for key, value in fields.items():
        setattr(run, key, value)
    db.commit()
    db.refresh(run)
    return run


def reconcile_nonterminal_runs(db: Session) -> int:
    statuses = ("QUEUED", "COLLECTING", "NORMALIZING", "CLASSIFYING", "ASSESSING", "GENERATING_REPORT")
    runs = list(db.scalars(select(RunModel).where(RunModel.status.in_(statuses))))
    now = utcnow()
    for run in runs:
        run.status = "FAILED"
        run.completed_at = now
        run.error_code = "SERVER_RESTARTED"
        run.error_message = "Run was interrupted by backend restart and was not resumed."
    if runs:
        db.commit()
    return len(runs)


def add_report_record(
    db: Session,
    *,
    run_id: str,
    provider: str,
    identity: str,
    classification: str,
    fingerprint: str | None,
    canonical_json: str,
) -> None:
    db.add(
        ReportRecordModel(
            run_id=run_id,
            provider=provider,
            compromise_identity=identity,
            classification=classification,
            observation_fingerprint=fingerprint,
            canonical_json=canonical_json,
        )
    )


def save_report(db: Session, *, run_id: str, report_id: str, pdf_path: str) -> ReportModel:
    report = ReportModel(
        report_id=report_id,
        run_id=run_id,
        status="SUCCEEDED",
        pdf_path=pdf_path,
        created_at=utcnow(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
