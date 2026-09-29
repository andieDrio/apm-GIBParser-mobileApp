from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.history import get_history, upsert_history
from app.db.models import Base, CompromiseHistoryModel, RunModel
from app.db.repository import create_run


def session_factory(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_idempotency_key_returns_same_run(tmp_path: Path):
    SessionLocal = session_factory(tmp_path)
    with SessionLocal() as db:
        first = create_run(db, "mobile-run-001")
        second = create_run(db, "mobile-run-001")
        assert first.run_id == second.run_id
        assert db.scalar(select(RunModel).where(RunModel.idempotency_key == "mobile-run-001")) is not None


def test_history_upsert_preserves_first_seen_and_updates_last_seen(tmp_path: Path):
    SessionLocal = session_factory(tmp_path)
    first = datetime(2026, 9, 1, tzinfo=timezone.utc)
    second = datetime(2026, 9, 2, tzinfo=timezone.utc)
    with SessionLocal() as db:
        upsert_history(
            db,
            provider="groupib",
            identity="identity-1",
            provider_record_id="record-1",
            observed_at=first,
            first_provider_seen=first,
            last_provider_seen=first,
            classification="NEW",
            fingerprint="a" * 64,
        )
        db.commit()
        upsert_history(
            db,
            provider="groupib",
            identity="identity-1",
            provider_record_id="record-1",
            observed_at=second,
            first_provider_seen=first,
            last_provider_seen=second,
            classification="REPEAT",
            fingerprint="b" * 64,
        )
        db.commit()
        history = get_history(db, "groupib", "identity-1")
        assert history is not None
        assert history.first_local_seen == first
        assert history.last_local_seen == second
        assert history.last_classification == "REPEAT"
        assert history.last_observation_fingerprint == "b" * 64
        assert history.first_provider_seen == first
        assert history.last_provider_seen == second


def test_history_identity_is_unique_per_provider(tmp_path: Path):
    SessionLocal = session_factory(tmp_path)
    observed = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with SessionLocal() as db:
        for provider in ("groupib", "other-provider"):
            upsert_history(
                db,
                provider=provider,
                identity="same-identity",
                provider_record_id=None,
                observed_at=observed,
                first_provider_seen=None,
                last_provider_seen=None,
                classification="OLD_HISTORICAL",
                fingerprint=None,
            )
        db.commit()
        assert db.scalar(select(CompromiseHistoryModel).where(CompromiseHistoryModel.compromise_identity == "same-identity").where(CompromiseHistoryModel.provider == "groupib")) is not None
        assert db.scalar(select(CompromiseHistoryModel).where(CompromiseHistoryModel.compromise_identity == "same-identity").where(CompromiseHistoryModel.provider == "other-provider")) is not None
