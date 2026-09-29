from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.history import classify_and_persist
from app.db.models import Base, CompromiseHistoryModel, ObservationModel, ProviderRecordModel, ReportRecordModel
from app.domain.classification import Classification
from app.domain.normalization import normalize_record


def test_classification_persists_new_and_repeat_without_password_fingerprint(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'a9.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    item = {
        "id": "record-1", "login": "user@example.test",
        "parsedLogin": {"domain": "example.test"},
        "dateFirstCompromised": "2026-09-28T08:00:00Z",
        "dateDetected": "2026-09-28T09:00:00Z",
        "dateFirstSeen": "2026-09-28T08:00:00Z",
        "dateLastSeen": "2026-09-28T08:00:00Z",
        "password": "secret", "events": [],
    }
    record = normalize_record(item)
    observed = datetime(2026, 9, 29, 8, tzinfo=timezone.utc)
    with Session() as db:
        first, _ = classify_and_persist(db, record, observed_at=observed, run_id="run-1")
        db.commit()
        assert first is Classification.NEW
        assert db.scalar(select(CompromiseHistoryModel)).last_classification == "NEW"
        assert db.scalar(select(ProviderRecordModel)) is not None
        assert db.scalar(select(ObservationModel)) is not None
        assert db.scalar(select(ReportRecordModel)) is not None
        second, _ = classify_and_persist(db, record, observed_at=observed, run_id="run-2")
        assert second is Classification.REPEAT
        db.commit()
        assert len(db.scalars(select(CompromiseHistoryModel)).all()) == 1


def test_old_future_and_missing_timeline_are_not_new(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'a9-b.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    observed = datetime(2026, 9, 29, tzinfo=timezone.utc)
    cases = [
        ("old", "2026-09-01T00:00:00Z", Classification.OLD_HISTORICAL),
        ("future", "2026-10-01T00:00:00Z", Classification.OLD_HISTORICAL),
        ("missing", None, Classification.OLD_HISTORICAL),
    ]
    with Session() as db:
        for ident, date, expected in cases:
            item = {"id": ident, "login": f"{ident}@example.test",
                    "parsedLogin": {"domain": "example.test"}, "events": []}
            if date: item["dateFirstCompromised"] = date
            record = normalize_record(item)
            result, _ = classify_and_persist(db, record, observed_at=observed)
            assert result is expected
        db.commit()
