from datetime import datetime, timedelta, timezone

from app.domain.classification import Classification, ClassificationInput, classify


def test_new_within_seven_day_window():
    now = datetime.now(timezone.utc)
    result = classify(ClassificationInput(False, None, "fp", now - timedelta(days=2), None, now))
    assert result == Classification.NEW


def test_old_when_provider_event_is_too_old():
    now = datetime.now(timezone.utc)
    result = classify(ClassificationInput(False, None, "fp", now - timedelta(days=8), None, now))
    assert result == Classification.OLD_HISTORICAL


def test_repeat_when_identity_and_fingerprint_match():
    now = datetime.now(timezone.utc)
    result = classify(ClassificationInput(True, "fp", "fp", None, None, now))
    assert result == Classification.REPEAT


def test_reseen_when_identity_exists_but_fingerprint_changes():
    now = datetime.now(timezone.utc)
    result = classify(ClassificationInput(True, "old", "new", None, None, now))
    assert result == Classification.RESEEN_RECYCLED


def test_future_provider_event_is_not_new():
    now = datetime.now(timezone.utc)
    result = classify(ClassificationInput(False, None, "fp", now + timedelta(minutes=1), None, now))
    assert result == Classification.OLD_HISTORICAL
