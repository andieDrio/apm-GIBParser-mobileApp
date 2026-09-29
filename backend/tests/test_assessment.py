from datetime import datetime, timezone

from app.domain.assessment import ActivityLevel, AssessmentConfidence, build_assessment
from app.domain.classification import Classification
from app.domain.normalization import normalize_record


def record(record_id: str, date: str, domain: str, malware: str | None = None) -> object:
    item = {
        "id": record_id,
        "login": f"user-{record_id}@{domain}",
        "parsedLogin": {"domain": domain},
        "dateFirstCompromised": date,
        "dateDetected": date,
        "dateFirstSeen": date,
        "dateLastSeen": date,
        "events": [],
    }
    if malware:
        item["malware"] = [{"name": malware, "id": malware.lower()}]
    return normalize_record(item)


def test_no_new_records_is_explicitly_not_safe_claim():
    result = build_assessment(
        run_id="run-1",
        records=[record("old-1", "2026-09-01T00:00:00Z", "example.test")],
        classifications=[Classification.OLD_HISTORICAL],
        normalization_warnings=0,
        baseline_available=True,
        evaluated_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    assert result.activity_level is ActivityLevel.NONE_OBSERVED
    assert "not evidence" in result.key_observations[-1]
    assert result.confidence is AssessmentConfidence.HIGH


def test_new_activity_level_and_facts_are_deterministic():
    records = [
        record("new-1", "2026-09-28T00:00:00Z", "a.example", "StealerA"),
        record("new-2", "2026-09-27T00:00:00Z", "b.example", "StealerA"),
        record("new-3", "2026-09-26T00:00:00Z", "c.example", "StealerB"),
    ]
    result = build_assessment(
        run_id="run-2",
        records=records,
        classifications=[Classification.NEW] * 3,
        normalization_warnings=0,
        baseline_available=True,
        evaluated_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    assert result.activity_level is ActivityLevel.MODERATE
    assert result.confidence is AssessmentConfidence.HIGH
    assert "NEW compromises observed: 3" in result.facts
    assert "StealerA" in result.key_observations[1]
    assert result.recommended_analyst_attention


def test_warning_reduces_confidence_deterministically():
    result = build_assessment(
        run_id="run-3",
        records=[record("new-1", "2026-09-28T00:00:00Z", "a.example")],
        classifications=[Classification.NEW],
        normalization_warnings=1,
        baseline_available=True,
        evaluated_at=datetime(2026, 9, 29, tzinfo=timezone.utc),
    )
    assert result.confidence is AssessmentConfidence.MEDIUM
    assert any("normalization warning" in item for item in result.recommended_analyst_attention)
