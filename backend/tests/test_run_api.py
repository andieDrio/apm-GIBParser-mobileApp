from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.runs import orchestrator
from app.db.models import Base
from app.db.repository import create_or_get_run, reconcile_nonterminal_runs
from app.db.session import engine
from app.main import app
from app.orchestration.run_service import progress_for_status


def test_progress_mapping_is_deterministic():
    assert progress_for_status("QUEUED") == 0
    assert progress_for_status("COLLECTING") == 20
    assert progress_for_status("NORMALIZING") == 40
    assert progress_for_status("SUCCEEDED") == 100


def test_reconcile_marks_interrupted_runs_failed(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'reconcile.db'}"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    local_engine = create_engine(db_url)
    Base.metadata.create_all(local_engine)
    LocalSession = sessionmaker(bind=local_engine, autoflush=False, expire_on_commit=False)
    from app.db.models import RunModel
    with LocalSession() as db:
        run = RunModel(run_id="r1", status="COLLECTING", created_at=datetime.now(timezone.utc), started_at=datetime.now(timezone.utc))
        db.add(run)
        db.commit()
        assert reconcile_nonterminal_runs(db) == 1
        db.refresh(run)
        assert run.status == "FAILED"
        assert run.error_code == "SERVER_RESTARTED"


def test_create_run_endpoint_is_idempotent(monkeypatch, tmp_path):
    # Use the real application database only after replacing the scheduler so no network task runs.
    monkeypatch.setattr(orchestrator, "schedule", lambda run_id: None)
    with TestClient(app) as client:
        first = client.post("/api/v1/runs", headers={"Idempotency-Key": "test-run-1"})
        second = client.post("/api/v1/runs", headers={"Idempotency-Key": "test-run-1"})
        assert first.status_code == 202
        assert second.status_code == 202
        assert first.json()["run_id"] == second.json()["run_id"]


def test_run_not_found_is_structured_error():
    with TestClient(app) as client:
        response = client.get("/api/v1/runs/does-not-exist")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "RUN_NOT_FOUND"
