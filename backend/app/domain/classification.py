from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum


class Classification(StrEnum):
    NEW = "NEW"
    OLD_HISTORICAL = "OLD_HISTORICAL"
    REPEAT = "REPEAT"
    RESEEN_RECYCLED = "RESEEN_RECYCLED"


@dataclass(frozen=True, slots=True)
class ClassificationInput:
    identity_exists: bool
    previous_fingerprint: str | None
    current_fingerprint: str
    compromised_date: datetime | None
    detected_date: datetime | None
    evaluated_at: datetime
    newness_days: int = 7


def effective_provider_event_date(value: ClassificationInput) -> datetime | None:
    candidates = [d for d in (value.compromised_date, value.detected_date) if d is not None]
    return min(candidates) if candidates else None


def classify(value: ClassificationInput) -> Classification:
    if value.identity_exists:
        return Classification.REPEAT if value.previous_fingerprint == value.current_fingerprint else Classification.RESEEN_RECYCLED
    event_date = effective_provider_event_date(value)
    if event_date is None:
        return Classification.OLD_HISTORICAL
    evaluated_at = value.evaluated_at.astimezone(timezone.utc)
    event_date = event_date.astimezone(timezone.utc)
    if event_date > evaluated_at:
        return Classification.OLD_HISTORICAL
    if event_date >= evaluated_at - timedelta(days=value.newness_days):
        return Classification.NEW
    return Classification.OLD_HISTORICAL
