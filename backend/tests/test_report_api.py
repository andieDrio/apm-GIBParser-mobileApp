from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.db.models import Base, ReportModel, ReportRecordModel, RunModel
from app.db.session import SessionLocal, engine
from app.main import app


def _seed_report(pdf_path: str) -> str:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        run = RunModel(
            run_id="run-a12-1",
            status="SUCCEEDED",
            created_at=datetime(2026, 9, 29, 1, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 9, 29, 1, 2, tzinfo=timezone.utc),
            records_retrieved=2,
            records_normalized=2,
            records_classified=2,
        )
        report = ReportModel(
            report_id="report-a12-1",
            run_id=run.run_id,
            status="SUCCEEDED",
            pdf_path=pdf_path,
            created_at=datetime(2026, 9, 29, 1, 2, tzinfo=timezone.utc),
        )
        db.add(run)
        db.add(report)
        db.add_all([
            ReportRecordModel(
                run_id=run.run_id,
                provider="groupib",
                compromise_identity="provider:gib-1",
                classification="NEW",
                observation_fingerprint="sha256:" + "a" * 64,
                canonical_json="{}",
            ),
            ReportRecordModel(
                run_id=run.run_id,
                provider="groupib",
                compromise_identity="provider:gib-2",
                classification="OLD_HISTORICAL",
                observation_fingerprint="sha256:" + "b" * 64,
                canonical_json="{}",
            ),
        ])
        db.commit()
    return report.report_id


def test_report_history_and_latest(monkeypatch, tmp_path):
    pdf = tmp_path / "report-a12-1.pdf"
    pdf.write_bytes(b"%PDF-test")
    report_id = _seed_report(str(pdf))
    monkeypatch.setattr("app.api.reports.REPORT_ROOT", tmp_path)

    with TestClient(app) as client:
        latest = client.get("/api/v1/reports/latest")
        assert latest.status_code == 200
        assert latest.json()["report_id"] == report_id
        assert latest.json()["new_compromises"] == 1
        assert latest.json()["pdf_available"] is True

        history = client.get("/api/v1/reports/history?limit=10")
        assert history.status_code == 200
        assert [item["report_id"] for item in history.json()["items"]] == [report_id]


def test_report_detail_and_download(monkeypatch, tmp_path):
    pdf = tmp_path / "report-a12-1.pdf"
    pdf.write_bytes(b"%PDF-test")
    report_id = _seed_report(str(pdf))
    monkeypatch.setattr("app.api.reports.REPORT_ROOT", tmp_path)

    with TestClient(app) as client:
        detail = client.get(f"/api/v1/reports/{report_id}")
        assert detail.status_code == 200
        assert detail.json()["run_id"] == "run-a12-1"

        download = client.get(f"/api/v1/reports/{report_id}/download")
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/pdf")
        assert download.content == b"%PDF-test"


def test_missing_report_returns_structured_error():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        response = client.get("/api/v1/reports/missing-report")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "REPORT_NOT_FOUND"
        assert response.json()["error"]["report_id"] == "missing-report"
