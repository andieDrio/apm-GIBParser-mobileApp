import json
from datetime import datetime, timezone
from pathlib import Path

from app.db.init_db import init_db
from app.db.models import AssessmentModel, Base, ReportRecordModel, RunModel
from app.db.session import SessionLocal, engine
from app.reporting.pdf import generate_report


def _record():
    return {
        "provider": "groupib",
        "provider_record_id": "gib-1",
        "compromise_identity": "provider:gib-1",
        "account": "analyst@example.com",
        "username": "analyst@example.com",
        "password": "Operational-Password-123!",
        "victim_domain": "example.com",
        "compromised_date": "2026-09-28T10:00:00+00:00",
        "last_compromised_date": "2026-09-28T10:00:00+00:00",
        "date_detected": "2026-09-28T11:00:00+00:00",
        "first_seen": "2026-09-28T11:00:00+00:00",
        "last_seen": "2026-09-28T11:00:00+00:00",
        "event_count": 1,
        "stealer_families": ["RedLine"],
        "malware_ids": ["redline"],
        "victim_ips": ["192.0.2.10"],
        "victim_countries": ["PH"],
        "victim_cities": ["Manila"],
        "victim_providers": ["Example ISP"],
        "target_urls": [],
        "source_types": ["infostealer"],
        "source_ids": ["src-1"],
        "source_names": ["Group-IB"],
        "source_links": ["https://example.com/source/1"],
        "threat_actors": ["ExampleActor"],
        "service_domain": "example.com",
        "service_host": "login.example.com",
        "service_url": "https://login.example.com",
        "login_url": "https://login.example.com",
        "event_ids": ["event-1"],
        "credential_present": True,
        "observation_fingerprint": "sha256:" + "a" * 64,
        "warnings": [],
    }


def test_generates_pdf_and_persists_artifact(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Base.metadata.drop_all(bind=engine)
    init_db()
    with SessionLocal() as db:
        run = RunModel(
            run_id="run-pdf-1", status="GENERATING_REPORT",
            created_at=datetime.now(timezone.utc), records_retrieved=1,
            records_normalized=1, records_classified=1,
        )
        db.add(run)
        db.add(AssessmentModel(
            assessment_id="assessment-1", run_id=run.run_id, activity_level="LOW", confidence="HIGH",
            facts_json=json.dumps(["Records evaluated: 1"]), observations_json=json.dumps(["Observed NEW activity"]),
            assessment="The run identified 1 NEW compromise record.",
            recommended_attention_json=json.dumps(["Review the account."]),
            basis_json=json.dumps(["Deterministic rules only."]),
        ))
        db.add(ReportRecordModel(
            run_id=run.run_id, provider="groupib", compromise_identity="provider:gib-1",
            classification="NEW", observation_fingerprint="sha256:" + "a" * 64,
            canonical_json=json.dumps(_record()),
        ))
        db.commit()
        report_id, path = generate_report(db, run)
        assert report_id
        assert Path(path).exists()
        payload = Path(path).read_bytes()
        assert payload.startswith(b"%PDF")
        assert b"Operational-Password-123!" in payload
        assert b"Group-IB" in payload


def test_report_generation_fails_without_assessment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Base.metadata.drop_all(bind=engine)
    init_db()
    with SessionLocal() as db:
        run = RunModel(run_id="run-pdf-2", status="GENERATING_REPORT", created_at=datetime.now(timezone.utc))
        db.add(run)
        db.commit()
        try:
            generate_report(db, run)
        except ValueError as exc:
            assert str(exc) == "Assessment is required before PDF generation."
        else:
            raise AssertionError("Expected missing-assessment failure.")
