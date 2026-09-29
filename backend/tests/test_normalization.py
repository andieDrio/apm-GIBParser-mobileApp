from datetime import datetime, timezone

from app.domain.normalization import normalize_record, normalize_records


def sample_item() -> dict:
    return {
        "id": "record-001",
        "login": "user@example.test",
        "dateFirstCompromised": "2026-09-25T08:00:00Z",
        "dateLastCompromised": "2026-09-26T08:00:00+00:00",
        "dateDetected": "2026-09-25T09:00:00Z",
        "dateFirstSeen": "2026-09-25T08:00:00Z",
        "dateLastSeen": "2026-09-26T08:00:00Z",
        "eventCount": 1,
        "parsedLogin": {"domain": "example.test"},
        "password": "secret-value",
        "sourceType": ["example-source"],
        "source": [{"id": "https://t.me/example/1", "name": "TG bot", "type": "Private channel"}],
        "malware": [{"id": "stealer-1", "name": "ExampleStealer"}],
        "service": {"domain": "example.test", "host": "portal.example.test", "url": "https://portal.example.test/login"},
        "events": [{
            "id": "event-1",
            "client": {"ipv4": {"ip": "192.0.2.10", "countryName": "Philippines", "city": "Quezon City", "provider": "Example ISP"}},
            "cnc": {"url": "https://example.test/cnc"},
            "threatActor": "Actor-A",
            "source": {"name": "Private channel", "type": "Telegram"},
        }],
    }


def test_normalizes_verified_shape_and_utc_dates():
    record = normalize_record(sample_item())
    assert record.provider == "groupib"
    assert record.compromise_identity == "provider:record-001"
    assert record.compromised_date == datetime(2026, 9, 25, 8, tzinfo=timezone.utc)
    assert record.last_compromised_date == datetime(2026, 9, 26, 8, tzinfo=timezone.utc)
    assert record.victim_domain == "example.test"
    assert record.victim_ips == ("192.0.2.10",)
    assert record.stealer_families == ("ExampleStealer",)
    assert record.threat_actors == ("Actor-A",)
    assert record.source_links == ("https://t.me/example/1",)


def test_password_is_not_in_observation_fingerprint():
    first = normalize_record(sample_item())
    changed = sample_item()
    changed["password"] = "different-secret"
    second = normalize_record(changed)
    assert first.password != second.password
    assert first.observation_fingerprint == second.observation_fingerprint


def test_provider_id_is_preferred_for_identity():
    item = sample_item()
    item["login"] = "different@example.test"
    assert normalize_record(item).compromise_identity == "provider:record-001"


def test_fallback_identity_is_deterministic_without_provider_id():
    item = sample_item()
    item.pop("id")
    first = normalize_record(item)
    second = normalize_record(dict(item))
    assert first.compromise_identity == second.compromise_identity
    assert first.compromise_identity.startswith("sha256:")


def test_missing_dates_are_null_not_invented():
    item = sample_item()
    for key in ("dateFirstCompromised", "dateLastCompromised", "dateDetected", "dateFirstSeen", "dateLastSeen"):
        item.pop(key, None)
    record = normalize_record(item)
    assert record.compromised_date is None
    assert record.last_compromised_date is None
    assert record.date_detected is None
    assert record.first_seen is None
    assert record.last_seen is None


def test_invalid_date_becomes_quality_warning():
    item = sample_item()
    item["dateDetected"] = "not-a-date"
    record = normalize_record(item)
    assert record.date_detected is None
    assert "invalid_dateDetected" in record.warnings


def test_invalid_ip_is_dropped_and_not_invented():
    item = sample_item()
    item["events"][0]["client"]["ipv4"]["ip"] = "999.999.999.999"
    record = normalize_record(item)
    assert record.victim_ips == ()


def test_records_have_deterministic_descending_last_seen_order():
    first = sample_item()
    second = sample_item()
    second["id"] = "record-002"
    second["dateLastSeen"] = "2026-09-27T08:00:00Z"
    records = normalize_records([first, second])
    assert [record.provider_record_id for record in records] == ["record-002", "record-001"]
