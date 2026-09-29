from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CompromiseHistoryModel


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_history(db: Session, provider: str, identity: str) -> CompromiseHistoryModel | None:
    return db.scalar(
        select(CompromiseHistoryModel).where(
            CompromiseHistoryModel.provider == provider,
            CompromiseHistoryModel.compromise_identity == identity,
        )
    )


def upsert_history(
    db: Session,
    *,
    provider: str,
    identity: str,
    provider_record_id: str | None,
    observed_at: datetime,
    first_provider_seen: datetime | None,
    last_provider_seen: datetime | None,
    classification: str,
    fingerprint: str | None,
) -> CompromiseHistoryModel:
    observed_at = _utc(observed_at)  # type: ignore[assignment]
    first_provider_seen = _utc(first_provider_seen)
    last_provider_seen = _utc(last_provider_seen)
    history = get_history(db, provider, identity)
    if history is None:
        history = CompromiseHistoryModel(
            provider=provider,
            compromise_identity=identity,
            provider_record_id=provider_record_id,
            first_local_seen=observed_at,
            last_local_seen=observed_at,
            first_provider_seen=first_provider_seen,
            last_provider_seen=last_provider_seen,
            last_classification=classification,
            last_observation_fingerprint=fingerprint,
            updated_at=observed_at,
        )
        db.add(history)
        return history

    history.first_local_seen = _utc(history.first_local_seen) or observed_at
    history.last_local_seen = observed_at
    history.last_classification = classification
    history.last_observation_fingerprint = fingerprint
    history.provider_record_id = provider_record_id or history.provider_record_id
    existing_first = _utc(history.first_provider_seen)
    existing_last = _utc(history.last_provider_seen)
    if first_provider_seen and (existing_first is None or first_provider_seen < existing_first):
        history.first_provider_seen = first_provider_seen
    if last_provider_seen and (existing_last is None or last_provider_seen > existing_last):
        history.last_provider_seen = last_provider_seen
    history.updated_at = observed_at
    return history
