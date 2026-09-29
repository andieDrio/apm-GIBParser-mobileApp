from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.runs import orchestrator
from app.db.models import Base, ReportModel, RunModel
from app.db.session import SessionLocal, engine
from app.main import app
from app.orchestration.run_service import RunOrchestrator
import app.api.reports as reports_api
import app.reporting.pdf as pdf_reporting


def _reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _provider_record(*, now: datetime, password: str = "e2e-operational-password") -> dict:
    timestamp = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "id": "gib-e2e-1",
        "login": "e2e-user@example.com",
        "password": password,
        "parsedLogin": {"domain": "example.com"},
        "dateFirstCompromised": timestamp,
        "dateLastCompromised": timestamp,
        "dateDetected": timestamp,
        "dateFirstSeen": timestamp,
        "dateLastSeen": timestamp,
        "eventCount": 1,
        "sourceType": ["infostealer"],
        "source": [{"id": "src-e2e-1", "name": "Group-IB", "url": "https://example.test/source/1"}],
        "malware": [{"id": "stealer-1", "name": "TestStealer"}],
        "threatActor": ["TestActor"],
        "service": {"domain": "example.com", "host": "login.example.com", "url": "https://login.example.com"},
        "events": [
            {
                "id": "event-e2e-1",
                "client": {
                    "ipv4": {
                        "ip": "192.0.2.20",
                        "countryName": "PH",
                        "city": "Manila",
                        "provider": "Example ISP",
                    }
                },
            }
        ],
    }


class FakeGroupIBClient:
    def __init__(self, username: str, api_token: str, *, base_url: str, timeout_seconds: float) -> None:
        assert username == "e2e-user"
        assert api_token == "e2e-token"

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def get_account_group_page(self, *, date_from: str, date_to: str, limit: int = 500, result_id: str | None = None):
        from app.groupib.client import AccountGroupPage

        return AccountGroupPage(
            count=1,
            result_id=None,
            items=(_provider_record(now=datetime.now(timezone.utc)),),
        )


