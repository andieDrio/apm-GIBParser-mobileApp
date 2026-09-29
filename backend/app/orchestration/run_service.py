from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable

from app.core.config import settings
from app.db.assessment import save_assessment
from app.db.history import classify_and_persist, get_history
from app.db.repository import get_run, save_report, transition_run
from app.db.session import SessionLocal
from app.domain.assessment import build_assessment
from app.domain.classification import Classification
from app.domain.normalization import normalize_records
from app.groupib.client import (
    GroupIBAuthenticationError, GroupIBClient, GroupIBConfigurationError,
    GroupIBRateLimitError, GroupIBSchemaError, GroupIBUnavailableError,
)
from app.reporting.pdf import generate_report

TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "PARTIAL"}
PROGRESS = {"QUEUED": 0, "COLLECTING": 20, "NORMALIZING": 40, "CLASSIFYING": 60,
            "ASSESSING": 75, "GENERATING_REPORT": 90, "SUCCEEDED": 100, "FAILED": 100, "PARTIAL": 100}


class RunOrchestrator:
    """In-process executor; durable SQLite run state remains authoritative."""

    def __init__(self, client_factory: Callable[..., GroupIBClient] = GroupIBClient) -> None:
        self._client_factory = client_factory
        self._active: set[str] = set()
        self._lock = Lock()

    def schedule(self, run_id: str) -> None:
        with self._lock:
            if run_id in self._active:
                return
            self._active.add(run_id)
        task = asyncio.create_task(self.execute(run_id))
        task.add_done_callback(lambda _: self._release(run_id))

    def _release(self, run_id: str) -> None:
        with self._lock:
            self._active.discard(run_id)

    async def execute(self, run_id: str) -> None:
        await asyncio.to_thread(self._execute_sync, run_id)

    def _execute_sync(self, run_id: str) -> None:
        with SessionLocal() as db:
            run = get_run(db, run_id)
            if run is None or run.status in TERMINAL_STATUSES:
                return
            now = datetime.now(timezone.utc)
            transition_run(db, run, "COLLECTING", started_at=run.started_at or now,
                           error_code=None, error_message=None)
            try:
                items = self._collect_with_retry()
                run = get_run(db, run_id)
                if run is None:
                    return
                transition_run(db, run, "NORMALIZING", records_retrieved=len(items))

                records = normalize_records(items, provider="groupib")
                warnings = sum(len(record.warnings) for record in records)
                run = get_run(db, run_id)
                if run is None:
                    return
                transition_run(db, run, "CLASSIFYING", records_normalized=len(records),
                               normalization_errors=warnings)

                observed_at = datetime.now(timezone.utc)
                baseline_available = False
                classified: list[tuple[object, Classification, str]] = []
                for record in records:
                    if get_history(db, record.provider, record.compromise_identity) is not None:
                        baseline_available = True
                    classification, reason = classify_and_persist(
                        db, record, observed_at=observed_at, newness_window_days=7, run_id=run_id)
                    classified.append((record, classification, reason))
                db.commit()

                run = get_run(db, run_id)
                if run is None:
                    return
                transition_run(db, run, "ASSESSING",
                               records_classified=len(classified),
                               previous_baseline_available=baseline_available)

                assessment = build_assessment(
                    run_id=run_id,
                    records=[item[0] for item in classified],
                    classifications=[item[1] for item in classified],
                    normalization_warnings=warnings,
                    baseline_available=baseline_available,
                    evaluated_at=observed_at,
                )
                save_assessment(db, assessment)
                db.commit()

                run = get_run(db, run_id)
                if run is None:
                    return
                transition_run(db, run, "GENERATING_REPORT")

                report_id, pdf_path = generate_report(db, run)
                save_report(db, run_id=run_id, report_id=report_id, pdf_path=pdf_path)
                run = get_run(db, run_id)
                if run is None:
                    return
                transition_run(db, run, "SUCCEEDED", completed_at=datetime.now(timezone.utc),
                               error_code=None, error_message=None)
            except GroupIBConfigurationError as exc:
                self._fail(db, run_id, "GROUPIB_NOT_CONFIGURED", str(exc))
            except GroupIBAuthenticationError as exc:
                self._fail(db, run_id, "GROUPIB_AUTH_FAILED", str(exc))
            except GroupIBRateLimitError as exc:
                self._fail(db, run_id, "GROUPIB_RATE_LIMITED", str(exc))
            except GroupIBSchemaError as exc:
                self._fail(db, run_id, "GROUPIB_INVALID_RESPONSE", str(exc))
            except GroupIBUnavailableError as exc:
                self._fail(db, run_id, "GROUPIB_UNAVAILABLE", str(exc))
            except Exception:
                self._fail(db, run_id, "REPORT_GENERATION_FAILED", "Run execution failed during report generation.")

    def _collect_with_retry(self) -> list[dict]:
        last_error: GroupIBUnavailableError | None = None
        for attempt in range(3):
            try:
                return self._collect_once()
            except GroupIBUnavailableError as exc:
                last_error = exc
                if attempt == 2:
                    raise
                time.sleep(0.5 * (2 ** attempt))
        assert last_error is not None
        raise last_error

    def _collect_once(self) -> list[dict]:
        username = settings.group_ib_username
        token = settings.group_ib_api_token.get_secret_value() if settings.group_ib_api_token else None
        with self._client_factory(username or "", token or "", base_url=settings.group_ib_base_url,
                                  timeout_seconds=settings.request_timeout_seconds) as client:
            evaluated_at = datetime.now(timezone.utc)
            date_from = (evaluated_at - timedelta(days=settings.group_ib_latest_lookback_days)).date().isoformat()
            date_to = evaluated_at.date().isoformat()
            result_id: str | None = None
            seen_result_ids: set[str] = set()
            items: list[dict] = []
            while True:
                page = client.get_account_group_page(date_from=date_from, date_to=date_to,
                                                     limit=500, result_id=result_id)
                items.extend(dict(item) for item in page.items)
                if page.result_id is None:
                    return items
                if page.result_id in seen_result_ids or page.result_id == result_id:
                    raise GroupIBSchemaError("Group-IB pagination returned a repeated resultId.")
                seen_result_ids.add(page.result_id)
                result_id = page.result_id

    def _fail(self, db, run_id: str, code: str, message: str) -> None:
        run = get_run(db, run_id)
        if run is None:
            return
        transition_run(db, run, "FAILED", completed_at=datetime.now(timezone.utc),
                       error_code=code, error_message=message)


def progress_for_status(status: str) -> int:
    return PROGRESS.get(status, 0)
