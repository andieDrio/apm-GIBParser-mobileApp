from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CompromiseHistoryModel, ObservationModel, ProviderRecordModel, ReportRecordModel
from app.domain.classification import Classification
from app.domain.normalization import CanonicalIntelligenceRecord


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_history(db: Session, provider: str, identity: str) -> CompromiseHistoryModel | None:
    return db.scalar(select(CompromiseHistoryModel).where(
        CompromiseHistoryModel.provider == provider,
        CompromiseHistoryModel.compromise_identity == identity,
    ))


def _effective_provider_event_date(record: CanonicalIntelligenceRecord) -> datetime | None:
    candidates = [value for value in (
        record.compromised_date, record.last_compromised_date,
        record.date_detected, record.first_seen
    ) if value is not None]
    return min(candidates) if candidates else None


def _classify(existing: CompromiseHistoryModel | None, record: CanonicalIntelligenceRecord,
              observed_at: datetime, newness_window_days: int) -> tuple[Classification, str]:
    if existing is not None:
        if existing.last_observation_fingerprint == record.observation_fingerprint:
            return Classification.REPEAT, "Durable identity exists and observation fingerprint is unchanged."
        return Classification.RESEEN_RECYCLED, "Durable identity exists but the provider observation changed."
    event_date = _effective_provider_event_date(record)
    if event_date is None:
        return Classification.OLD_HISTORICAL, "No usable provider compromise/detection timeline was supplied."
    if event_date > observed_at:
        return Classification.OLD_HISTORICAL, "Provider event time is in the future relative to the evaluation time."
    if event_date >= observed_at - timedelta(days=newness_window_days):
        return Classification.NEW, "Provider compromise/detection timeline is within the seven-day newness policy."
    return Classification.OLD_HISTORICAL, "Provider compromise/detection timeline predates the seven-day newness policy."


def classify_and_persist(db: Session, record: CanonicalIntelligenceRecord, *,
                         observed_at: datetime, newness_window_days: int = 7,
                         run_id: str | None = None) -> tuple[Classification, str]:
    if newness_window_days < 0:
        raise ValueError("newness_window_days cannot be negative.")
    observed_at = _utc(observed_at) or datetime.now(timezone.utc)
    existing = get_history(db, record.provider, record.compromise_identity)
    classification, reason = _classify(existing, record, observed_at, newness_window_days)

    if record.provider_record_id:
        provider_record = db.scalar(select(ProviderRecordModel).where(
            ProviderRecordModel.provider == record.provider,
            ProviderRecordModel.provider_record_id == record.provider_record_id,
        ))
        payload = record.to_json()
        if provider_record is None:
            db.add(ProviderRecordModel(provider=record.provider, provider_record_id=record.provider_record_id,
                                       payload_json=payload, created_at=observed_at))
        else:
            provider_record.payload_json = payload

    if existing is None:
        db.add(CompromiseHistoryModel(
            provider=record.provider, compromise_identity=record.compromise_identity,
            provider_record_id=record.provider_record_id, first_local_seen=observed_at,
            last_local_seen=observed_at, first_provider_seen=record.first_seen,
            last_provider_seen=record.last_seen, last_classification=classification.value,
            last_observation_fingerprint=record.observation_fingerprint, updated_at=observed_at))
    else:
        existing.last_local_seen = observed_at
        existing.last_classification = classification.value
        existing.last_observation_fingerprint = record.observation_fingerprint
        existing.provider_record_id = record.provider_record_id or existing.provider_record_id
        existing.updated_at = observed_at
        if record.first_seen is not None and (existing.first_provider_seen is None or record.first_seen < existing.first_provider_seen):
            existing.first_provider_seen = record.first_seen
        if record.last_seen is not None and (existing.last_provider_seen is None or record.last_seen > existing.last_provider_seen):
            existing.last_provider_seen = record.last_seen

    observation = db.scalar(select(ObservationModel).where(
        ObservationModel.provider == record.provider,
        ObservationModel.compromise_identity == record.compromise_identity,
        ObservationModel.observation_fingerprint == record.observation_fingerprint,
    ))
    if observation is None:
        db.add(ObservationModel(provider=record.provider, compromise_identity=record.compromise_identity,
                                observation_fingerprint=record.observation_fingerprint, observed_at=observed_at))

    if run_id is not None:
        report_record = db.scalar(select(ReportRecordModel).where(
            ReportRecordModel.run_id == run_id,
            ReportRecordModel.provider == record.provider,
            ReportRecordModel.compromise_identity == record.compromise_identity,
        ))
        if report_record is None:
            db.add(ReportRecordModel(run_id=run_id, provider=record.provider,
                                     compromise_identity=record.compromise_identity,
                                     classification=classification.value,
                                     observation_fingerprint=record.observation_fingerprint,
                                     canonical_json=record.to_json()))
    return classification, reason


def upsert_history(db: Session, *, provider: str, identity: str, provider_record_id: str | None,
                   observed_at: datetime, first_provider_seen: datetime | None,
                   last_provider_seen: datetime | None, classification: str,
                   fingerprint: str | None) -> CompromiseHistoryModel:
    observed_at = _utc(observed_at) or datetime.now(timezone.utc)
    first_provider_seen = _utc(first_provider_seen)
    last_provider_seen = _utc(last_provider_seen)
    history = get_history(db, provider, identity)
    if history is None:
        history = CompromiseHistoryModel(provider=provider, compromise_identity=identity,
                                         provider_record_id=provider_record_id,
                                         first_local_seen=observed_at, last_local_seen=observed_at,
                                         first_provider_seen=first_provider_seen,
                                         last_provider_seen=last_provider_seen,
                                         last_classification=classification,
                                         last_observation_fingerprint=fingerprint,
                                         updated_at=observed_at)
        db.add(history)
        return history
    history.first_local_seen = _utc(history.first_local_seen) or observed_at
    history.last_local_seen = observed_at
    history.last_classification = classification
    history.last_observation_fingerprint = fingerprint
    history.provider_record_id = provider_record_id or history.provider_record_id
    if first_provider_seen and (history.first_provider_seen is None or first_provider_seen < history.first_provider_seen):
        history.first_provider_seen = first_provider_seen
    if last_provider_seen and (history.last_provider_seen is None or last_provider_seen > history.last_provider_seen):
        history.last_provider_seen = last_provider_seen
    history.updated_at = observed_at
    return history