def _run_success(tmp_path, monkeypatch) -> tuple[str, str]:
    _reset_db()
    monkeypatch.setattr("app.core.config.settings.group_ib_username", "e2e-user")
    monkeypatch.setattr("app.core.config.settings.group_ib_api_token", "e2e-token")
    monkeypatch.setattr("app.core.config.settings.group_ib_latest_lookback_days", 7)
    monkeypatch.setattr("app.reporting.pdf.REPORT_ROOT", tmp_path)
    monkeypatch.setattr("app.api.reports.REPORT_ROOT", tmp_path)

    run_orchestrator = RunOrchestrator(client_factory=FakeGroupIBClient)
    with SessionLocal() as db:
        run = RunModel(
            run_id="run-e2e-success",
            status="QUEUED",
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()

    run_orchestrator._execute_sync(run.run_id)

    with SessionLocal() as db:
        persisted = db.get(RunModel, run.run_id)
        assert persisted is not None
        assert persisted.status == "SUCCEEDED"
        assert persisted.report is not None
        assert persisted.report.pdf_path is not None
        assert Path(persisted.report.pdf_path).is_file()
        return persisted.run_id, persisted.report.report_id


def test_full_run_produces_authoritative_report_and_download(tmp_path, monkeypatch):
    run_id, report_id = _run_success(tmp_path, monkeypatch)

    with TestClient(app) as client:
        run_response = client.get(f"/api/v1/runs/{run_id}")
        assert run_response.status_code == 200
        run_payload = run_response.json()
        assert run_payload["status"] == "SUCCEEDED"
        assert run_payload["progress"] == 100
        assert run_payload["records_retrieved"] == 1
        assert run_payload["records_normalized"] == 1
        assert run_payload["records_classified"] == 1
        assert run_payload["report_id"] == report_id

        latest = client.get("/api/v1/reports/latest")
        assert latest.status_code == 200
        assert latest.json()["report_id"] == report_id
        assert latest.json()["new_compromises"] == 1

        download = client.get(f"/api/v1/reports/{report_id}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/pdf")
        assert download.content.startswith(b"%PDF")


def test_repeat_execution_classifies_same_observation_as_repeat(tmp_path, monkeypatch):
    _reset_db()
    monkeypatch.setattr("app.core.config.settings.group_ib_username", "e2e-user")
    monkeypatch.setattr("app.core.config.settings.group_ib_api_token", "e2e-token")
    monkeypatch.setattr("app.reporting.pdf.REPORT_ROOT", tmp_path)

    class StableFakeClient(FakeGroupIBClient):
        def get_account_group_page(self, **_kwargs):
            from app.groupib.client import AccountGroupPage

            return AccountGroupPage(
                count=1,
                result_id=None,
                items=(_provider_record(now=datetime.now(timezone.utc)),),
            )

    run_orchestrator = RunOrchestrator(client_factory=StableFakeClient)
    for run_id in ("run-e2e-repeat-1", "run-e2e-repeat-2"):
        with SessionLocal() as db:
            db.add(RunModel(
                run_id=run_id,
                status="QUEUED",
                created_at=datetime.now(timezone.utc),
            ))
            db.commit()
        run_orchestrator._execute_sync(run_id)

    with SessionLocal() as db:
        first = db.get(RunModel, "run-e2e-repeat-1")
        second = db.get(RunModel, "run-e2e-repeat-2")
        assert first is not None and second is not None
        assert first.status == "SUCCEEDED"
        assert second.status == "SUCCEEDED"
        classifications = [row.classification for row in second.report_records]
        assert classifications == ["REPEAT"]
        assert second.previous_baseline_available is True


def test_authentication_failure_never_becomes_success(monkeypatch, tmp_path):
    _reset_db()
    monkeypatch.setattr("app.core.config.settings.group_ib_username", "e2e-user")
    monkeypatch.setattr("app.core.config.settings.group_ib_api_token", "e2e-token")
    monkeypatch.setattr("app.reporting.pdf.REPORT_ROOT", tmp_path)

    from app.groupib.client import AccountGroupPage, GroupIBAuthenticationError

    class AuthFailClient(FakeGroupIBClient):
        def get_account_group_page(self, **_kwargs) -> AccountGroupPage:
            raise GroupIBAuthenticationError("Unable to authenticate with Group-IB.")

    with SessionLocal() as db:
        db.add(RunModel(
            run_id="run-e2e-auth-fail",
            status="QUEUED",
            created_at=datetime.now(timezone.utc),
        ))
        db.commit()

    RunOrchestrator(client_factory=AuthFailClient)._execute_sync("run-e2e-auth-fail")

    with SessionLocal() as db:
        run = db.get(RunModel, "run-e2e-auth-fail")
        assert run is not None
        assert run.status == "FAILED"
        assert run.error_code == "GROUPIB_AUTH_FAILED"
        assert run.report is None


def test_malformed_provider_response_never_reaches_classification(monkeypatch, tmp_path):
    _reset_db()
    monkeypatch.setattr("app.core.config.settings.group_ib_username", "e2e-user")
    monkeypatch.setattr("app.core.config.settings.group_ib_api_token", "e2e-token")
    monkeypatch.setattr("app.reporting.pdf.REPORT_ROOT", tmp_path)

    from app.groupib.client import AccountGroupPage, GroupIBSchemaError

    class SchemaFailClient(FakeGroupIBClient):
        def get_account_group_page(self, **_kwargs) -> AccountGroupPage:
            raise GroupIBSchemaError("Group-IB response field 'items' must be an array of objects.")

    with SessionLocal() as db:
        db.add(RunModel(
            run_id="run-e2e-schema-fail",
            status="QUEUED",
            created_at=datetime.now(timezone.utc),
        ))
        db.commit()

    RunOrchestrator(client_factory=SchemaFailClient)._execute_sync("run-e2e-schema-fail")

    with SessionLocal() as db:
        run = db.get(RunModel, "run-e2e-schema-fail")
        assert run is not None
        assert run.status == "FAILED"
        assert run.error_code == "GROUPIB_INVALID_RESPONSE"
        assert run.report is None
